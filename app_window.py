from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from game import Game
from config import WINDOW_HEIGHT, WINDOW_WIDTH


PRESETS = {
    "easy": {
        "key": "easy",
        "name": "Spokojny",
        "label": "Łatwy",
        "description": "Wolniejsza kamera i łagodniejszy początek",
        "initial_difficulty": 0.15,
        "camera_speed": 0.20,
    },
    "normal": {
        "key": "normal",
        "name": "Klasyczny",
        "label": "Normalny",
        "description": "Zbalansowana rozgrywka i tempo przeszkód",
        "initial_difficulty": 0.50,
        "camera_speed": 0.30,
    },
    "hard": {
        "key": "hard",
        "name": "Hardcore",
        "label": "Trudny",
        "description": "Szybki start i agresywniejsze przeszkody",
        "initial_difficulty": 1.35,
        "camera_speed": 0.43,
    },
}


class DifficultyButton(QPushButton):
    def __init__(self, preset):
        super().__init__()
        self.preset = preset
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(78)
        self.setText(f"{preset['label']}\n{preset['description']}")
        self.setProperty("difficulty", True)


class MenuPage(QWidget):
    start_game = pyqtSignal(dict, bool)

    def __init__(self):
        super().__init__()
        self.selected_key = "normal"
        self.best_score = 0
        self.build_ui()

    def build_ui(self):
        self.setObjectName("menuPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#menuPage {
                background-color: #0d1420;
            }
            QWidget {
                background-color: #0d1420;
                color: #f1f5f9;
                font-family: Segoe UI;
            }
            QLabel#logo {
                color: #53e6a2;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#title {
                color: #ffffff;
                font-size: 38px;
                font-weight: 800;
            }
            QLabel#subtitle {
                color: #9aa7b8;
                font-size: 14px;
            }
            QFrame#panel {
                background-color: #121d2c;
                border: 1px solid #263348;
                border-radius: 20px;
            }
            QLabel#section {
                color: #dbe4ed;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton[difficulty="true"] {
                background-color: #172436;
                border: 1px solid #2b3b52;
                border-radius: 14px;
                color: #ced7e3;
                font-size: 12px;
                font-weight: 600;
                text-align: left;
                padding: 10px 14px;
            }
            QPushButton[difficulty="true"]:hover {
                border: 1px solid #4b617a;
                background-color: #1c2b40;
            }
            QPushButton[difficulty="true"]:checked {
                background-color: #16382f;
                border: 2px solid #53e6a2;
                color: #ffffff;
            }
            QCheckBox {
                color: #b8c4d2;
                font-size: 13px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 1px solid #44536a;
                background: #152131;
                border-radius: 5px;
            }
            QCheckBox::indicator:checked {
                border: 1px solid #53e6a2;
                background: #53e6a2;
                border-radius: 5px;
            }
            QPushButton#start {
                background-color: #53e6a2;
                border: none;
                border-radius: 15px;
                color: #07130e;
                font-size: 17px;
                font-weight: 800;
                padding: 16px;
            }
            QPushButton#start:hover {
                background-color: #6af0b2;
            }
            QLabel#best {
                background-color: #101b2b;
                border: 1px solid #253347;
                border-radius: 13px;
                color: #c8d3df;
                font-size: 13px;
                padding: 12px;
            }
            QLabel#controls {
                color: #7f8da1;
                font-size: 12px;
            }
        """)
        main = QVBoxLayout(self)
        main.setContentsMargins(34, 38, 34, 32)
        main.setSpacing(0)

        logo = QLabel("ARCADE PROJECT")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignCenter)
        title = QLabel("CROSSY ROAD")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        subtitle = QLabel("Przejdź jak najdalej, unikając ruchu ulicznego i rzek")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        main.addWidget(logo)
        main.addSpacing(10)
        main.addWidget(title)
        main.addSpacing(8)
        main.addWidget(subtitle)
        main.addSpacing(30)

        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        section = QLabel("WYBIERZ POZIOM TRUDNOŚCI")
        section.setObjectName("section")
        layout.addWidget(section)
        layout.addSpacing(4)

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        for key in ["easy", "normal", "hard"]:
            button = DifficultyButton(PRESETS[key])
            button.clicked.connect(lambda checked, selected=key: self.set_selected(selected))
            self.button_group.addButton(button)
            layout.addWidget(button)
            if key == self.selected_key:
                button.setChecked(True)

        layout.addSpacing(8)
        self.grid_checkbox = QCheckBox("Wyświetl siatkę pól podczas gry")
        self.grid_checkbox.setChecked(False)
        layout.addWidget(self.grid_checkbox)

        main.addWidget(panel)
        main.addSpacing(18)

        self.best_label = QLabel("Najlepszy wynik tej sesji: 0 pól")
        self.best_label.setObjectName("best")
        self.best_label.setAlignment(Qt.AlignCenter)
        main.addWidget(self.best_label)
        main.addSpacing(18)

        start = QPushButton("ROZPOCZNIJ GRĘ")
        start.setObjectName("start")
        start.setCursor(Qt.PointingHandCursor)
        start.clicked.connect(self.launch)
        main.addWidget(start)
        main.addStretch()

        controls = QLabel("Sterowanie: strzałki - ruch   |   P / Esc - pauza   |   F1 - debug")
        controls.setObjectName("controls")
        controls.setAlignment(Qt.AlignCenter)
        main.addWidget(controls)

    def set_selected(self, key):
        self.selected_key = key

    def launch(self):
        self.start_game.emit(PRESETS[self.selected_key], self.grid_checkbox.isChecked())

    def update_best_score(self, score):
        self.best_score = max(self.best_score, score)
        self.best_label.setText(f"Najlepszy wynik tej sesji: {self.best_score} pól")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Crossy Road Deluxe")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.menu = MenuPage()
        self.menu.start_game.connect(self.start_game)
        self.stack.addWidget(self.menu)
        self.current_game = None
        self.current_preset = PRESETS["normal"]
        self.current_grid = False

    def start_game(self, preset, show_grid):
        self.current_preset = preset
        self.current_grid = show_grid
        if self.current_game is not None:
            self.current_game.timer.stop()
            self.stack.removeWidget(self.current_game)
            self.current_game.deleteLater()
        self.current_game = Game(preset, show_grid)
        self.current_game.return_to_menu.connect(self.show_menu)
        self.current_game.restart_requested.connect(self.restart_game)
        self.current_game.score_recorded.connect(self.menu.update_best_score)
        self.stack.addWidget(self.current_game)
        self.stack.setCurrentWidget(self.current_game)
        self.current_game.setFocus()

    def restart_game(self):
        self.start_game(self.current_preset, self.current_grid)

    def show_menu(self):
        if self.current_game is not None:
            self.current_game.timer.stop()
        self.stack.setCurrentWidget(self.menu)
