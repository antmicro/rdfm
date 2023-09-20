from typing import List
from typing import Optional
from typing import Any
from sqlalchemy import ForeignKey
from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import datetime
import models.base


class Package(models.base.Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    driver: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(Text)
    info: Mapped[dict[str, Any]] = mapped_column(JSON)
