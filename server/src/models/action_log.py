import datetime
from typing import Optional
from models.base import Base
from sqlalchemy import JSON, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[str] = mapped_column(primary_key=True)
    action_id: Mapped[str] = mapped_column(Text)
    mac_address: Mapped[str] = mapped_column(Text)
    created: Mapped[datetime.datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(Text)
    download_url: Mapped[Optional[str]] = mapped_column(Text)
