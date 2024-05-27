import typing


class DeviceToken:
    """Represents data stored inside the device JWT token"""

    device_id: str
    created_at: int
    expires: int

    def __init__(self, **kwargs) -> None:
        for key in kwargs:
            setattr(self, key, kwargs[key])

    def to_dict(self) -> dict[str, typing.Any]:
        return vars(self)

    def from_dict(dict: dict[str, typing.Any]) -> "DeviceToken":
        return DeviceToken(**dict)
