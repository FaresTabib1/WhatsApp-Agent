import os
from datetime import datetime, timedelta, timezone
import bcrypt
from jose import JWTError, jwt

# --- Config ---
# Charge depuis l'environnement. Valeur par défaut uniquement pour les tests.
SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me-in-production")
if os.environ.get("ENVIRONMENT") == "production" and SECRET_KEY == "change-me-in-production":
    raise RuntimeError("SECRET_KEY must be configured in production")

ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
    os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

# --- Password ---


def hash_password(plain: str) -> str:
    pwd_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False

# --- JWT ---

def create_access_token(subject: str) -> str:
    """Crée un JWT avec le sub = user_id (UUID en string)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """
    Décode un JWT et retourne le sub (user_id).
    Retourne None si le token est invalide ou expiré.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
