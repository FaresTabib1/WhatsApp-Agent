"""
Dependency FastAPI : get_current_user().

Point de migration Supabase :
  Remplacer le corps de get_current_user() par la validation
  du JWT Supabase. Signature de retour inchangée : -> User.
  Tous les endpoints qui utilisent Depends(get_current_user)
  n'auront pas à changer.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Valide le JWT Bearer et retourne l'utilisateur correspondant.
    Lève HTTP 401 si le token est absent, invalide ou expiré.
    Lève HTTP 401 si l'utilisateur n'existe plus en base.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id_str = decode_access_token(credentials.credentials)
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = await session.get(User, user_id)
    if user is None:
        raise credentials_exception

    return user
