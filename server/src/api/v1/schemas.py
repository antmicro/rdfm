import marshmallow
import typing
from marshmallow import validate
from models.package import META_SOFT_VER, META_DEVICE_TYPE, META_MAC_ADDRESS


_T = typing.TypeVar("_T")


class Contains(validate.OneOf):
    """ Validator that succeeds if each of the chosen values is contained
        within the input sequence.
    """
    default_message = "Sequence must contain: {choices}."


    def _format_error(self, value) -> str:
        value_text = ", ".join(str(val) for val in value)
        return super()._format_error(value_text)


    def __call__(self, value: typing.Sequence[_T]) -> typing.Sequence[_T]:
        for required in self.choices:
            if required not in value:
                raise marshmallow.ValidationError(self._format_error(value))
        return value


class DeviceMetaSchema(marshmallow.Schema):
    """ Update check - metadata sent by the device
    """
    metadata = marshmallow.fields.Dict(keys=marshmallow.fields.Str(),
                                       values=marshmallow.fields.Str(),
                                       validate=Contains(choices=[META_SOFT_VER,
                                                                  META_DEVICE_TYPE,
                                                                  META_MAC_ADDRESS]))
