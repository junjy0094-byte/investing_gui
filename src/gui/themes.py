"""
QSS 테마 모듈
- 다크/라이트 테마 QSS 스타일시트 제공
- 향후 확장: 커스텀 테마, 테마 JSON 파일 로드 등
"""

from pathlib import Path

_ICONS_DIR = str(Path(__file__).resolve().parent / "icons").replace("\\", "/")

DARK_THEME = """
/* ===== 다크 테마 ===== */
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}

/* 그룹박스 */
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #89b4fa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* 입력 필드 */
QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
    min-height: 28px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border: 1px solid #89b4fa;
}

/* 콤보박스 드롭다운 */
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: url({ICONS}/arrow-down-dark.svg);
    width: 12px;
    height: 8px;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    border: 1px solid #45475a;
    color: #cdd6f4;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}

/* 스핀박스/데이트에디트 화살표 버튼 */
QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    background-color: #313244;
    border-left: 1px solid #45475a;
    border-bottom: 1px solid #45475a;
    border-top-right-radius: 5px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    background-color: #313244;
    border-left: 1px solid #45475a;
    border-top: 1px solid #45475a;
    border-bottom-right-radius: 5px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QDateEdit::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QDateEdit::down-button:hover {
    background-color: #45475a;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow {
    image: url({ICONS}/arrow-up-dark.svg);
    width: 10px;
    height: 6px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow {
    image: url({ICONS}/arrow-down-dark.svg);
    width: 10px;
    height: 6px;
}

/* 버튼 */
QPushButton {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: bold;
    min-height: 32px;
}
QPushButton:hover {
    background-color: #74c7ec;
}
QPushButton:pressed {
    background-color: #585b70;
    color: #cdd6f4;
}
QPushButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QPushButton#runButton {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-size: 15px;
    min-height: 40px;
    padding: 8px 16px;
}
QPushButton#runButton:hover {
    background-color: #94e2d5;
}
QPushButton#saveButton {
    background-color: #f9e2af;
    color: #1e1e2e;
    padding: 8px 16px;
}

/* 탭 위젯 */
QTabWidget::pane {
    border: 1px solid #45475a;
    border-radius: 6px;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #313244;
    color: #a6adc8;
    border: 1px solid #45475a;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 20px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    font-weight: bold;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover {
    background-color: #45475a;
}

/* 체크박스 */
QCheckBox {
    spacing: 8px;
    color: #cdd6f4;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border-color: #89b4fa;
}

/* 프로그래스바 */
QProgressBar {
    border: 1px solid #45475a;
    border-radius: 6px;
    background-color: #313244;
    text-align: center;
    color: #cdd6f4;
    min-height: 20px;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 5px;
}

/* 텍스트 에디트 (로그) */
QTextEdit {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    color: #a6adc8;
    font-family: 'DejaVu Sans Mono', 'Liberation Mono', 'FreeMono', monospace;
    font-size: 11px;
    padding: 6px;
}

/* 스크롤바 - 세로 */
QScrollBar:vertical {
    background-color: #181825;
    width: 14px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #585b70;
    border-radius: 5px;
    min-height: 30px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #6c7086;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* 스크롤바 - 가로 */
QScrollBar:horizontal {
    background-color: #181825;
    height: 14px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #585b70;
    border-radius: 5px;
    min-width: 30px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #6c7086;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* 스크롤 영역 */
QScrollArea {
    border: none;
    background-color: transparent;
}

/* 레이블 */
QLabel {
    color: #cdd6f4;
}
QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#summaryLabel {
    font-size: 12px;
    color: #a6adc8;
    padding: 4px;
}

/* 상태바 */
QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #45475a;
}

/* 스플리터 */
QSplitter::handle {
    background-color: #45475a;
    width: 2px;
}

/* 툴바 (matplotlib) */
QToolBar {
    background-color: #1e1e2e;
    border: none;
    spacing: 4px;
}
"""

