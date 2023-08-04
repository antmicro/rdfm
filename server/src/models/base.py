from typing import List
from typing import Optional
from typing import Any
from sqlalchemy import ForeignKey
from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

class Base(DeclarativeBase):
    """Base class for all DB entities, required by SQLAlchemy
    """

    type_annotation_map = {
        dict[str, Any]: JSON
    }