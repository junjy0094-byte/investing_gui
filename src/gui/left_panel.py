"""
좌측 입력 패널
- 포트폴리오 (다중 종목 + 비율) 설정
- 티커 검색/자동완성 지원
- 기간, 투자 규칙, 전략 설정
"""

from datetime import date

from PyQt6.QtCore import Qt, QDate, pyqtSignal, QStringListModel, QTimer
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QDateEdit,
    QComboBox,
    QPushButton,
    QCheckBox,
    QScrollArea,
    QFrame,
    QCompleter,
    QSizePolicy,
)

from src.data.ticker_database import (
    search_tickers,
    get_display_text,
    parse_ticker_from_display,
    TICKER_DATABASE,
)


class TickerSearchWidget(QWidget):
    """티커 검색 위젯 - 자동완성 기능 포함"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.input = QLineEdit()
        self.input.setPlaceholderText("티커 또는 종목명 검색 (예: QQQ, Apple)")
        self.input.setToolTip("티커 심볼 또는 종목명을 입력하면 자동완성됩니다")

        # 자동완성 설정
        self._all_items = [get_display_text(t, n) for t, n in TICKER_DATABASE]
        self._completer_model = QStringListModel(self._all_items)
        self._completer = QCompleter()
        self._completer.setModel(self._completer_model)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setMaxVisibleItems(15)
        self.input.setCompleter(self._completer)

        # 검색 결과 업데이트 (타이핑 시 필터링)
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(150)
        self._update_timer.timeout.connect(self._update_completions)
        self.input.textChanged.connect(lambda: self._update_timer.start())

        layout.addWidget(self.input)

    def _update_completions(self):
        text = self.input.text().strip()
        if text:
            results = search_tickers(text, limit=30)
            items = [get_display_text(t, n) for t, n in results]
        else:
            items = self._all_items
        self._completer_model.setStringList(items)

    def get_ticker(self) -> str:
        text = self.input.text().strip()
        if "  -  " in text:
            return parse_ticker_from_display(text)
        return text.upper()

    def set_ticker(self, ticker: str):
        # 데이터베이스에서 이름 찾기
        for t, name in TICKER_DATABASE:
            if t == ticker.upper():
                self.input.setText(get_display_text(t, name))
                return
        self.input.setText(ticker.upper())


class PortfolioRow(QWidget):
    """포트폴리오 종목 한 행: [티커 검색] [비율 %] [삭제]"""

    remove_requested = pyqtSignal(object)  # self를 전달

    def __init__(self, ticker: str = "", ratio: float = 100.0, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        # 티커 검색 위젯
        self.ticker_widget = TickerSearchWidget()
        if ticker:
            self.ticker_widget.set_ticker(ticker)
        layout.addWidget(self.ticker_widget, 3)

        # 비율 입력
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(1, 100)
        self.ratio_spin.setSingleStep(5)
        self.ratio_spin.setSuffix(" %")
        self.ratio_spin.setDecimals(0)
        self.ratio_spin.setValue(ratio)
        self.ratio_spin.setFixedWidth(85)
        layout.addWidget(self.ratio_spin, 0)

        # 삭제 버튼
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(28, 28)
        self.remove_btn.setToolTip("이 종목 제거")
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(self.remove_btn, 0)

    def get_data(self) -> dict:
        return {
            "ticker": self.ticker_widget.get_ticker(),
            "ratio": self.ratio_spin.value(),
        }

    def set_data(self, ticker: str, ratio: float):
        self.ticker_widget.set_ticker(ticker)
        self.ratio_spin.setValue(ratio)


class LeftPanel(QWidget):
    """좌측 파라미터 입력 패널"""

    # 시그널: Run 버튼 클릭 시 설정값 딕셔너리를 전달
    run_requested = pyqtSignal(dict)
    # 시그널: 주가 차트 로드 요청
    chart_requested = pyqtSignal(dict)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._portfolio_rows: list[PortfolioRow] = []
        self._init_ui()
        self._load_config(config)

    def _init_ui(self):
        # 스크롤 가능한 레이아웃
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # 타이틀
        title = QLabel("Backtest Settings")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # --- A. 포트폴리오 ---
        asset_group = QGroupBox("A. Portfolio")
        asset_layout = QVBoxLayout()

        asset_layout.addWidget(QLabel("종목을 추가하고 비율을 설정하세요:"))

        # 포트폴리오 행들이 들어갈 컨테이너
        self._portfolio_container = QVBoxLayout()
        self._portfolio_container.setSpacing(4)
        asset_layout.addLayout(self._portfolio_container)

        # 종목 추가 버튼 + 비율 합계 표시
        add_row_layout = QHBoxLayout()
        self.add_ticker_btn = QPushButton("+ Add Ticker")
        self.add_ticker_btn.setToolTip("포트폴리오에 종목 추가")
        self.add_ticker_btn.clicked.connect(self._add_empty_row)
        add_row_layout.addWidget(self.add_ticker_btn)

        self.ratio_total_label = QLabel("Total: 0%")
        self.ratio_total_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        add_row_layout.addWidget(self.ratio_total_label)
        asset_layout.addLayout(add_row_layout)

        # 비율 균등 분배 버튼
        self.equalize_btn = QPushButton("Equal Weight")
        self.equalize_btn.setToolTip("모든 종목 비율을 균등하게 분배")
        self.equalize_btn.clicked.connect(self._equalize_ratios)
        asset_layout.addWidget(self.equalize_btn)

        asset_group.setLayout(asset_layout)
        layout.addWidget(asset_group)

        # --- B. 기간/적립식 규칙 ---
        period_group = QGroupBox("B. Period / DCA Rule")
        period_layout = QVBoxLayout()

        # 시작일
        period_layout.addWidget(QLabel("Start Date:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        period_layout.addWidget(self.start_date)

        # 종료일
        period_layout.addWidget(QLabel("End Date:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        period_layout.addWidget(self.end_date)

        # 매수 주기 (월별/주별)
        period_layout.addWidget(QLabel("Buy Frequency:"))
        self.buy_frequency = QComboBox()
        self.buy_frequency.addItems(["Monthly (월별)", "Weekly (주별)"])
        self.buy_frequency.currentIndexChanged.connect(self._on_frequency_changed)
        period_layout.addWidget(self.buy_frequency)

        # 매수일
        self.buy_day_label = QLabel("Buy Day of Month:")
        period_layout.addWidget(self.buy_day_label)
        self.buy_day = QSpinBox()
        self.buy_day.setRange(1, 28)
        self.buy_day.setToolTip("매월 매수할 날짜 (1~28)")
        period_layout.addWidget(self.buy_day)

        # 매수 요일 (주별 모드용)
        self.buy_weekday_label = QLabel("Buy Day of Week:")
        period_layout.addWidget(self.buy_weekday_label)
        self.buy_weekday = QComboBox()
        self.buy_weekday.addItems([
            "Monday (월)", "Tuesday (화)", "Wednesday (수)",
            "Thursday (목)", "Friday (금)",
        ])
        period_layout.addWidget(self.buy_weekday)
        # 초기에는 주별 위젯 숨김
        self.buy_weekday_label.setVisible(False)
        self.buy_weekday.setVisible(False)

        # 휴장일 처리
        period_layout.addWidget(QLabel("Holiday Rule:"))
        self.holiday_rule = QComboBox()
        self.holiday_rule.addItems(["before (직전 거래일)", "after (직후 거래일)"])
        period_layout.addWidget(self.holiday_rule)

        # 투자금 (KRW) - 전체 포트폴리오 총 금액
        self.amount_label = QLabel("Monthly Total Investment (KRW):")
        period_layout.addWidget(self.amount_label)
        self.monthly_amount = QDoubleSpinBox()
        self.monthly_amount.setRange(10000, 100_000_000)
        self.monthly_amount.setSingleStep(10000)
        self.monthly_amount.setPrefix("₩ ")
        self.monthly_amount.setDecimals(0)
        period_layout.addWidget(self.monthly_amount)

        # 연간 투자금 증가율
        period_layout.addWidget(QLabel("Annual Increase (%):"))
        self.annual_increase = QDoubleSpinBox()
        self.annual_increase.setRange(0, 100)
        self.annual_increase.setSingleStep(0.5)
        self.annual_increase.setSuffix(" %")
        self.annual_increase.setDecimals(1)
        period_layout.addWidget(self.annual_increase)

        period_group.setLayout(period_layout)
        layout.addWidget(period_group)

        # --- C. 전략 선택 ---
        strategy_group = QGroupBox("C. Strategy")
        strategy_layout = QVBoxLayout()

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Pure DCA"])
        strategy_layout.addWidget(self.strategy_combo)

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # --- 버튼들 ---
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        # 주가 차트 로드 버튼
        self.chart_btn = QPushButton("Load Price Chart")
        self.chart_btn.setToolTip("선택한 종목의 주가 차트를 로드합니다")
        self.chart_btn.clicked.connect(self._on_chart_clicked)
        btn_layout.addWidget(self.chart_btn)

        # Run 백테스트 버튼
        self.run_btn = QPushButton("Run Backtest")
        self.run_btn.setObjectName("runButton")
        self.run_btn.setToolTip("백테스트를 실행합니다")
        self.run_btn.clicked.connect(self._on_run_clicked)
        btn_layout.addWidget(self.run_btn)

        # 결과 저장 버튼
        self.save_btn = QPushButton("Save Results (CSV)")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        # 스페이서
        layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _load_config(self, config: dict):
        """설정값을 위젯에 반영"""
        # 포트폴리오 로드
        portfolio = config.get("portfolio", None)
        if portfolio and isinstance(portfolio, list):
            for item in portfolio:
                self._add_portfolio_row(
                    ticker=item.get("ticker", ""),
                    ratio=item.get("ratio", 100),
                )
        else:
            # 기존 단일 티커 호환
            ticker = config.get("ticker", "QQQ")
            self._add_portfolio_row(ticker=ticker, ratio=100)

        self.start_date.setDate(QDate.fromString(config.get("start_date", "2020-01-01"), "yyyy-MM-dd"))
        self.end_date.setDate(QDate.fromString(config.get("end_date", "2025-12-31"), "yyyy-MM-dd"))
        self.buy_day.setValue(config.get("buy_day", 20))
        self.buy_weekday.setCurrentIndex(config.get("buy_weekday", 0))
        self.monthly_amount.setValue(config.get("monthly_amount", 500000))
        self.annual_increase.setValue(config.get("annual_increase_pct", 0.0))

        freq = config.get("buy_frequency", "monthly")
        self.buy_frequency.setCurrentIndex(0 if freq == "monthly" else 1)
        self._on_frequency_changed(self.buy_frequency.currentIndex())

        rule = config.get("holiday_rule", "before")
        self.holiday_rule.setCurrentIndex(0 if rule == "before" else 1)

    # ------------------------------------------------------------------
    # 포트폴리오 행 관리
    # ------------------------------------------------------------------
    def _add_portfolio_row(self, ticker: str = "", ratio: float = 100.0):
        """포트폴리오에 종목 행 추가"""
        row = PortfolioRow(ticker=ticker, ratio=ratio)
        row.remove_requested.connect(self._remove_portfolio_row)
        row.ratio_spin.valueChanged.connect(self._update_ratio_total)
        self._portfolio_rows.append(row)
        self._portfolio_container.addWidget(row)
        self._update_ratio_total()

    def _add_empty_row(self):
        """빈 종목 행 추가"""
        # 새 종목의 기본 비율 계산
        current_total = sum(r.ratio_spin.value() for r in self._portfolio_rows)
        remaining = max(0, 100 - current_total)
        self._add_portfolio_row(ticker="", ratio=min(remaining, 100) if remaining > 0 else 10)

    def _remove_portfolio_row(self, row: PortfolioRow):
        """포트폴리오에서 종목 행 제거"""
        if len(self._portfolio_rows) <= 1:
            return  # 최소 1개 유지
        self._portfolio_rows.remove(row)
        self._portfolio_container.removeWidget(row)
        row.deleteLater()
        self._update_ratio_total()

    def _equalize_ratios(self):
        """모든 종목 비율을 균등 분배"""
        n = len(self._portfolio_rows)
        if n == 0:
            return
        each = round(100 / n)
        remainder = 100 - each * n
        for i, row in enumerate(self._portfolio_rows):
            val = each + (1 if i < remainder else 0)
            row.ratio_spin.setValue(val)
        self._update_ratio_total()

    def _update_ratio_total(self):
        """비율 합계 라벨 업데이트"""
        total = sum(r.ratio_spin.value() for r in self._portfolio_rows)
        if abs(total - 100) < 0.01:
            self.ratio_total_label.setText(f"Total: {total:.0f}%")
            self.ratio_total_label.setStyleSheet("color: #a6e3a1;")
        else:
            self.ratio_total_label.setText(f"Total: {total:.0f}% (≠ 100%)")
            self.ratio_total_label.setStyleSheet("color: #f38ba8;")

    def _on_frequency_changed(self, index: int):
        """매수 주기 변경 시 UI 동적 전환"""
        is_weekly = index == 1
        # 월별 위젯
        self.buy_day_label.setVisible(not is_weekly)
        self.buy_day.setVisible(not is_weekly)
        # 주별 위젯
        self.buy_weekday_label.setVisible(is_weekly)
        self.buy_weekday.setVisible(is_weekly)
        # 라벨 변경
        if is_weekly:
            self.amount_label.setText("Weekly Total Investment (KRW):")
        else:
            self.amount_label.setText("Monthly Total Investment (KRW):")

    def get_portfolio(self) -> list[dict]:
        """포트폴리오 종목 리스트 반환"""
        portfolio = []
        for row in self._portfolio_rows:
            data = row.get_data()
            if data["ticker"]:
                portfolio.append(data)
        return portfolio

    def get_params(self) -> dict:
        """현재 입력된 파라미터를 딕셔너리로 반환"""
        rule = "before" if self.holiday_rule.currentIndex() == 0 else "after"
        freq = "monthly" if self.buy_frequency.currentIndex() == 0 else "weekly"
        portfolio = self.get_portfolio()

        # 하위 호환: 첫 번째 티커를 기본 ticker로
        first_ticker = portfolio[0]["ticker"] if portfolio else ""

        return {
            "portfolio": portfolio,
            "ticker": first_ticker,
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "end_date": self.end_date.date().toString("yyyy-MM-dd"),
            "buy_frequency": freq,
            "buy_day": self.buy_day.value(),
            "buy_weekday": self.buy_weekday.currentIndex(),
            "monthly_amount": self.monthly_amount.value(),
            "annual_increase_pct": self.annual_increase.value(),
            "holiday_rule": rule,
            "strategy": self.strategy_combo.currentText(),
        }

    def _on_run_clicked(self):
        params = self.get_params()
        portfolio = params.get("portfolio", [])
        if not portfolio:
            return
        self.run_requested.emit(params)

    def _on_chart_clicked(self):
        params = self.get_params()
        portfolio = params.get("portfolio", [])
        if not portfolio:
            return
        self.chart_requested.emit(params)

    def set_running(self, running: bool):
        """백테스트 실행 중 UI 잠금/해제"""
        self.run_btn.setEnabled(not running)
        self.chart_btn.setEnabled(not running)
        self.run_btn.setText("Running..." if running else "Run Backtest")
