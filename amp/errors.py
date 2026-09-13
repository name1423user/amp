"""Exception types for §6 of the spec. Every raise carries the message id and the offending field path."""


class AmpError(Exception):
    kind = "AmpError"

    def __init__(self, message_id: str, field_path: str, detail: str = ""):
        self.message_id = message_id
        self.field_path = field_path
        self.detail = detail
        super().__init__(f"{self.kind} in message {message_id!r} at {field_path!r}: {detail}")


class UnsupportedProtocol(AmpError):
    kind = "UnsupportedProtocol"


class UnsupportedAct(AmpError):
    kind = "UnsupportedAct"


class UnsupportedAspect(AmpError):
    kind = "UnsupportedAspect"


class UnsupportedRole(AmpError):
    kind = "UnsupportedRole"


class UnknownId(AmpError):
    kind = "UnknownId"


class NoGenericLabel(AmpError):
    kind = "NoGenericLabel"


class MissingField(AmpError):
    kind = "MissingField"


class InvalidValue(AmpError):
    kind = "InvalidValue"
