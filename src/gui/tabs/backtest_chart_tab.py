"""
탭 2: 백테스팅 결과 차트 탭
- 포트폴리오 (다중 종목) 백테스트 결과 시각화
- 개별 종목 가격 비교 + 총 포트폴리오 자산 곡선
- KRW 기준 수익금/수익률 표시 (환율 반영)
- 매수 타이밍 마커 표시
- 체크박스로 총 납입액, 수익금, 수익률 등 오버레이 선택
- 일별/주별/월별 보기
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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QCheckBox,
    QGroupBox,
    QFrame,
    QScrollArea,
)

from src.engine.backtest_engine import BacktestResult, PortfolioBacktestResult
from src.gui.themes import get_matplotlib_style

logger = logging.getLogger(__name__)

# 종목별 가격 색상 팔레트
PRICE_COLORS_DARK = [
    "#89b4fa", "#f9e2af", "#94e2d5", "#74c7ec",
    "#f5c2e7", "#b4befe", "#eba0ac", "#a6adc8",
    "#cdd6f4", "#89dceb",
]
PRICE_COLORS_LIGHT = [
    "#1e66f5", "#df8e1d", "#179299", "#209fb5",
    "#ea76cb", "#7287fd", "#e64553", "#6c6f85",
    "#4c4f69", "#04a5e5",
]


class BacktestChartTab(QWidget):
    """백테스팅 결과 시각화 탭 (포트폴리오 지원)"""

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self._result: Optional[PortfolioBacktestResult] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # --- 상단 컨트롤 바 ---
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # 봉 주기
        ctrl_layout.addWidget(QLabel("View:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.period_combo.currentIndexChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.period_combo)

        ctrl_layout.addWidget(self._vsep())

        # 오버레이 체크박스
        ctrl_layout.addWidget(QLabel("Overlay:"))

        self.chk_prices = QCheckBox("Individual Prices")
        self.chk_prices.setChecked(True)
        self.chk_prices.setToolTip("개별 종목 가격 표시 (정규화)")
        self.chk_prices.stateChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chk_prices)

        self.chk_invested = QCheckBox("Total Invested")
        self.chk_invested.setChecked(True)
        self.chk_invested.stateChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chk_invested)

        self.chk_profit = QCheckBox("Profit (KRW)")
        self.chk_profit.setChecked(False)
        self.chk_profit.stateChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chk_profit)

        self.chk_return = QCheckBox("Return (%)")
        self.chk_return.setChecked(False)
        self.chk_return.stateChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chk_return)

        self.chk_markers = QCheckBox("Buy Markers")
        self.chk_markers.setChecked(True)
        self.chk_markers.stateChanged.connect(self._redraw)
        ctrl_layout.addWidget(self.chk_markers)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # --- 요약 정보 라벨 ---
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryLabel")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # --- matplotlib 캔버스 ---
        style = get_matplotlib_style(self._theme)
        with plt.rc_context(style):
            self.fig, self.ax_price = plt.subplots(figsize=(12, 6))
            self.fig.subplots_adjust(left=0.07, right=0.88, top=0.92, bottom=0.10)

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
    def set_result(self, result: BacktestResult):
        """단일 종목 결과 (하위 호환) - PortfolioBacktestResult로 변환"""
        portfolio_result = PortfolioBacktestResult(
            portfolio=[{"ticker": result.ticker, "ratio": 100}],
            strategy_name=result.strategy_name,
            per_ticker_results={result.ticker: result},
            daily_data=result.daily_data,
            total_invested_krw=result.total_invested_krw,
            total_invested_usd=result.total_invested_usd,
            final_value_krw=result.final_value_krw,
            final_value_usd=result.final_value_usd,
            total_profit_krw=result.total_profit_krw,
            total_profit_usd=result.total_profit_usd,
            total_return_pct=result.total_return_pct,
            max_drawdown_pct=result.max_drawdown_pct,
            num_buys=result.num_buys,
            current_exchange_rate=result.current_exchange_rate,
        )
        self.set_portfolio_result(portfolio_result)

    def set_portfolio_result(self, result: PortfolioBacktestResult):
        """포트폴리오 백테스트 결과를 설정하고 차트를 그린다."""
        self._result = result
        self._update_summary()
        self._redraw()

    def set_theme(self, theme: str):
        self._theme = theme
        self._redraw()

    # ------------------------------------------------------------------
    # 내부
    # ------------------------------------------------------------------
    def _update_summary(self):
        """요약 통계 라벨 업데이트"""
        if self._result is None:
            self.summary_label.setText("")
            return

        r = self._result
        color_profit = "color: #a6e3a1;" if r.total_profit_krw >= 0 else "color: #f38ba8;"

        # 포트폴리오 구성 표시
        portfolio_parts = []
        for item in r.portfolio:
            ticker = item["ticker"]
            ratio = item["ratio"]
            if ticker in r.per_ticker_results:
                tr = r.per_ticker_results[ticker]
                div_part = ""
                if tr.total_dividend_usd > 0:
                    div_part = f" [Div: ${tr.total_dividend_usd:,.2f}]"
                portfolio_parts.append(
                    f"{ticker}({ratio:.0f}%): "
                    f"₩{tr.total_profit_krw:,.0f} ({tr.total_return_pct:+.1f}%){div_part}"
                )

        portfolio_str = " | ".join(portfolio_parts)

        tickers_str = " + ".join(
            f"{item['ticker']}({item['ratio']:.0f}%)"
            for item in r.portfolio
            if item['ticker'] in r.per_ticker_results
        )

        # 배당 정보
        div_str = ""
        if r.total_dividend_usd > 0:
            div_str = (
                f" | Dividend: <b>${r.total_dividend_usd:,.2f}</b>"
                f" (₩{r.total_dividend_krw:,.0f}) [DRIP]"
            )

        self.summary_label.setText(
            f"<b>{tickers_str}</b> | Strategy: {r.strategy_name} | "
            f"Buys: {r.num_buys}<br>"
            f"Invested: <b>₩{r.total_invested_krw:,.0f}</b> "
            f"(${r.total_invested_usd:,.0f}) | "
            f"Final: <b>₩{r.final_value_krw:,.0f}</b> "
            f"(${r.final_value_usd:,.0f}) | "
            f"<span style='{color_profit}'>"
            f"Profit: ₩{r.total_profit_krw:,.0f} "
            f"({r.total_return_pct:+.1f}%)</span> | "
            f"MDD: {r.max_drawdown_pct:.1f}%{div_str} | "
            f"Rate: ₩{r.current_exchange_rate:,.0f}/USD<br>"
            f"<small>{portfolio_str}</small>"
        )

    def _get_display_data(self) -> pd.DataFrame:
        """주기별 리샘플링"""
        if self._result is None:
            return pd.DataFrame()

        df = self._result.daily_data.copy()
        period = self.period_combo.currentText()

        if period in ("Weekly", "Monthly"):
            rule = "W" if period == "Weekly" else "ME"
            # 기본 집계 규칙
            agg = {
                "Portfolio_Value_USD": "last",
                "Portfolio_Value_KRW": "last",
                "Total_Invested_KRW": "last",
                "Total_Invested_USD": "last",
                "Profit_USD": "last",
                "Profit_KRW": "last",
                "Return_Pct": "last",
                "Buy_Flag": "max",
            }
            if "Cum_Dividend_USD" in df.columns:
                agg["Cum_Dividend_USD"] = "last"
            if "Cum_Dividend_KRW" in df.columns:
                agg["Cum_Dividend_KRW"] = "last"

            # 개별 종목 Close 컬럼 추가
            for col in df.columns:
                if col.startswith("Close_"):
                    agg[col] = "last"

            if "Exchange_Rate" in df.columns:
                agg["Exchange_Rate"] = "last"

            df = df.resample(rule).agg(agg).dropna(subset=["Portfolio_Value_KRW"])

        return df

    def _redraw(self):
        """차트를 다시 그린다."""
        df = self._get_display_data()
        if df.empty:
            return

        style = get_matplotlib_style(self._theme)
        price_colors = PRICE_COLORS_DARK if self._theme == "dark" else PRICE_COLORS_LIGHT

        # 오른쪽 여백 계산: 활성화된 추가 축 개수에 따라 동적 조정
        extra_axes = 0
        if self.chk_profit.isChecked():
            extra_axes += 1
        if self.chk_return.isChecked():
            extra_axes += 1
        # 기본 right=0.88 (equity 축 1개), 추가 축당 0.08씩 줄임
        right_margin = 0.88 - extra_axes * 0.08

        # 이전 축 모두 제거
        self.fig.clear()

        with plt.rc_context(style):
            self.ax_price = self.fig.add_subplot(111)
            self.ax_price.set_facecolor(style["axes.facecolor"])
            self.fig.set_facecolor(style["figure.facecolor"])

            # 1) 개별 종목 가격 (정규화, 왼쪽 축)
            if self.chk_prices.isChecked() and self._result is not None:
                close_cols = [c for c in df.columns if c.startswith("Close_")]
                for i, col in enumerate(close_cols):
                    ticker = col.replace("Close_", "")
                    color = price_colors[i % len(price_colors)]
                    series = df[col].dropna()
                    if not series.empty:
                        # 정규화 (시작=100)
                        base = series.iloc[0]
                        if base > 0:
                            normalized = (series / base) * 100
                        else:
                            normalized = series
                        self.ax_price.plot(
                            normalized.index, normalized,
                            color=color, linewidth=1.0,
                            label=f"{ticker} (Norm.)", alpha=0.7,
                            linestyle="-",
                        )

                if close_cols:
                    self.ax_price.set_ylabel("Normalized Price (Start=100)",
                                             color=style["text.color"])
                else:
                    self.ax_price.set_ylabel("Price", color=style["text.color"])
            else:
                self.ax_price.set_ylabel("", color=style["text.color"])

            # 2) 매수 마커 (가격 축에 표시)
            if self.chk_markers.isChecked():
                buy_dates = df[df["Buy_Flag"] > 0]
                if not buy_dates.empty and self.chk_prices.isChecked():
                    # 첫 번째 종목의 정규화 가격에 마커 표시
                    close_cols = [c for c in df.columns if c.startswith("Close_")]
                    if close_cols:
                        first_col = close_cols[0]
                        marker_series = buy_dates[first_col].dropna()
                        if not marker_series.empty:
                            base = df[first_col].dropna().iloc[0]
                            if base > 0:
                                marker_y = (marker_series / base) * 100
                            else:
                                marker_y = marker_series
                            marker_color = "#f9e2af" if self._theme == "dark" else "#df8e1d"
                            self.ax_price.scatter(
                                marker_y.index, marker_y,
                                marker="^", color=marker_color, s=40, zorder=5,
                                label="Buy", edgecolors="none", alpha=0.7,
                            )

            # 3) 누적 자산 곡선 - KRW (오른쪽 축)
            ax_equity = self.ax_price.twinx()
            equity_color = "#a6e3a1" if self._theme == "dark" else "#40a02b"
            ax_equity.plot(
                df.index, df["Portfolio_Value_KRW"], color=equity_color,
                linewidth=2.0, label="Portfolio (KRW)", alpha=0.9,
            )
            ax_equity.set_ylabel("Portfolio Value (KRW)", color=equity_color)
            ax_equity.tick_params(axis="y", labelcolor=equity_color)
            ax_equity.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, _: f"₩{x:,.0f}")
            )

            # 4) 총 납입액 오버레이 (KRW)
            if self.chk_invested.isChecked():
                inv_color = "#cba6f7" if self._theme == "dark" else "#8839ef"
                ax_equity.plot(
                    df.index, df["Total_Invested_KRW"], color=inv_color,
                    linewidth=1.2, linestyle="--", label="Invested (KRW)", alpha=0.8,
                )

            # 추가 축 위치 카운터 (equity 축 바로 바깥부터)
            next_axis_pos = 1.0

            # 5) 수익금 오버레이 (KRW)
            if self.chk_profit.isChecked():
                ax_profit = self.ax_price.twinx()
                next_axis_pos += 0.10
                ax_profit.spines["right"].set_position(("axes", next_axis_pos))
                profit_color = "#fab387" if self._theme == "dark" else "#fe640b"
                ax_profit.plot(
                    df.index, df["Profit_KRW"], color=profit_color,
                    linewidth=1.0, linestyle="-.", label="Profit (KRW)", alpha=0.8,
                )
                ax_profit.set_ylabel("Profit (KRW)", color=profit_color)
                ax_profit.tick_params(axis="y", labelcolor=profit_color)
                ax_profit.yaxis.set_major_formatter(
                    plt.FuncFormatter(lambda x, _: f"₩{x:,.0f}")
                )

            # 6) 수익률 오버레이
            if self.chk_return.isChecked():
                ax_return = self.ax_price.twinx()
                next_axis_pos += 0.10
                ax_return.spines["right"].set_position(("axes", next_axis_pos))
                ret_color = "#f38ba8" if self._theme == "dark" else "#d20f39"
                ax_return.plot(
                    df.index, df["Return_Pct"], color=ret_color,
                    linewidth=1.0, linestyle=":", label="Return (%)", alpha=0.8,
                )
                ax_return.set_ylabel("Return (%)", color=ret_color)
                ax_return.tick_params(axis="y", labelcolor=ret_color)

            # 제목
            if self._result is not None:
                tickers_str = " + ".join(
                    f"{item['ticker']}({item['ratio']:.0f}%)"
                    for item in self._result.portfolio
                    if item['ticker'] in self._result.per_ticker_results
                )
                self.ax_price.set_title(
                    f"Portfolio: {tickers_str} - {self._result.strategy_name}",
                    color=style["text.color"], fontsize=14, fontweight="bold",
                )

            self.ax_price.grid(True, alpha=float(style["grid.alpha"]), color=style["grid.color"])

            # 범례 합치기
            lines1, labels1 = self.ax_price.get_legend_handles_labels()
            lines2, labels2 = ax_equity.get_legend_handles_labels()
            self.ax_price.legend(
                lines1 + lines2, labels1 + labels2,
                loc="upper left", fontsize=8,
                facecolor=style["legend.facecolor"],
                edgecolor=style["legend.edgecolor"],
            )

            self.ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            self.fig.autofmt_xdate(rotation=30)

            self.fig.subplots_adjust(left=0.07, right=right_margin, top=0.92, bottom=0.12)

        self.canvas.draw_idle()
