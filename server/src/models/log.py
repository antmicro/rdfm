from sqlalchemy import ForeignKey
from sqlalchemy import Text, DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
import datetime

from models.base import Base
from models.device import Device


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    device_id: Mapped[int] = mapped_column(
        ForeignKey(Device.id, ondelete="RESTRICT")
    )
    device_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime)
    name: Mapped[str] = mapped_column(Text)
    entry: Mapped[str] = mapped_column(Text)
