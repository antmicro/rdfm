from typing import List, Optional
import models.action_log
from sqlalchemy import select, update, delete, desc
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class ActionLogsDB:
    """Wrapper class for managing actions assigned to devices"""

    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db

    def fetch_device_queue(self, mac_address: str) -> List[models.action_log.ActionLog]:
        """Fetches a list of pending actions assigned to a device,
        sorted by their creation date (oldest first).
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    select(models.action_log.ActionLog)
                    .where(models.action_log.ActionLog.mac_address == mac_address)
                    .where(models.action_log.ActionLog.status == "pending")
                    .order_by(models.action_log.ActionLog.created)
                )
                actions = session.scalars(stmt)
                if actions is None:
                    return []
                return [x for x in actions]
        except Exception as e:
            print("Action queue fetch failed:", repr(e))
            return []

    def fetch_device_log(self, mac_address: str) -> List[models.action_log.ActionLog]:
        """Fetches a list of all actions assigned to a device,
        sorted by their creation date (newest first).
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    select(models.action_log.ActionLog)
                    .where(models.action_log.ActionLog.mac_address == mac_address)
                    .order_by(desc(models.action_log.ActionLog.created))
                )
                actions = session.scalars(stmt)
                if actions is None:
                    return []
                return [x for x in actions]
        except Exception as e:
            print("Action log fetch failed:", repr(e))
            return []

    def insert(self, action: models.action_log.ActionLog):
        """Add an action execution to the database"""
        with Session(self.engine) as session:
            session.add(action)
            session.commit()
            session.refresh(action)
            return action.id

    def update_status(self, id: int, status: str):
        """Update the status of a specified action.
        """
        with Session(self.engine) as session:
            stmt = (
                update(models.action_log.ActionLog)
                .values(status=status)
                .where(models.action_log.ActionLog.id == id)
            )
            session.execute(stmt)
            session.commit()
