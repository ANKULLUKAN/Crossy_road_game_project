import random
from lane import Lane
from lane_types import LaneType


class WorldGenerator:

    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.last_lane_type = LaneType.SAFE

    def generate_lane(self, index, difficulty):
        possible = [LaneType.SAFE, LaneType.ROAD, LaneType.RIVER]

        if self.last_lane_type == LaneType.RIVER:
            possible.remove(LaneType.RIVER)

        weights = []
        for lane_type in possible:
            if lane_type == LaneType.SAFE:
                weights.append(max(10, 50 - difficulty * 4))
            elif lane_type == LaneType.ROAD:
                weights.append(30 + difficulty * 3)
            elif lane_type == LaneType.RIVER:
                weights.append(20 + difficulty * 2)

        lane_type = self.random.choices(possible, weights=weights, k=1)[0]
        self.last_lane_type = lane_type

        if lane_type == LaneType.SAFE:
            return Lane(index, lane_type)

        direction = self.random.choice([-1, 1])

        if lane_type == LaneType.ROAD:
            speed = 2.0 + difficulty * 0.6
            spawn_interval = max(35, int(120 - difficulty * 12))
        else:
            speed = 1.5 + difficulty * 0.45
            spawn_interval = max(45, int(140 - difficulty * 10))

        return Lane(index, lane_type, direction, speed, spawn_interval)

   