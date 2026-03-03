import sys
from PySide6.QtWidgets import QApplication
from bitcraft_preview.ui.main_window import MainWindow
from bitcraft_preview.logging_setup import init_logging

def main():
    logger = init_logging()
    logger.info("Starting BitCraft Preview application")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
