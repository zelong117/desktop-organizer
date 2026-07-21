"""
Desktop Organizer - AI-Powered File Management
Main entry point for the application.
"""
import sys
import json
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase

from src.gui.main_window import MainWindow


def resolve_desktop_path(path: str | None) -> str:
    """Resolve config desktop path, defaulting to the current user's Desktop."""
    path = path or os.path.expanduser("~/Desktop")
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def preferred_ui_font() -> QFont:
    """Return a Windows-friendly Chinese UI font with sensible fallbacks."""
    families = set(QFontDatabase.families())
    for family in ("Microsoft YaHei UI", "Microsoft YaHei", "微软雅黑", "Segoe UI"):
        if family in families:
            return QFont(family, 10)
    return QFont("Arial", 10)


def load_config() -> dict:
    """Load configuration from config.json."""
    config_path = os.path.join(project_root, "config.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config not found at {config_path}, using defaults")
        config = {
            "desktop_path": os.path.expanduser("~/Desktop"),
            "max_depth": 3,
            "skip_system_files": True,
            "system_files": ["desktop.ini", "thumbs.db", "ehthumbs.db"],
            "category_rules": {},
            "temp_patterns": [],
            "project_patterns": []
        }
    
    config["desktop_path"] = resolve_desktop_path(config.get("desktop_path"))
    return config


def main():
    """Main application entry point."""
    # High DPI support
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("桌面智能整理器")
    app.setOrganizationName("AI Desktop Tools")
    
    # Set default font
    app.setFont(preferred_ui_font())
    
    # Load configuration
    config = load_config()
    
    # Create and show main window
    window = MainWindow(config)
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
