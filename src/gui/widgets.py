"""
Custom PyQt6 widgets for the Desktop Organizer - Premium Dark Theme.
Design inspired by Linear.app / Raycast / Figma
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFrame,
    QSplitter, QGroupBox, QGridLayout, QProgressBar, QScrollArea,
    QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush

from ..utils import format_size, format_datetime


# ═══════════════════════════════════════════════════════════════
# PREMIUM COLOR SYSTEM - Linear.app / Raycast / Figma inspired
# ═══════════════════════════════════════════════════════════════
COLORS = {
    # Backgrounds
    'bg_primary': '#0f0f10',
    'bg_secondary': '#1a1a1e',
    'bg_tertiary': '#242428',
    'bg_elevated': '#2a2a2e',
    
    # Text - HIGH CONTRAST
    'text_primary': '#ffffff',
    'text_secondary': '#a1a1aa',
    'text_tertiary': '#71717a',
    
    # Accents
    'accent_blue': '#3b82f6',
    'accent_blue_hover': '#2563eb',
    'accent_purple': '#8b5cf6',
    'accent_purple_hover': '#7c3aed',
    'accent_green': '#22c55e',
    'accent_green_hover': '#16a34a',
    'accent_red': '#ef4444',
    'accent_red_hover': '#dc2626',
    'accent_yellow': '#eab308',
    'accent_cyan': '#06b6d4',
    'accent_orange': '#f97316',
    
    # Borders
    'border': '#27272a',
    'border_hover': '#3f3f46',
    'border_active': '#52525b',
    
    # Category colors
    'cat_cad': '#3b82f6',
    'cat_office': '#f97316',
    'cat_images': '#22c55e',
    'cat_archives': '#eab308',
    'cat_code': '#8b5cf6',
    'cat_video': '#ef4444',
    'cat_audio': '#06b6d4',
    'cat_text': '#a1a1aa',
    'cat_other': '#71717a',
}

# Category → color mapping
CATEGORY_COLORS = {
    'CAD': COLORS['cat_cad'],
    'Office': COLORS['cat_office'],
    'Images': COLORS['cat_images'],
    'Archives': COLORS['cat_archives'],
    'Code': COLORS['cat_code'],
    'Video': COLORS['cat_video'],
    'Audio': COLORS['cat_audio'],
    'Text': COLORS['cat_text'],
    'Other': COLORS['cat_other'],
}


def get_category_color(category: str) -> str:
    """Get color for a category."""
    return CATEGORY_COLORS.get(category, COLORS['cat_other'])


def score_dots(score: int) -> str:
    """Convert score (0-10) to dot display."""
    filled = score // 2
    return '●' * filled + '○' * (5 - filled)


# ═══════════════════════════════════════════════════════════════
# STAT CARD - Mini metric card
# ═══════════════════════════════════════════════════════════════
class StatCard(QFrame):
    """Premium stat card with icon, value, and label."""
    
    def __init__(self, icon: str, value: str, label: str, color: str = COLORS['accent_blue']):
        super().__init__()
        self.setFixedHeight(80)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 12px;
            }}
            QFrame:hover {{
                border-color: {COLORS['border_hover']};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        
        # Icon + value row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 18px; color: {color}; background: transparent; border: none;")
        top_row.addWidget(icon_label)
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            font-size: 22px; 
            font-weight: bold; 
            color: {COLORS['text_primary']};
            background: transparent;
            border: none;
        """)
        top_row.addWidget(self.value_label)
        top_row.addStretch()
        
        layout.addLayout(top_row)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 500;
            color: {COLORS['text_secondary']};
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(label_widget)
    
    def update_value(self, value: str):
        self.value_label.setText(value)


# ═══════════════════════════════════════════════════════════════
# CATEGORY WIDGET - Premium category row
# ═══════════════════════════════════════════════════════════════
class CategoryWidget(QFrame):
    """Premium category row with colored dot, name, and count badge."""
    
    clicked = pyqtSignal(str)
    
    def __init__(self, category: str, count: int, parent=None):
        super().__init__(parent)
        self.category = category
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        color = get_category_color(category)
        
        self._base_style = f"""
            QFrame {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """
        self._hover_style = f"""
            QFrame {{
                background: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """
        self.setStyleSheet(self._base_style)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(10)
        
        # Color dot
        dot = QLabel("●")
        dot.setFixedSize(12, 12)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setStyleSheet(f"font-size: 10px; color: {color}; background: transparent; border: none;")
        layout.addWidget(dot)
        
        # Name
        name_label = QLabel(category)
        name_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_primary']};
            background: transparent;
            border: none;
        """)
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Count badge
        badge = QLabel(str(count))
        badge.setFixedSize(32, 20)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {COLORS['text_secondary']};
            background: {COLORS['bg_elevated']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
            padding: 2px;
        """)
        layout.addWidget(badge)
    
    def enterEvent(self, event):
        self.setStyleSheet(self._hover_style)
    
    def leaveEvent(self, event):
        self.setStyleSheet(self._base_style)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.category)


