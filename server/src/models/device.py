from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import Text, DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
import datetime

from models.base import Base
import models.group


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    last_access: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=True
    )
    name: Mapped[str] = mapped_column(Text)
    mac_address: Mapped[str] = mapped_column(Text)
    capabilities: Mapped[str] = mapped_column(Text)
    device_metadata: Mapped[str] = mapped_column(Text)
    public_key: Mapped[Optional[str]] = mapped_column(Text)


class DeviceGroupAssignment(Base):
    __tablename__ = "devices_groups"
    device_id: Mapped[int] = mapped_column(
            ForeignKey(Device.id, ondelete="RESTRICT"),
            primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
            ForeignKey(models.group.Group.id, ondelete="RESTRICT"),
            primary_key=True
    )


class DeviceTag(Base):
    __tablename__ = "devices_tags"
    device_id: Mapped[int] = mapped_column(
            ForeignKey(Device.id, ondelete="RESTRICT"),
            primary_key=True
    )
    tag: Mapped[int] = mapped_column(Text, primary_key=True)
