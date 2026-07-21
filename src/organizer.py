"""
Organization Preview and Execution module for the Desktop Organizer.
Generates preview of desktop organization, handles file moves, and supports undo.
"""
import json
import os
import shutil
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass, field


@dataclass
class MoveOperation:
    """A single file move operation."""
    source_path: str
    dest_path: str
    file_name: str
    size_bytes: int
    status: str = "pending"  # pending, success, failed, skipped
    error: str = ""

    def to_dict(self):
        return {
            "source_path": self.source_path,
            "dest_path": self.dest_path,
            "file_name": self.file_name,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class OrganizationPreview:
    """Preview of what organization would look like."""
    total_files: int = 0
    files_to_move: int = 0
    files_to_delete: int = 0
    duplicates_to_resolve: int = 0
    estimated_space_savings: int = 0
    estimated_space_human: str = "0 B"
    risk_level: str = "low"  # low, medium, high
    operations: list = field(default_factory=list)  # List[MoveOperation]
    folder_summary: dict = field(default_factory=dict)  # folder -> count
    new_folders_needed: list = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self):
        return {
            "total_files": self.total_files,
            "files_to_move": self.files_to_move,
            "files_to_delete": self.files_to_delete,
            "duplicates_to_resolve": self.duplicates_to_resolve,
            "estimated_space_savings": self.estimated_space_savings,
            "estimated_space_human": self.estimated_space_human,
            "risk_level": self.risk_level,
            "operations_count": len(self.operations),
            "folder_summary": self.folder_summary,
            "new_folders_needed": self.new_folders_needed,
            "generated_at": self.generated_at,
        }


