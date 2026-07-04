"""
Smart Folder Suggestions for the Desktop Organizer.
Maps files to the user's existing 00-99 folder system and suggests new folders.
"""
import json
import os
import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class FolderSuggestion:
    """Suggestion for where a file should be placed."""
    file_path: str
    file_name: str
    target_folder: str
    confidence: float  # 0.0 - 1.0
    is_existing_folder: bool = True
    new_folder_name: str = ""
    reasoning: str = ""

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "target_folder": self.target_folder,
            "confidence": self.confidence,
            "is_existing_folder": self.is_existing_folder,
            "new_folder_name": self.new_folder_name,
            "reasoning": self.reasoning,
        }


class FolderSuggester:
    """Suggests target folders based on existing folder system and file analysis."""

    def __init__(self, config: dict):
        self.config = config
        self.folder_mappings = config.get("folder_mappings", {})
        self.category_rules = config.get("category_rules", {})

        # Project-specific keyword -> folder mapping
        self.project_folder_map = {
            "TAC28": "01_东宝龙制造工作",
            "P019": "01_东宝龙制造工作",
            "CH5091": "01_东宝龙制造工作",
            "504000002145": "01_东宝龙制造工作",
            "东宝龙": "01_东宝龙制造工作",
            "制造": "01_东宝龙制造工作",
            "模具": "01_东宝龙制造工作",
            "订单": "02_外贸订单与客户资料",
            "报价": "02_外贸订单与客户资料",
            "合同": "02_外贸订单与客户资料",
            "客户": "02_外贸订单与客户资料",
            "外贸": "02_外贸订单与客户资料",
            "trade": "02_外贸订单与客户资料",
            "order": "02_外贸订单与客户资料",
        }

        # Extension -> folder mapping (highest confidence first)
        self.ext_folder_rules = [
            # CAD files
            ([".sldprt", ".sldasm", ".slddrw", ".dwg", ".dxf", ".step", ".stp", ".stl", ".igs", ".iges"],
             "04_图纸_3D_研发", 0.95, "CAD/engineering file"),
            # Office docs
            ([".xlsx", ".xlsm", ".xls"], "01_东宝龙制造工作", 0.6, "Excel spreadsheet (default: manufacturing)"),
            ([".doc", ".docx"], "01_东宝龙制造工作", 0.6, "Word document (default: manufacturing)"),
            ([".ppt", ".pptx"], "01_东宝龙制造工作", 0.6, "PowerPoint presentation"),
            ([".pdf"], "01_东宝龙制造工作", 0.5, "PDF document"),
            # Images
            ([".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".ico", ".svg"],
             "07_图片视频素材", 0.85, "Image file"),
            # Video/Audio
            ([".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"], "07_图片视频素材", 0.85, "Video file"),
            ([".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma"], "07_图片视频素材", 0.85, "Audio file"),
            # Code
            ([".py", ".js", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".ts", ".jsx", ".tsx"],
             "06_AI_Codex_自用应用", 0.9, "Code/development file"),
            # Archives
            ([".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"], "99_其他归档", 0.8, "Archive file"),
            # Text
            ([".txt", ".md", ".csv", ".log"], "01_东宝龙制造工作", 0.5, "Text file"),
            # Software/Installers
            ([".exe", ".msi", ".dmg", ".app"], "98_软件安装包与工具", 0.85, "Software installer/executable"),
        ]

        # Temp file detection
        self.temp_exts = {'.bak', '.err', '.tmp', '.log', '.swp', '.temp', '~'}

    def suggest_all(self, file_items: list, ai_results: list = None) -> list:
        """
        Generate folder suggestions for all files.

        Args:
            file_items: List of FileItem objects
            ai_results: Optional list of ClassificationResult from AI classifier

        Returns: List of FolderSuggestion objects
        """
        suggestions = []

        # Build AI result lookup
        ai_lookup = {}
        if ai_results:
            for cr in ai_results:
                ai_lookup[cr.file_path] = cr

        for fi in file_items:
            if fi.is_directory:
                continue

            # If AI already classified, use that with high weight
            if fi.path in ai_lookup:
                cr = ai_lookup[fi.path]
                suggestions.append(FolderSuggestion(
                    file_path=fi.path,
                    file_name=fi.name,
                    target_folder=cr.target_folder,
                    confidence=cr.confidence,
                    is_existing_folder=cr.target_folder in self.folder_mappings,
                    reasoning=cr.reasoning,
                ))
                continue

            # Rule-based suggestion
            suggestion = self._suggest_single(fi)
            suggestions.append(suggestion)

        return suggestions

    def _suggest_single(self, fi) -> FolderSuggestion:
        """Generate a folder suggestion for a single file."""
        name_lower = fi.name.lower()
        ext = fi.extension.lower()

        # 1. Check temp file patterns first
        if self._is_temp(fi):
            return FolderSuggestion(
                file_path=fi.path,
                file_name=fi.name,
                target_folder="03_草稿单_临时待处理",
                confidence=0.9,
                is_existing_folder=True,
                reasoning="Temp file detected",
            )

        # 2. Check file extension rules FIRST (more specific)
        for exts, folder, confidence, reason in self.ext_folder_rules:
            if ext in exts:
                # Special case: Excel/Word with trade keywords
                if ext in ['.xlsx', '.xlsm', '.xls', '.doc', '.docx', '.pdf']:
                    trade_kw = ["订单", "报价", "合同", "客户", "外贸", "invoice",
                                "quote", "order", "contract", "customer", "trade"]
                    if any(kw in name_lower for kw in trade_kw):
                        return FolderSuggestion(
                            file_path=fi.path,
                            file_name=fi.name,
                            target_folder="02_外贸订单与客户资料",
                            confidence=0.8,
                            is_existing_folder=True,
                            reasoning="Office doc with trade/order keywords",
                        )
                return FolderSuggestion(
                    file_path=fi.path,
                    file_name=fi.name,
                    target_folder=folder,
                    confidence=confidence,
                    is_existing_folder=True,
                    reasoning=reason,
                )

        # 3. Check project keywords in filename (for files not matched by extension)
        for keyword, folder in self.project_folder_map.items():
            if keyword.lower() in name_lower:
                return FolderSuggestion(
                    file_path=fi.path,
                    file_name=fi.name,
                    target_folder=folder,
                    confidence=0.8,
                    is_existing_folder=True,
                    reasoning=f"Project keyword '{keyword}' found in filename",
                )

        # 4. Default: misc archive
        return FolderSuggestion(
            file_path=fi.path,
            file_name=fi.name,
            target_folder="99_其他归档",
            confidence=0.3,
            is_existing_folder=True,
            reasoning="No specific match found, placed in misc archive",
        )

    def _is_temp(self, fi) -> bool:
        """Check if a file is a temp file."""
        ext = fi.extension.lower()
        name = fi.name.lower()

        if ext in self.temp_exts:
            return True
        if name.startswith('~'):
            return True
        # Hash-like names
        if re.match(r'^[0-9a-f]{32,}', name):
            return True
        # Common temp suffixes
        temp_suffixes = ['-bak', '_bak', '-backup', '_backup', '-copy', '_copy', '副本']
        for s in temp_suffixes:
            if s in name:
                return True
        return False

    def suggest_new_folders(self, suggestions: list) -> list:
        """
        Analyze suggestions and suggest new folders for files that
        don't fit well into existing ones (low confidence or in misc).
        """
        # Group low-confidence and misc placements
        misc_files = [
            s for s in suggestions
            if s.target_folder == "99_其他归档" or s.confidence < 0.5
        ]

        if not misc_files:
            return []

        # Group by extension
        ext_groups = defaultdict(list)
        for s in misc_files:
            ext = os.path.splitext(s.file_name)[1].lower()
            ext_groups[ext].append(s)

        new_folder_suggestions = []
        for ext, files in ext_groups.items():
            if len(files) >= 3:  # Only suggest if 3+ files share extension
                new_name = f"99_待分类{ext.upper()}_需要整理"
                new_folder_suggestions.append({
                    "folder_name": new_name,
                    "reason": f"{len(files)} files with extension {ext}",
                    "file_count": len(files),
                    "sample_files": [f.file_name for f in files[:5]],
                })

        return new_folder_suggestions

    def to_json(self, suggestions: list) -> str:
        """Export suggestions to JSON string."""
        data = {
            "generated_at": datetime.now().isoformat(),
            "total_files": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)
