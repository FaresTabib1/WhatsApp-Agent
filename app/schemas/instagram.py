import uuid
from datetime import datetime
from pydantic import BaseModel

class ConnectResponse(BaseModel):
    authorize_url: str

class ConnectionStatusRead(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    provider: str
    provider_account_id: str
    status: str
    username: str | None = None
    account_type: str | None = None
    token_expires_at: str | None = None

class SyncResponse(BaseModel):
    """Résultat d'une synchronisation Instagram."""
    connection_id: uuid.UUID
    total_fetched: int
    created: int
    skipped: int
    failed: int
    token_expired: bool = False
    rate_limited: bool = False
    error: str | None = None