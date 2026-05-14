import sys
from PyQt5.QtWidgets import QApplication
from game import Game


def main():
    
    app = QApplication(sys.argv)
    game = Game()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()