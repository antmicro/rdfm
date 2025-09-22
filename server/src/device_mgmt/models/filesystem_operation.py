import threading
import uuid


class FilesystemOperation:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.response = None
        self.completed = threading.Event()
