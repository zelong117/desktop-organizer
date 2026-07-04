"""
Main window for the Desktop Organizer - Premium Dark Theme.
Design inspired by Linear.app / Raycast / Figma
"""
import json
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QToolBar, QStatusBar, QLabel, QPushButton,
    QFileDialog, QMessageBox, QTabWidget, QTextEdit,
    QApplication, QProgressBar, QFrame, QStackedWidget,
    QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QColor

from ..scanner import DesktopScanner
from ..analyzer import FileAnalyzer
from ..folder_suggester import FolderSuggester
from ..organizer import Organizer
from ..models import ScanResult
from .widgets import (
    CategoryWidget, StatCard, FileTable, InfoPanel, 
    OrgPreviewWidget, COLORS, get_category_color
)


class ScanThread(QThread):
    """Background thread for scanning files."""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    
    def __init__(self, scanner: DesktopScanner, analyzer: FileAnalyzer):
        super().__init__()
        self.scanner = scanner
        self.analyzer = analyzer
    
    def run(self):
        try:
            result = self.scanner.scan(progress_callback=self._on_progress)
            self.progress.emit(96, "Analyzing files...")
            result = self.analyzer.analyze(result)
            self.progress.emit(100, "Done!")
            self.finished.emit(result)
        except Exception as e:
            print(f"Scan error: {e}")
            self.finished.emit(None)
    
    def _on_progress(self, value: int, message: str):
        self.progress.emit(value, message)


