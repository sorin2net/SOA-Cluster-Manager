import uuid
from dataclasses import dataclass

import pymysql

DUPLICATE_ENTRY = 1062


class UsernameTakenError(Exception):
    pass


@dataclass(frozen=True)
class User:
    uid: uuid.UUID
    username: str
    password_hash: str | None
    role: str
    is_active: bool


class UserRepository:
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self._connection_args = dict(
            host=host, port=port, database=database, user=user, password=password,
            autocommit=True,
        )

    def _connect(self) -> pymysql.Connection:
        return pymysql.connect(**self._connection_args)

    def find_by_username(self, username: str) -> User | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT uid, username, password, role, is_active FROM Users WHERE username = %s",
                (username,),
            )
            row = cursor.fetchone()
        return _to_user(row) if row else None

    def list_all(self) -> list[User]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT uid, username, password, role, is_active FROM Users ORDER BY uid")
            rows = cursor.fetchall()
        return [_to_user(row) for row in rows]

    def create(self, uid: uuid.UUID, username: str, role: str) -> None:
        try:
            with self._connect() as connection, connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO Users (uid, username, password, role, is_active) "
                    "VALUES (%s, %s, NULL, %s, FALSE)",
                    (uid.bytes, username, role),
                )
        except pymysql.IntegrityError as error:
            if error.args[0] == DUPLICATE_ENTRY:
                raise UsernameTakenError(username) from error
            raise

    def activate(self, username: str, password_hash: str) -> bool:
        # Conditiile din WHERE garanteaza ca un cont nu poate fi activat de doua ori,
        # chiar daca doua cereri ajung in acelasi timp.
        with self._connect() as connection, connection.cursor() as cursor:
            updated = cursor.execute(
                "UPDATE Users SET password = %s, is_active = TRUE "
                "WHERE username = %s AND is_active = FALSE AND password IS NULL",
                (password_hash, username),
            )
        return updated == 1

    def deactivate(self, username: str) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("UPDATE Users SET is_active = FALSE WHERE username = %s", (username,))


def _to_user(row: tuple) -> User:
    uid, username, password_hash, role, is_active = row
    return User(uuid.UUID(bytes=uid), username, password_hash, role, bool(is_active))
