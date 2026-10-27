import datetime
from models.base import Base
from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import models.action_log


class GeneratedFile(Base):
    __tablename__ = "generated_files"

    exec_id: Mapped[str] = mapped_column(ForeignKey(models.action_log.ActionLog.id,
                                                    ondelete="CASCADE"),
                                         primary_key=True)
    filename: Mapped[str] = mapped_column(primary_key=True)
    download_url: Mapped[str] = mapped_column(Text)