class MainWindow(QMainWindow):
    """Main application window - Premium Dark Theme."""
    
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.scan_result = None
        self.current_filter = None
        self.folder_suggestions = None
        
        self.setup_ui()
        self.apply_theme()
        self.start_scan()
    
    def setup_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("桌面智能整理器")
        self.setMinimumSize(1200, 800)
        self.showMaximized()
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top bar
        self.create_top_bar(main_layout)
        
        # Main content splitter
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # Left sidebar
        left_sidebar = self.create_left_sidebar()
        content_layout.addWidget(left_sidebar)
        
        # Main content area
        main_content = self.create_main_content()
        content_layout.addWidget(main_content)
        
        # Set proportions: sidebar 280px, main content stretch
        content_layout.setStretch(0, 0)
        content_layout.setStretch(1, 1)
        
        main_layout.addWidget(content_widget, 1)
        
        # Status bar
        self.create_status_bar()
    
    def create_top_bar(self, parent_layout):
        """Create the premium top bar."""
        top_bar = QFrame()
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)
        
        # App icon + title
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        layout.addWidget(icon_label)
        
        title_label = QLabel("桌面智能整理器")
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {COLORS['text_primary']};
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)
        
        layout.addSpacing(32)
        
        # Tab buttons (pill style)
        self.tab_buttons = {}
        tab_names = ['全部文件', '临时文件', '重复文件', '项目文件', '智能整理']
        
        for name in tab_names:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['text_secondary']};
                    border: none;
                    border-radius: 6px;
                    padding: 0 16px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_tertiary']};
                    color: {COLORS['text_primary']};
                }}
                QPushButton:checked {{
                    background: {COLORS['accent_blue']}20;
                    color: {COLORS['accent_blue']};
                }}
            """)
            btn.clicked.connect(lambda checked, n=name: self.switch_tab(n))
            self.tab_buttons[name] = btn
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Scan button
        self.scan_btn = QPushButton("🔍 扫描")
        self.scan_btn.setFixedHeight(36)
        self.scan_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_blue']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_blue_hover']};
            }}
            QPushButton:pressed {{
                background: #1d4ed8;
            }}
        """)
        self.scan_btn.clicked.connect(self.start_scan)
        layout.addWidget(self.scan_btn)
        
        # AI Analyze button
        self.ai_btn = QPushButton("✨ AI分析")
        self.ai_btn.setFixedHeight(36)
        self.ai_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {COLORS['accent_purple']}, stop:1 #6366f1);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {COLORS['accent_purple_hover']}, stop:1 #4f46e5);
            }}
            QPushButton:pressed {{
                background: #6d28d9;
            }}
            QPushButton:disabled {{
                background: {COLORS['bg_tertiary']};
                color: {COLORS['text_tertiary']};
            }}
        """)
        self.ai_btn.clicked.connect(self.run_ai_analysis)
        self.ai_btn.setEnabled(False)
        layout.addWidget(self.ai_btn)
        
        parent_layout.addWidget(top_bar)
    
    def create_left_sidebar(self) -> QWidget:
        """Create the premium left sidebar."""
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        
        # Stats section
        stats_label = QLabel("📊 概览")
        stats_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {COLORS['text_secondary']};
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(stats_label)
        
        # Stats grid (2x2)
        stats_grid = QHBoxLayout()
        stats_grid.setSpacing(10)
        
        self.stat_files = StatCard("📁", "0", "文件", COLORS['accent_blue'])
        self.stat_folders = StatCard("📂", "0", "文件夹", COLORS['accent_cyan'])
        
        stats_grid.addWidget(self.stat_files)
        stats_grid.addWidget(self.stat_folders)
        
        layout.addLayout(stats_grid)
        
        stats_grid2 = QHBoxLayout()
        stats_grid2.setSpacing(10)
        
        self.stat_size = StatCard("💾", "0 MB", "大小", COLORS['accent_purple'])
        self.stat_temp = StatCard("🗑️", "0", "临时", COLORS['accent_red'])
        
        stats_grid2.addWidget(self.stat_size)
        stats_grid2.addWidget(self.stat_temp)
        
        layout.addLayout(stats_grid2)
        
        # Categories section
        categories_label = QLabel("📂 文件分类")
        categories_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {COLORS['text_secondary']};
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(categories_label)
        
        # Categories container (scrollable)
        self.categories_container = QWidget()
        self.categories_layout = QVBoxLayout(self.categories_container)
        self.categories_layout.setContentsMargins(0, 0, 0, 0)
        self.categories_layout.setSpacing(4)
        self.categories_layout.addStretch()
        
        scroll = QScrollArea()
        scroll.setWidget(self.categories_container)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(scroll)
        
        # Info panel
        self.info_panel = InfoPanel()
        layout.addWidget(self.info_panel)
        
        return sidebar
    
    def create_main_content(self) -> QWidget:
        """Create the main content area with tabs."""
        content = QFrame()
        content.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab content stack
        self.tab_stack = QStackedWidget()
        
        # All Files tab
        self.file_table = FileTable()
        self.file_table.file_selected.connect(self.on_file_selected)
        self.tab_stack.addWidget(self.file_table)
        
        # Temp Files tab
        self.temp_table = FileTable()
        self.temp_table.file_selected.connect(self.on_file_selected)
        self.tab_stack.addWidget(self.temp_table)
        
        # Duplicates tab
        self.duplicates_text = QTextEdit()
        self.duplicates_text.setReadOnly(True)
        self.duplicates_text.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 16px;
            }}
        """)
        self.tab_stack.addWidget(self.duplicates_text)
        
        # Projects tab
        self.projects_text = QTextEdit()
        self.projects_text.setReadOnly(True)
        self.projects_text.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: none;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 16px;
            }}
        """)
        self.tab_stack.addWidget(self.projects_text)
        
        # Organization Preview tab
        self.org_preview = OrgPreviewWidget()
        self.org_preview.execute_clicked.connect(self.execute_organization)
        self.tab_stack.addWidget(self.org_preview)
        
        layout.addWidget(self.tab_stack)
        
        return content
    
    def create_status_bar(self):
        """Create the premium status bar."""
        self.statusBar().setStyleSheet(f"""
            QStatusBar {{
                background: {COLORS['bg_secondary']};
                color: {COLORS['text_secondary']};
                border-top: 1px solid {COLORS['border']};
                padding: 4px 16px;
                font-size: 12px;
            }}
        """)
        
        self.status_label = QLabel("就绪")
        self.statusBar().addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {COLORS['accent_blue']};
                border-radius: 3px;
            }}
        """)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
    
    def apply_theme(self):
        """Apply the premium dark theme."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {COLORS['bg_primary']};
            }}
            QWidget {{
                background: transparent;
                color: {COLORS['text_primary']};
            }}
            QToolTip {{
                background: {COLORS['bg_elevated']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
        """)
    
    def switch_tab(self, tab_name: str):
        """Switch between tabs."""
        tab_map = {
            'All Files': 0,
            'Temp Files': 1,
            'Duplicates': 2,
            'Projects': 3,
            'Organization': 4
        }
        
        # Update button states
        for name, btn in self.tab_buttons.items():
            btn.setChecked(name == tab_name)
        
        # Switch stack
        if tab_name in tab_map:
            self.tab_stack.setCurrentIndex(tab_map[tab_name])
    
    def start_scan(self):
        """Start scanning the desktop."""
        self.scan_btn.setEnabled(False)
        self.ai_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在扫描桌面...")
        
        scanner = DesktopScanner(self.config)
        analyzer = FileAnalyzer(self.config)
        
        self.scan_thread = ScanThread(scanner, analyzer)
        self.scan_thread.progress.connect(self.on_scan_progress)
        self.scan_thread.finished.connect(self.on_scan_complete)
        self.scan_thread.start()
    
    def on_scan_progress(self, value: int, message: str):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def on_scan_complete(self, result: ScanResult):
        self.scan_result = result
        self.scan_btn.setEnabled(True)
        self.ai_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if result is None:
            self.status_label.setText("扫描失败！")
            return
        
        self.update_ui()
        self.status_label.setText(
            f"✅ 扫描完成: {result.total_files} 个文件, "
            f"{result.total_folders} 个文件夹, {result.total_size_human}"
        )
    
    def update_ui(self):
        """Update all UI elements with scan results."""
        if not self.scan_result:
            return
        
        result = self.scan_result
        
        # Update stats
        self.stat_files.update_value(str(result.total_files))
        self.stat_folders.update_value(str(result.total_folders))
        self.stat_size.update_value(result.total_size_human)
        self.stat_temp.update_value(str(len(result.temp_files)))
        
        # Update categories
        self.update_categories()
        
        # Update file table
        all_files = result.files + result.folders
        all_files.sort(key=lambda f: (f.is_directory, f.name.lower()))
        self.file_table.populate_files(all_files)
        
        # Update temp files table
        self.temp_table.populate_files(result.temp_files)
        
        # Update duplicates view
        self.update_duplicates_view()
        
        # Update projects view
        self.update_projects_view()
    
    def update_categories(self):
        """Update the categories panel."""
        # Clear existing
        while self.categories_layout.count():
            item = self.categories_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add categories
        categories = self.scan_result.categories
        for category, count in sorted(categories.items(), key=lambda x: -x[1]):
            widget = CategoryWidget(category, count)
            widget.clicked.connect(self.filter_by_category)
            self.categories_layout.addWidget(widget)
        
        self.categories_layout.addStretch()
    
    def update_duplicates_view(self):
        """Update the duplicates text view."""
        self.duplicates_text.clear()
        
        duplicates = self.scan_result.duplicate_candidates
        if not duplicates:
            self.duplicates_text.setPlainText("No duplicate candidates found.")
            return
        
        html = f"""
        <div style='margin-bottom: 16px;'>
            <span style='font-size: 18px; font-weight: bold; color: {COLORS['accent_yellow']};'>
                🔄 发现 {len(duplicates)} 组重复文件
            </span>
        </div>
        """
        
        for i, group in enumerate(duplicates[:50]):  # Limit to 50 groups
            html += f"""
            <div style='margin-bottom: 12px; padding: 12px; background: {COLORS['bg_secondary']}; 
                        border-radius: 8px; border: 1px solid {COLORS['border']};'>
                <div style='color: {COLORS['accent_yellow']}; font-weight: 600; margin-bottom: 8px;'>
                    {i+1}. {group['base_name']}
                </div>
            """
            for path in group['files']:
                html += f"""
                <div style='color: {COLORS['text_secondary']}; font-family: Consolas, monospace; 
                            font-size: 12px; padding: 4px 0;'>
                    📄 {path}
                </div>
                """
            html += "</div>"
        
        self.duplicates_text.setHtml(html)
    
    def update_projects_view(self):
        """Update the projects text view."""
        self.projects_text.clear()
        
        projects = self.scan_result.project_files
        if not projects:
            self.projects_text.setPlainText("No project patterns detected.")
            return
        
        html = f"""
        <div style='margin-bottom: 16px;'>
            <span style='font-size: 18px; font-weight: bold; color: {COLORS['accent_cyan']};'>
                📋 发现 {len(projects)} 个项目模式
            </span>
        </div>
        """
        
        for pattern, files in sorted(projects.items()):
            html += f"""
            <div style='margin-bottom: 16px; padding: 16px; background: {COLORS['bg_secondary']}; 
                        border-radius: 8px; border: 1px solid {COLORS['border']};'>
                <div style='color: {COLORS['accent_cyan']}; font-weight: 600; font-size: 14px; margin-bottom: 8px;'>
                    📋 {pattern} <span style='color: {COLORS['text_secondary']}; font-weight: normal;'>({len(files)} files)</span>
                </div>
            """
            for f in files[:15]:
                html += f"""
                <div style='color: {COLORS['text_secondary']}; font-family: Consolas, monospace; 
                            font-size: 12px; padding: 4px 0;'>
                    📄 {f.name}
                </div>
                """
            if len(files) > 15:
                html += f"""
                <div style='color: {COLORS['text_secondary']}; font-size: 12px; padding: 4px 0;'>
                    ... 还有 {len(files) - 15} 个更多
                </div>
                """
            html += "</div>"
        
        self.projects_text.setHtml(html)
    
    def filter_by_category(self, category: str):
        """Filter file table by category."""
        if not self.scan_result:
            return
        
        if self.current_filter == category:
            # Remove filter
            self.current_filter = None
            all_files = self.scan_result.files + self.scan_result.folders
        else:
            # Apply filter
            self.current_filter = category
            all_files = [f for f in self.scan_result.files if f.category == category]
        
        all_files.sort(key=lambda f: (f.is_directory, f.name.lower()))
        self.file_table.populate_files(all_files)
    
    def on_file_selected(self, file_item):
        """Handle file selection."""
        self.info_panel.show_file(file_item)
    
    def run_ai_analysis(self):
        """Run AI classification analysis."""
        if not self.scan_result:
            return
        
        self.ai_btn.setEnabled(False)
        self.status_label.setText("正在运行AI分析...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Run folder suggester (rule-based)
        suggester = FolderSuggester(self.config)
        self.folder_suggestions = suggester.suggest_all(self.scan_result.files)
        
        self.progress_bar.setValue(100)
        self.ai_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Switch to Organization tab
        self.switch_tab('Organization')
        
        # Update organization preview
        self.update_organization_preview()
        
        self.status_label.setText(f"✅ AI分析完成: {len(self.folder_suggestions)} 个文件已分类")
    
    def update_organization_preview(self):
        """Update the organization preview with suggestions."""
        if not self.folder_suggestions:
            return
        
        # Count operations
        files_to_move = [s for s in self.folder_suggestions if s.target_folder]
        temp_files = [s for s in self.folder_suggestions if '临时' in s.target_folder or 'temp' in s.target_folder.lower()]
        
        # Create preview text
        preview_lines = ["📋 整理计划:\\n"]
        
        # Group by target folder
        from collections import defaultdict
        folder_groups = defaultdict(list)
        for s in files_to_move:
            folder_groups[s.target_folder].append(s.file_name)
        
        for folder, files in sorted(folder_groups.items()):
            preview_lines.append(f"\\n📁 {folder} ({len(files)} 个文件)")
            for f in files[:5]:
                preview_lines.append(f"   • {f}")
            if len(files) > 5:
                preview_lines.append(f"   ... 还有 {len(files) - 5} 个更多")
        
        preview_text = '\n'.join(preview_lines)
        
        # Update preview widget
        preview_data = {
            'files_to_move': files_to_move,
            'files_to_delete': temp_files,
            'duplicates': self.scan_result.duplicate_candidates if self.scan_result else [],
            'risk_level': 'low',
            'summary': preview_text
        }
        
        self.org_preview.update_preview(preview_data)
    
    def execute_organization(self):
        """Execute the file organization."""
        if not self.folder_suggestions:
            return
        
        reply = QMessageBox.question(
            self,
            "执行整理",
            f"将 {len(self.folder_suggestions)} 个文件移动到建议的文件夹？\n\n此操作可以撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.status_label.setText("正在执行整理...")
            # TODO: Implement actual file moving
            QMessageBox.information(self, "成功", "整理预览完成，执行功能待实现。")
            self.status_label.setText("就绪")
    
    def export_results(self):
        """Export scan results to JSON."""
        if not self.scan_result:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出结果",
            os.path.expanduser("~/Desktop/扫描结果.json"),
            "JSON文件 (*.json)"
        )
        
        if file_path:
            scanner = DesktopScanner(self.config)
            scanner.export_json(self.scan_result, file_path)
            QMessageBox.information(self, "导出完成", f"结果已导出到：\n{file_path}")
