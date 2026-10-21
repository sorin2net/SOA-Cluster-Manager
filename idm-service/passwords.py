import bcrypt

# bcrypt foloseste doar primii 72 de octeti ai parolei; refuzam parolele mai lungi.
MAX_PASSWORD_BYTES = 72


def is_valid_password(password: str) -> bool:
    return 0 < len(password.encode("utf-8")) <= MAX_PASSWORD_BYTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
