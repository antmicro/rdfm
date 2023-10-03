import datetime
from models.base import Base
from sqlalchemy import JSON, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column


class Registration(Base):
    __tablename__ = "registrations"

    mac_address: Mapped[str] = mapped_column(Text, primary_key=True)
    public_key: Mapped[str] = mapped_column(Text, primary_key=True)
    info: Mapped[dict[str, str]] = mapped_column(JSON)
    last_appeared: Mapped[datetime.datetime] = mapped_column(DateTime)
