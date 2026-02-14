"""
좌측 입력 패널
- 종목, 기간, 투자 규칙, 전략 설정을 위한 입력 위젯 모음
- 향후 확장: 전략 파라미터 동적 로딩, 다중 종목 지원 등
"""

from datetime import date

from PyQt6.QtCore import Qt, QDate, pyqtSignal
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
)


class LeftPanel(QWidget):
    """좌측 파라미터 입력 패널"""

    # 시그널: Run 버튼 클릭 시 설정값 딕셔너리를 전달
    run_requested = pyqtSignal(dict)
    # 시그널: 주가 차트 로드 요청
    chart_requested = pyqtSignal(dict)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
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

        # --- A. 종목/자산 ---
        asset_group = QGroupBox("A. Ticker / Asset")
        asset_layout = QVBoxLayout()

        asset_layout.addWidget(QLabel("Ticker:"))
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("예: QQQ, VOO, AAPL")
        self.ticker_input.setToolTip("미국 주식/ETF 티커를 입력하세요")
        asset_layout.addWidget(self.ticker_input)

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

        # 투자금 (KRW)
        self.amount_label = QLabel("Monthly Investment (KRW):")
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
        # 향후 확장: 전략 리스트를 동적으로 로딩
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
        self.ticker_input.setText(config.get("ticker", "QQQ"))
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
            self.amount_label.setText("Weekly Investment (KRW):")
        else:
            self.amount_label.setText("Monthly Investment (KRW):")

    def get_params(self) -> dict:
        """현재 입력된 파라미터를 딕셔너리로 반환"""
        rule = "before" if self.holiday_rule.currentIndex() == 0 else "after"
        freq = "monthly" if self.buy_frequency.currentIndex() == 0 else "weekly"
        return {
            "ticker": self.ticker_input.text().strip().upper(),
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
        if params["ticker"]:
            self.run_requested.emit(params)

    def _on_chart_clicked(self):
        params = self.get_params()
        if params["ticker"]:
            self.chart_requested.emit(params)

    def set_running(self, running: bool):
        """백테스트 실행 중 UI 잠금/해제"""
        self.run_btn.setEnabled(not running)
        self.chart_btn.setEnabled(not running)
        self.run_btn.setText("Running..." if running else "Run Backtest")
