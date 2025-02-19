import threading
import queue
from typing import Union
import uuid

from request_models import Action


class ActionExecution:
    action: Action
    execution_id: str

    status_code: Union[None, int]
    output: str

    execution_control: queue.Queue

    execution_queued: threading.Event
    execution_completed: threading.Event

    def __init__(self, action: Action):
        self.action = action
        self.status_code = None
        self.execution_id = str(uuid.uuid4())

        self.execution_control = queue.Queue()

        self.execution_queued = threading.Event()
        self.execution_completed = threading.Event()

    def set_status(self, status: int):
        self.status_code = status
