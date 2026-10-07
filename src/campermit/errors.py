class CamPermitError(Exception):
    """Base exception for CamPermit errors."""


class InvalidInterface(CamPermitError):
    """The interface name is invalid."""


class NotVideoControl(CamPermitError):
    """The interface is not a UVC VideoControl interface."""


class InterfaceGone(CamPermitError):
    """The USB interface no longer exists."""


class BoundToOtherDriver(CamPermitError):
    """The interface is bound to another driver."""


class PermissionDenied(CamPermitError):
    """The operation was denied by the system."""


class SysfsReadError(CamPermitError):
    """A sysfs control read failed."""

    def __init__(
        self,
        message: str,
        errno_value: int | None = None,
    ):
        super().__init__(message)
        self.errno_value = errno_value


class SysfsWriteError(CamPermitError):
    """A sysfs control write failed."""

    def __init__(
        self,
        message: str,
        errno_value: int | None = None,
    ):
        super().__init__(message)
        self.errno_value = errno_value


class VerificationFailed(CamPermitError):
    """The requested driver state was not reached."""