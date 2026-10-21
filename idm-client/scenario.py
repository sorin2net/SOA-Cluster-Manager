"""Verifica automat toate metodele serviciului IDM si codurile de eroare cerute."""
import argparse
import base64
import json
import os
import uuid
from getpass import getpass

import grpc

from idm_client import IdmClient

OK = None  # rezultat asteptat: apel reusit
UNAUTHENTICATED = grpc.StatusCode.UNAUTHENTICATED
PERMISSION_DENIED = grpc.StatusCode.PERMISSION_DENIED
ALREADY_EXISTS = grpc.StatusCode.ALREADY_EXISTS
NOT_FOUND = grpc.StatusCode.NOT_FOUND


class Checker:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def call(self, description: str, expected: grpc.StatusCode | None, function):
        """Executa apelul si verifica rezultatul. Returneaza valoarea intoarsa daca apelul a reusit."""
        try:
            result = function()
            received = OK
        except grpc.RpcError as error:
            result = None
            received = error.code()

        self.check(description, received == expected,
                   f"asteptat {_name(expected)}, primit {_name(received)}")
        return result

    def check(self, description: str, condition: bool, failure_details: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"  [OK]   {description}")
        else:
            self.failed += 1
            print(f"  [FAIL] {description} -> {failure_details}")


def _name(code: grpc.StatusCode | None) -> str:
    return "OK" if code is None else code.name


def forge_admin_token(token: str) -> str:
    """Schimba rolul din payload in 'administrator', pastrand semnatura originala."""
    header, payload, signature = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["role"] = "administrator"
    forged_payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"{header}.{forged_payload}.{signature}"


def run(client: IdmClient, admin_password: str) -> Checker:
    checker = Checker()
    maintainer = f"maintainer-{uuid.uuid4().hex[:6]}"

    print("Pregatire")
    try:
        client.activate_account("admin", admin_password)
        print("  contul 'admin' a fost activat acum")
    except grpc.RpcError as error:
        if error.code() != PERMISSION_DENIED:
            raise

    print("Login")
    checker.call("parola gresita -> UNAUTHENTICATED", UNAUTHENTICATED,
                 lambda: client.login("admin", "parola-gresita"))
    checker.call("utilizator inexistent -> UNAUTHENTICATED", UNAUTHENTICATED,
                 lambda: client.login("nu-exista", "x"))
    admin_token = checker.call("admin cu parola corecta -> token", OK,
                               lambda: client.login("admin", admin_password))
    if admin_token is None:
        raise SystemExit("Fara token de administrator nu se poate continua (parola admin corecta?)")

    print("Validare token")
    info = checker.call("token admin valid", OK, lambda: client.validate_token(admin_token))
    checker.check("token-ul contine role = administrator", info is not None and info.role == "administrator")

    print("Creare cont")
    uid = checker.call(f"creare '{maintainer}'", OK,
                       lambda: client.create_account(admin_token, maintainer, "maintainer"))
    checker.check("uid-ul generat este UUIDv7", uid is not None and uuid.UUID(uid).version == 7)
    checker.call("username duplicat -> ALREADY_EXISTS", ALREADY_EXISTS,
                 lambda: client.create_account(admin_token, maintainer, "maintainer"))

    print("Activare cont")
    checker.call("login inainte de activare -> PERMISSION_DENIED", PERMISSION_DENIED,
                 lambda: client.login(maintainer, "parola-maintainer"))
    checker.call("activare cu parola initiala", OK,
                 lambda: client.activate_account(maintainer, "parola-maintainer"))
    checker.call("a doua activare (cont activ) -> PERMISSION_DENIED", PERMISSION_DENIED,
                 lambda: client.activate_account(maintainer, "alta-parola"))
    maintainer_token = checker.call("login dupa activare -> token", OK,
                                    lambda: client.login(maintainer, "parola-maintainer"))

    print("Autorizare (operatii de administrator)")
    checker.call("listare cu token de maintainer -> PERMISSION_DENIED", PERMISSION_DENIED,
                 lambda: client.list_accounts(maintainer_token))
    accounts = checker.call("listare cu token de admin", OK, lambda: client.list_accounts(admin_token))
    checker.check("lista contine noul cont, activ",
                  accounts is not None and any(a.username == maintainer and a.is_active for a in accounts))

    print("Token falsificat (rol schimbat in payload)")
    forged = forge_admin_token(maintainer_token)
    checker.call("listare cu token falsificat -> PERMISSION_DENIED", PERMISSION_DENIED,
                 lambda: client.list_accounts(forged))
    checker.call("token-ul falsificat e in blacklist -> UNAUTHENTICATED", UNAUTHENTICATED,
                 lambda: client.validate_token(forged))

    print("Dezactivare cont")
    checker.call("dezactivare cont inexistent -> NOT_FOUND", NOT_FOUND,
                 lambda: client.deactivate_account(admin_token, "nu-exista"))
    checker.call(f"dezactivare '{maintainer}'", OK,
                 lambda: client.deactivate_account(admin_token, maintainer))
    checker.call("login cont dezactivat -> PERMISSION_DENIED", PERMISSION_DENIED,
                 lambda: client.login(maintainer, "parola-maintainer"))
    checker.call("reactivare cont blocat -> PERMISSION_DENIED", PERMISSION_DENIED,
                 lambda: client.activate_account(maintainer, "parola-noua"))

    print("Logout (distrugere token)")
    checker.call("distrugere token maintainer", OK, lambda: client.destroy_token(maintainer_token))
    checker.call("validare token distrus -> UNAUTHENTICATED", UNAUTHENTICATED,
                 lambda: client.validate_token(maintainer_token))
    checker.call("a doua distrugere -> UNAUTHENTICATED", UNAUTHENTICATED,
                 lambda: client.destroy_token(maintainer_token))
    checker.call("distrugere token admin", OK, lambda: client.destroy_token(admin_token))
    checker.call("operatie admin dupa logout -> PERMISSION_DENIED", PERMISSION_DENIED,
                 lambda: client.list_accounts(admin_token))

    return checker


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", default="localhost:50051", help="adresa serviciului IDM")
    args = parser.parse_args()

    admin_password = os.getenv("IDM_ADMIN_PASSWORD") or getpass("Parola contului 'admin': ")
    with IdmClient(args.address) as client:
        checker = run(client, admin_password)

    print(f"\nRezultat: {checker.passed} verificari reusite, {checker.failed} esuate")
    raise SystemExit(1 if checker.failed else 0)


if __name__ == "__main__":
    main()
