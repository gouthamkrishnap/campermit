from dataclasses import dataclass, field
from enum import Enum


class CameraState(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    PARTIAL = "partial"
    BOUND_TO_OTHER_DRIVER = "bound-to-other-driver"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


@dataclass
class UvcFunction:
    control_interface: str
    streaming_interfaces: list[str] = field(default_factory=list)
    driver: str | None = None
    bound: bool = False
    video_nodes: list[str] = field(default_factory=list)


@dataclass
class Camera:
    id: str
    bus_path: str
    vid: str
    pid: str
    name: str | None = None
    serial: str | None = None
    vendor: str | None = None
    product: str | None = None
    removable: bool | None = None
    functions: list[UvcFunction] = field(default_factory=list)
    state: CameraState = CameraState.UNKNOWN