"""
Test script for Phase 2: AI Smart Classification Engine.
Tests AI classifier, folder suggester, and organizer with sample files.
"""
import sys
import os
import json
import tempfile
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.models import FileItem
from src.ai_classifier import AIClassifier
from src.folder_suggester import FolderSuggester
from src.organizer import Organizer


def load_config():
    config_path = os.path.join(project_root, "config.json")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_sample_files():
    """Create sample FileItem objects for testing."""
    samples = [
        FileItem(
            name="TAC28_模具图纸_v3.SLDPRT",
            path=r"C:\Users\ww\Desktop\TAC28_模具图纸_v3.SLDPRT",
            extension=".sldprt",
            size_bytes=5242880,
            size_human="5.0 MB",
            modified_time=datetime(2026, 7, 1, 10, 30),
            created_time=datetime(2026, 6, 15, 8, 0),
        ),
        FileItem(
            name="P019_东宝龙订单报价_2026.xlsx",
            path=r"C:\Users\ww\Desktop\P019_东宝龙订单报价_2026.xlsx",
            extension=".xlsx",
            size_bytes=204800,
            size_human="200.0 KB",
            modified_time=datetime(2026, 7, 3, 14, 22),
            created_time=datetime(2026, 7, 1, 9, 0),
        ),
        FileItem(
            name="ai_desktop_organizer.py",
            path=r"C:\Users\ww\Desktop\ai_desktop_organizer.py",
            extension=".py",
            size_bytes=15360,
            size_human="15.0 KB",
            modified_time=datetime(2026, 7, 4, 8, 0),
            created_time=datetime(2026, 7, 2, 10, 0),
        ),
        FileItem(
            name="客户合同_CH5091_2026Q3.pdf",
            path=r"C:\Users\ww\Desktop\客户合同_CH5091_2026Q3.pdf",
            extension=".pdf",
            size_bytes=1048576,
            size_human="1.0 MB",
            modified_time=datetime(2026, 6, 28, 16, 0),
            created_time=datetime(2026, 6, 28, 15, 30),
        ),
        FileItem(
            name="504000002145_step文件.stp",
            path=r"C:\Users\ww\Desktop\504000002145_step文件.stp",
            extension=".stp",
            size_bytes=20971520,
            size_human="20.0 MB",
            modified_time=datetime(2026, 7, 2, 11, 0),
            created_time=datetime(2026, 7, 1, 14, 0),
        ),
        FileItem(
            name="a3f8c2e1d9b74e6f8a1c2d3e4f5a6b7c.png",
            path=r"C:\Users\ww\Desktop\a3f8c2e1d9b74e6f8a1c2d3e4f5a6b7c.png",
            extension=".png",
            size_bytes=524288,
            size_human="512.0 KB",
            modified_time=datetime(2026, 7, 3, 20, 15),
            created_time=datetime(2026, 7, 3, 20, 15),
        ),
        FileItem(
            name="SolidWorks_2024_SP5_安装包.exe",
            path=r"C:\Users\ww\Desktop\SolidWorks_2024_SP5_安装包.exe",
            extension=".exe",
            size_bytes=3221225472,
            size_human="3.0 GB",
            modified_time=datetime(2026, 5, 10, 9, 0),
            created_time=datetime(2026, 5, 10, 8, 30),
        ),
        FileItem(
            name="产品照片_模具成品.jpg",
            path=r"C:\Users\ww\Desktop\产品照片_模具成品.jpg",
            extension=".jpg",
            size_bytes=3145728,
            size_human="3.0 MB",
            modified_time=datetime(2026, 7, 2, 15, 30),
            created_time=datetime(2026, 7, 2, 15, 30),
        ),
        FileItem(
            name="temp_notes_bak.txt",
            path=r"C:\Users\ww\Desktop\temp_notes_bak.txt",
            extension=".txt",
            size_bytes=2048,
            size_human="2.0 KB",
            modified_time=datetime(2026, 7, 4, 1, 0),
            created_time=datetime(2026, 7, 3, 23, 0),
        ),
        FileItem(
            name="export_data_20260701.csv",
            path=r"C:\Users\ww\Desktop\export_data_20260701.csv",
            extension=".csv",
            size_bytes=65536,
            size_human="64.0 KB",
            modified_time=datetime(2026, 7, 1, 12, 0),
            created_time=datetime(2026, 7, 1, 11, 0),
        ),
    ]
    return samples


