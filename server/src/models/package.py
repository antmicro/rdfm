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

""" Metadata key for currently running software version """
META_SOFT_VER = "rdfm.software.version"

""" Metadata key for the device type a package is compatible with """
META_DEVICE_TYPE = "rdfm.hardware.devtype"

class Package(models.base.Base):
    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    driver: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(Text)
    info: Mapped[dict[str, Any]] = mapped_column(JSON)
