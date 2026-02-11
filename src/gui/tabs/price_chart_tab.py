"""
탭 1: 주가 차트 탭
- 캔들스틱 / 라인 차트 표시
- 일봉/주봉/월봉 선택
- 스크롤(좌우 이동), 확대/축소, 기간 선택 기능
- matplotlib을 PyQt6에 임베딩
- 향후 확장: 기술 지표 오버레이(MA, BB, RSI 등), 거래량 바 차트
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.patches import Rectangle

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QPushButton,
    QDateEdit,
    QFrame,
)
from PyQt6.QtCore import QDate

from src.gui.themes import get_matplotlib_style

logger = logging.getLogger(__name__)


class PriceChartTab(QWidget):
    """주가 차트 탭 위젯"""

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self._price_data: Optional[pd.DataFrame] = None
        self._ticker = ""
        self._view_start = 0  # 현재 뷰 시작 인덱스
        self._view_size = 252  # 기본 1년 (약 252 거래일)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # --- 상단 컨트롤 바 ---
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # 차트 타입
        ctrl_layout.addWidget(QLabel("Chart:"))
        self.chart_type = QComboBox()
        self.chart_type.addItems(["Candlestick", "Line"])
        self.chart_type.currentIndexChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chart_type)

        # 봉 주기
        ctrl_layout.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        ctrl_layout.addWidget(self.period_combo)

        ctrl_layout.addWidget(self._vsep())

        # 기간 선택
        ctrl_layout.addWidget(QLabel("From:"))
        self.range_start = QDateEdit()
        self.range_start.setCalendarPopup(True)
        self.range_start.setDisplayFormat("yyyy-MM-dd")
        ctrl_layout.addWidget(self.range_start)

        ctrl_layout.addWidget(QLabel("To:"))
        self.range_end = QDateEdit()
        self.range_end.setCalendarPopup(True)
        self.range_end.setDisplayFormat("yyyy-MM-dd")
        ctrl_layout.addWidget(self.range_end)

        go_btn = QPushButton("Go")
        go_btn.setFixedWidth(50)
        go_btn.clicked.connect(self._on_range_go)
        ctrl_layout.addWidget(go_btn)

        ctrl_layout.addWidget(self._vsep())

        # 스크롤/줌 버튼
        btn_left = QPushButton("<<")
        btn_left.setFixedWidth(36)
        btn_left.setToolTip("이전 기간으로 스크롤")
        btn_left.clicked.connect(lambda: self._scroll(-0.5))
        ctrl_layout.addWidget(btn_left)

        btn_right = QPushButton(">>")
        btn_right.setFixedWidth(36)
        btn_right.setToolTip("다음 기간으로 스크롤")
        btn_right.clicked.connect(lambda: self._scroll(0.5))
        ctrl_layout.addWidget(btn_right)

        btn_zin = QPushButton("Zoom +")
        btn_zin.setFixedWidth(64)
        btn_zin.clicked.connect(lambda: self._zoom(0.5))
        ctrl_layout.addWidget(btn_zin)

        btn_zout = QPushButton("Zoom -")
        btn_zout.setFixedWidth(64)
        btn_zout.clicked.connect(lambda: self._zoom(2.0))
        ctrl_layout.addWidget(btn_zout)

        btn_all = QPushButton("All")
        btn_all.setFixedWidth(40)
        btn_all.setToolTip("전체 기간 표시")
        btn_all.clicked.connect(self._show_all)
        ctrl_layout.addWidget(btn_all)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # --- matplotlib 캔버스 ---
        style = get_matplotlib_style(self._theme)
        with plt.rc_context(style):
            self.fig, self.ax = plt.subplots(figsize=(12, 6))
            self.fig.subplots_adjust(left=0.06, right=0.96, top=0.94, bottom=0.10)

        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

    def _vsep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def set_data(self, ticker: str, price_data: pd.DataFrame):
        """새 주가 데이터를 설정하고 차트를 그린다."""
        self._ticker = ticker
        self._price_data = price_data.copy()

        if not price_data.empty:
            self.range_start.setDate(QDate(
                price_data.index[0].year,
                price_data.index[0].month,
                price_data.index[0].day,
            ))
            self.range_end.setDate(QDate(
                price_data.index[-1].year,
                price_data.index[-1].month,
                price_data.index[-1].day,
            ))

        # 최근 1년을 기본 뷰로
        total = len(self._get_display_data())
        self._view_size = min(252, total)
        self._view_start = max(0, total - self._view_size)
        self._redraw()

    def set_theme(self, theme: str):
        self._theme = theme
        self._redraw()

    # ------------------------------------------------------------------
    # 내부: 데이터 변환
    # ------------------------------------------------------------------
    def _get_display_data(self) -> pd.DataFrame:
        """현재 선택된 봉 주기에 맞춰 데이터를 리샘플링"""
        if self._price_data is None or self._price_data.empty:
            return pd.DataFrame()

        df = self._price_data.copy()
        period = self.period_combo.currentText()

        if period == "Weekly":
            df = df.resample("W").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna()
        elif period == "Monthly":
            df = df.resample("ME").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna()

        return df

    # ------------------------------------------------------------------
    # 내부: 그리기
    # ------------------------------------------------------------------
    def _redraw(self):
        """현재 뷰 범위의 차트를 다시 그린다."""
        df = self._get_display_data()
        if df.empty:
            return

        # 뷰 범위 클램프
        total = len(df)
        self._view_start = max(0, min(self._view_start, total - 1))
        end_idx = min(self._view_start + self._view_size, total)
        view_df = df.iloc[self._view_start:end_idx]

        if view_df.empty:
            return

        style = get_matplotlib_style(self._theme)

        self.ax.clear()
        with plt.rc_context(style):
            self.ax.set_facecolor(style["axes.facecolor"])
            self.fig.set_facecolor(style["figure.facecolor"])

            chart_type = self.chart_type.currentText()

            if chart_type == "Candlestick":
                self._draw_candlestick(view_df, style)
            else:
                self._draw_line(view_df, style)

            self.ax.set_title(
                f"{self._ticker} - {self.period_combo.currentText()}",
                color=style["text.color"],
                fontsize=14,
                fontweight="bold",
            )
            self.ax.grid(True, alpha=float(style["grid.alpha"]), color=style["grid.color"])
            self.ax.tick_params(colors=style["xtick.color"])

            # x축 날짜 포맷
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            self.fig.autofmt_xdate(rotation=30)

        self.canvas.draw_idle()

    def _draw_candlestick(self, df: pd.DataFrame, style: dict):
        """캔들스틱 차트 그리기 (matplotlib 수동 구현)"""
        dates = mdates.date2num(df.index.to_pydatetime())
        opens = df["Open"].values
        highs = df["High"].values
        lows = df["Low"].values
        closes = df["Close"].values

        # 봉 너비 계산
        if len(dates) > 1:
            width = np.median(np.diff(dates)) * 0.6
        else:
            width = 0.8

        up_color = "#a6e3a1" if self._theme == "dark" else "#40a02b"
        down_color = "#f38ba8" if self._theme == "dark" else "#d20f39"

        for i in range(len(dates)):
            color = up_color if closes[i] >= opens[i] else down_color

            # 꼬리 (high-low)
            self.ax.plot(
                [dates[i], dates[i]], [lows[i], highs[i]],
                color=color, linewidth=0.8,
            )

            # 몸통 (open-close)
            body_bottom = min(opens[i], closes[i])
            body_height = abs(closes[i] - opens[i])
            rect = Rectangle(
                (dates[i] - width / 2, body_bottom),
                width, body_height,
                facecolor=color, edgecolor=color, linewidth=0.5,
            )
            self.ax.add_patch(rect)

        self.ax.set_xlim(dates[0] - width * 2, dates[-1] + width * 2)
        margin = (df["High"].max() - df["Low"].min()) * 0.05
        self.ax.set_ylim(df["Low"].min() - margin, df["High"].max() + margin)

    def _draw_line(self, df: pd.DataFrame, style: dict):
        """라인 차트 그리기"""
        line_color = "#89b4fa" if self._theme == "dark" else "#1e66f5"
        self.ax.plot(df.index, df["Close"], color=line_color, linewidth=1.5, label="Close")
        self.ax.fill_between(df.index, df["Close"], alpha=0.1, color=line_color)
        self.ax.legend(loc="upper left")

    # ------------------------------------------------------------------
    # 내부: 스크롤/줌/기간 선택
    # ------------------------------------------------------------------
    def _scroll(self, ratio: float):
        """ratio만큼 뷰를 이동 (0.5 = 뷰 크기의 절반)"""
        step = int(self._view_size * ratio)
        total = len(self._get_display_data())
        self._view_start = max(0, min(self._view_start + step, total - self._view_size))
        self._redraw()

    def _zoom(self, factor: float):
        """factor로 뷰 크기를 조절 (0.5 = 축소/확대, 2.0 = 확대/축소)"""
        total = len(self._get_display_data())
        center = self._view_start + self._view_size // 2
        new_size = max(20, min(int(self._view_size * factor), total))
        self._view_size = new_size
        self._view_start = max(0, min(center - new_size // 2, total - new_size))
        self._redraw()

    def _show_all(self):
        """전체 데이터 표시"""
        total = len(self._get_display_data())
        self._view_start = 0
        self._view_size = total
        self._redraw()

    def _on_range_go(self):
        """기간 선택 Go 버튼"""
        df = self._get_display_data()
        if df.empty:
            return

        start = pd.Timestamp(self.range_start.date().toPyDate())
        end = pd.Timestamp(self.range_end.date().toPyDate())

        # 해당 범위의 인덱스 찾기
        mask = (df.index >= start) & (df.index <= end)
        filtered = df.loc[mask]
        if filtered.empty:
            return

        first_idx = df.index.get_loc(filtered.index[0])
        last_idx = df.index.get_loc(filtered.index[-1])

        if isinstance(first_idx, slice):
            first_idx = first_idx.start
        if isinstance(last_idx, slice):
            last_idx = last_idx.stop

        self._view_start = int(first_idx)
        self._view_size = int(last_idx - first_idx + 1)
        self._redraw()

    def _on_period_changed(self):
        """봉 주기 변경 시 뷰 리셋"""
        total = len(self._get_display_data())
        self._view_size = min(252, total)
        self._view_start = max(0, total - self._view_size)
        self._redraw()