# ═══════════════════════════════════════════════════════════════
# SCORE DOTS WIDGET
# ═══════════════════════════════════════════════════════════════
class ScoreDots(QWidget):
    """Display importance score as colored dots."""
    
    def __init__(self, score: int = 0):
        super().__init__()
        self.score = score
        self.setFixedSize(60, 20)
    
    def set_score(self, score: int):
        self.score = score
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        filled = self.score // 2
        for i in range(5):
            if i < filled:
                if self.score >= 7:
                    color = QColor(COLORS['accent_green'])
                elif self.score >= 4:
                    color = QColor(COLORS['accent_yellow'])
                else:
                    color = QColor(COLORS['accent_red'])
            else:
                color = QColor(COLORS['border'])
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(i * 12 + 2, 4, 8, 8)
        
        painter.end()


# ═══════════════════════════════════════════════════════════════
# CATEGORY TAG (pill-shaped)
# ═══════════════════════════════════════════════════════════════
class CategoryTag(QLabel):
    """Pill-shaped category tag."""
    
    def __init__(self, category: str):
        super().__init__(category)
        color = get_category_color(category)
        self.setStyleSheet(f"""
            font-size: 10px;
            font-weight: 600;
            color: {color};
            background: {color}20;
            border: 1px solid {color}40;
            border-radius: 8px;
            padding: 2px 8px;
        """)
        self.setFixedHeight(20)


# ═══════════════════════════════════════════════════════════════
# FILE TABLE - Premium data table
# ═══════════════════════════════════════════════════════════════
class FileTable(QTableWidget):
    """Premium file table with modern styling."""
    
    file_selected = pyqtSignal(object)
    
    COLUMNS = ['Name', 'Type', 'Size', 'Modified', 'Category', 'Score']
    
    def __init__(self):
        super().__init__(0, len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self._setup_table()
    
    def _setup_table(self):
        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(True)
        
        # Header styling
        header = self.horizontalHeader()
        header.setDefaultSectionSize(150)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(5, 70)
        
        header.setStyleSheet(f"""
            QHeaderView::section {{
                background: {COLORS['bg_secondary']};
                color: {COLORS['text_secondary']};
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border: none;
                border-bottom: 2px solid {COLORS['border']};
                padding: 10px 12px;
            }}
        """)
        
        self.setStyleSheet(f"""
            QTableWidget {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: none;
                gridline-color: {COLORS['border']};
                selection-background-color: {COLORS['accent_blue']}30;
                selection-color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QTableWidget::item:selected {{
                background: {COLORS['accent_blue']}20;
            }}
            QTableWidget::item:hover {{
                background: {COLORS['bg_tertiary']};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLORS['border_hover']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        self.setRowHeight(0, 44)
    
    def populate_files(self, files):
        self.setRowCount(len(files))
        for row, file_item in enumerate(files):
            self.setRowHeight(row, 44)
            
            # Name with icon
            icon = "📁" if file_item.is_directory else self._get_file_icon(file_item.extension)
            name_item = QTableWidgetItem(f"{icon}  {file_item.name}")
            name_item.setData(Qt.ItemDataRole.UserRole, file_item)
            self.setItem(row, 0, name_item)
            
            # Type
            ext = file_item.extension.upper().replace('.', '') if file_item.extension else 'Folder'
            type_item = QTableWidgetItem(ext)
            type_item.setForeground(QColor(COLORS['text_secondary']))
            self.setItem(row, 1, type_item)
            
            # Size
            size_item = QTableWidgetItem(file_item.size_human)
            size_item.setForeground(QColor(COLORS['text_secondary']))
            self.setItem(row, 2, size_item)
            
            # Modified
            mod_item = QTableWidgetItem(file_item.modified_time.strftime('%Y-%m-%d'))
            mod_item.setForeground(QColor(COLORS['text_secondary']))
            self.setItem(row, 3, mod_item)
            
            # Category (as tag)
            category = getattr(file_item, 'category', 'Other')
            cat_item = QTableWidgetItem(category)
            cat_color = get_category_color(category)
            cat_item.setForeground(QColor(cat_color))
            self.setItem(row, 4, cat_item)
            
            # Score
            score = getattr(file_item, 'importance_score', 5)
            score_item = QTableWidgetItem(score_dots(score))
            if score >= 7:
                score_item.setForeground(QColor(COLORS['accent_green']))
            elif score >= 4:
                score_item.setForeground(QColor(COLORS['accent_yellow']))
            else:
                score_item.setForeground(QColor(COLORS['accent_red']))
            self.setItem(row, 5, score_item)
    
    def _get_file_icon(self, ext: str) -> str:
        ext = ext.lower()
        if ext in ['.dwg', '.dxf', '.sldprt', '.sldasm', '.slddrw', '.stp', '.step', '.stl', '.igs']:
            return "📐"
        elif ext in ['.xlsx', '.xls', '.xlsm', '.csv']:
            return "📊"
        elif ext in ['.docx', '.doc', '.pdf']:
            return "📄"
        elif ext in ['.py', '.js', '.ts', '.tsx', '.html', '.css', '.json']:
            return "💻"
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
            return "🖼️"
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
            return "📦"
        elif ext in ['.mp4', '.avi', '.mkv', '.mov']:
            return "🎬"
        elif ext in ['.mp3', '.wav', '.flac']:
            return "🎵"
        elif ext in ['.txt', '.md', '.log']:
            return "📝"
        elif ext in ['.bak', '.err', '.tmp', '.swp']:
            return "🗑️"
        return "📄"
    
    def itemSelectionChanged(self):
        items = self.selectedItems()
        if items:
            item = self.item(items[0].row(), 0)
            if item:
                file_item = item.data(Qt.ItemDataRole.UserRole)
                self.file_selected.emit(file_item)


# ═══════════════════════════════════════════════════════════════
# INFO PANEL - File details sidebar
# ═══════════════════════════════════════════════════════════════
class InfoPanel(QFrame):
    """File details panel with modern card design."""
    
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(120)
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        
        title = QLabel("📋 File Details")
        title.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {COLORS['text_secondary']};
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title)
        
        self.detail_label = QLabel("Select a file to view details")
        self.detail_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_tertiary']};
            background: transparent;
            border: none;
        """)
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)
        
        layout.addStretch()
    
    def show_file(self, file_item):
        if file_item is None:
            self.detail_label.setText("Select a file to view details")
            return
        
        details = f"""
<b>{file_item.name}</b><br>
<span style="color: {COLORS['text_secondary']}">
📁 {file_item.path}<br>
📏 {file_item.size_human}<br>
📅 Modified: {file_item.modified_time.strftime('%Y-%m-%d %H:%M')}
</span>
"""
        self.detail_label.setText(details)


