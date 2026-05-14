from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

import random
import tkinter as tk
from tkinter import messagebox

from config import WINDOW_WIDTH, WINDOW_HEIGHT, TILE_SIZE, ROWS_VISIBLE, COLS
from lane import Lane
from lane_types import LaneType
from obstacle import Obstacle
from generator import WorldGenerator
from event_logger import EventLogger
from save_manager import save_game, load_game
from replay_manager import ReplayManager
import copy


class Game(QWidget):
    def __init__(self):
        super().__init__()

        self.textures = {
            "SAFE": QPixmap("textures/trawa.png"),
            "ROAD": QPixmap("textures/droga.png"),
            "RIVER": QPixmap("textures/water.png"),
            "log": QPixmap("textures/log.png"),
            "car": QPixmap("textures/car.png"),
            "tree": QPixmap("textures/tree.png"),
            "player": QPixmap("textures/player.png"),
        }

        self.is_alive = True

        # czas
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)

        # spawn gracza
        self.player_col = COLS // 2
        self.player_screen_row = ROWS_VISIBLE - 4
        self.player_world_row = self.player_screen_row

        #kolumna gwartrantujaca przejscie
        self.safe_path_col = self.player_col


        #kamera
        self.camera_y = (self.player_world_row - self.player_screen_row) * TILE_SIZE
        self.camera_speed = 0.3

        # okno
        self.setWindowTitle("Crossy Road")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # generacja świata i trudność
        self.generator = WorldGenerator()
        self.difficulty = 0.5

        self.start_word_row = self.player_world_row
        self.last_difficulty_step = 0

        # logger
        self.logger = EventLogger()

        # debugmode
        self.debug_mode = False

        # tworzenie linii
        self.lanes = {}
        self.generate_initial_lanes()

        # replay
        self.game_tick = 0
        self.replay = ReplayManager()
        self.replay.save_initial_state(self.get_current_state())

        self.show()

    def get_current_state(self):
        return {
            "is_alive": self.is_alive,
            "player_col": self.player_col,
            "player_screen_row": self.player_screen_row,
            "player_world_row": self.player_world_row,
            "difficulty": self.difficulty,
            "start_word_row": self.start_word_row,
            "last_difficulty_step": self.last_difficulty_step,
            "camera_y": self.camera_y,
            "lanes": copy.deepcopy(self.lanes),
        }

    def restore_state(self, state):
        self.is_alive = state["is_alive"]
        self.player_col = state["player_col"]
        self.player_screen_row = state["player_screen_row"]
        self.player_world_row = state["player_world_row"]
        self.difficulty = state["difficulty"]
        self.start_word_row = state["start_word_row"]
        self.last_difficulty_step = state["last_difficulty_step"]
        self.lanes = copy.deepcopy(state["lanes"])

        
        self.camera_y = state.get(
            "camera_y",
            (self.player_world_row - self.player_screen_row) * TILE_SIZE
        )

        self.game_tick = 0
        self.update()


    def snap_to_grid(self):
        col = round((self.player_col * TILE_SIZE + 5 - 5) / TILE_SIZE)
        col = max(0, min(COLS - 1, col))
        self.player_col = col


    
    def update_safe_path_col(self):
        move = random.choice([-1, 0, 1])
        self.safe_path_col += move
        self.safe_path_col = max(0, min(COLS - 1, self.safe_path_col))

    def add_trees_to_safe_lane(self, lane):
        if lane.lane_type != LaneType.SAFE:
            return
        
        self.update_safe_path_col()

        count = random.randint(2, 5)
        used_cols = set()

        for _ in range(count):
            col = random.randint(0, COLS - 1)

            if col == self.safe_path_col:
                continue

            if col in used_cols:
                continue

            used_cols.add(col)

            x = col * TILE_SIZE + 5

            obstacle = Obstacle(
                x=x,
                y=0,
                width=TILE_SIZE - 10,
                height=TILE_SIZE - 10,
                speed=0,
                direction=0,
                color="purple",
                obstacle_type="tree",
                solid=True,
                deadly=False
            )

            lane.obstacles.append(obstacle)



    def update_difficulty(self):
        passed_rows = abs(self.player_world_row - self.start_word_row)
        current_step = passed_rows // 5

        if current_step > self.last_difficulty_step:
            increase = (current_step - self.last_difficulty_step) * 0.5
            self.difficulty += increase
            self.last_difficulty_step = current_step

            self.apply_difficulty_to_lanes()

            self.logger.log(
                "DIFFICULTY_UP",
                f"difficulty={self.difficulty}"
            )

            print("DIFFICULTY:", self.difficulty)


    def apply_difficulty_to_lanes(self):
        for lane in self.lanes.values():
            if lane.lane_type == LaneType.ROAD:
                lane.speed = 2.0 + self.difficulty * 0.6
                lane.spawn_interval = max(35, int(120 - self.difficulty * 12))

            elif lane.lane_type == LaneType.RIVER:
                lane.speed = 1.5 + self.difficulty * 0.45
                lane.spawn_interval = max(45, int(140 - self.difficulty * 10))


    def update_camera(self):
        speed = self.camera_speed * (1 + self.difficulty * 0.750)
        self.camera_y -= speed



    def get_player_screen_y(self):
        return self.player_world_row * TILE_SIZE - self.camera_y + 5


    def check_camera_death(self):
        player_y = self.get_player_screen_y()
        if player_y > WINDOW_HEIGHT:
            self.is_alive = False


    def update_obstacles(self):
        for lane in self.lanes.values():
            if lane.lane_type not in [LaneType.ROAD, LaneType.RIVER]:
                continue

            lane.spawn_timer += 1

            if lane.spawn_timer >= lane.spawn_interval:
                lane.spawn_timer = 0

                if lane.direction == 1:
                    x = -60
                else:
                    x = WINDOW_WIDTH + 60

                if lane.lane_type == LaneType.ROAD:
                    color = "red"
                    width = TILE_SIZE
                    height = TILE_SIZE - 10
                    obstacle_type = "car"
                    solid = False
                    deadly = True
                else:
                    color = "black"
                    width = TILE_SIZE * 2
                    height = TILE_SIZE - 10
                    obstacle_type = "log"
                    solid = False
                    deadly = False

                obstacle = Obstacle(
                    x=x,
                    y=0,
                    width=width,
                    height=height,
                    speed=lane.speed,
                    direction=lane.direction,
                    color=color,
                    obstacle_type=obstacle_type,
                    solid=solid,
                    deadly=deadly
                )

                lane.obstacles.append(obstacle)

            for obs in lane.obstacles:
                if obs.obstacle_type in ["car", "log"]:
                    obs.update()

            lane.obstacles = [
                o for o in lane.obstacles
                if o.obstacle_type == "tree" or (-200 < o.x < WINDOW_WIDTH + 200)
            ]


    def update_game(self):
        if self.replay.is_replaying:
            moves = self.replay.get_moves_for_current_tick()

            for move in moves:
                self.perform_move(move)

            if self.check_car_collision():
                self.is_alive = False

            log = self.check_water_collision()

            if log is None:
                self.is_alive = False
            elif log is not False:
                self.player_col += (log.speed * log.direction) / TILE_SIZE

            if self.is_alive:
                self.update_obstacles()
                self.update_camera()
                self.update_world()
                self.check_camera_death()

            self.game_tick += 1
            self.replay.advance_tick()

            if not self.is_alive or self.replay.has_finished():
                self.replay.stop_replay()

            self.update()
            return

        if self.check_car_collision():
            self.is_alive = False

        log = self.check_water_collision()

        if log is None:
            self.is_alive = False
        elif log is not False:
            self.player_col += (log.speed * log.direction) / TILE_SIZE

        if self.is_alive:
            self.update_obstacles()
            self.update_camera()
            self.update_world()
            self.check_camera_death()

            self.game_tick += 1
            self.update()
        else:
            self.timer.stop()
            messagebox.showinfo("KONIEC GRY", "PORAŻKA!")


    def check_water_collision(self):
        lane = self.lanes.get(self.player_world_row)

        if lane and lane.lane_type == LaneType.RIVER:
            for obs in lane.obstacles:
                obs_x1 = obs.x
                obs_x2 = obs.x + obs.width

                player_x1 = self.player_col * TILE_SIZE + 5
                player_x2 = player_x1 + TILE_SIZE - 10

                if not (player_x2 <= obs_x1 or player_x1 >= obs_x2):
                    return obs

            return None

        return False
    

    def check_car_collision(self):
        lane = self.lanes.get(self.player_world_row)

        if lane and lane.lane_type == LaneType.ROAD:
            for obs in lane.obstacles:
                obs_x1 = obs.x
                obs_x2 = obs.x + obs.width

                player_x1 = self.player_col * TILE_SIZE + 5
                player_x2 = player_x1 + TILE_SIZE - 10

                if not (player_x2 <= obs_x1 or player_x1 >= obs_x2):
                    return True

        return False


    def can_move(self, new_col, new_screen_row, new_world_row):
        lane = self.lanes.get(new_world_row)

        if lane is None:
            return False

        if lane.lane_type == LaneType.RIVER or lane.lane_type == LaneType.ROAD:
            return True

        for obs in lane.obstacles:
            if obs.solid:
                obs_x1 = obs.x
                obs_x2 = obs.x + obs.width

                player_x1 = new_col * TILE_SIZE + 5
                player_x2 = player_x1 + TILE_SIZE - 10

                if not (player_x2 <= obs_x1 or player_x1 >= obs_x2):
                    return False

        return True

    def perform_move(self, move):
        old_col = self.player_col
        old_row = self.player_world_row

        if move == "UP":
            log = self.check_water_collision()
            if log not in [None, False]:
                self.snap_to_grid()

            new_row = self.player_world_row - 1

            if self.can_move(self.player_col, self.player_screen_row, new_row):
                self.player_world_row = new_row
                self.update_world()
                self.update_difficulty()

        elif move == "DOWN":
            log = self.check_water_collision()
            if log not in [None, False]:
                self.snap_to_grid()

            new_row = self.player_world_row + 1

            if self.can_move(self.player_col, self.player_screen_row, new_row):
                self.player_world_row = new_row
                self.update_world()

        elif move == "LEFT":
            if self.player_col > 0:
                new_col = self.player_col - 1

                if self.can_move(new_col, self.player_screen_row, self.player_world_row):
                    self.player_col = new_col

        elif move == "RIGHT":
            if self.player_col < COLS - 1:
                new_col = self.player_col + 1

                if self.can_move(new_col, self.player_screen_row, self.player_world_row):
                    self.player_col = new_col

        if self.player_col != old_col or self.player_world_row != old_row:
            self.logger.log(
                "PLAYER_MOVE",
                f"move={move}, col={self.player_col}, row={-self.player_world_row}"
            )

    def start_replay(self):
        if self.replay.initial_state is None or not self.replay.recorded_moves:
            return

        self.restore_state(self.replay.initial_state)
        self.is_alive = True
        self.camera_y = (self.player_world_row - self.player_screen_row) * TILE_SIZE

        self.replay.start_replay()
        self.timer.start(16)


    def keyPressEvent(self, event):
        if self.replay.is_replaying:
            return

        if event.key() == Qt.Key_F1:
            self.debug_mode = not self.debug_mode
            self.update()
            return

        if event.key() == Qt.Key_S:
            save_game(self)
            return

        if event.key() == Qt.Key_L:
            load_game(self)
            self.camera_y = (self.player_world_row - self.player_screen_row) * TILE_SIZE
            self.update()
            return

        if event.key() == Qt.Key_R:
            self.start_replay()
            return

        if event.key() == Qt.Key_Up:
            old_row = self.player_world_row
            old_col = self.player_col
            self.perform_move("UP")
            if self.player_world_row != old_row or self.player_col != old_col:
                self.replay.record_move(self.game_tick, "UP")

        elif event.key() == Qt.Key_Down:
            old_row = self.player_world_row
            old_col = self.player_col
            self.perform_move("DOWN")
            if self.player_world_row != old_row or self.player_col != old_col:
                self.replay.record_move(self.game_tick, "DOWN")

        elif event.key() == Qt.Key_Left:
            old_col = self.player_col
            self.perform_move("LEFT")
            if self.player_col != old_col:
                self.replay.record_move(self.game_tick, "LEFT")

        elif event.key() == Qt.Key_Right:
            old_col = self.player_col
            self.perform_move("RIGHT")
            if self.player_col != old_col:
                self.replay.record_move(self.game_tick, "RIGHT")

        self.update()


    def generate_initial_lanes(self):
        min_row = self.player_world_row - self.player_screen_row
        max_row = min_row + ROWS_VISIBLE - 1

        for row in range(min_row, max_row + 1):
            if row == self.player_world_row:
                lane = Lane(row, LaneType.SAFE)
            else:
                lane = self.generator.generate_lane(row, self.difficulty)

            self.add_trees_to_safe_lane(lane)

            self.lanes[row] = lane

    def update_world(self):
        camera_min_row = int(self.camera_y // TILE_SIZE) - 5
        camera_max_row = int(self.camera_y // TILE_SIZE) + ROWS_VISIBLE + 8

        player_min_row = self.player_world_row - self.player_screen_row - 5
        player_max_row = self.player_world_row + (ROWS_VISIBLE - self.player_screen_row) + 5

        min_row = min(camera_min_row, player_min_row)
        max_row = max(camera_max_row, player_max_row)

        for row in range(min_row, max_row + 1):
            if row not in self.lanes:
                lane = self.generator.generate_lane(row, self.difficulty)

                self.add_trees_to_safe_lane(lane)

                self.lanes[row] = lane
                self.logger.log("LANE_GENERATED", f"type={lane.lane_type}")

        to_remove = [
            row for row in self.lanes
            if row < min_row - 15 or row > max_row + 15
        ]

        for row in to_remove:
            del self.lanes[row]


    def draw_debug(self, painter):

        painter.setPen(Qt.red)

        player_x = int(self.player_col * TILE_SIZE + 5)
        player_y = int(self.player_world_row * TILE_SIZE - self.camera_y + 5)

        painter.drawRect(player_x, player_y, TILE_SIZE - 10, TILE_SIZE - 10)

        painter.drawText(10, 20, "DEBUG MODE")
        painter.drawText(10, 60, f"Difficulty: {self.difficulty}")
        painter.drawText(10, 80, f"Player row: {self.player_world_row}")
        painter.drawText(10, 100, f"Player col: {self.player_col}")
        

        first_row = int(self.camera_y // TILE_SIZE) - 2
        last_row = first_row + ROWS_VISIBLE + 5

        for world_row in range(first_row, last_row + 1):
            lane = self.lanes.get(world_row)

            if lane is None:
                continue

            y = int(world_row * TILE_SIZE - self.camera_y)

            painter.drawText(5, y + 15, f"{lane.lane_type.name} | row={world_row}")

            for obs in lane.obstacles:
                painter.drawRect(
                    int(obs.x),
                    int(y + 5),
                    int(obs.width),
                    int(obs.height)
                )


    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw_lanes(painter)
        self.draw_grid(painter)
        self.draw_obstacles(painter)
        self.draw_player(painter)

        if self.debug_mode:
            self.draw_debug(painter)



    def draw_obstacles(self, painter):
        painter.setPen(Qt.black)

        first_row = int(self.camera_y // TILE_SIZE) - 2
        last_row = first_row + ROWS_VISIBLE + 5

        for world_row in range(first_row, last_row + 1):
            lane = self.lanes.get(world_row)

            if lane is None:
                continue

            y = int(world_row * TILE_SIZE - self.camera_y + 5)

            for obs in lane.obstacles:
                texture = self.textures.get(obs.obstacle_type)

                if texture and not texture.isNull():
                    painter.drawPixmap(
                        int(obs.x),
                        int(y),
                        int(obs.width),
                        int(obs.height),
                        texture
                    )
                else:
                    painter.setBrush(QColor(obs.color))
                    painter.drawRect(
                        int(obs.x),
                        int(y),
                        int(obs.width),
                        int(obs.height)
                    )



    def draw_lanes(self, painter):
        first_row = int(self.camera_y // TILE_SIZE) - 2
        last_row = first_row + ROWS_VISIBLE + 5

        for world_row in range(first_row, last_row + 1):
            lane = self.lanes.get(world_row)

            if not lane:
                continue

            y = int(world_row * TILE_SIZE - self.camera_y)

            if lane.lane_type.name == "SAFE":
                color = QColor(80, 170, 90)
            elif lane.lane_type.name == "ROAD":
                color = QColor(70, 70, 70)
            elif lane.lane_type.name == "RIVER":
                color = QColor(50, 120, 220)
            else:
                color = QColor(255, 255, 255)

            texture = self.textures.get(lane.lane_type.name)

            if texture and not texture.isNull():
                for col in range(COLS):
                    x = col * TILE_SIZE
                    painter.drawPixmap(x, y, TILE_SIZE, TILE_SIZE, texture)
            else:
                painter.fillRect(0, y, WINDOW_WIDTH, TILE_SIZE, color)



    def draw_grid(self, painter):
        pen = QPen(QColor(200, 200, 200))
        painter.setPen(pen)

        first_row = int(self.camera_y // TILE_SIZE) - 2
        last_row = first_row + ROWS_VISIBLE + 5

        for world_row in range(first_row, last_row + 1):
            y = int(world_row * TILE_SIZE - self.camera_y)

            for col in range(COLS):
                x = col * TILE_SIZE
                painter.drawRect(x, y, TILE_SIZE, TILE_SIZE)



    def draw_player(self, painter):
        x = int(self.player_col * TILE_SIZE + 5)
        y = int(self.player_world_row * TILE_SIZE - self.camera_y + 5)

        painter.drawPixmap(
            x,
            y,
            TILE_SIZE - 10,
            TILE_SIZE - 10,
            self.textures["player"]
        )