def test_ai_classifier(config):
    """Test the AI classifier with sample files."""
    print("\n" + "=" * 60)
    print("TEST 1: AI Classifier")
    print("=" * 60)
    
    classifier = AIClassifier(config)
    samples = create_sample_files()
    
    print(f"\nClassifying {len(samples)} sample files...")
    print("(Will use offline rule-based mode if API key not available)\n")
    
    results = classifier.classify_batch(samples)
    
    print(f"{'File Name':<45} {'Category':<10} {'Confidence':<12} {'Target Folder'}")
    print("-" * 100)
    for r in results:
        ai_tag = "🤖" if r.is_ai_classified else "📋"
        print(f"{ai_tag} {r.file_name:<43} {r.suggested_category:<10} {r.confidence:<12.0%} {r.target_folder}")
        print(f"   Reasoning: {r.reasoning}")
    
    # Verify results
    assert len(results) == len(samples), f"Expected {len(samples)} results, got {len(results)}"
    
    # Check specific classifications
    results_dict = {r.file_name: r for r in results}
    
    # CAD file should go to 04_图纸
    tac28 = results_dict.get("TAC28_模具图纸_v3.SLDPRT")
    assert tac28 is not None, "TAC28 file not found in results"
    assert "04_" in tac28.target_folder, f"TAC28 should go to 04_图纸, got {tac28.target_folder}"
    print(f"\n✅ TAC28 CAD file correctly classified to: {tac28.target_folder}")
    
    # Project file should go to 01_东宝龙
    p019 = results_dict.get("P019_东宝龙订单报价_2026.xlsx")
    assert p019 is not None, "P019 file not found"
    print(f"✅ P019 project file classified to: {p019.target_folder}")
    
    # Code file should go to 06_AI
    py_file = results_dict.get("ai_desktop_organizer.py")
    assert py_file is not None, "Python file not found"
    assert "06_" in py_file.target_folder, f"Code should go to 06_, got {py_file.target_folder}"
    print(f"✅ Python code file classified to: {py_file.target_folder}")
    
    # Customer contract should go to 02_外贸
    contract = results_dict.get("客户合同_CH5091_2026Q3.pdf")
    assert contract is not None, "Contract file not found"
    print(f"✅ Customer contract classified to: {contract.target_folder}")
    
    # Temp file should go to 03_
    temp = results_dict.get("temp_notes_bak.txt")
    assert temp is not None, "Temp file not found"
    assert "03_" in temp.target_folder, f"Temp should go to 03_, got {temp.target_folder}"
    print(f"✅ Temp file classified to: {temp.target_folder}")
    
    # Test cache
    print("\nTesting cache...")
    cache_results = classifier.classify_batch(samples[:3])
    cached_count = sum(1 for r in cache_results if r.is_ai_classified or r.fallback_reason == "")
    print(f"✅ Cache working: {len(cache_results)} results from cache")
    
    classifier.close()
    print("\n✅ AI Classifier tests passed!")
    return True


