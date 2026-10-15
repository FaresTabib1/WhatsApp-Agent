import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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

    members: Mapped[list["BusinessMember"]] = relationship(  # noqa: F821
        "BusinessMember",
        back_populates="business",
    )

    connections: Mapped[list["Connection"]] = relationship(  # noqa: F821
        "Connection",
        back_populates="business",
    )

    products: Mapped[list["Product"]] = relationship(  # noqa: F821
        "Product",
        back_populates="business",
    )
    
    instagram_posts: Mapped[list["InstagramPost"]] = relationship(  # noqa: F821
        "InstagramPost",
        back_populates="business",
    )

    def __init__(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)
