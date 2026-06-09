"""Entry point: python -m bde_xbrl_editor"""

import multiprocessing
import sys


def _create_qapplication(argv: list[str]):
    from PySide6.QtWidgets import QApplication

    return QApplication(argv)


def _create_main_window():
    from bde_xbrl_editor.ui.app import create_app

    return create_app()


def main() -> None:
    multiprocessing.freeze_support()

    app = _create_qapplication(sys.argv)
    window = _create_main_window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