LIGHT_THEME = """
/* ===== 라이트 테마 ===== */
QMainWindow, QWidget {
    background-color: #eff1f5;
    color: #4c4f69;
}

QGroupBox {
    border: 1px solid #ccd0da;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #1e66f5;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QComboBox {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    border-radius: 6px;
    padding: 6px 10px;
    color: #4c4f69;
    min-height: 28px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QComboBox:focus {
    border: 1px solid #1e66f5;
}

/* 콤보박스 드롭다운 */
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: url({ICONS}/arrow-down-light.svg);
    width: 12px;
    height: 8px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    color: #4c4f69;
    selection-background-color: #ccd0da;
    selection-color: #4c4f69;
}

/* 스핀박스/데이트에디트 화살표 버튼 */
QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    background-color: #e6e9ef;
    border-left: 1px solid #ccd0da;
    border-bottom: 1px solid #ccd0da;
    border-top-right-radius: 5px;
}
QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    background-color: #e6e9ef;
    border-left: 1px solid #ccd0da;
    border-top: 1px solid #ccd0da;
    border-bottom-right-radius: 5px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QDateEdit::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QDateEdit::down-button:hover {
    background-color: #ccd0da;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow {
    image: url({ICONS}/arrow-up-light.svg);
    width: 10px;
    height: 6px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow {
    image: url({ICONS}/arrow-down-light.svg);
    width: 10px;
    height: 6px;
}

QPushButton {
    background-color: #1e66f5;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: bold;
    min-height: 32px;
}
QPushButton:hover {
    background-color: #2a7de1;
}
QPushButton:pressed {
    background-color: #bcc0cc;
    color: #4c4f69;
}
QPushButton:disabled {
    background-color: #ccd0da;
    color: #9ca0b0;
}
QPushButton#runButton {
    background-color: #40a02b;
    color: #ffffff;
    font-size: 15px;
    min-height: 40px;
    padding: 8px 16px;
}
QPushButton#runButton:hover {
    background-color: #36a31e;
}
QPushButton#saveButton {
    background-color: #df8e1d;
    color: #ffffff;
    padding: 8px 16px;
}

QTabWidget::pane {
    border: 1px solid #ccd0da;
    border-radius: 6px;
    background-color: #eff1f5;
}
QTabBar::tab {
    background-color: #e6e9ef;
    color: #6c6f85;
    border: 1px solid #ccd0da;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 20px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #eff1f5;
    color: #1e66f5;
    font-weight: bold;
    border-bottom: 2px solid #1e66f5;
}
QTabBar::tab:hover {
    background-color: #ccd0da;
}

QCheckBox {
    spacing: 8px;
    color: #4c4f69;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #ccd0da;
    border-radius: 4px;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #1e66f5;
    border-color: #1e66f5;
}

QProgressBar {
    border: 1px solid #ccd0da;
    border-radius: 6px;
    background-color: #e6e9ef;
    text-align: center;
    color: #4c4f69;
    min-height: 20px;
}
QProgressBar::chunk {
    background-color: #1e66f5;
    border-radius: 5px;
}

QTextEdit {
    background-color: #ffffff;
    border: 1px solid #ccd0da;
    border-radius: 6px;
    color: #4c4f69;
    font-family: 'DejaVu Sans Mono', 'Liberation Mono', 'FreeMono', monospace;
    font-size: 11px;
    padding: 6px;
}

/* 스크롤바 - 세로 */
QScrollBar:vertical {
    background-color: #e6e9ef;
    width: 14px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background-color: #acb0be;
    border-radius: 5px;
    min-height: 30px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #9ca0b0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* 스크롤바 - 가로 */
QScrollBar:horizontal {
    background-color: #e6e9ef;
    height: 14px;
    border-radius: 7px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background-color: #acb0be;
    border-radius: 5px;
    min-width: 30px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #9ca0b0;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* 스크롤 영역 */
QScrollArea {
    border: none;
    background-color: transparent;
}

QLabel {
    color: #4c4f69;
}
QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #1e66f5;
}
QLabel#summaryLabel {
    font-size: 12px;
    color: #6c6f85;
    padding: 4px;
}

/* 상태바 */
QStatusBar {
    background-color: #e6e9ef;
    color: #4c4f69;
    border-top: 1px solid #ccd0da;
}

QSplitter::handle {
    background-color: #ccd0da;
    width: 2px;
}

/* 툴바 (matplotlib) */
QToolBar {
    background-color: #eff1f5;
    border: none;
    spacing: 4px;
}
"""


def get_theme_stylesheet(theme: str) -> str:
    """테마 이름에 해당하는 QSS 반환 (아이콘 경로 치환 포함)"""
    qss = DARK_THEME if theme == "dark" else LIGHT_THEME
    return qss.replace("{ICONS}", _ICONS_DIR)


def get_matplotlib_style(theme: str) -> dict:
    """matplotlib 차트에 적용할 스타일 딕셔너리 반환"""
    if theme == "dark":
        return {
            "figure.facecolor": "#1e1e2e",
            "axes.facecolor": "#181825",
            "axes.edgecolor": "#45475a",
            "axes.labelcolor": "#cdd6f4",
            "text.color": "#cdd6f4",
            "xtick.color": "#a6adc8",
            "ytick.color": "#a6adc8",
            "grid.color": "#313244",
            "grid.alpha": 0.5,
            "legend.facecolor": "#313244",
            "legend.edgecolor": "#45475a",
        }
    else:
        return {
            "figure.facecolor": "#eff1f5",
            "axes.facecolor": "#ffffff",
            "axes.edgecolor": "#ccd0da",
            "axes.labelcolor": "#4c4f69",
            "text.color": "#4c4f69",
            "xtick.color": "#6c6f85",
            "ytick.color": "#6c6f85",
            "grid.color": "#e6e9ef",
            "grid.alpha": 0.7,
            "legend.facecolor": "#ffffff",
            "legend.edgecolor": "#ccd0da",
        }
