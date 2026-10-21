import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Variabila de mediu {name} lipseste (vezi .env.example)")
    return value


@dataclass(frozen=True)
class Config:
    grpc_port: int
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    jwt_secret: str
    jwt_issuer: str
    token_ttl_seconds: int


def load_config() -> Config:
    return Config(
        grpc_port=int(os.getenv("IDM_GRPC_PORT", "50051")),
        db_host=os.getenv("MARIADB_HOST", "127.0.0.1"),
        db_port=int(os.getenv("MARIADB_PORT", "3306")),
        db_name=os.getenv("MARIADB_DATABASE", "idm"),
        db_user=_required("MARIADB_USER"),
        db_password=_required("MARIADB_PASSWORD"),
        jwt_secret=_required("IDM_JWT_SECRET"),
        jwt_issuer=_required("IDM_ISSUER"),
        token_ttl_seconds=int(os.getenv("IDM_TOKEN_TTL_SECONDS", "3600")),
    )
