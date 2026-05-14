from enum import Enum, auto


class LaneType(Enum):
    
    SAFE = auto()
    ROAD = auto()
    RIVER = auto()