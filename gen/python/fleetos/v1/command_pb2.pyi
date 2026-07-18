from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VelocityCommand(_message.Message):
    __slots__ = ("linear_mps", "angular_rps")
    LINEAR_MPS_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_RPS_FIELD_NUMBER: _ClassVar[int]
    linear_mps: float
    angular_rps: float
    def __init__(self, linear_mps: _Optional[float] = ..., angular_rps: _Optional[float] = ...) -> None: ...

class StopCommand(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class RobotCommand(_message.Message):
    __slots__ = ("command_id", "robot_id", "issued_at", "velocity", "stop")
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    ROBOT_ID_FIELD_NUMBER: _ClassVar[int]
    ISSUED_AT_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    STOP_FIELD_NUMBER: _ClassVar[int]
    command_id: str
    robot_id: str
    issued_at: _timestamp_pb2.Timestamp
    velocity: VelocityCommand
    stop: StopCommand
    def __init__(self, command_id: _Optional[str] = ..., robot_id: _Optional[str] = ..., issued_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., velocity: _Optional[_Union[VelocityCommand, _Mapping]] = ..., stop: _Optional[_Union[StopCommand, _Mapping]] = ...) -> None: ...
