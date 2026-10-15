import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ConnectionProvider(str, enum.Enum):
    instagram = "instagram"
    whatsapp = "whatsapp"


class ConnectionStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"


class Connection(Base):
    __tablename__ = "connections"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_account_id",
            name="uq_connections_provider_account",
        ),
        # Contrainte UNIQUE composite requise comme cible de la FK composite
        # instagram_posts(connection_id, business_id) → connections(id, business_id).
        UniqueConstraint(
            "id",
            "business_id",
            name="uq_connections_id_business_id",
        ),
        Index("ix_connections_business_id", "business_id"),
        Index("ix_connections_provider_account_id", "provider_account_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[ConnectionProvider] = mapped_column(
        Enum(ConnectionProvider, name="connection_provider"),
        nullable=False,
    )
    provider_account_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, name="connection_status"),
        nullable=False,
        server_default=ConnectionStatus.inactive.value,
    )
    # Référence Secret Manager (ex: "projects/123/secrets/wa-token-abc/versions/latest")
    # Jamais un token en clair.
    secret_ref: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        default=None,
    )
   
    meta: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    business: Mapped["Business"] = relationship( 
        "Business",
        back_populates="connections",
    )

    instagram_posts: Mapped[list["InstagramPost"]] = relationship(  # noqa: F821
        "InstagramPost",
        primaryjoin="Connection.id == InstagramPost.connection_id",
        foreign_keys="[InstagramPost.connection_id]",
        back_populates="connection",
        passive_deletes=True,
    )

    def __init__(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)
