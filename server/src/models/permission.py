from sqlalchemy import UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from models.base import Base
import datetime


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("user_id",
                                       "resource",
                                       "resource_id",
                                       "permission",
                                       name="unique_permission"), )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resource: Mapped[str]
    user_id: Mapped[str]
    resource_id: Mapped[int]
    permission: Mapped[str]
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
