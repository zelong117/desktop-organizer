"""
Data models for the Desktop Organizer application.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FileItem:
    """Represents a single file on the desktop."""
    name: str
    path: str
    extension: str
    size_bytes: int
    size_human: str
    modified_time: datetime
    created_time: datetime
    is_directory: bool = False
    file_count: int = 0  # for directories
    
    # Analysis results
    category: str = "Other"
    importance_score: int = 0  # 0-10
    is_temp: bool = False
    is_duplicate_candidate: bool = False
    project_pattern: Optional[str] = None
    
    def to_dict(self):
        return {
            "name": self.name,
            "path": self.path,
            "extension": self.extension,
            "size_bytes": self.size_bytes,
            "size_human": self.size_human,
            "modified_time": self.modified_time.isoformat(),
            "created_time": self.created_time.isoformat(),
            "is_directory": self.is_directory,
            "file_count": self.file_count,
            "category": self.category,
            "importance_score": self.importance_score,
            "is_temp": self.is_temp,
            "is_duplicate_candidate": self.is_duplicate_candidate,
            "project_pattern": self.project_pattern,
        }


@dataclass
class ScanResult:
    """Contains the complete scan results."""
    desktop_path: str
    scan_time: datetime
    total_files: int = 0
    total_folders: int = 0
    total_size_bytes: int = 0
    total_size_human: str = "0 B"
    files: list = field(default_factory=list)  # List[FileItem]
    folders: list = field(default_factory=list)  # List[FileItem]
    
    # Analysis results
    categories: dict = field(default_factory=dict)  # category -> count
    temp_files: list = field(default_factory=list)
    duplicate_candidates: list = field(default_factory=list)
    project_files: dict = field(default_factory=dict)  # pattern -> files
    
    def to_dict(self):
        return {
            "desktop_path": self.desktop_path,
            "scan_time": self.scan_time.isoformat(),
            "total_files": self.total_files,
            "total_folders": self.total_folders,
            "total_size_bytes": self.total_size_bytes,
            "total_size_human": self.total_size_human,
            "files": [f.to_dict() for f in self.files],
            "folders": [f.to_dict() for f in self.folders],
            "categories": self.categories,
            "temp_files": [f.name for f in self.temp_files],
            "duplicate_candidates": self.duplicate_candidates,
            "project_files": {k: [f.name for f in v] for k, v in self.project_files.items()},
        }
