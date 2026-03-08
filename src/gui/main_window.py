"""
메인 윈도우
- 좌측 패널 + 우측 탭 + 하단 로그 + 프로그래스바 조립
- 백테스트 실행 워커 스레드 관리 (포트폴리오 지원)
- 테마 토글
- CSV 저장 기능
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QProgressBar,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QStatusBar,
)

from src.data.data_manager import DataManager
from src.engine.backtest_engine import (
    BacktestEngine,
    BacktestResult,
    PortfolioBacktestResult,
)
from src.strategies.pure_dca import PureDCAStrategy
from src.utils.config_manager import ConfigManager
from src.gui.left_panel import LeftPanel
from src.gui.tabs.price_chart_tab import PriceChartTab
from src.gui.tabs.backtest_chart_tab import BacktestChartTab
from src.gui.themes import get_theme_stylesheet

logger = logging.getLogger(__name__)

# 결과 저장 디렉토리
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ======================================================================
# 로그 핸들러: QTextEdit에 로그 출력
# ======================================================================
class QTextEditLogHandler(logging.Handler):
    """logging 핸들러 → QTextEdit에 로그를 추가"""

    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)


# ======================================================================
# 백테스트 워커 스레드 (포트폴리오 지원)
# ======================================================================
class BacktestWorker(QObject):
    """별도 스레드에서 포트폴리오 백테스트를 실행하는 워커"""

    finished = pyqtSignal(object)   # PortfolioBacktestResult 또는 None
    progress = pyqtSignal(int)      # 진행률 (0~100)
    error = pyqtSignal(str)         # 에러 메시지

    def __init__(
        self,
        data_manager: DataManager,
        engine: BacktestEngine,
        params: dict,
    ):
        super().__init__()
        self.data_manager = data_manager
        self.engine = engine
        self.params = params

    def run(self):
        try:
            p = self.params
            portfolio = p.get("portfolio", [])
            self.progress.emit(5)

            if not portfolio:
                self.error.emit("포트폴리오에 종목이 없습니다.")
                self.finished.emit(None)
                return

            tickers = [item["ticker"] for item in portfolio]
            ticker_str = ", ".join(tickers)

            # 1) 각 종목 주가 데이터 다운로드
            price_data_map: dict[str, pd.DataFrame] = {}
            progress_per_ticker = 30 / len(tickers)

            for i, ticker in enumerate(tickers):
                logger.info(f"데이터 다운로드: {ticker} ({i+1}/{len(tickers)})")
                price_data = self.data_manager.get_price_data(
                    ticker=ticker,
                    start=p["start_date"],
                    end=p["end_date"],
                )
                if price_data.empty:
                    self.error.emit(f"데이터를 가져올 수 없습니다: {ticker}")
                    self.finished.emit(None)
                    return
                price_data_map[ticker] = price_data
                self.progress.emit(int(5 + (i + 1) * progress_per_ticker))

            # 2) USD/KRW 환율 데이터 다운로드
            logger.info("USD/KRW 환율 데이터 다운로드 중...")
            exchange_rate_data = self.data_manager.get_exchange_rate_data(
                start=p["start_date"],
                end=p["end_date"],
            )
            self.progress.emit(45)

            # 3) 현재 환율 조회
            current_rate = self.data_manager.get_current_exchange_rate()
            self.progress.emit(50)

            # 4) 전략 선택
            strategy_name = p.get("strategy", "Pure DCA")
            if strategy_name == "Pure DCA":
                strategy = PureDCAStrategy()
            else:
                strategy = PureDCAStrategy()

            self.progress.emit(55)

            # 5) 포트폴리오 백테스트 실행
            logger.info(f"포트폴리오 백테스트 실행 중: {ticker_str}")
            result = self.engine.run_portfolio(
                portfolio=portfolio,
                price_data_map=price_data_map,
                strategy=strategy,
                buy_day=p["buy_day"],
                monthly_amount=p["monthly_amount"],
                annual_increase_pct=p["annual_increase_pct"],
                start_date=p["start_date"],
                end_date=p["end_date"],
                holiday_rule=p["holiday_rule"],
                exchange_rate_data=exchange_rate_data,
                current_exchange_rate=current_rate,
                buy_frequency=p.get("buy_frequency", "monthly"),
                buy_weekday=p.get("buy_weekday", 0),
            )
            self.progress.emit(90)

            if result is None:
                self.error.emit("백테스트 결과가 없습니다.")
            self.finished.emit(result)

        except Exception as e:
            logger.error(f"백테스트 워커 에러: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit(None)


# ======================================================================
# 메인 윈도우
# ======================================================================
class MainWindow(QMainWindow):
    """앱 메인 윈도우"""

    def __init__(self):
        super().__init__()

        # 코어 모듈 초기화
        self.config_manager = ConfigManager()
        self.data_manager = DataManager()
        self.engine = BacktestEngine()

        # 현재 테마
        self._theme = self.config_manager.get("theme", "dark")
        # 현재 백테스트 결과
        self._current_result: Optional[PortfolioBacktestResult] = None
        # 워커 스레드
        self._worker_thread: Optional[QThread] = None

        self._init_ui()
        self._setup_logging()
        self._apply_theme()

        logger.info("앱이 시작되었습니다. 포트폴리오를 설정하고 Run Backtest를 누르세요.")

    def _init_ui(self):
        self.setWindowTitle("Stock DCA Backtester")
        config = self.config_manager.get_all()
        self.resize(config.get("window_width", 1600), config.get("window_height", 900))

        # --- 중앙 위젯 ---
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # 상단: 테마 토글
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.theme_btn = QPushButton("Toggle Theme")
        self.theme_btn.setFixedWidth(140)
        self.theme_btn.clicked.connect(self._toggle_theme)
        top_bar.addWidget(self.theme_btn)
        main_layout.addLayout(top_bar)

        # --- 메인 스플리터 (좌측패널 | 우측탭) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 좌측 패널
        self.left_panel = LeftPanel(config)
        self.left_panel.setMinimumWidth(320)
        self.left_panel.setMaximumWidth(480)
        self.left_panel.run_requested.connect(self._on_run_backtest)
        self.left_panel.chart_requested.connect(self._on_load_chart)
        self.left_panel.save_btn.clicked.connect(self._on_save_csv)
        splitter.addWidget(self.left_panel)

        # 우측: 탭 + 로그
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 탭 위젯
        self.tabs = QTabWidget()
        self.price_chart_tab = PriceChartTab(theme=self._theme)
        self.backtest_chart_tab = BacktestChartTab(theme=self._theme)
        self.tabs.addTab(self.price_chart_tab, "Price Chart")
        self.tabs.addTab(self.backtest_chart_tab, "Backtest Results")
        right_layout.addWidget(self.tabs, 4)

        # 프로그래스바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        # 로그 창
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setPlaceholderText("Log output...")
        right_layout.addWidget(self.log_text, 1)

        splitter.addWidget(right_widget)
        splitter.setSizes([360, 1240])

        main_layout.addWidget(splitter)

        # 상태바
        self.statusBar().showMessage("Ready")

    def _setup_logging(self):
        """로그를 GUI 로그 창에 출력하도록 설정"""
        handler = QTextEditLogHandler(self.log_text)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

    def _apply_theme(self):
        """현재 테마를 앱에 적용"""
        self.setStyleSheet(get_theme_stylesheet(self._theme))
        self.price_chart_tab.set_theme(self._theme)
        self.backtest_chart_tab.set_theme(self._theme)

    def _toggle_theme(self):
        """다크/라이트 테마 토글"""
        self._theme = "light" if self._theme == "dark" else "dark"
        self.config_manager.set("theme", self._theme)
        self.config_manager.save()
        self._apply_theme()
        logger.info(f"테마 변경: {self._theme}")

    # ------------------------------------------------------------------
    # 이벤트 핸들러
    # ------------------------------------------------------------------
    @pyqtSlot(dict)
    def _on_load_chart(self, params: dict):
        """주가 차트 로드 (포트폴리오 전체)"""
        portfolio = params.get("portfolio", [])
        if not portfolio:
            return

        tickers = [item["ticker"] for item in portfolio]
        ticker_str = ", ".join(tickers)
        self.statusBar().showMessage(f"Loading {ticker_str}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

        try:
            price_data_map: dict[str, pd.DataFrame] = {}
            for i, ticker in enumerate(tickers):
                price_data = self.data_manager.get_price_data(
                    ticker=ticker,
                    start=params["start_date"],
                    end=params["end_date"],
                )
                if price_data.empty:
                    QMessageBox.warning(self, "Error", f"No data found for {ticker}")
                    return
                price_data_map[ticker] = price_data
                self.progress_bar.setValue(int(10 + (i + 1) * 70 / len(tickers)))

            self.price_chart_tab.set_multi_data(price_data_map)
            self.tabs.setCurrentIndex(0)
            logger.info(f"주가 차트 로드 완료: {ticker_str}")

        except Exception as e:
            logger.error(f"차트 로드 에러: {e}")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            self.statusBar().showMessage("Ready")

    @pyqtSlot(dict)
    def _on_run_backtest(self, params: dict):
        """포트폴리오 백테스트 실행 (워커 스레드)"""
        if self._worker_thread and self._worker_thread.isRunning():
            logger.warning("이미 백테스트가 실행 중입니다.")
            return

        # 비율 합계 검증
        portfolio = params.get("portfolio", [])
        total_ratio = sum(item["ratio"] for item in portfolio)
        if abs(total_ratio - 100) > 0.1:
            QMessageBox.warning(
                self, "Warning",
                f"포트폴리오 비율 합계가 100%가 아닙니다 ({total_ratio:.0f}%).\n"
                "비율을 조정해주세요."
            )
            return

        # 설정 저장
        self.config_manager.update(params)

        tickers = [item["ticker"] for item in portfolio]
        self.left_panel.set_running(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.statusBar().showMessage(f"Running backtest: {', '.join(tickers)}...")

        # 워커 생성 및 스레드 시작
        self._worker_thread = QThread()
        self._worker = BacktestWorker(self.data_manager, self.engine, params)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._on_backtest_done)
        self._worker.finished.connect(self._worker_thread.quit)

        self._worker_thread.start()

    @pyqtSlot(int)
    def _on_progress(self, value: int):
        self.progress_bar.setValue(value)

    @pyqtSlot(str)
    def _on_worker_error(self, msg: str):
        logger.error(f"백테스트 에러: {msg}")

    @pyqtSlot(object)
    def _on_backtest_done(self, result: Optional[PortfolioBacktestResult]):
        """백테스트 완료 콜백"""
        self.left_panel.set_running(False)
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)

        if result is None:
            self.statusBar().showMessage("Backtest failed")
            QMessageBox.warning(self, "Error", "백테스트 실행에 실패했습니다. 로그를 확인하세요.")
            return

        self._current_result = result

        # 주가 차트 탭에 모든 종목 데이터 반영
        price_data_map = {}
        for ticker, r in result.per_ticker_results.items():
            price_data_map[ticker] = r.daily_data
        self.price_chart_tab.set_multi_data(price_data_map)

        # 백테스트 결과 차트 표시
        self.backtest_chart_tab.set_portfolio_result(result)
        self.tabs.setCurrentIndex(1)

        # CSV 저장 버튼 활성화
        self.left_panel.save_btn.setEnabled(True)

        tickers_str = " + ".join(
            f"{item['ticker']}({item['ratio']}%)"
            for item in result.portfolio
            if item['ticker'] in result.per_ticker_results
        )
        self.statusBar().showMessage(
            f"Backtest complete: {tickers_str} | "
            f"Return: {result.total_return_pct:+.1f}% | "
            f"Profit: ₩{result.total_profit_krw:,.0f} | "
            f"Rate: ₩{result.current_exchange_rate:,.0f}/USD"
        )

    def _on_save_csv(self):
        """백테스트 결과를 CSV로 저장"""
        if self._current_result is None:
            return

        tickers_str = "_".join(
            item["ticker"] for item in self._current_result.portfolio
            if item["ticker"] in self._current_result.per_ticker_results
        )
        default_name = (
            f"backtest_{tickers_str}_"
            f"{self._current_result.strategy_name.replace(' ', '_')}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", str(OUTPUT_DIR / default_name),
            "CSV Files (*.csv);;All Files (*)",
        )

        if not file_path:
            return

        try:
            df = self._current_result.daily_data.copy()
            df.to_csv(file_path)
            logger.info(f"결과 저장 완료: {file_path}")
            self.statusBar().showMessage(f"Saved: {file_path}")
        except Exception as e:
            logger.error(f"CSV 저장 에러: {e}")
            QMessageBox.critical(self, "Error", f"저장 실패: {e}")

    def closeEvent(self, event):
        """앱 종료 시 설정 저장"""
        self.config_manager.set("window_width", self.width())
        self.config_manager.set("window_height", self.height())
        self.config_manager.save()
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            self._worker_thread.wait(3000)
        super().closeEvent(event)
