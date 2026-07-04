"""
Desktop file scanner module.
Recursively scans the desktop and collects file information.
"""
import os
import json
import time
from datetime import datetime
from typing import Callable, Optional

from .models import FileItem, ScanResult
from .utils import format_size, get_file_extension, is_system_file


class DesktopScanner:
    """Scans the desktop directory recursively."""
    
    def __init__(self, config: dict):
        self.config = config
        self.desktop_path = config.get("desktop_path", os.path.expanduser("~/Desktop"))
        self.max_depth = config.get("max_depth", 3)
        self.system_files = config.get("system_files", [])
        self.skip_system = config.get("skip_system_files", True)
    
    def scan(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> ScanResult:
        """
        Scan the desktop directory.
        
        Args:
            progress_callback: Optional callback(current, message) for progress updates
            
        Returns:
            ScanResult with all discovered files and folders
        """
        result = ScanResult(
            desktop_path=self.desktop_path,
            scan_time=datetime.now()
        )
        
        # First pass: count files for progress (lightweight, avoids double I/O on small dirs)
        if progress_callback:
            progress_callback(0, "Counting files...")
        
        try:
            file_count = self._count_files(self.desktop_path, 0)
        except Exception as e:
            import sys
            print(f"Error counting files: {e}", file=sys.stderr)
            file_count = 800  # reasonable fallback for typical desktop
        
        if progress_callback:
            progress_callback(5, f"Found {file_count} items to scan...")
        
        # Second pass: collect file info
        scanned = 0
        scanned = self._scan_directory(
            self.desktop_path, result, 0, 
            progress_callback, file_count, scanned
        )
        
        # Calculate totals
        result.total_files = len(result.files)
        result.total_folders = len(result.folders)
        result.total_size_bytes = sum(f.size_bytes for f in result.files)
        result.total_size_human = format_size(result.total_size_bytes)
        
        if progress_callback:
            progress_callback(100, f"Scan complete: {result.total_files} files, {result.total_folders} folders")
        
        return result
    
    def _count_files(self, path: str, depth: int) -> int:
        """Count files for progress bar."""
        if depth > self.max_depth:
            return 0
        
        count = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file():
                    count += 1
                elif entry.is_dir() and depth < self.max_depth:
                    count += 1 + self._count_files(entry.path, depth + 1)
        except (PermissionError, OSError):
            pass
        
        return count
    
    def _scan_directory(self, path: str, result: ScanResult, depth: int,
                       progress_callback, total_files: int, scanned: int) -> int:
        """Recursively scan a directory."""
        if depth > self.max_depth:
            return scanned
        
        try:
            entries = list(os.scandir(path))
        except (PermissionError, OSError) as e:
            import sys
            print(f"Cannot access {path}: {e}", file=sys.stderr)
            return scanned
        
        for entry in entries:
            scanned += 1
            
            # Update progress
            if progress_callback and total_files > 0:
                progress = min(95, int(scanned / total_files * 95))
                progress_callback(progress, f"Scanning: {entry.name}")
            
            try:
                # Guard against broken symlinks / junctions on Windows
                try:
                    is_file = entry.is_file()
                    is_dir = entry.is_dir()
                except OSError:
                    continue

                if is_file:
                    file_item = self._create_file_item(entry)
                    if file_item:
                        result.files.append(file_item)
                
                elif is_dir:
                    # Skip system directories
                    if entry.name.startswith('.') or entry.name.lower() in ['__pycache__', '.git']:
                        continue
                    # Skip Windows junction/symlink loops
                    try:
                        real_path = os.path.realpath(entry.path)
                        if real_path.lower() != entry.path.lower() and depth > 0:
                            continue  # skip symlinks to avoid loops
                    except OSError:
                        pass
                    
                    folder_item = self._create_folder_item(entry)
                    if folder_item:
                        result.folders.append(folder_item)
                    
                    # Recurse into subdirectory
                    if depth < self.max_depth:
                        scanned = self._scan_directory(
                            entry.path, result, depth + 1,
                            progress_callback, total_files, scanned
                        )
            except (PermissionError, OSError) as e:
                import sys
                print(f"Error processing {entry.path}: {e}", file=sys.stderr)
                continue
        
        return scanned
    
    def _create_file_item(self, entry) -> Optional[FileItem]:
        """Create a FileItem from a directory entry."""
        try:
            stat = entry.stat()
            name = entry.name
            
            # Skip system files
            if self.skip_system and is_system_file(name, self.system_files):
                return None
            
            return FileItem(
                name=name,
                path=entry.path,
                extension=get_file_extension(name),
                size_bytes=stat.st_size,
                size_human=format_size(stat.st_size),
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                created_time=datetime.fromtimestamp(stat.st_ctime),
                is_directory=False
            )
        except (OSError, PermissionError):
            return None
    
    def _create_folder_item(self, entry) -> Optional[FileItem]:
        """Create a FileItem for a folder."""
        try:
            stat = entry.stat()
            
            # Count files in folder
            file_count = 0
            total_size = 0
            try:
                for sub_entry in os.scandir(entry.path):
                    if sub_entry.is_file():
                        file_count += 1
                        try:
                            total_size += sub_entry.stat().st_size
                        except OSError:
                            pass
            except OSError:
                pass
            
            return FileItem(
                name=entry.name,
                path=entry.path,
                extension="",
                size_bytes=total_size,
                size_human=format_size(total_size),
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                created_time=datetime.fromtimestamp(stat.st_ctime),
                is_directory=True,
                file_count=file_count
            )
        except (OSError, PermissionError):
            return None
    
    def export_json(self, result: ScanResult, output_path: str):
        """Export scan results to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