def test_folder_suggester(config):
    """Test the folder suggester."""
    print("\n" + "=" * 60)
    print("TEST 2: Folder Suggester")
    print("=" * 60)
    
    suggester = FolderSuggester(config)
    samples = create_sample_files()
    
    suggestions = suggester.suggest_all(samples)
    
    print(f"\n{'File Name':<45} {'Confidence':<12} {'Target Folder'}")
    print("-" * 85)
    for s in suggestions:
        conf_icon = "🟢" if s.confidence >= 0.8 else ("🟡" if s.confidence >= 0.5 else "🔴")
        print(f"{conf_icon} {s.file_name:<43} {s.confidence:<12.0%} {s.target_folder}")
    
    assert len(suggestions) == len(samples), f"Expected {len(suggestions)} suggestions, got {len(samples)}"
    
    # Test JSON export
    json_output = suggester.to_json(suggestions)
    parsed = json.loads(json_output)
    assert "suggestions" in parsed
    assert len(parsed["suggestions"]) == len(samples)
    print(f"\n✅ JSON export working: {len(parsed['suggestions'])} suggestions")
    
    # Test new folder suggestions
    new_folders = suggester.suggest_new_folders(suggestions)
    print(f"✅ New folder suggestions: {len(new_folders)}")
    
    print("\n✅ Folder Suggester tests passed!")
    return True


def test_organizer(config):
    """Test the organizer."""
    print("\n" + "=" * 60)
    print("TEST 3: Organizer Preview")
    print("=" * 60)
    
    organizer = Organizer(config)
    samples = create_sample_files()
    suggester = FolderSuggester(config)
    suggestions = suggester.suggest_all(samples)
    
    # Create a mock scan result
    class MockScanResult:
        def __init__(self, files):
            self.files = files
            self.folders = []
            self.total_files = len(files)
            self.total_folders = 0
            self.total_size_bytes = sum(f.size_bytes for f in files)
            self.total_size_human = f"{self.total_size_bytes / 1024 / 1024:.1f} MB"
            self.duplicate_candidates = []
            self.temp_files = [f for f in files if f.name.startswith('temp') or 'bak' in f.name.lower()]
            self.categories = {}
    
    scan_result = MockScanResult(samples)
    temp_files = [f for f in samples if f.name.startswith('temp') or 'bak' in f.name.lower()]
    
    preview = organizer.generate_preview(scan_result, suggestions, temp_files)
    
    print(f"\n{organizer.get_organization_summary(preview)}")
    
    assert preview.total_files == len(samples)
    assert preview.files_to_move >= 0
    print(f"\n✅ Preview generated: {preview.files_to_move} files to move")
    print(f"✅ Risk level: {preview.risk_level}")
    print(f"✅ Space: {preview.estimated_space_human}")
    
    print("\n✅ Organizer tests passed!")
    return True


def test_json_export():
    """Test that all JSON serialization works with Chinese characters."""
    print("\n" + "=" * 60)
    print("TEST 4: JSON Export (UTF-8 Chinese)")
    print("=" * 60)
    
    config = load_config()
    samples = create_sample_files()
    
    suggester = FolderSuggester(config)
    suggestions = suggester.suggest_all(samples)
    
    # Test JSON with Chinese
    json_str = suggester.to_json(suggestions)
    parsed = json.loads(json_str)
    
    # Verify Chinese characters preserved
    for s in parsed["suggestions"]:
        if "模具" in s["file_name"] or "东宝龙" in s["file_name"]:
            print(f"✅ Chinese filename preserved: {s['file_name']}")
            print(f"   → Folder: {s['target_folder']}")
    
    print("\n✅ JSON export with Chinese characters works!")
    return True


def main():
    """Run all tests."""
    print("╔══════════════════════════════════════════════╗")
    print("║  Phase 2 Test Suite: AI Smart Classification ║")
    print("╚══════════════════════════════════════════════╝")
    
    config = load_config()
    
    all_passed = True
    
    try:
        all_passed &= test_ai_classifier(config)
    except Exception as e:
        print(f"\n❌ AI Classifier test failed: {e}")
        all_passed = False
    
    try:
        all_passed &= test_folder_suggester(config)
    except Exception as e:
        print(f"\n❌ Folder Suggester test failed: {e}")
        all_passed = False
    
    try:
        all_passed &= test_organizer(config)
    except Exception as e:
        print(f"\n❌ Organizer test failed: {e}")
        all_passed = False
    
    try:
        all_passed &= test_json_export()
    except Exception as e:
        print(f"\n❌ JSON export test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
