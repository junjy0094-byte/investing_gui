"""
백테스트 엔진
- 전략이 생성한 매수 신호를 기반으로 포트폴리오 시뮬레이션 수행
- 일별 자산 가치, 수익률, 수익금 등 계산
- 향후 확장: 매도 로직, 수수료/세금, 다중 종목 포트폴리오 등
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """백테스트 결과 데이터 컨테이너"""
    ticker: str
    strategy_name: str
    # 일별 상세 데이터
    daily_data: pd.DataFrame
    # 요약 통계
    total_invested: float       # 총 투자금
    final_value: float          # 최종 자산 가치
    total_return_pct: float     # 총 수익률 (%)
    total_profit: float         # 총 수익금
    total_shares: float         # 총 보유 주수
    num_buys: int               # 매수 횟수
    avg_buy_price: float        # 평균 매수 단가
    max_drawdown_pct: float     # 최대 낙폭 (%)


class BacktestEngine:
    """
    백테스트 실행 엔진.
    전략 신호를 받아 일별 포트폴리오 상태를 시뮬레이션한다.
    """

    def __init__(self):
        # 향후 확장: 수수료율, 슬리피지 등 설정 가능
        self.commission_rate = 0.0  # 수수료율 (현재 0%)

    def run(
        self,
        ticker: str,
        price_data: pd.DataFrame,
        strategy: BaseStrategy,
        buy_day: int,
        monthly_amount: float,
        annual_increase_pct: float,
        start_date: str,
        end_date: str,
        holiday_rule: str = "before",
    ) -> Optional[BacktestResult]:
        """
        백테스트 메인 실행 함수.

        Returns
        -------
        BacktestResult 또는 None (실패 시)
        """
        try:
            # 1) 전략으로부터 매수 신호 생성
            signals = strategy.generate_signals(
                price_data=price_data,
                buy_day=buy_day,
                monthly_amount=monthly_amount,
                annual_increase_pct=annual_increase_pct,
                start_date=start_date,
                end_date=end_date,
                holiday_rule=holiday_rule,
            )

            if not signals:
                logger.warning("매수 신호가 없습니다.")
                return None

            # 2) 신호를 날짜별 딕셔너리로 변환
            signal_map: dict[pd.Timestamp, TradeSignal] = {}
            for s in signals:
                signal_map[s.date] = s

            # 3) 일별 시뮬레이션
            daily_data = self._simulate(price_data, signal_map, start_date, end_date)

            if daily_data.empty:
                return None

            # 4) 요약 통계 계산
            result = self._compute_summary(daily_data, ticker, strategy.name)
            return result

        except Exception as e:
            logger.error(f"백테스트 실행 에러: {e}", exc_info=True)
            return None

    def _simulate(
        self,
        price_data: pd.DataFrame,
        signal_map: dict[pd.Timestamp, TradeSignal],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """일별 포트폴리오 시뮬레이션"""
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)

        # 기간 필터링
        mask = (price_data.index >= start_dt) & (price_data.index <= end_dt)
        df = price_data.loc[mask].copy()

        if df.empty:
            logger.error("선택 기간에 데이터가 없습니다.")
            return pd.DataFrame()

        # 시뮬레이션 컬럼 초기화
        n = len(df)
        shares_held = np.zeros(n)        # 누적 보유 주수
        total_invested = np.zeros(n)     # 누적 투자금
        buy_flag = np.zeros(n, dtype=int)  # 매수 여부 (0 or 1)
        buy_amount = np.zeros(n)         # 해당일 매수 금액
        shares_bought = np.zeros(n)      # 해당일 매수 주수

        cum_shares = 0.0
        cum_invested = 0.0

        for i, (date, row) in enumerate(df.iterrows()):
            close_price = row["Close"]

            if date in signal_map:
                sig = signal_map[date]
                if sig.action == "BUY" and close_price > 0:
                    # 매수 실행 (소수점 주수 허용 - 분할 매수 가정)
                    amt = sig.amount_usd
                    new_shares = amt / close_price
                    cum_shares += new_shares
                    cum_invested += amt
                    buy_flag[i] = 1
                    buy_amount[i] = amt
                    shares_bought[i] = new_shares

            shares_held[i] = cum_shares
            total_invested[i] = cum_invested

        # 결과 DataFrame 구성
        df["Shares_Held"] = shares_held
        df["Total_Invested"] = total_invested
        df["Buy_Flag"] = buy_flag
        df["Buy_Amount"] = buy_amount
        df["Shares_Bought"] = shares_bought
        df["Portfolio_Value"] = shares_held * df["Close"]
        df["Profit"] = df["Portfolio_Value"] - df["Total_Invested"]
        df["Return_Pct"] = np.where(
            df["Total_Invested"] > 0,
            (df["Profit"] / df["Total_Invested"]) * 100,
            0.0,
        )

        return df

    def _compute_summary(
        self, daily_data: pd.DataFrame, ticker: str, strategy_name: str
    ) -> BacktestResult:
        """요약 통계를 계산하여 BacktestResult 반환"""
        last = daily_data.iloc[-1]

        total_invested = last["Total_Invested"]
        final_value = last["Portfolio_Value"]
        total_profit = last["Profit"]
        total_return_pct = last["Return_Pct"]
        total_shares = last["Shares_Held"]
        num_buys = int(daily_data["Buy_Flag"].sum())
        avg_buy_price = total_invested / total_shares if total_shares > 0 else 0

        # 최대 낙폭 (MDD) 계산
        portfolio = daily_data["Portfolio_Value"]
        running_max = portfolio.expanding().max()
        drawdown = (portfolio - running_max) / running_max * 100
        # 투자금이 0인 초기 구간 제외
        drawdown = drawdown.replace([np.inf, -np.inf], 0).fillna(0)
        max_drawdown_pct = abs(drawdown.min())

        result = BacktestResult(
            ticker=ticker,
            strategy_name=strategy_name,
            daily_data=daily_data,
            total_invested=round(total_invested, 2),
            final_value=round(final_value, 2),
            total_return_pct=round(total_return_pct, 2),
            total_profit=round(total_profit, 2),
            total_shares=round(total_shares, 6),
            num_buys=num_buys,
            avg_buy_price=round(avg_buy_price, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
        )

        logger.info(
            f"[백테스트 완료] {ticker} | {strategy_name} | "
            f"투자: ${total_invested:,.0f} → 자산: ${final_value:,.0f} | "
            f"수익률: {total_return_pct:.1f}% | MDD: {max_drawdown_pct:.1f}%"
        )
        return result
