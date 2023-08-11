from typing import List
from typing import Optional, Any
from sqlalchemy import ForeignKey
from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime

from models.base import Base
import models.package

class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    package_id: Mapped[Optional[int]] = mapped_column(ForeignKey(models.package.Package.id, ondelete="RESTRICT"))
    info: Mapped[dict[str, Any]] = mapped_column(JSON)