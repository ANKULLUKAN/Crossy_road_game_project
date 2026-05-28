import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from app_window import MainWindow


def main():
    os.chdir(Path(__file__).resolve().parent)
    app = QApplication(sys.argv)
    app.setApplicationName("Crossy Road Deluxe")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
