import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class MemberRole(str, enum.Enum):
    owner = "owner"
    member = "member"
class BusinessMember(Base):
    __tablename__ = "business_members"

    __table_args__ = (
        UniqueConstraint(
            "business_id", "user_id", name="uq_business_members_business_user"
        ),
        Index("ix_business_members_business_id", "business_id"),
        Index("ix_business_members_user_id", "user_id"),
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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MemberRole | None] = mapped_column(
        Enum(MemberRole, name="member_role"),
        nullable=True,
        server_default=MemberRole.member.value,
        default=MemberRole.member,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    business: Mapped["Business"] = relationship(  # noqa: F821
        "Business",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="memberships",
    )

    def __init__(self, **kwargs):
        if kwargs.get("id") is None:
            kwargs["id"] = uuid.uuid4()
        if "role" not in kwargs:
            kwargs["role"] = MemberRole.member
        super().__init__(**kwargs)