"""
Pure DCA (Dollar-Cost Averaging) 전략
- 매월 지정일 또는 매주 지정 요일에 무조건 정액 매수
- 가장 기본적인 적립식 투자 전략
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from src.strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["월", "화", "수", "목", "금"]


class PureDCAStrategy(BaseStrategy):
    """정해진 주기에 무조건 정액 매수하는 순수 DCA 전략"""

    def __init__(self):
        super().__init__(
            name="Pure DCA",
            description="정해진 주기(월별/주별)에 무조건 정액 매수 (Dollar-Cost Averaging)",
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
        buy_frequency: str = "monthly",
        buy_weekday: int = 0,
    ) -> list[TradeSignal]:
        """
        Pure DCA 신호 생성:
        monthly: 매월 buy_day에 해당하는 거래일을 찾아서 BUY 신호 생성
        weekly: 매주 buy_weekday에 해당하는 거래일을 찾아서 BUY 신호 생성
        """
        if price_data.empty:
            logger.warning("가격 데이터가 비어있습니다.")
            return []

        if buy_frequency == "weekly":
            return self._generate_weekly_signals(
                price_data, buy_weekday, monthly_amount,
                annual_increase_pct, start_date, end_date, holiday_rule,
            )
        else:
            return self._generate_monthly_signals(
                price_data, buy_day, monthly_amount,
                annual_increase_pct, start_date, end_date, holiday_rule,
            )

    def _generate_monthly_signals(
        self,
        price_data: pd.DataFrame,
        buy_day: int,
        monthly_amount: float,
        annual_increase_pct: float,
        start_date: str,
        end_date: str,
        holiday_rule: str,
    ) -> list[TradeSignal]:
        """월별 매수 신호 생성"""
        signals: list[TradeSignal] = []
        trading_dates = price_data.index.sort_values()
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)
        base_year = start_dt.year

        current = start_dt.replace(day=1)
        while current <= end_dt:
            year = current.year
            month = current.month

            years_elapsed = year - base_year
            current_amount = monthly_amount * (
                (1 + annual_increase_pct / 100) ** years_elapsed
            )

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

            if month == 12:
                current = current.replace(year=year + 1, month=1)
            else:
                current = current.replace(month=month + 1)

        logger.info(f"[Pure DCA 월별] 총 {len(signals)}개 매수 신호 생성")
        return signals

    def _generate_weekly_signals(
        self,
        price_data: pd.DataFrame,
        buy_weekday: int,
        weekly_amount: float,
        annual_increase_pct: float,
        start_date: str,
        end_date: str,
        holiday_rule: str,
    ) -> list[TradeSignal]:
        """주별 매수 신호 생성"""
        signals: list[TradeSignal] = []
        trading_dates = price_data.index.sort_values()
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)
        base_year = start_dt.year

        # 기간 내 거래일 필터
        mask = (trading_dates >= start_dt) & (trading_dates <= end_dt)
        period_dates = trading_dates[mask]

        if period_dates.empty:
            return signals

        # ISO 캘린더 기준 (year, week) 별로 그룹핑
        seen_weeks: set[tuple[int, int]] = set()

        for date in period_dates:
            iso = date.isocalendar()
            week_key = (iso[0], iso[1])  # (iso_year, iso_week)

            if week_key in seen_weeks:
                continue

            year = date.year
            years_elapsed = year - base_year
            current_amount = weekly_amount * (
                (1 + annual_increase_pct / 100) ** years_elapsed
            )

            # 해당 주의 거래일 중 목표 요일 찾기
            week_dates = period_dates[
                (period_dates.isocalendar().year == iso[0])
                & (period_dates.isocalendar().week == iso[1])
            ]

            target_date = self._find_weekday_in_week(
                week_dates, buy_weekday, holiday_rule
            )

            if target_date is not None:
                seen_weeks.add(week_key)
                day_name = WEEKDAY_NAMES[buy_weekday]
                signals.append(
                    TradeSignal(
                        date=target_date,
                        action="BUY",
                        amount_krw=round(current_amount, 0),
                        reason=f"DCA 매수 (매주 {day_name}요일)",
                    )
                )

        logger.info(f"[Pure DCA 주별] 총 {len(signals)}개 매수 신호 생성")
        return signals

    @staticmethod
    def _find_weekday_in_week(
        week_dates: pd.DatetimeIndex,
        target_weekday: int,
        holiday_rule: str,
    ) -> Optional[pd.Timestamp]:
        """
        주어진 주의 거래일 중에서 목표 요일에 해당하는 거래일을 찾는다.
        target_weekday: 0=월, 1=화, 2=수, 3=목, 4=금
        """
        if week_dates.empty:
            return None

        # 해당 요일이 거래일이면 바로 반환
        exact = week_dates[week_dates.dayofweek == target_weekday]
        if not exact.empty:
            return exact[0]

        # 휴장일인 경우
        if holiday_rule == "before":
            # 목표 요일 이전의 가장 가까운 거래일
            before = week_dates[week_dates.dayofweek < target_weekday]
            if not before.empty:
                return before[-1]
            after = week_dates[week_dates.dayofweek > target_weekday]
            return after[0] if not after.empty else None
        else:  # 'after'
            after = week_dates[week_dates.dayofweek > target_weekday]
            if not after.empty:
                return after[0]
            before = week_dates[week_dates.dayofweek < target_weekday]
            return before[-1] if not before.empty else None

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

        last_day = calendar.monthrange(year, month)[1]
        target_day = min(day, last_day)

        try:
            target = pd.Timestamp(year=year, month=month, day=target_day)
        except ValueError:
            return None

        month_dates = trading_dates[
            (trading_dates.year == year) & (trading_dates.month == month)
        ]

        if month_dates.empty:
            return None

        if target in month_dates:
            return target

        if holiday_rule == "before":
            before = month_dates[month_dates <= target]
            if not before.empty:
                return before[-1]
            after = month_dates[month_dates > target]
            return after[0] if not after.empty else None
        else:  # 'after'
            after = month_dates[month_dates >= target]
            if not after.empty:
                return after[0]
            before = month_dates[month_dates < target]
            return before[-1] if not before.empty else None
