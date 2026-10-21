import uuid

import grpc

import idm_pb2
import idm_pb2_grpc
from passwords import MAX_PASSWORD_BYTES, hash_password, is_valid_password, verify_password
from tokens import InvalidTokenError, TokenManager
from users_repository import UserRepository, UsernameTakenError

MAX_USERNAME_LENGTH = 255

ROLE_TO_PROTO = {"administrator": idm_pb2.ADMINISTRATOR, "maintainer": idm_pb2.MAINTAINER}
PROTO_TO_ROLE = {value: key for key, value in ROLE_TO_PROTO.items()}


class IdentityService(idm_pb2_grpc.IdentityServiceServicer):
    # context.abort() arunca o exceptie: metoda se opreste acolo,
    # iar clientul primeste codul de stare gRPC impreuna cu mesajul.

    def __init__(self, users: UserRepository, tokens: TokenManager):
        self._users = users
        self._tokens = tokens

    def Login(self, request, context):
        user = self._users.find_by_username(request.username)
        if user is None:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Nume de utilizator sau parola gresita")
        if not user.is_active:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Contul nu este activ")
        if not is_valid_password(request.password) or not verify_password(request.password, user.password_hash):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "Nume de utilizator sau parola gresita")

        token = self._tokens.issue(str(user.uid), user.role)
        return idm_pb2.LoginResponse(token=token)

    def CreateAccount(self, request, context):
        self._require_admin(request.token, context)
        if not 0 < len(request.username) <= MAX_USERNAME_LENGTH:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                          f"Numele de utilizator trebuie sa aiba intre 1 si {MAX_USERNAME_LENGTH} caractere")
        if request.role not in PROTO_TO_ROLE:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "Rolul trebuie sa fie ADMINISTRATOR sau MAINTAINER")

        uid = uuid.uuid7()
        try:
            self._users.create(uid, request.username, PROTO_TO_ROLE[request.role])
        except UsernameTakenError:
            context.abort(grpc.StatusCode.ALREADY_EXISTS, f"Utilizatorul '{request.username}' exista deja")
        return idm_pb2.CreateAccountResponse(uid=str(uid))

    def ActivateAccount(self, request, context):
        user = self._users.find_by_username(request.username)
        if user is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Utilizatorul '{request.username}' nu exista")
        if user.is_active:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Contul este deja activ")
        if user.password_hash is not None:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Contul este blocat (a fost dezactivat)")
        if not is_valid_password(request.password):
            context.abort(grpc.StatusCode.INVALID_ARGUMENT,
                          f"Parola trebuie sa aiba intre 1 si {MAX_PASSWORD_BYTES} octeti")

        if not self._users.activate(request.username, hash_password(request.password)):
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Contul a fost activat intre timp")
        return idm_pb2.ActivateAccountResponse()

    def ListAccounts(self, request, context):
        self._require_admin(request.token, context)
        accounts = [
            idm_pb2.Account(
                uid=str(user.uid),
                username=user.username,
                role=ROLE_TO_PROTO[user.role],
                is_active=user.is_active,
            )
            for user in self._users.list_all()
        ]
        return idm_pb2.ListAccountsResponse(accounts=accounts)

    def DeactivateAccount(self, request, context):
        self._require_admin(request.token, context)
        if self._users.find_by_username(request.username) is None:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Utilizatorul '{request.username}' nu exista")

        self._users.deactivate(request.username)
        return idm_pb2.DeactivateAccountResponse()

    def ValidateToken(self, request, context):
        try:
            claims = self._tokens.validate(request.token)
        except InvalidTokenError as error:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, str(error))
        return idm_pb2.ValidateTokenResponse(sub=claims["sub"], role=ROLE_TO_PROTO[claims["role"]])

    def DestroyToken(self, request, context):
        try:
            self._tokens.revoke(request.token)
        except InvalidTokenError as error:
            context.abort(grpc.StatusCode.UNAUTHENTICATED, str(error))
        return idm_pb2.DestroyTokenResponse()

    def _require_admin(self, token: str, context) -> None:
        try:
            claims = self._tokens.validate(token)
        except InvalidTokenError as error:
            context.abort(grpc.StatusCode.PERMISSION_DENIED, str(error))
        if claims["role"] != "administrator":
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Operatie permisa doar administratorilor")
