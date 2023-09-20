import marshmallow
import typing
from marshmallow import validate


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
