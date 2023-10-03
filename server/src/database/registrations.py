import datetime
from typing import List, Optional
import models.registration
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class RegistrationsDB:
    """ Wrapper class for managing device registrations
    """
    engine: Engine

    def __init__(self, db: Engine):
        self.engine = db


    def fetch_all(self) -> List[models.registration.Registration]:
        """ Fetches all device registration requests
        """
        with Session(self.engine) as session:
            stmt = (
                select(models.registration.Registration)
            )
            regs = session.scalars(stmt)
            if regs is None:
                return []
            return [x for x in regs]


    def create_registration(self,
                            mac: str,
                            public_key: str,
                            metadata: dict[str, str]):
        """ Creates a registration request for the device with specified
            MAC and public key.

        If a registration for the specified public key and MAC already exists,
        the previous registration's metadata is overwritten.
        """
        with Session(self.engine) as session:
            reg = models.registration.Registration()
            reg.mac_address = mac
            reg.public_key = public_key
            reg.info = metadata
            reg.last_appeared = datetime.datetime.now()
            session.merge(reg)
            session.commit()


    def fetch_one(self,
                  mac: str,
                  public_key: str) -> Optional[models.registration.Registration]:
        """ Fetch a registration from the database with the given MAC
            and public key.
        """
        with Session(self.engine) as session:
            stmt = (
                select(models.registration.Registration)
                .where(models.registration.Registration.mac_address == mac)
                .where(models.registration.Registration.public_key == public_key)
            )
            return session.scalar(stmt)


    def delete_registration(self,
                            mac: str,
                            public_key: str):
        """ Delete the registration specified by the given
            (mac, public_key) pair.
        """
        with Session(self.engine) as session:
            stmt = (
                delete(models.registration.Registration)
                .where(models.registration.Registration.mac_address == mac)
                .where(models.registration.Registration.public_key == public_key)
            )
            session.execute(stmt)
            session.commit()

