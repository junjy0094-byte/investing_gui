"""
백테스트 엔진
- 전략이 생성한 매수 신호를 기반으로 포트폴리오 시뮬레이션 수행
- KRW로 매수하고 당일 환율로 USD 환전 후 주식 구매
- 일별 자산 가치, 수익률, 수익금 등 계산 (KRW/USD 이중 표시)
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
    # 요약 통계 (USD 기준)
    total_invested_usd: float       # 총 투자금 (USD 환산 합계)
    final_value_usd: float          # 최종 자산 가치 (USD)
    total_return_pct: float         # 총 수익률 (%)
    total_profit_usd: float         # 총 수익금 (USD)
    total_shares: float             # 총 보유 주수
    num_buys: int                   # 매수 횟수
    avg_buy_price: float            # 평균 매수 단가 (USD)
    max_drawdown_pct: float         # 최대 낙폭 (%)
    # KRW 기준
    total_invested_krw: float       # 총 투자금 (KRW)
    final_value_krw: float          # 최종 자산 가치 (KRW, 현재 환율 적용)
    total_profit_krw: float         # 총 수익금 (KRW)
    current_exchange_rate: float    # 현재 환율 (최종 평가 시 사용)


class BacktestEngine:
    """
    백테스트 실행 엔진.
    전략 신호를 받아 일별 포트폴리오 상태를 시뮬레이션한다.
    KRW 투자금을 당일 환율로 USD 환전 후 주식 매수.
    """

    def __init__(self):
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
        exchange_rate_data: Optional[pd.DataFrame] = None,
        current_exchange_rate: float = 1350.0,
    ) -> Optional[BacktestResult]:
        """
        백테스트 메인 실행 함수.

        Parameters
        ----------
        exchange_rate_data : 일별 USD/KRW 환율 DataFrame (index=Date, Close 컬럼)
        current_exchange_rate : 현재 환율 (최종 자산 KRW 환산 시 사용)

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
            daily_data = self._simulate(
                price_data, signal_map, start_date, end_date,
                exchange_rate_data,
            )

            if daily_data.empty:
                return None

            # 4) 요약 통계 계산
            result = self._compute_summary(
                daily_data, ticker, strategy.name, current_exchange_rate
            )
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
        exchange_rate_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """일별 포트폴리오 시뮬레이션 (KRW→USD 환전 포함)"""
        start_dt = pd.Timestamp(start_date)
        end_dt = pd.Timestamp(end_date)

        # 기간 필터링
        mask = (price_data.index >= start_dt) & (price_data.index <= end_dt)
        df = price_data.loc[mask].copy()

        if df.empty:
            logger.error("선택 기간에 데이터가 없습니다.")
            return pd.DataFrame()

        # 환율 데이터를 price_data 인덱스에 맞춰 정렬 (forward-fill)
        if exchange_rate_data is not None and not exchange_rate_data.empty:
            fx = exchange_rate_data["Close"].reindex(df.index, method="ffill")
            # 앞쪽 NaN은 backfill
            fx = fx.bfill()
        else:
            # 환율 데이터가 없으면 기본값 사용
            fx = pd.Series(1350.0, index=df.index)
            logger.warning("환율 데이터 없음 - 기본 환율 1350.0 사용")

        # 시뮬레이션 컬럼 초기화
        n = len(df)
        shares_held = np.zeros(n)
        total_invested_krw = np.zeros(n)
        total_invested_usd = np.zeros(n)
        buy_flag = np.zeros(n, dtype=int)
        buy_amount_krw = np.zeros(n)
        buy_amount_usd = np.zeros(n)
        shares_bought = np.zeros(n)
        exchange_rates = fx.values.copy()

        cum_shares = 0.0
        cum_invested_krw = 0.0
        cum_invested_usd = 0.0

        for i, (date, row) in enumerate(df.iterrows()):
            close_price = row["Close"]
            rate = exchange_rates[i]

            if date in signal_map:
                sig = signal_map[date]
                if sig.action == "BUY" and close_price > 0 and rate > 0:
                    # KRW → USD 환전
                    krw_amt = sig.amount_krw
                    usd_amt = krw_amt / rate
                    # USD로 주식 매수 (소수점 주수 허용)
                    new_shares = usd_amt / close_price

                    cum_shares += new_shares
                    cum_invested_krw += krw_amt
                    cum_invested_usd += usd_amt

                    buy_flag[i] = 1
                    buy_amount_krw[i] = krw_amt
                    buy_amount_usd[i] = usd_amt
                    shares_bought[i] = new_shares

            shares_held[i] = cum_shares
            total_invested_krw[i] = cum_invested_krw
            total_invested_usd[i] = cum_invested_usd

        # 결과 DataFrame 구성
        df["Exchange_Rate"] = exchange_rates
        df["Shares_Held"] = shares_held
        df["Total_Invested_KRW"] = total_invested_krw
        df["Total_Invested_USD"] = total_invested_usd
        df["Buy_Flag"] = buy_flag
        df["Buy_Amount_KRW"] = buy_amount_krw
        df["Buy_Amount_USD"] = buy_amount_usd
        df["Shares_Bought"] = shares_bought
        df["Portfolio_Value_USD"] = shares_held * df["Close"]
        df["Portfolio_Value_KRW"] = df["Portfolio_Value_USD"] * df["Exchange_Rate"]
        df["Profit_USD"] = df["Portfolio_Value_USD"] - df["Total_Invested_USD"]
        df["Profit_KRW"] = df["Portfolio_Value_KRW"] - df["Total_Invested_KRW"]
        df["Return_Pct"] = np.where(
            df["Total_Invested_KRW"] > 0,
            (df["Profit_KRW"] / df["Total_Invested_KRW"]) * 100,
            0.0,
        )

        return df

    def _compute_summary(
        self,
        daily_data: pd.DataFrame,
        ticker: str,
        strategy_name: str,
        current_exchange_rate: float,
    ) -> BacktestResult:
        """요약 통계를 계산하여 BacktestResult 반환"""
        last = daily_data.iloc[-1]

        total_invested_usd = last["Total_Invested_USD"]
        total_invested_krw = last["Total_Invested_KRW"]
        total_shares = last["Shares_Held"]

        # USD 기준 최종 평가
        final_value_usd = last["Portfolio_Value_USD"]
        total_profit_usd = final_value_usd - total_invested_usd

        # KRW 기준 최종 평가 (현재 환율 적용)
        final_value_krw = final_value_usd * current_exchange_rate
        total_profit_krw = final_value_krw - total_invested_krw

        # 수익률은 KRW 기준 (실제 원화 수익)
        total_return_pct = (
            (total_profit_krw / total_invested_krw * 100)
            if total_invested_krw > 0
            else 0.0
        )

        num_buys = int(daily_data["Buy_Flag"].sum())
        avg_buy_price = total_invested_usd / total_shares if total_shares > 0 else 0

        # 최대 낙폭 (MDD) - KRW 기준
        portfolio = daily_data["Portfolio_Value_KRW"]
        running_max = portfolio.expanding().max()
        drawdown = (portfolio - running_max) / running_max * 100
        drawdown = drawdown.replace([np.inf, -np.inf], 0).fillna(0)
        max_drawdown_pct = abs(drawdown.min())

        result = BacktestResult(
            ticker=ticker,
            strategy_name=strategy_name,
            daily_data=daily_data,
            total_invested_usd=round(total_invested_usd, 2),
            final_value_usd=round(final_value_usd, 2),
            total_return_pct=round(total_return_pct, 2),
            total_profit_usd=round(total_profit_usd, 2),
            total_shares=round(total_shares, 6),
            num_buys=num_buys,
            avg_buy_price=round(avg_buy_price, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            total_invested_krw=round(total_invested_krw, 0),
            final_value_krw=round(final_value_krw, 0),
            total_profit_krw=round(total_profit_krw, 0),
            current_exchange_rate=round(current_exchange_rate, 2),
        )

        logger.info(
            f"[백테스트 완료] {ticker} | {strategy_name} | "
            f"투자: ₩{total_invested_krw:,.0f} → 자산: ₩{final_value_krw:,.0f} | "
            f"수익률: {total_return_pct:.1f}% | MDD: {max_drawdown_pct:.1f}% | "
            f"현재 환율: {current_exchange_rate:.0f}"
        )
        return result
