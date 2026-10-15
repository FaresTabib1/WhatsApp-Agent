import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, ForeignKeyConstraint, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ImportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class InstagramPost(Base):
    __tablename__ = "instagram_posts"

    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "external_post_id",
            name="uq_instagram_posts_connection_external",
        ),
        # Contrainte UNIQUE composite requise comme cible de la FK composite
        # products(source_post_id, business_id) → instagram_posts(id, business_id).
        # Garantit qu'un produit ne peut référencer qu'une publication de sa propre boutique.
        UniqueConstraint(
            "id",
            "business_id",
            name="uq_instagram_posts_id_business_id",
        ),
        # Clé étrangère composite garantissant l'isolation cross-tenant :
        # Une publication ne peut référencer qu'une connexion appartenant à la même boutique.
        ForeignKeyConstraint(
            ["connection_id", "business_id"],
            ["connections.id", "connections.business_id"],
            ondelete="CASCADE",
            name="fk_instagram_posts_connection_composite",
        ),
        # Index business_id : lookup par boutique (isolation multi-tenant)
        Index("ix_instagram_posts_business_id", "business_id"),
        # Index connection_id : lookup par connexion source
        Index("ix_instagram_posts_connection_id", "connection_id"),
        # Index external_post_id : idempotence lors de l'import
        Index("ix_instagram_posts_external_post_id", "external_post_id"),
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
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    # Identifiant de la publication dans l'API Instagram Graph (ex: "17854360229135492")
    external_post_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    caption: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # URL fournie par l'API Instagram au moment de l'import.
    # ATTENTION : les URLs de médias Instagram sont éphémères (expiration ~1h).
    # Ce champ ne constitue pas un stockage durable du média.
    # Le téléchargement vers un stockage permanent (ex: GCS) est hors scope MVP.
    media_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        default=None,
    )
    permalink: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        default=None,
    )
    # Horodatage de publication sur Instagram (fourni par l'API, peut être absent)
    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    import_status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, name="import_status"),
        nullable=False,
        default=ImportStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # Pas de updated_at : un post importé n'est pas modifié,
    # seul import_status évolue (traçable via created_at + import_status).

    business: Mapped["Business"] = relationship(  # noqa: F821
        "Business",
        foreign_keys=[business_id],
        back_populates="instagram_posts",
    )
    connection: Mapped["Connection"] = relationship(  # noqa: F821
        "Connection",
        primaryjoin="InstagramPost.connection_id == Connection.id",
        foreign_keys="[InstagramPost.connection_id]",
        back_populates="instagram_posts",
    )
    # Produits extraits depuis cette publication.
    # ISOLATION : garantie au niveau DB par la FK composite
    # products(source_post_id, business_id) → instagram_posts(id, business_id).
    products: Mapped[list["Product"]] = relationship(  # noqa: F821
        "Product",
        primaryjoin="Product.source_post_id == InstagramPost.id",
        foreign_keys="[Product.source_post_id]",
        back_populates="source_post",
    )

    def __init__(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        if "import_status" not in kwargs:
            kwargs["import_status"] = ImportStatus.pending
        super().__init__(**kwargs)