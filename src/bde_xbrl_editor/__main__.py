"""Entry point: python -m bde_xbrl_editor"""

import sys


def main() -> None:
    from PySide6.QtWidgets import QApplication

    from bde_xbrl_editor.ui.app import create_app

    app = QApplication(sys.argv)
    window = create_app()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
