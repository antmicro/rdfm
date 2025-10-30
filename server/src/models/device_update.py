import datetime
from models.base import Base
from sqlalchemy import JSON, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column


class DeviceUpdate(Base):
    __tablename__ = "device_updates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mac_address: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    version: Mapped[str] = mapped_column(Text)
    progress: Mapped[str] = mapped_column(Integer)
