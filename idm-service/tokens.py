import time
import uuid

import jwt

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["iss", "sub", "exp", "jti", "role"]
ROLES = ("administrator", "maintainer")


class InvalidTokenError(Exception):
    pass


class TokenManager:
    def __init__(self, secret: str, issuer: str, ttl_seconds: int):
        self._secret = secret
        self._issuer = issuer
        self._ttl_seconds = ttl_seconds
        self._blacklist: dict[str, str] = {}  # token -> motivul invalidarii

    def issue(self, uid: str, role: str) -> str:
        claims = {
            "iss": self._issuer,
            "sub": uid,
            "exp": int(time.time()) + self._ttl_seconds,
            "jti": str(uuid.uuid4()),
            "role": role,
        }
        return jwt.encode(claims, self._secret, algorithm=ALGORITHM)

    def validate(self, token: str) -> dict:
        """Returneaza claim-urile token-ului; un token invalid ajunge in blacklist."""
        if token in self._blacklist:
            raise InvalidTokenError(f"Token-ul este in blacklist ({self._blacklist[token]})")

        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                issuer=self._issuer,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.ExpiredSignatureError:
            self._blacklist[token] = "expirat"
            raise InvalidTokenError("Token-ul a expirat")
        except jwt.InvalidTokenError as error:
            self._blacklist[token] = "invalid"
            raise InvalidTokenError(f"Token invalid: {error}")

        if claims["role"] not in ROLES:
            self._blacklist[token] = "invalid"
            raise InvalidTokenError("Token invalid: rol necunoscut")
        return claims

    def revoke(self, token: str) -> None:
        self.validate(token)
        self._blacklist[token] = "logout"
