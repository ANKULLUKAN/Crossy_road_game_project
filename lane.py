from lane_types import LaneType

class Lane:
    def __init__(self, index, lane_type, direction=1, speed=0, spawn_interval=100):

        self.index = index
        self.lane_type = lane_type

        self.direction = direction
        self.speed = speed
        self.spawn_interval = spawn_interval
        self.spawn_timer = 0

        self.obstacles = []