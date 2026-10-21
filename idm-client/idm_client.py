from dataclasses import dataclass

import grpc

import idm_pb2
import idm_pb2_grpc

ROLE_TO_PROTO = {"administrator": idm_pb2.ADMINISTRATOR, "maintainer": idm_pb2.MAINTAINER}
PROTO_TO_ROLE = {value: key for key, value in ROLE_TO_PROTO.items()}


@dataclass(frozen=True)
class Account:
    uid: str
    username: str
    role: str
    is_active: bool


@dataclass(frozen=True)
class TokenInfo:
    sub: str
    role: str


class IdmClient:
    """Biblioteca client pentru serviciul IDM. Erorile serverului sunt aruncate ca grpc.RpcError."""

    def __init__(self, address: str = "localhost:50051"):
        self._channel = grpc.insecure_channel(address)
        self._stub = idm_pb2_grpc.IdentityServiceStub(self._channel)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self) -> None:
        self._channel.close()

    def login(self, username: str, password: str) -> str:
        response = self._stub.Login(idm_pb2.LoginRequest(username=username, password=password))
        return response.token

    def create_account(self, token: str, username: str, role: str) -> str:
        request = idm_pb2.CreateAccountRequest(
            token=token,
            username=username,
            role=ROLE_TO_PROTO.get(role, idm_pb2.ROLE_UNSPECIFIED),
        )
        return self._stub.CreateAccount(request).uid

    def activate_account(self, username: str, password: str) -> None:
        self._stub.ActivateAccount(idm_pb2.ActivateAccountRequest(username=username, password=password))

    def list_accounts(self, token: str) -> list[Account]:
        response = self._stub.ListAccounts(idm_pb2.ListAccountsRequest(token=token))
        return [
            Account(account.uid, account.username, PROTO_TO_ROLE[account.role], account.is_active)
            for account in response.accounts
        ]

    def deactivate_account(self, token: str, username: str) -> None:
        self._stub.DeactivateAccount(idm_pb2.DeactivateAccountRequest(token=token, username=username))

    def validate_token(self, token: str) -> TokenInfo:
        response = self._stub.ValidateToken(idm_pb2.ValidateTokenRequest(token=token))
        return TokenInfo(response.sub, PROTO_TO_ROLE[response.role])

    def destroy_token(self, token: str) -> None:
        self._stub.DestroyToken(idm_pb2.DestroyTokenRequest(token=token))
