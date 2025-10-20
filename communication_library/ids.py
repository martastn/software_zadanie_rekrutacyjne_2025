from enum import Enum, IntEnum, unique

HEADER_ID = 0x05


@unique
class BoardID(IntEnum):
    SOFTWARE = 0x01
    ROCKET = 0x02
    LAST_BOARD = 0x09
    PROXY = 0x1E
    BROADCAST = 0x1F


class DeviceID(IntEnum):
    SERVO = 0x00
    RELAY = 0x01
    SENSOR = 0x02


@unique
class ActionID(IntEnum):
    FEED = 0x00
    SERVICE = 0x01
    ACK = 0x02
    NACK = 0x03
    HEARTBEAT = 0x04
    REQUEST = 0x05
    RESPONSE = 0x06
    SCHEDULE = 0x07
    SACK = 0x08
    SNACK = 0x09


@unique
class DataTypeID(IntEnum):
    NO_DATA = 0x00
    UINT32 = 0x01
    UINT16 = 0x02
    UINT8 = 0x03
    INT32 = 0x04
    INT16 = 0x05
    INT8 = 0x06
    FLOAT = 0x07
    INT16X2 = 0x08
    UINT16INT16 = 0x09


@unique
class PriorityID(IntEnum):
    HIGH = 0x00
    LOW = 0x01


@unique
class _ServoOperationID(IntEnum):
    OPEN = 0x01
    CLOSE = 0x02
    OPENED_POS = 0x03
    CLOSED_POS = 0x04
    POSITION = 0x05
    DISABLE = 0x06
    RANGE = 0x07


@unique
class _DynamixelOperationID(IntEnum):
    OPEN = 0x01
    CLOSE = 0x02
    OPENED_POS = 0x03
    CLOSED_POS = 0x04
    POSITION = 0x05
    DISABLE = 0x06
    RANGE = 0x07
    RESET = 0x08
    VELOCITY = 0x09


@unique
class _RelayOperationID(IntEnum):
    OPEN = 0x01
    CLOSE = 0x02
    STATUS = 0x03


class _SupplyOperationID(IntEnum):
    OPEN = 0x01
    CLOSE = 0x02
    STATUS = 0x03


class _SchedulerOperationID(IntEnum):
    CLEAR = 0x01
    START = 0x02
    ABORT = 0x03


class _IgniterOperationID(IntEnum):
    IGNITE = 0x01
    OFF = 0x02
    RESISTANCE = 0x03
    STATUS = 0x04


class _FlashOperationID(IntEnum):
    ERASE = 0x01
    PURGE = 0x02
    START_LOGGING = 0x03
    STOP_LOGGING = 0x04


class _SensorOperationID(IntEnum):
    READ = 0x01


class _RecoveryOperationID(IntEnum):
    ARM = 0x01
    DISARM = 0x02


class _ParachuteOperationID(IntEnum):
    DROGUE = 0x01
    MAIN = 0x02


class _ResetOperationID(IntEnum):
    RESET = 0x01


class _KeepAliveOperationID(IntEnum):
    KEEPALIVE = 0x01


class _HeatingLampOperationID(IntEnum):
    OPEN = 0x01
    CLOSE = 0x02
    STATUS = 0x03


class OperationID(Enum):
    SERVO = _ServoOperationID
    DYNAMIXEL = _DynamixelOperationID
    RELAY = _RelayOperationID
    SCHEDULER = _SchedulerOperationID
    IGNITER = _IgniterOperationID
    FLASH = _FlashOperationID
    SENSOR = _SensorOperationID
    PISTON = _SensorOperationID
    RECOVERY = _RecoveryOperationID
    SUPPLY = _SupplyOperationID
    PARACHUTE = _ParachuteOperationID
    RESET = _ResetOperationID
    KEEPALIVE = _KeepAliveOperationID
    HEATINGLAMP = _HeatingLampOperationID
    MULTISENSOR = _SensorOperationID


class AckStatus(IntEnum):
    DISABLED = 0
    WAITING = 1
    READY = 2
    SUCCESSFUL = 3
    FAILED = 4


class LogLevel(IntEnum):
    NOTSET = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50