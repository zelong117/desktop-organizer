"""
File analysis engine.
Categorizes files, detects patterns, and scores importance.
"""
import re
from collections import defaultdict
from datetime import datetime, timedelta

from .models import ScanResult, FileItem


class FileAnalyzer:
    """Analyzes scanned files for categorization and insights."""
    
    def __init__(self, config: dict):
        self.config = config
        self.category_rules = config.get("category_rules", {})
        self.temp_patterns = config.get("temp_patterns", [])
        self.project_patterns = config.get("project_patterns", [])
        # Precompute extension -> category lookup for O(1) categorization
        self._ext_to_category: dict[str, str] = {}
        for category, extensions in self.category_rules.items():
            for ext in extensions:
                self._ext_to_category[ext.lower()] = category
    
    def analyze(self, scan_result: ScanResult) -> ScanResult:
        """
        Analyze all files in the scan result.
        
        Modifies the scan_result in-place and returns it.
        """
        # Build lookup for duplicate detection
        name_groups = defaultdict(list)
        
        for file_item in scan_result.files:
            if not file_item.is_directory:
                # Categorize
                file_item.category = self._categorize(file_item)
                
                # Check for temp files
                file_item.is_temp = self._is_temp_file(file_item)
                
                # Detect project patterns
                file_item.project_pattern = self._detect_project_pattern(file_item)
                
                # Score importance
                file_item.importance_score = self._score_importance(file_item, scan_result)
                
                # Group by base name for duplicate detection
                base_name = self._get_base_name(file_item.name)
                name_groups[base_name].append(file_item)
        
        # Detect duplicates
        for base_name, files in name_groups.items():
            if len(files) > 1:
                for f in files:
                    f.is_duplicate_candidate = True
                scan_result.duplicate_candidates.append({
                    "base_name": base_name,
                    "files": [f.path for f in files]
                })
        
        # Build category summary
        scan_result.categories = defaultdict(int)
        for f in scan_result.files:
            if not f.is_directory:
                scan_result.categories[f.category] += 1
        
        # Collect temp files
        scan_result.temp_files = [f for f in scan_result.files if f.is_temp]
        
        # Group project files
        scan_result.project_files = defaultdict(list)
        for f in scan_result.files:
            if f.project_pattern:
                scan_result.project_files[f.project_pattern].append(f)
        
        return scan_result
    
    def _categorize(self, file_item: FileItem) -> str:
        """Determine the category of a file based on its extension."""
        ext = file_item.extension.lower()
        return self._ext_to_category.get(ext, "Other")
    
    def _is_temp_file(self, file_item: FileItem) -> bool:
        """Check if a file matches temp file patterns."""
        name = file_item.name
        
        # Check extension-based temp patterns
        temp_extensions = ['.bak', '.err', '.tmp', '.log', '.swp', '.temp']
        if file_item.extension.lower() in temp_extensions:
            return True
        
        # Check name patterns
        # Hash-like names (32+ hex chars)
        if re.match(r'^[0-9a-f]{32,}', name, re.IGNORECASE):
            return True
        
        # Files starting with ~
        if name.startswith('~'):
            return True
        
        # Files with common temp suffixes
        temp_suffixes = ['-bak', '_bak', '-backup', '_backup', '-copy', '_copy', '副本']
        name_lower = name.lower()
        for suffix in temp_suffixes:
            if suffix in name_lower:
                return True
        
        # Check against configured patterns
        for pattern in self.temp_patterns:
            if pattern.startswith('*') and pattern.endswith('*'):
                if pattern[1:-1] in name_lower:
                    return True
            elif pattern.startswith('*'):
                if name_lower.endswith(pattern[1:]):
                    return True
            elif pattern.endswith('*'):
                if name_lower.startswith(pattern[:-1]):
                    return True
        
        return False
    
    def _detect_project_pattern(self, file_item: FileItem) -> str:
        """Detect project number patterns in filename."""
        name = file_item.name
        
        for pattern_str in self.project_patterns:
            match = re.search(pattern_str, name, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _get_base_name(self, filename: str) -> str:
        """Get the base name without extension for duplicate detection."""
        # Remove extension
        base = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Remove common suffixes for comparison
        # e.g., "file (1)" -> "file", "file - 副本" -> "file"
        base = re.sub(r'\s*\(?\d+\)?$', '', base)
        base = re.sub(r'\s*[-_]副本\s*$', '', base)
        base = re.sub(r'\s*[-_]\s*copy\s*$', '', base, flags=re.IGNORECASE)
        
        return base.strip().lower()
    
    def _score_importance(self, file_item: FileItem, scan_result: ScanResult) -> int:
        """
        Score file importance from 0-10.
        
        Criteria:
        - File type (CAD/Office files are more important)
        - Project pattern presence
        - Recency of modification
        - File size
        - Whether it's in a subfolder
        """
        score = 5  # Base score
        
        # Category boost
        high_importance = ['CAD', 'Office']
        medium_importance = ['Code', 'Text']
        low_importance = ['Images', 'Archives']
        
        if file_item.category in high_importance:
            score += 2
        elif file_item.category in medium_importance:
            score += 1
        elif file_item.category in low_importance:
            score -= 1
        
        # Project pattern boost
        if file_item.project_pattern:
            score += 1
        
        # Recency boost
        days_old = (datetime.now() - file_item.modified_time).days
        if days_old < 7:
            score += 2
        elif days_old < 30:
            score += 1
        elif days_old > 365:
            score -= 1
        
        # Size considerations
        if file_item.size_bytes > 10 * 1024 * 1024:  # > 10MB
            score += 1  # Likely important if large
        elif file_item.size_bytes < 1024:  # < 1KB
            score -= 1  # Might be temp/insignificant
        
        # Temp file penalty
        if file_item.is_temp:
            score -= 3
        
        # Clamp to 0-10
        return max(0, min(10, score))
    
    def get_category_summary(self, scan_result: ScanResult) -> dict:
        """Get a summary of files by category."""
        summary = defaultdict(lambda: {"count": 0, "size_bytes": 0})
        
        for f in scan_result.files:
            if not f.is_directory:
                summary[f.category]["count"] += 1
                summary[f.category]["size_bytes"] += f.size_bytes
        
        return dict(summary)
