from typing import TypeVar, Optional, List, Generator
import datetime
import models.log
from sqlalchemy import select, desc, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import server


class LogsDB:
    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db

    def fetch_one(self, identifier: int) -> Optional[models.log.Log]:
        """Fetch a log with the given identifier.

        Args:
            identifier: numeric ID of a log

        Returns:
            A log with the specified ID, None if not found
        """
        with Session(self.engine) as session:
            stmt = select(models.log.Log).where(
                models.log.Log.id == identifier
            )
            return session.scalar(stmt)

    def fetch(self, device_identifiers: Optional[List[int]],
              names: Optional[List[str]],
              time_from: Optional[datetime.datetime],
              time_to: Optional[datetime.datetime]) -> List[models.log.Log]:
        """Fetch any amount of logs based on the specified arguments.

        Args:
            device_identifiers: a list of numeric IDs of
            devices associated with a log entry,
            passing `None` will fetch logs from all devices, exercise caution

            names: a list of names of log entries,
            passing `None` will fetch logs regardless of name

            time_from: datetime object denoting the earliest
            `device_timestamp` the fetched logs can have

            time_to: datetime object denoting the latest
            `device_timestamp` the fetched lgos can have

        Returns:
            A list of `models.log.Log` adhering to the argument requirements
        """

        try:
            with Session(self.engine) as session:
                stmt = (
                    select(models.log.Log)
                    .where(
                        (models.log.Log.device_id.in_(device_identifiers))
                        if device_identifiers else True
                    )
                    .where(
                        (models.log.Log.name.in_(names))
                        if names else True
                    ).where(
                        (models.log.Log.device_timestamp >= time_from)
                        if time_from else True
                    ).where(
                        (models.log.Log.device_timestamp <= time_to)
                        if time_to else True
                    )
                ).order_by(desc(models.log.Log.device_timestamp))
                logs = session.scalars(stmt)
                if logs is None:
                    return []
                return [x for x in logs]
        except Exception as e:
            print("Logs fetch failed:", repr(e))
            return []

    def fetch_one(self, identifier: int) -> Optional[models.log.Log]:
        """Fetch a log with the given identifier.

        Args:
            identifier: numeric ID of a log

        Returns:
            A log with the specified ID, None if not found
        """
        with Session(self.engine) as session:
            stmt = select(models.log.Log).where(
                models.log.Log.id == identifier
            )
            return session.scalar(stmt)

    def create(self, logs: Generator) -> bool:
        """Creates multiple new log entries

        Args:
            logs: list of log entries to crate

        Returns:
            True if the operation was successful
        """
        try:
            with Session(self.engine) as session:
                session.add_all(logs)
                session.commit()
                return True
        except Exception as e:
            print("Log entries creation failed:", repr(e))
            return False

    def delete(self, device_identifiers: Optional[List[int]],
               names: Optional[List[str]],
               time_from: Optional[datetime.datetime],
               time_to: Optional[datetime.datetime]) -> bool:
        """Delete any amount of logs based on the specified arguments.

        Args:
            device_identifiers: list of numeric IDs
            of devices associated with a log entry,
            passing `None` will drop log entries
            from every device, exercise caution

            name: list of names of log entries, passing
            `None` will delete logs regardless of name

            time_from: datetime object denoting the
            earliest `device_timestamp` the deleted logs can have

            time_to: datetime object denoting the latest
            `device_timestamp` the delted logs can have

        Returns:
            True if the operation was successful
        """
        try:
            with Session(self.engine) as session:
                stmt = (
                    delete(models.log.Log)
                    .where(
                        (models.log.Log.device_id.in_(device_identifiers))
                        if device_identifiers else True
                    )
                    .where(
                        (models.log.Log.name.in_(names))
                        if names else True
                    )
                    .where(
                        models.log.Log.device_timestamp
                        >= time_from if time_from else True
                    ).where(
                        models.log.Log.device_timestamp
                        <= time_to if time_to else True
                    )
                )
                session.execute(stmt)
                session.commit()
                return True
        except IntegrityError as e:
            print("Log deletion failed:", repr(e))
            return False

    def delete_one(self, identifier: int) -> bool:
        """Delete a log with the specified ID.

        Args:
            identifier: numeric ID of the log

        Returns:
            True if the operation was successful
        """
        try:
            with Session(self.engine) as session:
                stmt = delete(models.log.Log).where(
                    models.log.Log.id
                    == identifier
                )
                session.execute(stmt)
                session.commit()
                return True
        except IntegrityError as e:
            print("Log deletion failed:", repr(e))
            return False
