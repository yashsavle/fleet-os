from fleetos.v1 import common_pb2 as _common_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RobotTelemetry(_message.Message):
    __slots__ = ("robot_id", "sequence", "observed_at", "pose", "velocity", "battery_percent", "state", "active_faults")
    ROBOT_ID_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    OBSERVED_AT_FIELD_NUMBER: _ClassVar[int]
    POSE_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    BATTERY_PERCENT_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FAULTS_FIELD_NUMBER: _ClassVar[int]
    robot_id: str
    sequence: int
    observed_at: _timestamp_pb2.Timestamp
    pose: _common_pb2.Pose2D
    velocity: _common_pb2.Twist2D
    battery_percent: float
    state: _common_pb2.RobotOperatingState
    active_faults: _containers.RepeatedCompositeFieldContainer[_common_pb2.Fault]
    def __init__(self, robot_id: _Optional[str] = ..., sequence: _Optional[int] = ..., observed_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., pose: _Optional[_Union[_common_pb2.Pose2D, _Mapping]] = ..., velocity: _Optional[_Union[_common_pb2.Twist2D, _Mapping]] = ..., battery_percent: _Optional[float] = ..., state: _Optional[_Union[_common_pb2.RobotOperatingState, str]] = ..., active_faults: _Optional[_Iterable[_Union[_common_pb2.Fault, _Mapping]]] = ...) -> None: ...
