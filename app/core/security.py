import os
import secrets
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
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

# --- OAuth state (protection CSRF) ---

_OAUTH_STATE_EXPIRE_MINUTES = 10
_OAUTH_STATE_PURPOSE = "instagram_oauth"

def create_oauth_state(business_id: str, user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=_OAUTH_STATE_EXPIRE_MINUTES)
    payload = {
        "purpose": _OAUTH_STATE_PURPOSE,
        "business_id": business_id,
        "user_id": user_id,
        "nonce": secrets.token_hex(16),
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
class OAuthStateData:
    def __init__(self, business_id: str, user_id: str):
        self.business_id = business_id
        self.user_id = user_id


def decode_oauth_state(state: str) -> OAuthStateData | None:

    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != _OAUTH_STATE_PURPOSE:
            return None
        business_id = payload.get("business_id")
        user_id = payload.get("user_id")
        if not business_id or not user_id:
            return None
        return OAuthStateData(business_id=business_id, user_id=user_id)
    except JWTError:
        return None
