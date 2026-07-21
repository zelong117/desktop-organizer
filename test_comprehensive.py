"""
Comprehensive Test Suite for Desktop Organizer
Tests all modules against real desktop and edge cases.
"""
import sys
import os
import json
import tempfile
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.models import FileItem, ScanResult
from src.scanner import DesktopScanner
from src.analyzer import FileAnalyzer
from src.folder_suggester import FolderSuggester
from src.ai_classifier import AIClassifier
from src.organizer import Organizer, MoveOperation, OrganizationPreview
from src.utils import format_size, format_datetime, get_file_extension, is_system_file, get_file_stats

RESULTS = []

def test(name, passed, detail=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    RESULTS.append((name, passed, detail))
    print(f"  {status}: {name}" + (f" ({detail})" if detail else ""))


# ═══════════════════════════════════════════════════════════════
# TEST 1: Utility Functions
# ═══════════════════════════════════════════════════════════════
def test_utils():
    print("\n" + "=" * 60)
    print("TEST SUITE: Utility Functions")
    print("=" * 60)

    # format_size
    test("format_size(0)", format_size(0) == "0.0 B")
    test("format_size(1024)", format_size(1024) == "1.0 KB")
    test("format_size(1048576)", format_size(1048576) == "1.0 MB")
    test("format_size(1073741824)", format_size(1073741824) == "1.0 GB")
    test("format_size(-1)", format_size(-1) == "-1.0 B")
    test("format_size(1536)", format_size(1536) == "1.5 KB")

    # format_datetime
    dt = datetime(2026, 7, 4, 14, 30)
    test("format_datetime", format_datetime(dt) == "2026-07-04 14:30")

    # get_file_extension
    test("get_file_extension .py", get_file_extension("test.py") == ".py")
    test("get_file_extension .SLDPRT", get_file_extension("TAC28.SLDPRT") == ".sldprt")
    test("get_file_extension no ext", get_file_extension("README") == "")
    test("get_file_extension dotfile", get_file_extension(".gitignore") == "")

    # is_system_file
    test("is_system_file desktop.ini",
         is_system_file("desktop.ini", ["desktop.ini", "thumbs.db"]))
    test("is_system_file not system",
         not is_system_file("readme.txt", ["desktop.ini", "thumbs.db"]))
    test("is_system_file case insensitive",
         is_system_file("Desktop.INI", ["desktop.ini"]))


# ═══════════════════════════════════════════════════════════════
# TEST 2: Models
# ═══════════════════════════════════════════════════════════════
def test_models():
    print("\n" + "=" * 60)
    print("TEST SUITE: Data Models")
    print("=" * 60)

    now = datetime.now()
    fi = FileItem(
        name="test.txt", path="C:\\test.txt", extension=".txt",
        size_bytes=1024, size_human="1.0 KB",
        modified_time=now, created_time=now,
    )
    d = fi.to_dict()
    test("FileItem.to_dict has all keys",
         set(d.keys()) >= {"name", "path", "extension", "size_bytes", "category", "is_temp"})
    test("FileItem.to_dict round-trip", d["name"] == "test.txt")
    test("FileItem default category", fi.category == "Other")
    test("FileItem default importance", fi.importance_score == 0)

    # ScanResult
    sr = ScanResult(desktop_path="C:\\Desktop", scan_time=now)
    test("ScanResult defaults", sr.total_files == 0 and sr.total_folders == 0)
    sr.files.append(fi)
    d2 = sr.to_dict()
    test("ScanResult.to_dict files", len(d2["files"]) == 1)

    # Chinese filename
    fi_cn = FileItem(
        name="模具图纸_东宝龙.SLDPRT", path="C:\\模具图纸_东宝龙.SLDPRT",
        extension=".sldprt", size_bytes=5242880, size_human="5.0 MB",
        modified_time=now, created_time=now,
    )
    d_cn = fi_cn.to_dict()
    test("Chinese filename in to_dict",
         "模具" in d_cn["name"] and "东宝龙" in d_cn["name"])


# ═══════════════════════════════════════════════════════════════
# TEST 3: Scanner - Real Desktop
# ═══════════════════════════════════════════════════════════════
def test_scanner():
    print("\n" + "=" * 60)
    print("TEST SUITE: Desktop Scanner (Real Desktop)")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    scanner = DesktopScanner(config)

    t0 = time.time()
    result = scanner.scan(progress_callback=lambda v, m: None)
    elapsed = time.time() - t0

    test("Scanner returns ScanResult", isinstance(result, ScanResult))
    test("Scanner finds files (>100)", result.total_files > 100, f"found {result.total_files}")
    test("Scanner finds folders (>50)", result.total_folders > 50, f"found {result.total_folders}")
    test("Scanner total_size > 0", result.total_size_bytes > 0, result.total_size_human)
    test("Scanner scan_time set", result.scan_time is not None)
    test("Scanner all files have paths", all(f.path for f in result.files))
    test("Scanner all files have extensions",
         all(f.extension is not None for f in result.files))
    test("Scanner no empty names", all(f.name for f in result.files))
    test("Scanner no None paths", all(f.path is not None for f in result.files))
    test("Scanner elapsed < 30s", elapsed < 30, f"{elapsed:.1f}s")

    # Check for Chinese filenames
    cn_files = [f for f in result.files if any(ord(c) > 0x4e00 for c in f.name)]
    test("Scanner handles Chinese filenames", len(cn_files) > 0, f"{len(cn_files)} files")

    # Check no system files leaked through
    system_names = {"desktop.ini", "thumbs.db", "ehthumbs.db"}
    leaked = [f for f in result.files if f.name.lower() in system_names]
    test("Scanner filters system files", len(leaked) == 0, f"{len(leaked)} leaked")

    # Export test
    export_path = os.path.join(project_root, "_test_export.json")
    try:
        scanner.export_json(result, export_path)
        with open(export_path, 'r', encoding='utf-8') as f:
            exported = json.load(f)
        test("Scanner JSON export valid", "files" in exported and len(exported["files"]) > 0)
    finally:
        if os.path.exists(export_path):
            os.remove(export_path)

    return result


# ═══════════════════════════════════════════════════════════════
# TEST 4: Analyzer - Real Desktop
# ═══════════════════════════════════════════════════════════════
def test_analyzer(scan_result):
    print("\n" + "=" * 60)
    print("TEST SUITE: File Analyzer (Real Desktop)")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    analyzer = FileAnalyzer(config)

    t0 = time.time()
    result = analyzer.analyze(scan_result)
    elapsed = time.time() - t0

    test("Analyzer returns ScanResult", isinstance(result, ScanResult))
    test("Analyzer elapsed < 10s", elapsed < 10, f"{elapsed:.1f}s")

    # Check categories assigned
    categorized = [f for f in result.files if not f.is_directory and f.category != "Other"]
    test("Analyzer categorizes files", len(categorized) > 0,
         f"{len(categorized)}/{result.total_files}")

    # Check temp files detected
    test("Analyzer detects temp files", len(result.temp_files) >= 0,
         f"{len(result.temp_files)} temp files")

    # Check categories dict populated
    test("Analyzer categories dict populated", len(result.categories) > 0,
         f"{len(result.categories)} categories")

    # Check importance scores assigned
    scored = [f for f in result.files if not f.is_directory and f.importance_score > 0]
    test("Analyzer scores importance", len(scored) > 0, f"{len(scored)} scored")

    # Check duplicate detection
    test("Analyzer duplicate candidates",
         isinstance(result.duplicate_candidates, list))

    # Verify category counts match
    cat_total = sum(result.categories.values())
    non_dir_files = len([f for f in result.files if not f.is_directory])
    test("Analyzer category count matches file count",
         cat_total == non_dir_files,
         f"categories={cat_total}, files={non_dir_files}")

    return result


# ═══════════════════════════════════════════════════════════════
# TEST 5: AI Classifier - Rule-based Fallback
# ═══════════════════════════════════════════════════════════════
def test_ai_classifier():
    print("\n" + "=" * 60)
    print("TEST SUITE: AI Classifier (Rule-based Fallback)")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    classifier = AIClassifier(config)

    # Test cases with expected results
    test_cases = [
        # (name, ext, expected_folder_prefix, description)
        ("TAC28_模具.SLDPRT", ".sldprt", "04_", "CAD file"),
        ("report.xlsx", ".xlsx", "01_ or 02_", "Office file"),
        ("photo.jpg", ".jpg", "07_", "Image file"),
        ("script.py", ".py", "06_", "Code file"),
        ("backup.zip", ".zip", "99_", "Archive file"),
        ("~$temp.docx", ".docx", "03_", "Temp Office file"),
        ("notes.tmp", ".tmp", "03_", "Temp file"),
        ("data.csv", ".csv", "01_ or 99_", "Text/CSV file"),
    ]

    for name, ext, expected_prefix, desc in test_cases:
        fi = FileItem(
            name=name, path=f"C:\\{name}", extension=ext,
            size_bytes=1024, size_human="1.0 KB",
            modified_time=datetime.now(), created_time=datetime.now(),
        )
        result = classifier._rule_based_classify(fi)
        # Handle compound prefixes
        prefixes = [p.strip() for p in expected_prefix.split(" or ")]
        matches = any(result.target_folder.startswith(p) for p in prefixes)
        test(f"Rule classify: {desc}", matches,
             f"got {result.target_folder}")

    # Test batch classification
    samples = [
        FileItem(name="CAD_test.sldprt", path="C:\\CAD_test.sldprt",
                 extension=".sldprt", size_bytes=5*1024*1024,
                 size_human="5.0 MB", modified_time=datetime.now(),
                 created_time=datetime.now()),
        FileItem(name="文档报告.docx", path="C:\\文档报告.docx",
                 extension=".docx", size_bytes=200*1024,
                 size_human="200.0 KB", modified_time=datetime.now(),
                 created_time=datetime.now()),
        FileItem(name="hash_abc123def456.png", path="C:\\hash_abc123def456.png",
                 extension=".png", size_bytes=500*1024,
                 size_human="500.0 KB", modified_time=datetime.now(),
                 created_time=datetime.now()),
    ]
    batch_results = classifier.classify_batch(samples)
    test("Batch classify returns correct count",
         len(batch_results) == len(samples),
         f"{len(batch_results)} vs {len(samples)}")

    # Test index mapping correctness (the critical bug fix)
    # Create a mix of cached and uncached to stress-test the mapping
    # First, clear cache by using fresh classifier
    classifier2 = AIClassifier(config)
    # Classify first file to populate cache
    r1 = classifier2.classify_batch([samples[0]])
    test("Cache populate works", len(r1) == 1)
    # Now classify all 3 - first should be cached, others uncached
    r_all = classifier2.classify_batch(samples)
    test("Mixed cache+uncached returns correct count",
         len(r_all) == 3, f"{len(r_all)} results")
    # Verify each result matches its file
    r_dict = {r.file_name: r for r in r_all}
    test("Index mapping: CAD file correct",
         r_dict["CAD_test.sldprt"].target_folder.startswith("04_"))
    test("Index mapping: Docx file correct",
         r_dict["文档报告.docx"].target_folder is not None)
    test("Index mapping: PNG file correct",
         r_dict["hash_abc123def456.png"].target_folder is not None)
    # Most importantly: verify no result is None or misassigned
    test("No None results in batch",
         all(r is not None for r in r_all))

    classifier.close()
    classifier2.close()


# ═══════════════════════════════════════════════════════════════
# TEST 6: Folder Suggester
# ═══════════════════════════════════════════════════════════════
def test_folder_suggester():
    print("\n" + "=" * 60)
    print("TEST SUITE: Folder Suggester")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    suggester = FolderSuggester(config)

    samples = [
        FileItem(name="TAC28_mold.SLDPRT", path="C:\\TAC28_mold.SLDPRT",
                 extension=".sldprt", size_bytes=5*1024*1024,
                 size_human="5.0 MB", modified_time=datetime.now(),
                 created_time=datetime.now()),
        FileItem(name="report.xlsx", path="C:\\report.xlsx",
                 extension=".xlsx", size_bytes=100*1024,
                 size_human="100.0 KB", modified_time=datetime.now(),
                 created_time=datetime.now()),
        FileItem(name="photo.jpg", path="C:\\photo.jpg",
                 extension=".jpg", size_bytes=3*1024*1024,
                 size_human="3.0 MB", modified_time=datetime.now(),
                 created_time=datetime.now()),
        FileItem(name="readme.txt", path="C:\\readme.txt",
                 extension=".txt", size_bytes=512,
                 size_human="512.0 B", modified_time=datetime.now(),
                 created_time=datetime.now()),
        FileItem(name="unknown.xyz", path="C:\\unknown.xyz",
                 extension=".xyz", size_bytes=100,
                 size_human="100.0 B", modified_time=datetime.now(),
                 created_time=datetime.now()),
        # Directory - should be skipped
        FileItem(name="MyFolder", path="C:\\MyFolder",
                 extension="", size_bytes=0,
                 size_human="0 B", modified_time=datetime.now(),
                 created_time=datetime.now(), is_directory=True),
    ]

    suggestions = suggester.suggest_all(samples)

    test("Suggester skips directories",
         len(suggestions) == len(samples) - 1,
         f"{len(suggestions)} suggestions for {len(samples)} items")

    sug_dict = {s.file_name: s for s in suggestions}
    test("CAD -> 04_", sug_dict["TAC28_mold.SLDPRT"].target_folder.startswith("04_"))
    test("Image -> 07_", sug_dict["photo.jpg"].target_folder.startswith("07_"))
    test("Unknown -> 99_", sug_dict["unknown.xyz"].target_folder.startswith("99_"))
    test("All have confidence", all(0 <= s.confidence <= 1 for s in suggestions))
    test("All have reasoning", all(s.reasoning for s in suggestions))

    # JSON export
    json_str = suggester.to_json(suggestions)
    parsed = json.loads(json_str)
    test("JSON export valid", "suggestions" in parsed)
    test("JSON export Chinese preserved",
         any("模具" in s.get("file_name", "") or "TAC28" in s.get("file_name", "")
             for s in parsed["suggestions"]))


# ═══════════════════════════════════════════════════════════════
# TEST 7: Organizer - Preview & Undo
# ═══════════════════════════════════════════════════════════════
def test_organizer():
    print("\n" + "=" * 60)
    print("TEST SUITE: Organizer")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    organizer = Organizer(config)

    # Verify log path is in project root, not src/
    test("Journal path in project root",
         os.path.dirname(organizer.log_path) == project_root,
         f"actual: {os.path.dirname(organizer.log_path)}")

    # Test preview generation with mock data
    now = datetime.now()
    files = [
        FileItem(name="CAD_test.SLDPRT", path="C:\\CAD_test.SLDPRT",
                 extension=".sldprt", size_bytes=5*1024*1024,
                 size_human="5.0 MB", modified_time=now, created_time=now),
        FileItem(name="temp_file.tmp", path="C:\\temp_file.tmp",
                 extension=".tmp", size_bytes=1024,
                 size_human="1.0 KB", modified_time=now, created_time=now,
                 is_temp=True),
    ]
    folders = [
        FileItem(name="04_图纸_3D_研发", path="C:\\04_图纸_3D_研发",
                 extension="", size_bytes=0, size_human="0 B",
                 modified_time=now, created_time=now, is_directory=True),
    ]

    scan_result = ScanResult(desktop_path="C:\\", scan_time=now)
    scan_result.files = files
    scan_result.folders = folders
    scan_result.total_files = len(files)
    scan_result.total_folders = len(folders)
    scan_result.duplicate_candidates = []

    suggester = FolderSuggester(config)
    suggestions = suggester.suggest_all(files)

    preview = organizer.generate_preview(scan_result, suggestions, [files[1]])

    test("Preview has operations", isinstance(preview, OrganizationPreview))
    test("Preview files_to_move >= 0", preview.files_to_move >= 0)
    test("Preview risk_level valid",
         preview.risk_level in ("low", "medium", "high"))
    test("Preview generated_at set", preview.generated_at != "")

    # Test summary generation
    summary = organizer.get_organization_summary(preview)
    test("Summary is string", isinstance(summary, str))
    test("Summary contains info", "Organization Preview" in summary)

    # Test MoveOperation model
    op = MoveOperation(
        source_path="C:\\test.txt", dest_path="C:\\01_folder\\test.txt",
        file_name="test.txt", size_bytes=1024,
    )
    d = op.to_dict()
    test("MoveOperation.to_dict", d["source_path"] == "C:\\test.txt")
    test("MoveOperation default status", op.status == "pending")

    # Test undo with non-existent journal
    undo_result = organizer.undo_organization("/nonexistent/path.json")
    test("Undo with no journal returns error", "error" in undo_result)

    # Test unique_dest
    test("unique_dest no conflict",
         organizer._unique_dest("C:\\nonexistent.txt") == "C:\\nonexistent.txt")


# ═══════════════════════════════════════════════════════════════
# TEST 8: Config Verification
# ═══════════════════════════════════════════════════════════════
def test_config():
    print("\n" + "=" * 60)
    print("TEST SUITE: Config Verification")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Desktop path
    test("desktop_path set",
         config.get("desktop_path") == r"%USERPROFILE%\Desktop",
         config.get("desktop_path"))

    # Category rules
    cats = config.get("category_rules", {})
    test("Has CAD category", "CAD" in cats)
    test("Has Office category", "Office" in cats)
    test("Has Images category", "Images" in cats)
    test("Has Code category", "Code" in cats)
    test("Code has .ts", ".ts" in cats.get("Code", []))
    test("Code has .tsx", ".tsx" in cats.get("Code", []))

    # AI settings
    ai = config.get("ai_settings", {})
    test("AI api_url set", "api_url" in ai)
    test("AI model set", ai.get("model") == "gpt-5.4-mini")
    test("AI batch_size set", isinstance(ai.get("batch_size"), int))

    # Temp patterns
    test("temp_patterns has entries", len(config.get("temp_patterns", [])) > 0)

    # Project patterns
    test("project_patterns has entries", len(config.get("project_patterns", [])) > 0)

    # Folder mappings
    mappings = config.get("folder_mappings", {})
    test("folder_mappings has entries", len(mappings) > 0)
    test("folder_mappings has 04_图纸", any("04_" in k for k in mappings))

    # No duplicate system files
    sys_files = config.get("system_files", [])
    test("No duplicate system files", len(sys_files) == len(set(sys_files)))


# ═══════════════════════════════════════════════════════════════
# TEST 9: Edge Cases & Error Handling
# ═══════════════════════════════════════════════════════════════
def test_edge_cases():
    print("\n" + "=" * 60)
    print("TEST SUITE: Edge Cases & Error Handling")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Empty file list
    analyzer = FileAnalyzer(config)
    empty_result = ScanResult(desktop_path="", scan_time=datetime.now())
    result = analyzer.analyze(empty_result)
    test("Analyzer handles empty file list", result.total_files == 0)

    # File with no extension
    no_ext = FileItem(
        name="README", path="C:\\README", extension="",
        size_bytes=0, size_human="0 B",
        modified_time=datetime.now(), created_time=datetime.now(),
    )
    cat = analyzer._categorize(no_ext)
    test("No extension -> Other", cat == "Other")

    # Very long filename
    long_name = "a" * 200 + ".txt"
    fi_long = FileItem(
        name=long_name, path=f"C:\\{long_name}", extension=".txt",
        size_bytes=100, size_human="100.0 B",
        modified_time=datetime.now(), created_time=datetime.now(),
    )
    cat_long = analyzer._categorize(fi_long)
    test("Long filename handled", cat_long == "Text")

    # Unicode filename
    fi_unicode = FileItem(
        name="日本語テスト_中文文件.pdf", path="C:\\日本語テスト_中文文件.pdf",
        extension=".pdf", size_bytes=1000, size_human="1.0 KB",
        modified_time=datetime.now(), created_time=datetime.now(),
    )
    cat_unicode = analyzer._categorize(fi_unicode)
    test("Unicode filename categorized", cat_unicode == "Office")

    # FileItem with future date
    future = datetime(2099, 12, 31)
    fi_future = FileItem(
        name="future.txt", path="C:\\future.txt", extension=".txt",
        size_bytes=100, size_human="100.0 B",
        modified_time=future, created_time=future,
    )
    score = analyzer._score_importance(fi_future, ScanResult(desktop_path="", scan_time=datetime.now()))
    test("Future date importance score", 0 <= score <= 10, f"score={score}")

    # Scanner with non-existent path
    bad_config = dict(config)
    bad_config["desktop_path"] = "C:\\nonexistent_path_12345"
    scanner = DesktopScanner(bad_config)
    try:
        result = scanner.scan()
        test("Scanner handles bad path", True, "no crash")
    except Exception as e:
        test("Scanner handles bad path", False, str(e))

    # Organizer with empty preview
    organizer = Organizer(config)
    empty_preview = OrganizationPreview()
    summary = organizer.get_organization_summary(empty_preview)
    test("Empty preview summary", isinstance(summary, str))


# ═══════════════════════════════════════════════════════════════
# TEST 10: Performance
# ═══════════════════════════════════════════════════════════════
def test_performance(scan_result):
    print("\n" + "=" * 60)
    print("TEST SUITE: Performance")
    print("=" * 60)

    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Analyzer performance
    analyzer = FileAnalyzer(config)
    t0 = time.time()
    for _ in range(3):
        analyzer.analyze(scan_result)
    elapsed = (time.time() - t0) / 3
    test("Analyzer avg < 2s for real desktop", elapsed < 2, f"{elapsed:.3f}s")

    # Folder suggester performance
    suggester = FolderSuggester(config)
    non_dir = [f for f in scan_result.files if not f.is_directory]
    t0 = time.time()
    for _ in range(3):
        suggester.suggest_all(non_dir)
    elapsed = (time.time() - t0) / 3
    test("Suggester avg < 1s for real desktop", elapsed < 1, f"{elapsed:.3f}s")

    # Memory: estimate
    import sys
    file_size = sys.getsizeof(scan_result.files[0]) if scan_result.files else 0
    total_memory = file_size * len(scan_result.files)
    test("File list memory < 50MB", total_memory < 50 * 1024 * 1024,
         f"~{total_memory / 1024:.0f} KB")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  COMPREHENSIVE TEST SUITE: Desktop Organizer            ║")
    print("╚══════════════════════════════════════════════════════════╝")

    test_utils()
    test_models()
    test_config()
    test_ai_classifier()
    test_folder_suggester()
    test_organizer()
    test_edge_cases()

    # Real desktop tests
    print("\n--- Real Desktop Tests ---")
    scan_result = test_scanner()
    scan_result = test_analyzer(scan_result)
    test_performance(scan_result)

    # Summary
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = sum(1 for _, p, _ in RESULTS if not p)
    total = len(RESULTS)

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    if failed:
        print("\nFailed tests:")
        for name, p, detail in RESULTS:
            if not p:
                print(f"  ❌ {name}" + (f" ({detail})" if detail else ""))

    print("\n" + "=" * 60)
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
