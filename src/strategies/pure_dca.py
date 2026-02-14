"""
Pure DCA (Dollar-Cost Averaging) 전략
- 매월 지정일에 무조건 정액 매수
- 가장 기본적인 적립식 투자 전략
- 향후 확장: 이 파일을 복사해서 조건부 DCA, 밸류 DCA 등으로 변형 가능
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from src.strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)


class PureDCAStrategy(BaseStrategy):
    """매월 정해진 날짜에 무조건 정액 매수하는 순수 DCA 전략"""

    def __init__(self):
        super().__init__(
            name="Pure DCA",
            description="매월 지정일에 무조건 정액 매수 (Dollar-Cost Averaging)",
        )

    def generate_signals(
        self,
        price_data: pd.DataFrame,
        buy_day: int,
        monthly_amount: float,
        annual_increase_pct: float,
        start_date: str,
        end_date: str,
        holiday_rule: str = "before",
    ) -> list[TradeSignal]:
        """
        Pure DCA 신호 생성:
        매월 buy_day에 해당하는 거래일을 찾아서 BUY 신호를 생성.
        """
        signals: list[TradeSignal] = []

        if price_data.empty:
            logger.warning("가격 데이터가 비어있습니다.")
            return signals

        # 거래일 목록 (인덱스)
        trading_dates = price_data.index.sort_values()
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)

        # 시작 연도 (투자금 증가율 계산 기준)
        base_year = start_dt.year

        # 시작월 ~ 종료월까지 월별 순회
        current = start_dt.replace(day=1)
        while current <= end_dt:
            year = current.year
            month = current.month

            # 매년 투자금 증가 적용
            years_elapsed = year - base_year
            current_amount = monthly_amount * (
                (1 + annual_increase_pct / 100) ** years_elapsed
            )

            # 해당 월의 매수 목표일 찾기
            target_date = self._find_buy_date(
                trading_dates, year, month, buy_day, holiday_rule
            )

            if target_date is not None and start_dt <= target_date <= end_dt:
                signals.append(
                    TradeSignal(
                        date=target_date,
                        action="BUY",
                        amount_krw=round(current_amount, 0),
                        reason=f"DCA 매수 (매월 {buy_day}일)",
                    )
                )

            # 다음 달로 이동
            if month == 12:
                current = current.replace(year=year + 1, month=1)
            else:
                current = current.replace(month=month + 1)

        logger.info(f"[Pure DCA] 총 {len(signals)}개 매수 신호 생성")
        return signals

    @staticmethod
    def _find_buy_date(
        trading_dates: pd.DatetimeIndex,
        year: int,
        month: int,
        day: int,
        holiday_rule: str,
    ) -> Optional[pd.Timestamp]:
        """
        특정 년/월에서 매수일에 해당하는 실제 거래일을 찾는다.
        holiday_rule: 'before' → 직전 거래일, 'after' → 직후 거래일
        """
        import calendar

        # 해당 월의 마지막 날 확인 (day가 월말을 넘으면 보정)
        last_day = calendar.monthrange(year, month)[1]
        target_day = min(day, last_day)

        try:
            target = pd.Timestamp(year=year, month=month, day=target_day)
        except ValueError:
            return None

        # 해당 월의 거래일만 필터
        month_dates = trading_dates[
            (trading_dates.year == year) & (trading_dates.month == month)
        ]

        if month_dates.empty:
            return None

        if target in month_dates:
            return target

        if holiday_rule == "before":
            # 목표일 이전의 가장 가까운 거래일
            before = month_dates[month_dates <= target]
            if not before.empty:
                return before[-1]
            # 이전 거래일이 없으면 직후 거래일
            after = month_dates[month_dates > target]
            return after[0] if not after.empty else None
        else:  # 'after'
            # 목표일 이후의 가장 가까운 거래일
            after = month_dates[month_dates >= target]
            if not after.empty:
                return after[0]
            before = month_dates[month_dates < target]
            return before[-1] if not before.empty else None