# ═══════════════════════════════════════════════════════════════
# ORGANIZATION PREVIEW WIDGET
# ═══════════════════════════════════════════════════════════════
class OrgPreviewWidget(QFrame):
    """Organization preview with before/after split view."""
    
    execute_clicked = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg_primary']};
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Summary cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(12)
        
        self.files_to_move = StatCard("📦", "0", "Files to Move", COLORS['accent_blue'])
        self.files_to_delete = StatCard("🗑️", "0", "Temp Files", COLORS['accent_red'])
        self.duplicates = StatCard("🔄", "0", "Duplicates", COLORS['accent_yellow'])
        self.risk_level = StatCard("⚡", "Low", "Risk Level", COLORS['accent_green'])
        
        summary_layout.addWidget(self.files_to_move)
        summary_layout.addWidget(self.files_to_delete)
        summary_layout.addWidget(self.duplicates)
        summary_layout.addWidget(self.risk_level)
        
        layout.addLayout(summary_layout)
        
        # Preview content area
        preview_label = QLabel("📋 Organization Preview")
        preview_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {COLORS['text_primary']};
            background: transparent;
            border: none;
        """)
        layout.addWidget(preview_label)
        
        self.preview_text = QLabel("Click 'AI Analyze' to generate organization suggestions")
        self.preview_text.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_secondary']};
            background: {COLORS['bg_secondary']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            padding: 20px;
        """)
        self.preview_text.setWordWrap(True)
        layout.addWidget(self.preview_text)
        
        layout.addStretch()
        
        # Execute button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.execute_btn = QPushButton("✨ Execute Organization")
        self.execute_btn.setFixedHeight(44)
        self.execute_btn.setMinimumWidth(200)
        self.execute_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent_green']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 24px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent_green_hover']};
            }}
            QPushButton:pressed {{
                background: #15803d;
            }}
            QPushButton:disabled {{
                background: {COLORS['bg_tertiary']};
                color: {COLORS['text_tertiary']};
            }}
        """)
        self.execute_btn.clicked.connect(self.execute_clicked.emit)
        self.execute_btn.setEnabled(False)
        btn_layout.addWidget(self.execute_btn)
        
        layout.addLayout(btn_layout)
    
    def update_preview(self, preview_data):
        if preview_data is None:
            return
        
        move_count = len(preview_data.get('files_to_move', []))
        temp_count = len(preview_data.get('files_to_delete', []))
        dup_count = len(preview_data.get('duplicates', []))
        risk = preview_data.get('risk_level', 'low')
        
        self.files_to_move.update_value(str(move_count))
        self.files_to_delete.update_value(str(temp_count))
        self.duplicates.update_value(str(dup_count))
        self.risk_level.update_value(risk.capitalize())
        
        # Update risk color
        risk_colors = {
            'low': COLORS['accent_green'],
            'medium': COLORS['accent_yellow'],
            'high': COLORS['accent_red']
        }
        
        summary = preview_data.get('summary', 'No preview available')
        self.preview_text.setText(summary)
        
        self.execute_btn.setEnabled(move_count > 0 or temp_count > 0)
