from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RobotOperatingState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ROBOT_OPERATING_STATE_UNSPECIFIED: _ClassVar[RobotOperatingState]
    ROBOT_OPERATING_STATE_IDLE: _ClassVar[RobotOperatingState]
    ROBOT_OPERATING_STATE_MOVING: _ClassVar[RobotOperatingState]
    ROBOT_OPERATING_STATE_FAULT: _ClassVar[RobotOperatingState]
    ROBOT_OPERATING_STATE_OFFLINE: _ClassVar[RobotOperatingState]
ROBOT_OPERATING_STATE_UNSPECIFIED: RobotOperatingState
ROBOT_OPERATING_STATE_IDLE: RobotOperatingState
ROBOT_OPERATING_STATE_MOVING: RobotOperatingState
ROBOT_OPERATING_STATE_FAULT: RobotOperatingState
ROBOT_OPERATING_STATE_OFFLINE: RobotOperatingState

class Pose2D(_message.Message):
    __slots__ = ("x_m", "y_m", "heading_rad")
    X_M_FIELD_NUMBER: _ClassVar[int]
    Y_M_FIELD_NUMBER: _ClassVar[int]
    HEADING_RAD_FIELD_NUMBER: _ClassVar[int]
    x_m: float
    y_m: float
    heading_rad: float
    def __init__(self, x_m: _Optional[float] = ..., y_m: _Optional[float] = ..., heading_rad: _Optional[float] = ...) -> None: ...

class Twist2D(_message.Message):
    __slots__ = ("linear_mps", "angular_rps")
    LINEAR_MPS_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_RPS_FIELD_NUMBER: _ClassVar[int]
    linear_mps: float
    angular_rps: float
    def __init__(self, linear_mps: _Optional[float] = ..., angular_rps: _Optional[float] = ...) -> None: ...

class Fault(_message.Message):
    __slots__ = ("code", "message")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: str
    message: str
    def __init__(self, code: _Optional[str] = ..., message: _Optional[str] = ...) -> None: ...
