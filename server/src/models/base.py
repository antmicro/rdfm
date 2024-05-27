from typing import Any
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all DB entities, required by SQLAlchemy"""

    type_annotation_map = {dict[str, Any]: JSON}
