"""
Utility functions for the Desktop Organizer application.
"""
import os
from datetime import datetime
from typing import Optional


def format_size(size_bytes: float) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M")


def get_file_extension(filepath: str) -> str:
    """Get file extension (lowercase, with dot)."""
    _, ext = os.path.splitext(filepath)
    return ext.lower()


def is_system_file(filename: str, system_files: list) -> bool:
    """Check if a file is a system file to skip."""
    return filename.lower() in [sf.lower() for sf in system_files]


def get_file_stats(filepath: str) -> Optional[dict]:
    """Get file statistics including size and timestamps."""
    try:
        stat = os.stat(filepath)
        return {
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "created": datetime.fromtimestamp(stat.st_ctime),
        }
    except (OSError, PermissionError):
        return None
