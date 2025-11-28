from sqlalchemy import UniqueConstraint, CheckConstraint, DateTime, String, Computed, text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from models.base import Base
import datetime


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("user_id",
                                       "resource",
                                       "permission",
                                       "value",
                                       name="unique_permission"),
                      CheckConstraint("resource_id IS NOT NULL OR resource_name IS NOT NULL",
                                      name="at_least_one_not_null"), )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resource: Mapped[str]
    user_id: Mapped[str]
    resource_id: Mapped[int | None]
    resource_name: Mapped[str | None]
    permission: Mapped[str]
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    value: Mapped[str] = mapped_column(
        String,
        Computed(
            text("COALESCE(CAST(resource_id AS VARCHAR), resource_name)"),
            persisted=True
        ),
        nullable=False
    )