class Organizer:
    """Generates organization previews and executes file moves with undo support."""

    def __init__(self, config: dict):
        self.config = config
        desktop_path = config.get("desktop_path") or os.path.expanduser("~/Desktop")
        self.desktop_path = os.path.abspath(os.path.expandvars(os.path.expanduser(desktop_path)))
        # Save journal in project root (one level up from src/)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_path = os.path.join(project_root, "organization_log.json")

    def generate_preview(
        self,
        scan_result,
        suggestions: list,
        temp_files: list = None,
    ) -> OrganizationPreview:
        """
        Generate a preview of what the desktop would look like after organizing.

        Args:
            scan_result: ScanResult from scanner
            suggestions: List of FolderSuggestion from folder_suggester
            temp_files: Optional list of FileItem temp files to delete

        Returns: OrganizationPreview
        """
        preview = OrganizationPreview()
        preview.generated_at = datetime.now().isoformat()
        preview.total_files = scan_result.total_files

        # Build suggestion lookup
        sug_lookup = {s.file_path: s for s in suggestions}

        # Create operations for files to move
        operations = []
        folder_summary = {}

        for fi in scan_result.files:
            if fi.is_directory:
                continue

            sug = sug_lookup.get(fi.path)
            if not sug:
                continue

            # Skip files already in their target folder
            if self._already_in_folder(fi.path, sug.target_folder):
                continue

            # Build destination path
            dest_dir = os.path.join(self.desktop_path, sug.target_folder)
            dest_path = os.path.join(dest_dir, fi.name)

            # Handle name conflicts
            dest_path = self._unique_dest(dest_path)

            op = MoveOperation(
                source_path=fi.path,
                dest_path=dest_path,
                file_name=fi.name,
                size_bytes=fi.size_bytes,
            )
            operations.append(op)

            # Track folder summary
            folder_summary[sug.target_folder] = folder_summary.get(sug.target_folder, 0) + 1

        preview.operations = operations
        preview.files_to_move = len(operations)
        preview.folder_summary = folder_summary

        # Temp files for deletion
        if temp_files:
            preview.files_to_delete = len(temp_files)
            preview.estimated_space_savings = sum(f.size_bytes for f in temp_files)

        # Space savings from moves
        preview.estimated_space_savings += sum(op.size_bytes for op in operations)

        from .utils import format_size
        preview.estimated_space_human = format_size(preview.estimated_space_savings)

        # Duplicates
        preview.duplicates_to_resolve = len(scan_result.duplicate_candidates)

        # Risk assessment
        preview.risk_level = self._assess_risk(preview)

        # New folders needed
        existing_folders = set(f.name for f in scan_result.folders if f.is_directory)
        needed = set(folder_summary.keys()) - existing_folders
        preview.new_folders_needed = list(needed)

        return preview

    def _already_in_folder(self, file_path: str, folder_name: str) -> bool:
        """Check if a file is already in the target folder."""
        parent = os.path.basename(os.path.dirname(file_path))
        return parent == folder_name

    def _unique_dest(self, dest_path: str) -> str:
        """Generate a unique destination path if file already exists."""
        if not os.path.exists(dest_path):
            return dest_path

        base, ext = os.path.splitext(dest_path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def _assess_risk(self, preview: OrganizationPreview) -> str:
        """Assess the risk level of the organization plan."""
        total_ops = preview.files_to_move + preview.files_to_delete
        if total_ops > 100:
            return "high"
        elif total_ops > 30:
            return "medium"
        return "low"

    def execute_organization(
        self,
        preview: OrganizationPreview,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        delete_temps: bool = True,
        temp_files: list = None,
    ) -> dict:
        """
        Execute the organization plan.

        Returns a journal of operations for undo support.
        """
        journal = {
            "timestamp": datetime.now().isoformat(),
            "operations": [],
            "folders_created": [],
            "temp_files_deleted": [],
        }

        total = len(preview.operations) + (len(temp_files) if temp_files and delete_temps else 0)
        done = 0

        # Create necessary folders
        folders_needed = set()
        for op in preview.operations:
            folder = os.path.dirname(op.dest_path)
            folders_needed.add(folder)

        for folder in folders_needed:
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                journal["folders_created"].append(folder)

        # Execute moves
        for op in preview.operations:
            done += 1
            if progress_callback:
                progress_callback(
                    int(done / total * 100) if total else 100,
                    f"Moving: {op.file_name}",
                )

            try:
                # Ensure source exists
                if not os.path.exists(op.source_path):
                    op.status = "skipped"
                    op.error = "Source file not found"
                    journal["operations"].append(op.to_dict())
                    continue

                # Create destination directory
                dest_dir = os.path.dirname(op.dest_path)
                os.makedirs(dest_dir, exist_ok=True)

                # Move file
                shutil.move(op.source_path, op.dest_path)
                op.status = "success"
                journal["operations"].append(op.to_dict())

            except Exception as e:
                op.status = "failed"
                op.error = str(e)
                journal["operations"].append(op.to_dict())

        # Delete temp files
        if temp_files and delete_temps:
            for fi in temp_files:
                done += 1
                if progress_callback:
                    progress_callback(
                        int(done / total * 100) if total else 100,
                        f"Deleting temp: {fi.name}",
                    )
                try:
                    if os.path.exists(fi.path):
                        os.remove(fi.path)
                        journal["temp_files_deleted"].append({
                            "path": fi.path,
                            "name": fi.name,
                            "size_bytes": fi.size_bytes,
                        })
                except Exception as e:
                    journal["temp_files_deleted"].append({
                        "path": fi.path,
                        "name": fi.name,
                        "error": str(e),
                    })

        # Save journal
        self._save_journal(journal)

        if progress_callback:
            progress_callback(100, "Organization complete!")

        return journal

    def undo_organization(self, journal_path: str = None) -> dict:
        """Undo a previous organization using the saved journal."""
        if journal_path is None:
            journal_path = self.log_path

        if not os.path.exists(journal_path):
            return {"error": "No journal file found"}

        with open(journal_path, "r", encoding="utf-8") as f:
            journal = json.load(f)

        undo_results = {"restored": 0, "failed": 0, "errors": []}

        # Undo moves (reverse order)
        for op in reversed(journal.get("operations", [])):
            if op.get("status") == "success":
                try:
                    src = op["dest_path"]
                    dst = op["source_path"]
                    # Ensure source directory exists
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
                    undo_results["restored"] += 1
                except Exception as e:
                    undo_results["failed"] += 1
                    undo_results["errors"].append(str(e))

        # Undo folder creation
        for folder in reversed(journal.get("folders_created", [])):
            try:
                if os.path.exists(folder) and not os.listdir(folder):
                    os.rmdir(folder)
            except Exception:
                pass

        return undo_results

    def _save_journal(self, journal: dict):
        """Save operation journal for undo support."""
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(journal, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save journal: {e}")

    def get_organization_summary(self, preview: OrganizationPreview) -> str:
        """Generate a human-readable summary of the preview."""
        lines = [
            f"📁 Organization Preview",
            f"{'=' * 40}",
            f"Total files on desktop: {preview.total_files}",
            f"Files to move: {preview.files_to_move}",
            f"Temp files to delete: {preview.files_to_delete}",
            f"Duplicates to review: {preview.duplicates_to_resolve}",
            f"Estimated space: {preview.estimated_space_human}",
            f"Risk level: {preview.risk_level.upper()}",
            f"",
            f"📂 Target Folders:",
        ]
        for folder, count in sorted(preview.folder_summary.items(), key=lambda x: -x[1]):
            lines.append(f"  {folder}: {count} files")

        if preview.new_folders_needed:
            lines.append("")
            lines.append("🆕 New Folders Needed:")
            for folder in preview.new_folders_needed:
                lines.append(f"  {folder}")

        return "\n".join(lines)
