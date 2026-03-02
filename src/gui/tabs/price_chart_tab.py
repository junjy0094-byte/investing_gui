"""
탭 1: 주가 차트 탭
- 캔들스틱 / 라인 차트 표시 (다중 종목 지원)
- 다중 종목: 라인 차트로 비교 (정규화 옵션)
- 일봉/주봉/월봉 선택
- 스크롤(좌우 이동), 확대/축소, 기간 선택 기능
- matplotlib을 PyQt6에 임베딩
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
    QCheckBox,
)
from PyQt6.QtCore import QDate

from src.gui.themes import get_matplotlib_style

logger = logging.getLogger(__name__)

# 다중 종목 색상 팔레트
MULTI_COLORS_DARK = [
    "#89b4fa", "#a6e3a1", "#fab387", "#f38ba8",
    "#cba6f7", "#f9e2af", "#94e2d5", "#74c7ec",
    "#f5c2e7", "#b4befe",
]
MULTI_COLORS_LIGHT = [
    "#1e66f5", "#40a02b", "#fe640b", "#d20f39",
    "#8839ef", "#df8e1d", "#179299", "#209fb5",
    "#ea76cb", "#7287fd",
]


class PriceChartTab(QWidget):
    """주가 차트 탭 위젯 (다중 종목 지원)"""

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        # 다중 종목 데이터: {ticker: DataFrame}
        self._price_data_map: dict[str, pd.DataFrame] = {}
        self._tickers: list[str] = []
        self._view_start = 0
        self._view_size = 252
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
        self.chart_type.addItems(["Line", "Candlestick"])
        self.chart_type.currentIndexChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chart_type)

        # 봉 주기
        ctrl_layout.addWidget(QLabel("Period:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        ctrl_layout.addWidget(self.period_combo)

        ctrl_layout.addWidget(self._vsep())

        # 정규화 (100 기준)
        self.chk_normalize = QCheckBox("Normalize (100)")
        self.chk_normalize.setToolTip("시작점을 100으로 정규화하여 비교")
        self.chk_normalize.setChecked(False)
        self.chk_normalize.stateChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chk_normalize)

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
        go_btn.setFixedWidth(56)
        go_btn.clicked.connect(self._on_range_go)
        ctrl_layout.addWidget(go_btn)

        ctrl_layout.addWidget(self._vsep())

        # 스크롤/줌 버튼
        btn_left = QPushButton("<<")
        btn_left.setFixedWidth(44)
        btn_left.setToolTip("이전 기간으로 스크롤")
        btn_left.clicked.connect(lambda: self._scroll(-0.5))
        ctrl_layout.addWidget(btn_left)

        btn_right = QPushButton(">>")
        btn_right.setFixedWidth(44)
        btn_right.setToolTip("다음 기간으로 스크롤")
        btn_right.clicked.connect(lambda: self._scroll(0.5))
        ctrl_layout.addWidget(btn_right)

        btn_zin = QPushButton("Zoom +")
        btn_zin.setFixedWidth(80)
        btn_zin.clicked.connect(lambda: self._zoom(0.5))
        ctrl_layout.addWidget(btn_zin)

        btn_zout = QPushButton("Zoom -")
        btn_zout.setFixedWidth(80)
        btn_zout.clicked.connect(lambda: self._zoom(2.0))
        ctrl_layout.addWidget(btn_zout)

        btn_all = QPushButton("All")
        btn_all.setFixedWidth(52)
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
        """단일 종목 데이터 설정 (하위 호환)"""
        self.set_multi_data({ticker: price_data})

    def set_multi_data(self, price_data_map: dict[str, pd.DataFrame]):
        """다중 종목 데이터를 설정하고 차트를 그린다."""
        self._price_data_map = {t: df.copy() for t, df in price_data_map.items()}
        self._tickers = list(price_data_map.keys())

        # 다중 종목이면 캔들스틱 비활성화
        if len(self._tickers) > 1:
            self.chart_type.setCurrentIndex(0)  # Line
            self.chk_normalize.setVisible(True)
        else:
            self.chk_normalize.setVisible(True)

        # 날짜 범위 설정 (전체 합집합)
        all_dates = pd.DatetimeIndex([])
        for df in price_data_map.values():
            if not df.empty:
                all_dates = all_dates.union(df.index)

        if len(all_dates) > 0:
            all_dates = all_dates.sort_values()
            self.range_start.setDate(QDate(
                all_dates[0].year, all_dates[0].month, all_dates[0].day,
            ))
            self.range_end.setDate(QDate(
                all_dates[-1].year, all_dates[-1].month, all_dates[-1].day,
            ))

        # 최근 1년을 기본 뷰로
        total = len(self._get_combined_index())
        self._view_size = min(252, total)
        self._view_start = max(0, total - self._view_size)
        self._redraw()

    def set_theme(self, theme: str):
        self._theme = theme
        self._redraw()

    # ------------------------------------------------------------------
    # 내부: 데이터 변환
    # ------------------------------------------------------------------
    def _get_combined_index(self) -> pd.DatetimeIndex:
        """모든 종목의 날짜 합집합 (리샘플링 반영)"""
        if not self._price_data_map:
            return pd.DatetimeIndex([])

        period = self.period_combo.currentText()
        all_dates = pd.DatetimeIndex([])

        for ticker, df in self._price_data_map.items():
            resampled = self._resample(df, period)
            if not resampled.empty:
                all_dates = all_dates.union(resampled.index)

        return all_dates.sort_values()

    def _resample(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """주기별 리샘플링"""
        if df.empty:
            return df

        if period == "Weekly":
            return df.resample("W").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna()
        elif period == "Monthly":
            return df.resample("ME").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna()
        return df

    def _get_display_data(self, ticker: str) -> pd.DataFrame:
        """특정 종목의 리샘플링된 데이터"""
        if ticker not in self._price_data_map:
            return pd.DataFrame()
        df = self._price_data_map[ticker]
        period = self.period_combo.currentText()
        return self._resample(df, period)

    # ------------------------------------------------------------------
    # 내부: 그리기
    # ------------------------------------------------------------------
    def _redraw(self):
        """현재 뷰 범위의 차트를 다시 그린다."""
        if not self._tickers:
            return

        combined_idx = self._get_combined_index()
        if combined_idx.empty:
            return

        # 뷰 범위 클램프
        total = len(combined_idx)
        self._view_start = max(0, min(self._view_start, total - 1))
        end_idx = min(self._view_start + self._view_size, total)
        view_dates = combined_idx[self._view_start:end_idx]

        if view_dates.empty:
            return

        style = get_matplotlib_style(self._theme)
        colors = MULTI_COLORS_DARK if self._theme == "dark" else MULTI_COLORS_LIGHT

        self.ax.clear()
        with plt.rc_context(style):
            self.ax.set_facecolor(style["axes.facecolor"])
            self.fig.set_facecolor(style["figure.facecolor"])

            chart_type = self.chart_type.currentText()
            normalize = self.chk_normalize.isChecked()

            if len(self._tickers) == 1 and chart_type == "Candlestick":
                # 단일 종목 캔들스틱
                ticker = self._tickers[0]
                df = self._get_display_data(ticker)
                view_mask = (df.index >= view_dates[0]) & (df.index <= view_dates[-1])
                view_df = df.loc[view_mask]
                if not view_df.empty:
                    self._draw_candlestick(view_df, style)
                    self.ax.set_title(
                        f"{ticker} - {self.period_combo.currentText()}",
                        color=style["text.color"], fontsize=14, fontweight="bold",
                    )
            else:
                # 라인 차트 (다중 종목 지원)
                for i, ticker in enumerate(self._tickers):
                    df = self._get_display_data(ticker)
                    if df.empty:
                        continue

                    view_mask = (df.index >= view_dates[0]) & (df.index <= view_dates[-1])
                    view_df = df.loc[view_mask]
                    if view_df.empty:
                        continue

                    color = colors[i % len(colors)]
                    y_values = view_df["Close"]

                    if normalize and len(y_values) > 0:
                        base = y_values.iloc[0]
                        if base > 0:
                            y_values = (y_values / base) * 100

                    self.ax.plot(
                        view_df.index, y_values,
                        color=color, linewidth=1.5,
                        label=ticker, alpha=0.9,
                    )

                    if len(self._tickers) == 1:
                        self.ax.fill_between(view_df.index, y_values, alpha=0.1, color=color)

                title_tickers = " / ".join(self._tickers)
                suffix = " (Normalized)" if normalize else ""
                self.ax.set_title(
                    f"{title_tickers} - {self.period_combo.currentText()}{suffix}",
                    color=style["text.color"], fontsize=14, fontweight="bold",
                )

                if normalize:
                    self.ax.set_ylabel("Normalized (Start=100)", color=style["text.color"])
                else:
                    self.ax.set_ylabel("Price (USD)", color=style["text.color"])

                self.ax.legend(
                    loc="upper left", fontsize=9,
                    facecolor=style["legend.facecolor"],
                    edgecolor=style["legend.edgecolor"],
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

    # ------------------------------------------------------------------
    # 내부: 스크롤/줌/기간 선택
    # ------------------------------------------------------------------
    def _scroll(self, ratio: float):
        step = int(self._view_size * ratio)
        total = len(self._get_combined_index())
        self._view_start = max(0, min(self._view_start + step, total - self._view_size))
        self._redraw()

    def _zoom(self, factor: float):
        total = len(self._get_combined_index())
        center = self._view_start + self._view_size // 2
        new_size = max(20, min(int(self._view_size * factor), total))
        self._view_size = new_size
        self._view_start = max(0, min(center - new_size // 2, total - new_size))
        self._redraw()

    def _show_all(self):
        total = len(self._get_combined_index())
        self._view_start = 0
        self._view_size = total
        self._redraw()

    def _on_range_go(self):
        combined_idx = self._get_combined_index()
        if combined_idx.empty:
            return

        start = pd.Timestamp(self.range_start.date().toPyDate())
        end = pd.Timestamp(self.range_end.date().toPyDate())

        mask = (combined_idx >= start) & (combined_idx <= end)
        filtered = combined_idx[mask]
        if filtered.empty:
            return

        first_idx = combined_idx.get_loc(filtered[0])
        last_idx = combined_idx.get_loc(filtered[-1])

        if isinstance(first_idx, slice):
            first_idx = first_idx.start
        if isinstance(last_idx, slice):
            last_idx = last_idx.stop

        self._view_start = int(first_idx)
        self._view_size = int(last_idx - first_idx + 1)
        self._redraw()

    def _on_period_changed(self):
        total = len(self._get_combined_index())
        self._view_size = min(252, total)
        self._view_start = max(0, total - self._view_size)
        self._redraw()
