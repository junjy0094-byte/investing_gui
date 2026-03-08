"""
좌측 입력 패널
- 포트폴리오 (다중 종목 + 비율) 설정
- 티커 검색/자동완성 지원
- 기간, 투자 규칙, 전략 설정
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

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


class KrwSpinBox(QSpinBox):
    """KRW 금액 입력 - 콤마 구분 표시 (예: ₩500,000)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPrefix("₩")

    def textFromValue(self, value: int) -> str:
        return f"{value:,}"

    def valueFromText(self, text: str) -> int:
        clean = text.replace("₩", "").replace(",", "").strip()
        try:
            return int(clean)
        except ValueError:
            return 0


class TickerSearchWidget(QWidget):
    """티커 검색 위젯 - 자동완성 기능 포함"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.input = QLineEdit()
        self.input.setPlaceholderText("티커/종목명 (예: QQQ)")
        self.input.setToolTip("티커 심볼 또는 종목명을 입력하면 자동완성됩니다")
        self.input.setFixedHeight(22)

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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # 티커 검색 위젯
        self.ticker_widget = TickerSearchWidget()
        if ticker:
            self.ticker_widget.set_ticker(ticker)
        layout.addWidget(self.ticker_widget, 3)

        # 비율 입력
        self.ratio_spin = QDoubleSpinBox()
        self.ratio_spin.setRange(1, 100)
        self.ratio_spin.setSingleStep(5)
        self.ratio_spin.setSuffix("%")
        self.ratio_spin.setDecimals(0)
        self.ratio_spin.setValue(ratio)
        self.ratio_spin.setFixedWidth(65)
        self.ratio_spin.setFixedHeight(22)
        layout.addWidget(self.ratio_spin, 0)

        # 삭제 버튼
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(22, 22)
        self.remove_btn.setStyleSheet("font-size: 10px; padding: 0px; min-height: 18px;")
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
        # 컴팩트 레이아웃 - 스크롤 없이 한 페이지에 모두 표시
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(6, 4, 6, 4)

        # 타이틀
        title = QLabel("Backtest Settings")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 13px; padding: 0px; margin: 0px;")
        layout.addWidget(title)

        # --- A. 포트폴리오 ---
        asset_group = QGroupBox("A. Portfolio (종목 & 비율)")
        asset_group.setStyleSheet("QGroupBox { padding-top: 12px; margin-top: 6px; font-size: 11px; }")
        asset_layout = QVBoxLayout()
        asset_layout.setSpacing(2)
        asset_layout.setContentsMargins(4, 4, 4, 4)

        # 포트폴리오 행들이 들어갈 컨테이너
        self._portfolio_container = QVBoxLayout()
        self._portfolio_container.setSpacing(1)
        asset_layout.addLayout(self._portfolio_container)

        # 종목 추가 버튼 + 비율 합계 표시
        add_row_layout = QHBoxLayout()
        add_row_layout.setSpacing(4)
        self.add_ticker_btn = QPushButton("+ Add")
        self.add_ticker_btn.setToolTip("포트폴리오에 종목 추가")
        self.add_ticker_btn.setFixedHeight(22)
        self.add_ticker_btn.setStyleSheet("font-size: 11px; padding: 1px 6px; min-height: 20px;")
        self.add_ticker_btn.clicked.connect(self._add_empty_row)
        add_row_layout.addWidget(self.add_ticker_btn)

        self.equalize_btn = QPushButton("Equal")
        self.equalize_btn.setToolTip("모든 종목 비율을 균등하게 분배")
        self.equalize_btn.setFixedHeight(22)
        self.equalize_btn.setStyleSheet("font-size: 11px; padding: 1px 6px; min-height: 20px;")
        self.equalize_btn.clicked.connect(self._equalize_ratios)
        add_row_layout.addWidget(self.equalize_btn)

        self.ratio_total_label = QLabel("Total: 0%")
        self.ratio_total_label.setStyleSheet("font-size: 11px;")
        self.ratio_total_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        add_row_layout.addWidget(self.ratio_total_label)
        asset_layout.addLayout(add_row_layout)

        asset_group.setLayout(asset_layout)
        layout.addWidget(asset_group)

        # --- B. 기간/적립식 규칙 ---
        period_group = QGroupBox("B. Backtest Period & DCA Rule (기간 & 적립 규칙)")
        period_group.setStyleSheet("QGroupBox { padding-top: 12px; margin-top: 6px; font-size: 11px; }")
        period_layout = QVBoxLayout()
        period_layout.setSpacing(3)
        period_layout.setContentsMargins(4, 4, 4, 4)

        # 시작일 (별도 행 + quick 버튼)
        start_row = QHBoxLayout()
        start_row.setSpacing(4)
        start_row.addWidget(QLabel("Start Date (시작일):"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setFixedHeight(24)
        self.start_date.setMinimumWidth(110)
        start_row.addWidget(self.start_date, 1)
        period_layout.addLayout(start_row)

        # 시작일 퀵 버튼 행
        start_quick_row = QHBoxLayout()
        start_quick_row.setSpacing(2)
        quick_btn_style = "font-size: 10px; padding: 1px 4px; min-height: 18px; min-width: 28px;"
        self._start_quick_buttons = []
        self._start_quick_years = [1, 2, 3, 4, 5]  # 기본 연수 (사용자 변경 가능)
        for yr in self._start_quick_years:
            btn = QPushButton(f"{yr}Y")
            btn.setToolTip(f"{yr}년 전부터 시작")
            btn.setFixedHeight(20)
            btn.setStyleSheet(quick_btn_style)
            btn.clicked.connect(lambda checked, y=yr: self._set_start_years_ago(y))
            start_quick_row.addWidget(btn)
            self._start_quick_buttons.append(btn)
        start_quick_row.addStretch()
        period_layout.addLayout(start_quick_row)

        # 종료일 (별도 행 + Today 버튼)
        end_row = QHBoxLayout()
        end_row.setSpacing(4)
        end_row.addWidget(QLabel("End Date (종료일):"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setFixedHeight(24)
        self.end_date.setMinimumWidth(110)
        end_row.addWidget(self.end_date, 1)
        self.today_btn = QPushButton("Today")
        self.today_btn.setToolTip("종료일을 오늘 날짜로 설정")
        self.today_btn.setFixedHeight(22)
        self.today_btn.setStyleSheet("font-size: 10px; padding: 1px 6px; min-height: 18px;")
        self.today_btn.clicked.connect(self._set_end_today)
        end_row.addWidget(self.today_btn)
        period_layout.addLayout(end_row)

        # 매수 주기 행
        freq_row = QHBoxLayout()
        freq_row.setSpacing(4)
        freq_row.addWidget(QLabel("Buy Frequency (매수 주기):"))
        self.buy_frequency = QComboBox()
        self.buy_frequency.addItems(["Monthly (매월)", "Weekly (매주)"])
        self.buy_frequency.setFixedHeight(24)
        self.buy_frequency.currentIndexChanged.connect(self._on_frequency_changed)
        freq_row.addWidget(self.buy_frequency, 1)
        period_layout.addLayout(freq_row)

        # 매수일 + 휴장일 규칙
        day_row = QHBoxLayout()
        day_row.setSpacing(4)
        self.buy_day_label = QLabel("Buy Day (매수일):")
        day_row.addWidget(self.buy_day_label)
        self.buy_day = QSpinBox()
        self.buy_day.setRange(1, 28)
        self.buy_day.setFixedHeight(24)
        self.buy_day.setFixedWidth(55)
        self.buy_day.setToolTip("매월 매수할 날짜 (1~28)")
        day_row.addWidget(self.buy_day)

        self.buy_weekday_label = QLabel("Buy Day (매수 요일):")
        day_row.addWidget(self.buy_weekday_label)
        self.buy_weekday = QComboBox()
        self.buy_weekday.addItems(["Mon (월)", "Tue (화)", "Wed (수)", "Thu (목)", "Fri (금)"])
        self.buy_weekday.setFixedHeight(24)
        day_row.addWidget(self.buy_weekday)
        self.buy_weekday_label.setVisible(False)
        self.buy_weekday.setVisible(False)

        day_row.addWidget(QLabel("Holiday (휴장):"))
        self.holiday_rule = QComboBox()
        self.holiday_rule.addItems(["Before (직전 거래일)", "After (직후 거래일)"])
        self.holiday_rule.setFixedHeight(24)
        day_row.addWidget(self.holiday_rule)
        period_layout.addLayout(day_row)

        # 투자금
        amount_row = QHBoxLayout()
        amount_row.setSpacing(4)
        self.amount_label = QLabel("Investment (투자금):")
        amount_row.addWidget(self.amount_label)
        self.monthly_amount = KrwSpinBox()
        self.monthly_amount.setRange(10000, 100_000_000)
        self.monthly_amount.setSingleStep(10000)
        self.monthly_amount.setFixedHeight(24)
        amount_row.addWidget(self.monthly_amount, 1)
        period_layout.addLayout(amount_row)

        # 연간 증가율
        increase_row = QHBoxLayout()
        increase_row.setSpacing(4)
        increase_row.addWidget(QLabel("Annual Increase (연간 증가율):"))
        self.annual_increase = QDoubleSpinBox()
        self.annual_increase.setRange(0, 100)
        self.annual_increase.setSingleStep(0.5)
        self.annual_increase.setSuffix(" %/year")
        self.annual_increase.setDecimals(1)
        self.annual_increase.setFixedHeight(24)
        increase_row.addWidget(self.annual_increase, 1)
        period_layout.addLayout(increase_row)

        period_group.setLayout(period_layout)
        layout.addWidget(period_group)

        # --- C. 전략 선택 ---
        strategy_group = QGroupBox("C. Strategy (전략)")
        strategy_group.setStyleSheet("QGroupBox { padding-top: 12px; margin-top: 6px; font-size: 11px; }")
        strategy_layout = QVBoxLayout()
        strategy_layout.setSpacing(2)
        strategy_layout.setContentsMargins(4, 4, 4, 4)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Pure DCA (적립식 매수)"])
        self.strategy_combo.setFixedHeight(24)
        strategy_layout.addWidget(self.strategy_combo)

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # --- 버튼들 ---
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(3)

        # 주가 차트 로드 버튼
        self.chart_btn = QPushButton("Load Price Chart (주가 차트)")
        self.chart_btn.setToolTip("선택한 종목의 주가 차트를 로드합니다")
        self.chart_btn.setFixedHeight(26)
        self.chart_btn.setStyleSheet("font-size: 11px; min-height: 24px; padding: 2px 8px;")
        self.chart_btn.clicked.connect(self._on_chart_clicked)
        btn_layout.addWidget(self.chart_btn)

        # Run 백테스트 버튼
        self.run_btn = QPushButton("Run Backtest (백테스트 실행)")
        self.run_btn.setObjectName("runButton")
        self.run_btn.setToolTip("백테스트를 실행합니다")
        self.run_btn.setFixedHeight(32)
        self.run_btn.setStyleSheet("font-size: 12px; min-height: 30px; padding: 3px 10px;")
        self.run_btn.clicked.connect(self._on_run_clicked)
        btn_layout.addWidget(self.run_btn)

        # 결과 저장 버튼
        self.save_btn = QPushButton("Save Results CSV (결과 저장)")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setFixedHeight(26)
        self.save_btn.setStyleSheet("font-size: 11px; min-height: 24px; padding: 2px 8px;")
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        # 스페이서
        layout.addStretch()

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

        # 퀵 시작일 버튼 설정 로드
        quick_years = config.get("quick_start_years", None)
        if quick_years and isinstance(quick_years, list):
            self.set_quick_start_years(quick_years)

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

    def _set_start_years_ago(self, years: int):
        """시작일을 N년 전으로 설정"""
        target = date.today() - relativedelta(years=years)
        self.start_date.setDate(QDate(target.year, target.month, target.day))

    def _set_end_today(self):
        """종료일을 오늘 날짜로 설정"""
        today = date.today()
        self.end_date.setDate(QDate(today.year, today.month, today.day))

    def set_quick_start_years(self, years_list: list[int]):
        """퀵 시작일 버튼의 연수를 사용자 설정으로 변경"""
        self._start_quick_years = years_list
        for i, btn in enumerate(self._start_quick_buttons):
            if i < len(years_list):
                yr = years_list[i]
                btn.setText(f"{yr}Y")
                btn.setToolTip(f"{yr}년 전부터 시작")
                btn.setVisible(True)
                # 기존 연결 해제 후 새로 연결
                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass
                btn.clicked.connect(lambda checked, y=yr: self._set_start_years_ago(y))
            else:
                btn.setVisible(False)

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
            self.amount_label.setText("Investment (투자금/주):")
        else:
            self.amount_label.setText("Investment (투자금/월):")

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
