import argparse
from getpass import getpass

import grpc

from idm_client import IdmClient


class Console:
    def __init__(self, client: IdmClient):
        self._client = client
        self._token = ""
        self._actions = {
            "1": ("Login", self._login),
            "2": ("Activare cont", self._activate_account),
            "3": ("Creare cont", self._create_account),
            "4": ("Listare conturi", self._list_accounts),
            "5": ("Dezactivare cont", self._deactivate_account),
            "6": ("Validare token", self._validate_token),
            "7": ("Logout (distrugere token)", self._destroy_token),
            "8": ("Seteaza manual token-ul curent", self._set_token),
        }

    def run(self) -> None:
        while True:
            self._print_menu()
            choice = input("Optiune: ").strip()
            if choice == "0":
                return
            if choice not in self._actions:
                print("Optiune invalida")
                continue

            _, action = self._actions[choice]
            try:
                action()
            except grpc.RpcError as error:
                print(f"Eroare {error.code().name}: {error.details()}")

    def _print_menu(self) -> None:
        current = f"{self._token[:25]}..." if self._token else "(niciunul)"
        print(f"\n=== Client IDM ===   token curent: {current}")
        for key, (label, _) in self._actions.items():
            print(f"  {key}. {label}")
        print("  0. Iesire")

    def _login(self) -> None:
        username = input("Username: ")
        password = getpass("Parola: ")
        self._token = self._client.login(username, password)
        print(f"Autentificat. Token:\n{self._token}")

    def _activate_account(self) -> None:
        username = input("Username: ")
        password = getpass("Parola initiala: ")
        self._client.activate_account(username, password)
        print("Cont activat. Te poti autentifica.")

    def _create_account(self) -> None:
        username = input("Username nou: ")
        role = input("Rol (administrator/maintainer): ").strip()
        uid = self._client.create_account(self._token, username, role)
        print(f"Cont creat cu uid {uid} (inactiv pana la activare)")

    def _list_accounts(self) -> None:
        accounts = self._client.list_accounts(self._token)
        print(f"{'UID':36}  {'USERNAME':25}  {'ROL':13}  ACTIV")
        for account in accounts:
            print(f"{account.uid:36}  {account.username:25}  {account.role:13}  {'da' if account.is_active else 'nu'}")

    def _deactivate_account(self) -> None:
        username = input("Username de dezactivat: ")
        self._client.deactivate_account(self._token, username)
        print("Cont dezactivat.")

    def _validate_token(self) -> None:
        info = self._client.validate_token(self._token)
        print(f"Token valid. sub = {info.sub}, role = {info.role}")

    def _destroy_token(self) -> None:
        self._client.destroy_token(self._token)
        self._token = ""
        print("Token distrus (pus in blacklist).")

    def _set_token(self) -> None:
        self._token = input("Token: ").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Client consola pentru serviciul IDM")
    parser.add_argument("--address", default="localhost:50051", help="adresa serviciului IDM")
    args = parser.parse_args()

    with IdmClient(args.address) as client:
        Console(client).run()


if __name__ == "__main__":
    main()
