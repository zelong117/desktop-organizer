"""
AI Classification Service for the Desktop Organizer.
Uses OpenAI-compatible API (rehdasu.cn, gpt-5.4-mini) to intelligently classify files.
Supports batch processing, caching, retry logic, and offline fallback.
"""
import json
import hashlib
import sqlite3
import os
import time
import re
from datetime import datetime, timedelta
from typing import Optional, Callable
from dataclasses import dataclass, field

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


@dataclass
class ClassificationResult:
    """Result of AI classification for a single file."""
    file_path: str
    file_name: str
    suggested_category: str
    confidence: float  # 0.0 - 1.0
    target_folder: str
    reasoning: str
    is_ai_classified: bool = True
    fallback_reason: str = ""

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "suggested_category": self.suggested_category,
            "confidence": self.confidence,
            "target_folder": self.target_folder,
            "reasoning": self.reasoning,
            "is_ai_classified": self.is_ai_classified,
            "fallback_reason": self.fallback_reason,
        }


class AIClassifier:
    """AI-powered file classification service."""

    def __init__(self, config: dict):
        self.config = config
        ai_cfg = config.get("ai_settings", {})
        cache_cfg = config.get("cache_settings", {})

        self.api_url = ai_cfg.get("api_url", "https://rehdasu.cn/v1")
        self.api_key_env = ai_cfg.get("api_key_env_var", "OPENAI_API_KEY")
        self.model = ai_cfg.get("model", "gpt-5.4-mini")
        self.batch_size = ai_cfg.get("batch_size", 15)
        self.max_tokens = ai_cfg.get("max_tokens", 2000)
        self.timeout = ai_cfg.get("timeout", 30)
        self.max_retries = ai_cfg.get("max_retries", 3)
        self.retry_delay = ai_cfg.get("retry_delay", 2)

        self.cache_enabled = cache_cfg.get("cache_enabled", True)
        self.cache_ttl_hours = cache_cfg.get("cache_ttl_hours", 168)

        self.folder_mappings = config.get("folder_mappings", {})
        self.category_rules = config.get("category_rules", {})

        # Reverse mapping: category -> folder name
        self._category_to_folder = self._build_category_folder_map()

        # Initialize cache
        self._init_cache()

    def _build_category_folder_map(self) -> dict:
        """Build a reverse lookup from category to target folder."""
        mapping = {}
        for folder_name, tags in self.folder_mappings.items():
            for tag in tags:
                mapping[tag.lower()] = folder_name
        # Direct category matches
        mapping["cad"] = "04_图纸_3D_研发"
        mapping["office"] = "01_东宝龙制造工作"
        mapping["images"] = "07_图片视频素材"
        mapping["video"] = "07_图片视频素材"
        mapping["code"] = "06_AI_Codex_自用应用"
        mapping["archives"] = "99_其他归档"
        mapping["text"] = "01_东宝龙制造工作"
        return mapping

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or config file."""
        key = os.environ.get(self.api_key_env)
        if key:
            return key

        # Try loading from a .env file or api_key.txt
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for fname in [".env", "api_key.txt"]:
            fpath = os.path.join(project_root, fname)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if "=" in content:
                        for line in content.splitlines():
                            if line.startswith(self.api_key_env + "="):
                                return line.split("=", 1)[1].strip().strip('"').strip("'")
                    elif content:
                        return content
        return None

    # ─── Cache ───────────────────────────────────────────────────────────

    def _init_cache(self):
        """Initialize SQLite cache database."""
        if not self.cache_enabled:
            self._cache_conn = None
            return

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cache_path = os.path.join(project_root, "cache.db")
        self._cache_conn = sqlite3.connect(cache_path)
        self._cache_conn.execute("""
            CREATE TABLE IF NOT EXISTS classification_cache (
                file_hash TEXT PRIMARY KEY,
                file_path TEXT,
                result_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._cache_conn.commit()

    @staticmethod
    def compute_file_hash(file_path: str, size_bytes: int, mtime) -> str:
        """Compute a hash from file path + size + mtime for cache key.

        Includes a version prefix so stale cache entries from older code
        are automatically invalidated.
        """
        _CACHE_VERSION = "v2"
        raw = f"{_CACHE_VERSION}|{file_path}|{size_bytes}|{mtime}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _cache_get(self, file_hash: str) -> Optional[dict]:
        """Retrieve cached classification."""
        if not self._cache_conn:
            return None
        try:
            cur = self._cache_conn.execute(
                "SELECT result_json, created_at FROM classification_cache WHERE file_hash = ?",
                (file_hash,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            result_json, created_at = row
            created_dt = datetime.fromisoformat(created_at)
            if datetime.now() - created_dt > timedelta(hours=self.cache_ttl_hours):
                return None  # expired
            return json.loads(result_json)
        except Exception:
            return None

    def _cache_put(self, file_hash: str, file_path: str, result: dict):
        """Store classification in cache."""
        if not self._cache_conn:
            return
        try:
            self._cache_conn.execute(
                "INSERT OR REPLACE INTO classification_cache (file_hash, file_path, result_json, created_at) VALUES (?, ?, ?, ?)",
                (file_hash, file_path, json.dumps(result, ensure_ascii=False), datetime.now().isoformat()),
            )
            self._cache_conn.commit()
        except Exception:
            pass

    # ─── API Calls ───────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        return (
            "You are an expert file organizer for an industrial manufacturing company "
            "(机械/模具/外贸) in China. The user's desktop has CAD files, Office documents, "
            "project files, images, software, and temp files. Their existing folder system "
            "uses numbered folders (00-99). You classify files and suggest which folder "
            "they belong to. Always respond in valid JSON."
        )

    def _build_batch_prompt(self, files_metadata: list) -> str:
        """Build prompt for batch classification."""
        folders = list(self.folder_mappings.keys())

        files_desc = []
        for i, fm in enumerate(files_metadata, 1):
            files_desc.append(
                f'{i}. name="{fm["name"]}", ext="{fm["extension"]}", '
                f'size={fm["size_human"]}, category="{fm.get("existing_category", "Other")}", '
                f'path="{fm.get("relative_path", fm["name"])}"'
            )

        files_text = "\n".join(files_desc)
        folders_text = "\n".join(f"  - {f}" for f in folders)

        return (
            f"Classify these {len(files_metadata)} files into folders.\n\n"
            f"Available folders:\n{folders_text}\n\n"
            f"Files:\n{files_text}\n\n"
            'Return a JSON array. Each element must have:\n'
            '  "file_index": (number matching the list above)\n'
            '  "suggested_category": (short category like "CAD", "Office", "Temp", etc.)\n'
            '  "confidence": (0.0-1.0)\n'
            '  "target_folder": (exact folder name from the list above, or a NEW folder name if none fit)\n'
            '  "reasoning": (brief explanation in English)\n\n'
            "Return ONLY the JSON array, no extra text."
        )

    def _call_api(self, prompt: str) -> Optional[str]:
        """Call the OpenAI-compatible API with retry logic."""
        api_key = self._get_api_key()
        if not api_key:
            return None

        if not HAS_REQUESTS:
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
        }

        url = f"{self.api_url}/chat/completions"

        for attempt in range(self.max_retries):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    print(f"API call failed after {self.max_retries} attempts: {e}")
                    return None
        return None

    def _parse_ai_response(self, response_text: str) -> list:
        """Parse AI JSON response, handling markdown code fences."""
        text = response_text.strip()
        # Strip markdown fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines if they are fences
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            # Try to find JSON array in text
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return []

    # ─── Offline / Rule-Based Fallback ───────────────────────────────────

    def _rule_based_classify(self, file_item) -> ClassificationResult:
        """Offline rule-based fallback classification."""
        ext = file_item.extension.lower()
        name = file_item.name.lower()

        # Determine category from extension
        category = "Other"
        for cat, exts in self.category_rules.items():
            if ext in [e.lower() for e in exts]:
                category = cat
                break

        # Temp file check
        is_temp = False
        temp_exts = ['.bak', '.err', '.tmp', '.log', '.swp', '.temp']
        if ext in temp_exts or name.startswith('~') or name.startswith('~$') or name.startswith('temp'):
            is_temp = True
            category = "Temp"

        # Project pattern check
        project_match = None
        for pat in self.config.get("project_patterns", []):
            m = re.search(pat, file_item.name, re.IGNORECASE)
            if m:
                project_match = m.group(0)
                break

        # Determine folder
        if is_temp:
            folder = "03_草稿单_临时待处理"
            confidence = 0.9
            reasoning = "Temp file detected by extension/pattern"
        elif category == "CAD":
            folder = "04_图纸_3D_研发"
            confidence = 0.95
            reasoning = f"CAD file (extension {ext})"
        elif category == "Images":
            folder = "07_图片视频素材"
            confidence = 0.85
            reasoning = f"Image file (extension {ext})"
        elif category == "Video" or category == "Audio":
            folder = "07_图片视频素材"
            confidence = 0.85
            reasoning = f"Media file (extension {ext})"
        elif category == "Code":
            folder = "06_AI_Codex_自用应用"
            confidence = 0.9
            reasoning = f"Code file (extension {ext})"
        elif category == "Archives":
            folder = "99_其他归档"
            confidence = 0.8
            reasoning = f"Archive file (extension {ext})"
        elif project_match:
            folder = "01_东宝龙制造工作"
            confidence = 0.85
            reasoning = f"Project file pattern detected: {project_match}"
        elif category == "Office":
            # Heuristic: check name for trade/order keywords
            trade_keywords = ["订单", "报价", "合同", "客户", "外贸", "order", "quote", "contract"]
            if any(kw in name for kw in trade_keywords):
                folder = "02_外贸订单与客户资料"
                confidence = 0.75
                reasoning = "Office doc with trade/order keywords"
            else:
                folder = "01_东宝龙制造工作"
                confidence = 0.7
                reasoning = f"Office document (extension {ext})"
        else:
            folder = "99_其他归档"
            confidence = 0.4
            reasoning = "No clear match, placed in misc archive"

        return ClassificationResult(
            file_path=file_item.path,
            file_name=file_item.name,
            suggested_category=category,
            confidence=confidence,
            target_folder=folder,
            reasoning=reasoning,
            is_ai_classified=False,
            fallback_reason="rule_based_offline",
        )

    # ─── Main Classification API ─────────────────────────────────────────

    def classify_batch(
        self,
        file_items: list,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> list:
        """
        Classify a list of FileItem objects.

        Returns a list of ClassificationResult, one per file.
        Uses cache, then AI in batches, falling back to rules.
        """
        results: list[Optional[ClassificationResult]] = []
        # Map: file_path -> index in results (only for non-directory files)
        path_to_result_idx: dict[str, int] = {}
        to_query_ai: list = []  # files needing AI/rule classification

        total = len(file_items)

        # Step 1: Check cache for each file; build results list with placeholders
        for i, fi in enumerate(file_items):
            if fi.is_directory:
                continue
            fhash = self.compute_file_hash(fi.path, fi.size_bytes, fi.modified_time.isoformat())
            cached = self._cache_get(fhash)
            result_idx = len(results)
            path_to_result_idx[fi.path] = result_idx
            if cached:
                results.append(ClassificationResult(**{
                    "file_path": cached["file_path"],
                    "file_name": cached["file_name"],
                    "suggested_category": cached["suggested_category"],
                    "confidence": cached["confidence"],
                    "target_folder": cached["target_folder"],
                    "reasoning": cached.get("reasoning", ""),
                    "is_ai_classified": cached.get("is_ai_classified", True),
                    "fallback_reason": cached.get("fallback_reason", ""),
                }))
                if progress_callback:
                    progress_callback(int((i + 1) / total * 100), f"Cache hit: {fi.name}")
            else:
                to_query_ai.append(fi)
                results.append(None)  # placeholder

        # Step 2: Try AI classification for uncached files
        ai_success = True
        api_key = self._get_api_key()
        if not api_key or not HAS_REQUESTS:
            ai_success = False

        if ai_success and to_query_ai:
            batches = [
                to_query_ai[j : j + self.batch_size]
                for j in range(0, len(to_query_ai), self.batch_size)
            ]
            batch_idx = 0
            for batch in batches:
                batch_idx += 1
                if progress_callback:
                    progress_callback(
                        0,
                        f"AI batch {batch_idx}/{len(batches)}: {len(batch)} files...",
                    )

                # Build metadata
                meta = []
                for fi in batch:
                    meta.append({
                        "name": fi.name,
                        "extension": fi.extension,
                        "size_human": fi.size_human,
                        "existing_category": fi.category,
                        "relative_path": os.path.basename(fi.path),
                    })

                prompt = self._build_batch_prompt(meta)
                response = self._call_api(prompt)

                if response:
                    parsed = self._parse_ai_response(response)
                    # Map results back using path_to_result_idx
                    ai_map = {}
                    for item in parsed:
                        idx = item.get("file_index", 0) - 1
                        if 0 <= idx < len(batch):
                            fi = batch[idx]
                            cr = ClassificationResult(
                                file_path=fi.path,
                                file_name=fi.name,
                                suggested_category=item.get("suggested_category", "Other"),
                                confidence=float(item.get("confidence", 0.5)),
                                target_folder=item.get("target_folder", "99_其他归档"),
                                reasoning=item.get("reasoning", ""),
                                is_ai_classified=True,
                            )
                            ai_map[fi.path] = cr
                            # Cache it
                            fhash = self.compute_file_hash(fi.path, fi.size_bytes, fi.modified_time.isoformat())
                            self._cache_put(fhash, fi.path, cr.to_dict())

                    # Fill in results at correct indices
                    for fi in batch:
                        if fi.path in ai_map and fi.path in path_to_result_idx:
                            results[path_to_result_idx[fi.path]] = ai_map[fi.path]
                else:
                    # AI failed for this batch, fall through to rules
                    pass

        # Step 3: Fill remaining None entries with rule-based fallback
        for fi in to_query_ai:
            if fi.path in path_to_result_idx:
                idx = path_to_result_idx[fi.path]
                if results[idx] is None:
                    cr = self._rule_based_classify(fi)
                    results[idx] = cr
                    fhash = self.compute_file_hash(fi.path, fi.size_bytes, fi.modified_time.isoformat())
                    self._cache_put(fhash, fi.path, cr.to_dict())

        # Filter out None (directories were never added)
        return [r for r in results if r is not None]

    def classify_single(self, file_item) -> ClassificationResult:
        """Classify a single file (convenience wrapper)."""
        results = self.classify_batch([file_item])
        return results[0] if results else self._rule_based_classify(file_item)

    def close(self):
        """Close cache connection."""
        if self._cache_conn:
            self._cache_conn.close()
            self._cache_conn = None
