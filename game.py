import copy
import random
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from config import COLS, ROWS_VISIBLE, TILE_SIZE, WINDOW_HEIGHT, WINDOW_WIDTH
from event_logger import EventLogger
from generator import WorldGenerator
from lane import Lane
from lane_types import LaneType
from obstacle import Obstacle
from replay_manager import ReplayManager
from save_manager import load_game, save_game


class Game(QWidget):
    return_to_menu = pyqtSignal()
    restart_requested = pyqtSignal()
    score_recorded = pyqtSignal(int)

    def __init__(self, preset, show_grid=False):
        super().__init__()
        self.preset = preset
        self.show_grid = show_grid
        self.is_alive = True
        self.paused = False
        self.end_screen = None
        self.toast = None
        self.score = 0
        self.textures = {
            "SAFE": QPixmap("textures/trawa.png"),
            "ROAD": QPixmap("textures/droga.png"),
            "RIVER": QPixmap("textures/water.png"),
            "log": QPixmap("textures/log.png"),
            "car": QPixmap("textures/car.png"),
            "tree": QPixmap("textures/tree.png"),
            "player": QPixmap("textures/player.png"),
        }
        self.player_col = COLS // 2
        self.player_screen_row = ROWS_VISIBLE - 4
        self.player_world_row = self.player_screen_row
        self.safe_path_col = self.player_col
        self.camera_y = (self.player_world_row - self.player_screen_row) * TILE_SIZE
        self.camera_speed = preset["camera_speed"]
        self.generator = WorldGenerator()
        self.difficulty = preset["initial_difficulty"]
        self.start_word_row = self.player_world_row
        self.last_difficulty_step = 0
        self.logger = EventLogger()
        self.debug_mode = False
        self.lanes = {}
        self.generate_initial_lanes()
        self.game_tick = 0
        self.replay = ReplayManager()
        self.replay.save_initial_state(self.get_current_state())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setFocusPolicy(Qt.StrongFocus)
        self.build_hud()
        self.update_hud()

    def build_hud(self):
        self.setStyleSheet("""
            QFrame#hud {
                background-color: rgba(11, 17, 28, 224);
                border: 1px solid rgba(75, 94, 118, 190);
                border-radius: 16px;
            }
            QLabel#hudValue {
                color: white;
                font-size: 17px;
                font-weight: 800;
            }
            QLabel#hudCaption {
                color: #8ea1b8;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton#mini {
                background-color: rgba(32, 45, 63, 230);
                border: 1px solid #34465d;
                border-radius: 9px;
                color: #e5edf5;
                font-size: 11px;
                font-weight: 700;
                padding: 7px 10px;
            }
            QPushButton#mini:hover {
                background-color: #2a394d;
                border: 1px solid #53e6a2;
            }
            QLabel#hint {
                background-color: rgba(11, 17, 28, 214);
                border: 1px solid rgba(75, 94, 118, 160);
                border-radius: 12px;
                color: #e2e9f1;
                font-size: 11px;
                padding: 8px;
            }
        """)
        self.hud = QFrame(self)
        self.hud.setObjectName("hud")
        self.hud.setGeometry(12, 10, WINDOW_WIDTH - 24, 92)
        layout = QVBoxLayout(self.hud)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(7)
        first = QHBoxLayout()
        first.setSpacing(18)
        self.score_value, score_box = self.create_metric("WYNIK")
        self.level_value, level_box = self.create_metric("TRYB")
        self.speed_value, speed_box = self.create_metric("POZIOM")
        first.addLayout(score_box)
        first.addLayout(level_box)
        first.addLayout(speed_box)
        first.addStretch()
        layout.addLayout(first)
        second = QHBoxLayout()
        second.setSpacing(7)
        for text, handler in [
            ("PAUZA", self.toggle_pause),
            ("ZAPISZ", self.save_current),
            ("WCZYTAJ", self.load_current),
            ("REPLAY", self.start_replay),
            ("MENU", self.return_to_menu.emit),
        ]:
            button = QPushButton(text)
            button.setObjectName("mini")
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(handler)
            second.addWidget(button)
            if text == "PAUZA":
                self.pause_button = button
        layout.addLayout(second)
        self.hint = QLabel("STRZAŁKI  ruch     P / ESC  pauza     S  zapis     L  odczyt     R  replay", self)
        self.hint.setObjectName("hint")
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setGeometry(22, WINDOW_HEIGHT - 42, WINDOW_WIDTH - 44, 31)
        self.hud.raise_()
        self.hint.raise_()

    def create_metric(self, caption):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        value = QLabel("0")
        value.setObjectName("hudValue")
        label = QLabel(caption)
        label.setObjectName("hudCaption")
        layout.addWidget(value)
        layout.addWidget(label)
        return value, layout

    def update_hud(self):
        self.score = max(self.score, max(0, self.start_word_row - self.player_world_row))
        self.score_value.setText(str(self.score))
        self.level_value.setText(self.preset["label"])
        level = max(1, self.last_difficulty_step + 1)
        self.speed_value.setText(str(level))

    def show_toast(self, text):
        if self.toast is not None:
            self.toast.deleteLater()
        self.toast = QLabel(text, self)
        self.toast.setAlignment(Qt.AlignCenter)
        self.toast.setStyleSheet("background-color: rgba(16,26,40,238); color: #53e6a2; border: 1px solid #53e6a2; border-radius: 11px; font-weight: 700; padding: 8px;")
        self.toast.setGeometry(90, 114, WINDOW_WIDTH - 180, 38)
        self.toast.show()
        self.toast.raise_()
        QTimer.singleShot(1450, self.clear_toast)

    def clear_toast(self):
        if self.toast is not None:
            self.toast.deleteLater()
            self.toast = None

    def save_current(self):
        if not self.is_alive:
            return
        save_game(self)
        self.show_toast("Gra została zapisana")
        self.setFocus()

    def load_current(self):
        try:
            load_game(self)
            self.camera_y = (self.player_world_row - self.player_screen_row) * TILE_SIZE
            self.is_alive = True
            self.paused = False
            self.timer.start(16)
            self.pause_button.setText("PAUZA")
            self.close_end_screen()
            self.update_hud()
            self.update()
            self.show_toast("Wczytano zapis gry")
        except (FileNotFoundError, KeyError, ValueError):
            self.show_toast("Brak poprawnego zapisu")
        self.setFocus()

    def toggle_pause(self):
        if not self.is_alive or self.replay.is_replaying:
            return
        self.paused = not self.paused
        if self.paused:
            self.timer.stop()
            self.pause_button.setText("WZNÓW")
            self.show_pause_overlay()
        else:
            self.timer.start(16)
            self.pause_button.setText("PAUZA")
            self.close_pause_overlay()
        self.setFocus()

    def show_pause_overlay(self):
        self.pause_overlay = QFrame(self)
        self.pause_overlay.setGeometry(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.pause_overlay.setStyleSheet("background-color: rgba(5, 10, 18, 145);")
        label = QLabel("PAUZA", self.pause_overlay)
        label.setAlignment(Qt.AlignCenter)
        label.setGeometry(100, 355, 300, 55)
        label.setStyleSheet("color: white; font-size: 36px; font-weight: 800; background: transparent;")
        sub = QLabel("Naciśnij P, Esc lub przycisk WZNÓW", self.pause_overlay)
        sub.setAlignment(Qt.AlignCenter)
        sub.setGeometry(60, 410, 380, 35)
        sub.setStyleSheet("color: #d2dce8; font-size: 13px; background: transparent;")
        self.pause_overlay.show()
        self.pause_overlay.raise_()
        self.hud.raise_()

    def close_pause_overlay(self):
        if hasattr(self, "pause_overlay") and self.pause_overlay is not None:
            self.pause_overlay.deleteLater()
            self.pause_overlay = None

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
        self.camera_y = state.get("camera_y", (self.player_world_row - self.player_screen_row) * TILE_SIZE)
        self.game_tick = 0
        self.score = 0
        self.update_hud()
        self.update()

    def snap_to_grid(self):
        col = round(self.player_col)
        self.player_col = max(0, min(COLS - 1, col))

    def update_safe_path_col(self):
        self.safe_path_col += random.choice([-1, 0, 1])
        self.safe_path_col = max(0, min(COLS - 1, self.safe_path_col))

    def add_trees_to_safe_lane(self, lane):
        if lane.lane_type != LaneType.SAFE:
            return
        self.update_safe_path_col()
        used_cols = set()
        for _ in range(random.randint(2, 5)):
            col = random.randint(0, COLS - 1)
            if col == self.safe_path_col or col in used_cols:
                continue
            used_cols.add(col)
            lane.obstacles.append(Obstacle(col * TILE_SIZE + 5, 0, TILE_SIZE - 10, TILE_SIZE - 10, 0, 0, "purple", "tree", True, False))

    def update_difficulty(self):
        passed_rows = abs(self.player_world_row - self.start_word_row)
        current_step = passed_rows // 5
        if current_step > self.last_difficulty_step:
            self.difficulty += (current_step - self.last_difficulty_step) * 0.5
            self.last_difficulty_step = current_step
            self.apply_difficulty_to_lanes()
            self.logger.log("DIFFICULTY_UP", f"difficulty={self.difficulty}")
            self.show_toast(f"Poziom {self.last_difficulty_step + 1} - tempo rośnie")
            self.update_hud()

    def apply_difficulty_to_lanes(self):
        for lane in self.lanes.values():
            if lane.lane_type == LaneType.ROAD:
                lane.speed = 2.0 + self.difficulty * 0.6
                lane.spawn_interval = max(35, int(120 - self.difficulty * 12))
            elif lane.lane_type == LaneType.RIVER:
                lane.speed = 1.5 + self.difficulty * 0.45
                lane.spawn_interval = max(45, int(140 - self.difficulty * 10))

    def update_camera(self):
        self.camera_y -= self.camera_speed * (1 + self.difficulty * 0.750)

    def get_player_screen_y(self):
        return self.player_world_row * TILE_SIZE - self.camera_y + 5

    def check_camera_death(self):
        if self.get_player_screen_y() > WINDOW_HEIGHT or self.player_col < -0.85 or self.player_col > COLS - 0.15:
            self.finish_game()

    def update_obstacles(self):
        for lane in self.lanes.values():
            if lane.lane_type not in [LaneType.ROAD, LaneType.RIVER]:
                continue
            lane.spawn_timer += 1
            if lane.spawn_timer >= lane.spawn_interval:
                lane.spawn_timer = 0
                x = -60 if lane.direction == 1 else WINDOW_WIDTH + 60
                if lane.lane_type == LaneType.ROAD:
                    props = (TILE_SIZE, TILE_SIZE - 10, "red", "car", True)
                else:
                    props = (TILE_SIZE * 2, TILE_SIZE - 10, "black", "log", False)
                lane.obstacles.append(Obstacle(x, 0, props[0], props[1], lane.speed, lane.direction, props[2], props[3], False, props[4]))
            for obs in lane.obstacles:
                if obs.obstacle_type in ["car", "log"]:
                    obs.update()
            lane.obstacles = [o for o in lane.obstacles if o.obstacle_type == "tree" or -200 < o.x < WINDOW_WIDTH + 200]

    def update_game(self):
        if self.paused or not self.is_alive:
            return
        if self.replay.is_replaying:
            for move in self.replay.get_moves_for_current_tick():
                self.perform_move(move)
        if self.check_car_collision():
            self.finish_game()
            return
        log = self.check_water_collision()
        if log is None:
            self.finish_game()
            return
        if log is not False:
            self.player_col += (log.speed * log.direction) / TILE_SIZE
        self.update_obstacles()
        self.update_camera()
        self.update_world()
        self.check_camera_death()
        if not self.is_alive:
            return
        self.game_tick += 1
        if self.replay.is_replaying:
            self.replay.advance_tick()
            if self.replay.has_finished():
                self.replay.stop_replay()
                self.show_toast("Koniec powtórki")
        self.update_hud()
        self.update()

    def finish_game(self):
        if not self.is_alive:
            return
        self.is_alive = False
        self.timer.stop()
        self.score_recorded.emit(self.score)
        self.show_end_screen()
        self.update()

    def show_end_screen(self):
        self.close_end_screen()
        self.end_screen = QFrame(self)
        self.end_screen.setGeometry(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.end_screen.setStyleSheet("background-color: rgba(5, 9, 16, 195);")
        panel = QFrame(self.end_screen)
        panel.setGeometry(56, 220, WINDOW_WIDTH - 112, 352)
        panel.setStyleSheet("background-color: #111c2b; border: 1px solid #304156; border-radius: 24px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 28, 28, 26)
        layout.setSpacing(14)
        title = QLabel("KONIEC GRY")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #ffffff; font-size: 30px; font-weight: 800; border: none;")
        score = QLabel(f"Twój wynik:  {self.score} pól")
        score.setAlignment(Qt.AlignCenter)
        score.setStyleSheet("color: #53e6a2; font-size: 22px; font-weight: 800; border: none;")
        mode = QLabel(f"Tryb: {self.preset['label']}  |  Osiągnięty poziom: {self.last_difficulty_step + 1}")
        mode.setAlignment(Qt.AlignCenter)
        mode.setStyleSheet("color: #9eb0c4; font-size: 12px; border: none;")
        restart = QPushButton("ZAGRAJ PONOWNIE")
        menu = QPushButton("WRÓĆ DO MENU")
        for button in [restart, menu]:
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedHeight(48)
            button.setStyleSheet("QPushButton { background-color: #223147; border: 1px solid #364b66; border-radius: 12px; color: white; font-weight: 800; font-size: 14px; } QPushButton:hover { border: 1px solid #53e6a2; background-color: #293a51; }")
        restart.setStyleSheet("QPushButton { background-color: #53e6a2; border: none; border-radius: 12px; color: #06140e; font-weight: 800; font-size: 14px; } QPushButton:hover { background-color: #6af0b2; }")
        restart.clicked.connect(self.restart_requested.emit)
        menu.clicked.connect(self.return_to_menu.emit)
        layout.addWidget(title)
        layout.addWidget(score)
        layout.addWidget(mode)
        layout.addSpacing(10)
        layout.addWidget(restart)
        layout.addWidget(menu)
        self.end_screen.show()
        self.end_screen.raise_()

    def close_end_screen(self):
        if self.end_screen is not None:
            self.end_screen.deleteLater()
            self.end_screen = None

    def check_water_collision(self):
        lane = self.lanes.get(self.player_world_row)
        if lane and lane.lane_type == LaneType.RIVER:
            for obs in lane.obstacles:
                player_x1 = self.player_col * TILE_SIZE + 5
                player_x2 = player_x1 + TILE_SIZE - 10
                if not (player_x2 <= obs.x or player_x1 >= obs.x + obs.width):
                    return obs
            return None
        return False

    def check_car_collision(self):
        lane = self.lanes.get(self.player_world_row)
        if lane and lane.lane_type == LaneType.ROAD:
            for obs in lane.obstacles:
                player_x1 = self.player_col * TILE_SIZE + 5
                player_x2 = player_x1 + TILE_SIZE - 10
                if not (player_x2 <= obs.x or player_x1 >= obs.x + obs.width):
                    return True
        return False

    def can_move(self, new_col, new_screen_row, new_world_row):
        lane = self.lanes.get(new_world_row)
        if lane is None:
            return False
        if lane.lane_type in [LaneType.RIVER, LaneType.ROAD]:
            return True
        for obs in lane.obstacles:
            if obs.solid:
                player_x1 = new_col * TILE_SIZE + 5
                player_x2 = player_x1 + TILE_SIZE - 10
                if not (player_x2 <= obs.x or player_x1 >= obs.x + obs.width):
                    return False
        return True

    def perform_move(self, move):
        old_col = self.player_col
        old_row = self.player_world_row
        if move == "UP":
            if self.check_water_collision() not in [None, False]:
                self.snap_to_grid()
            new_row = self.player_world_row - 1
            if self.can_move(self.player_col, self.player_screen_row, new_row):
                self.player_world_row = new_row
                self.update_world()
                self.update_difficulty()
        elif move == "DOWN":
            if self.check_water_collision() not in [None, False]:
                self.snap_to_grid()
            new_row = self.player_world_row + 1
            if self.can_move(self.player_col, self.player_screen_row, new_row):
                self.player_world_row = new_row
                self.update_world()
        elif move == "LEFT" and self.player_col > 0:
            new_col = self.player_col - 1
            if self.can_move(new_col, self.player_screen_row, self.player_world_row):
                self.player_col = new_col
        elif move == "RIGHT" and self.player_col < COLS - 1:
            new_col = self.player_col + 1
            if self.can_move(new_col, self.player_screen_row, self.player_world_row):
                self.player_col = new_col
        if self.player_col != old_col or self.player_world_row != old_row:
            self.logger.log("PLAYER_MOVE", f"move={move}, col={self.player_col}, row={-self.player_world_row}")
            self.update_hud()

    def start_replay(self):
        if self.replay.initial_state is None or not self.replay.recorded_moves or not self.is_alive:
            self.show_toast("Brak ruchów do odtworzenia")
            return
        self.restore_state(self.replay.initial_state)
        self.is_alive = True
        self.paused = False
        self.camera_y = (self.player_world_row - self.player_screen_row) * TILE_SIZE
        self.replay.start_replay()
        self.timer.start(16)
        self.show_toast("Odtwarzanie rozgrywki")
        self.setFocus()

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_P, Qt.Key_Escape]:
            self.toggle_pause()
            return
        if not self.is_alive or self.paused or self.replay.is_replaying:
            return
        if event.key() == Qt.Key_F1:
            self.debug_mode = not self.debug_mode
            self.update()
            return
        if event.key() == Qt.Key_S:
            self.save_current()
            return
        if event.key() == Qt.Key_L:
            self.load_current()
            return
        if event.key() == Qt.Key_R:
            self.start_replay()
            return
        moves = {
            Qt.Key_Up: "UP",
            Qt.Key_Down: "DOWN",
            Qt.Key_Left: "LEFT",
            Qt.Key_Right: "RIGHT",
        }
        if event.key() in moves:
            old_row = self.player_world_row
            old_col = self.player_col
            move = moves[event.key()]
            self.perform_move(move)
            if self.player_world_row != old_row or self.player_col != old_col:
                self.replay.record_move(self.game_tick, move)
        self.update()

    def generate_initial_lanes(self):
        min_row = self.player_world_row - self.player_screen_row
        max_row = min_row + ROWS_VISIBLE - 1
        for row in range(min_row, max_row + 1):
            lane = Lane(row, LaneType.SAFE) if row == self.player_world_row else self.generator.generate_lane(row, self.difficulty)
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
        for row in [row for row in self.lanes if row < min_row - 15 or row > max_row + 15]:
            del self.lanes[row]

    def paintEvent(self, event):
        painter = QPainter(self)
        self.draw_lanes(painter)
        if self.show_grid:
            self.draw_grid(painter)
        self.draw_obstacles(painter)
        self.draw_player(painter)
        if self.debug_mode:
            self.draw_debug(painter)

    def draw_lanes(self, painter):
        first_row = int(self.camera_y // TILE_SIZE) - 2
        last_row = first_row + ROWS_VISIBLE + 5
        for world_row in range(first_row, last_row + 1):
            lane = self.lanes.get(world_row)
            if not lane:
                continue
            y = int(world_row * TILE_SIZE - self.camera_y)
            texture = self.textures.get(lane.lane_type.name)
            if texture and not texture.isNull():
                for col in range(COLS):
                    painter.drawPixmap(col * TILE_SIZE, y, TILE_SIZE, TILE_SIZE, texture)
            else:
                colors = {"SAFE": QColor(80, 170, 90), "ROAD": QColor(70, 70, 70), "RIVER": QColor(50, 120, 220)}
                painter.fillRect(0, y, WINDOW_WIDTH, TILE_SIZE, colors[lane.lane_type.name])

    def draw_grid(self, painter):
        painter.setPen(QPen(QColor(255, 255, 255, 55)))
        first_row = int(self.camera_y // TILE_SIZE) - 2
        last_row = first_row + ROWS_VISIBLE + 5
        for world_row in range(first_row, last_row + 1):
            y = int(world_row * TILE_SIZE - self.camera_y)
            for col in range(COLS):
                painter.drawRect(col * TILE_SIZE, y, TILE_SIZE, TILE_SIZE)

    def draw_obstacles(self, painter):
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
                    painter.drawPixmap(int(obs.x), y, int(obs.width), int(obs.height), texture)
                else:
                    painter.fillRect(int(obs.x), y, int(obs.width), int(obs.height), QColor(obs.color))

    def draw_player(self, painter):
        x = int(self.player_col * TILE_SIZE + 5)
        y = int(self.player_world_row * TILE_SIZE - self.camera_y + 5)
        painter.drawPixmap(x, y, TILE_SIZE - 10, TILE_SIZE - 10, self.textures["player"])

    def draw_debug(self, painter):
        painter.setPen(Qt.red)
        painter.setFont(QFont("Consolas", 9))
        player_x = int(self.player_col * TILE_SIZE + 5)
        player_y = int(self.player_world_row * TILE_SIZE - self.camera_y + 5)
        painter.drawRect(player_x, player_y, TILE_SIZE - 10, TILE_SIZE - 10)
        painter.fillRect(8, 115, 180, 82, QColor(0, 0, 0, 170))
        painter.drawText(15, 135, "DEBUG MODE")
        painter.drawText(15, 154, f"Difficulty: {self.difficulty:.2f}")
        painter.drawText(15, 173, f"World row: {self.player_world_row}")
        painter.drawText(15, 192, f"Column: {self.player_col:.2f}")
