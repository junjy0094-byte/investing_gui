"""
백테스트 엔진
- 전략이 생성한 매수 신호를 기반으로 포트폴리오 시뮬레이션 수행
- KRW로 매수하고 당일 환율로 USD 환전 후 주식 구매
- 일별 자산 가치, 수익률, 수익금 등 계산 (KRW/USD 이중 표시)
- 다중 종목 포트폴리오 지원
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from src.strategies.base_strategy import BaseStrategy, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """단일 종목 백테스트 결과 데이터 컨테이너"""
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
    # 포트폴리오 내 비율
    allocation_pct: float = 100.0   # 포트폴리오 내 할당 비율
    # 배당 관련
    total_dividend_usd: float = 0.0      # 누적 배당금 (USD)
    total_dividend_krw: float = 0.0      # 누적 배당금 (KRW)
    dividend_reinvest_shares: float = 0.0  # 배당 재투자로 매수한 주수


@dataclass
class PortfolioBacktestResult:
    """다중 종목 포트폴리오 백테스트 결과"""
    portfolio: list[dict]                           # [{"ticker": "QQQ", "ratio": 50}, ...]
    strategy_name: str
    per_ticker_results: dict[str, BacktestResult]   # ticker -> 개별 결과
    # 통합 포트폴리오 일별 데이터
    daily_data: pd.DataFrame
    # 통합 요약 통계
    total_invested_krw: float
    total_invested_usd: float
    final_value_krw: float
    final_value_usd: float
    total_profit_krw: float
    total_profit_usd: float
    total_return_pct: float
    max_drawdown_pct: float
    num_buys: int
    current_exchange_rate: float
    # 배당 관련
    total_dividend_usd: float = 0.0
    total_dividend_krw: float = 0.0


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
        buy_frequency: str = "monthly",
        buy_weekday: int = 0,
        allocation_pct: float = 100.0,
        dividend_data: Optional[pd.DataFrame] = None,
    ) -> Optional[BacktestResult]:
        """
        단일 종목 백테스트 실행.

        Parameters
        ----------
        allocation_pct : 포트폴리오 내 이 종목의 할당 비율 (%)
        """
        try:
            # 실제 투자금 = 전체 금액 * 비율
            actual_amount = monthly_amount * (allocation_pct / 100.0)

            # 1) 전략으로부터 매수 신호 생성
            signals = strategy.generate_signals(
                price_data=price_data,
                buy_day=buy_day,
                monthly_amount=actual_amount,
                annual_increase_pct=annual_increase_pct,
                start_date=start_date,
                end_date=end_date,
                holiday_rule=holiday_rule,
                buy_frequency=buy_frequency,
                buy_weekday=buy_weekday,
            )

            if not signals:
                logger.warning(f"[{ticker}] 매수 신호가 없습니다.")
                return None

            # 2) 신호를 날짜별 딕셔너리로 변환
            signal_map: dict[pd.Timestamp, TradeSignal] = {}
            for s in signals:
                signal_map[s.date] = s

            # 3) 일별 시뮬레이션
            daily_data = self._simulate(
                price_data, signal_map, start_date, end_date,
                exchange_rate_data, dividend_data,
            )

            if daily_data.empty:
                return None

            # 4) 요약 통계 계산
            result = self._compute_summary(
                daily_data, ticker, strategy.name, current_exchange_rate,
                allocation_pct,
            )
            return result

        except Exception as e:
            logger.error(f"백테스트 실행 에러 ({ticker}): {e}", exc_info=True)
            return None

    def run_portfolio(
        self,
        portfolio: list[dict],
        price_data_map: dict[str, pd.DataFrame],
        strategy: BaseStrategy,
        buy_day: int,
        monthly_amount: float,
        annual_increase_pct: float,
        start_date: str,
        end_date: str,
        holiday_rule: str = "before",
        exchange_rate_data: Optional[pd.DataFrame] = None,
        current_exchange_rate: float = 1350.0,
        buy_frequency: str = "monthly",
        buy_weekday: int = 0,
        dividend_data_map: Optional[dict[str, pd.DataFrame]] = None,
    ) -> Optional[PortfolioBacktestResult]:
        """
        다중 종목 포트폴리오 백테스트 실행.

        Parameters
        ----------
        portfolio : [{"ticker": "QQQ", "ratio": 50}, {"ticker": "VOO", "ratio": 50}]
        price_data_map : {ticker: DataFrame} 각 종목의 주가 데이터
        """
        try:
            per_ticker_results: dict[str, BacktestResult] = {}

            for item in portfolio:
                ticker = item["ticker"]
                ratio = item["ratio"]
                price_data = price_data_map.get(ticker)

                if price_data is None or price_data.empty:
                    logger.error(f"[{ticker}] 주가 데이터가 없습니다.")
                    continue

                div_data = None
                if dividend_data_map:
                    div_data = dividend_data_map.get(ticker)

                result = self.run(
                    ticker=ticker,
                    price_data=price_data,
                    strategy=strategy,
                    buy_day=buy_day,
                    monthly_amount=monthly_amount,
                    annual_increase_pct=annual_increase_pct,
                    start_date=start_date,
                    end_date=end_date,
                    holiday_rule=holiday_rule,
                    exchange_rate_data=exchange_rate_data,
                    current_exchange_rate=current_exchange_rate,
                    buy_frequency=buy_frequency,
                    buy_weekday=buy_weekday,
                    allocation_pct=ratio,
                    dividend_data=div_data,
                )

                if result is not None:
                    per_ticker_results[ticker] = result

            if not per_ticker_results:
                logger.error("포트폴리오 백테스트: 유효한 결과가 없습니다.")
                return None

            # 통합 포트폴리오 데이터 계산
            portfolio_result = self._aggregate_portfolio(
                portfolio, per_ticker_results, strategy.name,
                current_exchange_rate,
            )
            return portfolio_result

        except Exception as e:
            logger.error(f"포트폴리오 백테스트 에러: {e}", exc_info=True)
            return None

    def _simulate(
        self,
        price_data: pd.DataFrame,
        signal_map: dict[pd.Timestamp, TradeSignal],
        start_date: str,
        end_date: str,
        exchange_rate_data: Optional[pd.DataFrame] = None,
        dividend_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """일별 포트폴리오 시뮬레이션 (KRW→USD 환전 + 배당 재투자 포함)"""
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

        # 배당 데이터를 날짜별 딕셔너리로 변환
        div_map: dict[pd.Timestamp, float] = {}
        if dividend_data is not None and not dividend_data.empty:
            for div_date, div_row in dividend_data.iterrows():
                div_map[div_date] = div_row["Dividend"]

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
        # 배당 관련
        dividend_per_day_usd = np.zeros(n)
        dividend_reinvest_shares_arr = np.zeros(n)
        cum_dividend_usd = np.zeros(n)
        cum_dividend_krw = np.zeros(n)

        cum_shares = 0.0
        cum_invested_krw = 0.0
        cum_invested_usd = 0.0
        cum_div_usd = 0.0
        cum_div_krw = 0.0

        for i, (date, row) in enumerate(df.iterrows()):
            close_price = row["Close"]
            rate = exchange_rates[i]

            # DCA 매수 처리
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

            # 배당 재투자 처리
            if date in div_map and cum_shares > 0 and close_price > 0:
                div_per_share = div_map[date]
                div_total_usd = div_per_share * cum_shares
                div_total_krw = div_total_usd * rate

                # 배당금으로 주식 재매수 (DRIP)
                reinvest_shares = div_total_usd / close_price
                cum_shares += reinvest_shares

                cum_div_usd += div_total_usd
                cum_div_krw += div_total_krw

                dividend_per_day_usd[i] = div_total_usd
                dividend_reinvest_shares_arr[i] = reinvest_shares

            shares_held[i] = cum_shares
            total_invested_krw[i] = cum_invested_krw
            total_invested_usd[i] = cum_invested_usd
            cum_dividend_usd[i] = cum_div_usd
            cum_dividend_krw[i] = cum_div_krw

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
        # 배당 관련 컬럼
        df["Dividend_USD"] = dividend_per_day_usd
        df["Dividend_Reinvest_Shares"] = dividend_reinvest_shares_arr
        df["Cum_Dividend_USD"] = cum_dividend_usd
        df["Cum_Dividend_KRW"] = cum_dividend_krw

        return df

    def _compute_summary(
        self,
        daily_data: pd.DataFrame,
        ticker: str,
        strategy_name: str,
        current_exchange_rate: float,
        allocation_pct: float = 100.0,
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

        # 배당 관련
        total_dividend_usd = float(last.get("Cum_Dividend_USD", 0))
        total_dividend_krw = float(last.get("Cum_Dividend_KRW", 0))
        dividend_reinvest_shares = float(daily_data["Dividend_Reinvest_Shares"].sum()) if "Dividend_Reinvest_Shares" in daily_data.columns else 0.0

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
            allocation_pct=allocation_pct,
            total_dividend_usd=round(total_dividend_usd, 2),
            total_dividend_krw=round(total_dividend_krw, 0),
            dividend_reinvest_shares=round(dividend_reinvest_shares, 6),
        )

        div_info = ""
        if total_dividend_usd > 0:
            div_info = f" | 배당: ${total_dividend_usd:,.2f} (재투자 {dividend_reinvest_shares:.4f}주)"

        logger.info(
            f"[백테스트 완료] {ticker} ({allocation_pct:.0f}%) | {strategy_name} | "
            f"투자: ₩{total_invested_krw:,.0f} → 자산: ₩{final_value_krw:,.0f} | "
            f"수익률: {total_return_pct:.1f}% | MDD: {max_drawdown_pct:.1f}%{div_info}"
        )
        return result

    def _aggregate_portfolio(
        self,
        portfolio: list[dict],
        per_ticker_results: dict[str, BacktestResult],
        strategy_name: str,
        current_exchange_rate: float,
    ) -> PortfolioBacktestResult:
        """개별 종목 결과를 포트폴리오 수준으로 통합"""
        # 모든 종목의 daily_data를 공통 날짜 인덱스로 정렬
        all_dates = None
        for ticker, result in per_ticker_results.items():
            dates = result.daily_data.index
            if all_dates is None:
                all_dates = dates
            else:
                all_dates = all_dates.union(dates)

        all_dates = all_dates.sort_values()

        # 통합 DataFrame 생성
        combined = pd.DataFrame(index=all_dates)
        combined.index.name = "Date"

        # 각 종목의 값을 통합 인덱스에 맞춰 정렬
        total_portfolio_value_krw = pd.Series(0.0, index=all_dates)
        total_portfolio_value_usd = pd.Series(0.0, index=all_dates)
        total_invested_krw = pd.Series(0.0, index=all_dates)
        total_invested_usd = pd.Series(0.0, index=all_dates)
        total_buy_flag = pd.Series(0, index=all_dates, dtype=int)
        total_cum_div_usd = pd.Series(0.0, index=all_dates)
        total_cum_div_krw = pd.Series(0.0, index=all_dates)

        for ticker, result in per_ticker_results.items():
            df = result.daily_data
            # reindex to align with all_dates, forward-fill
            pv_krw = df["Portfolio_Value_KRW"].reindex(all_dates, method="ffill").fillna(0)
            pv_usd = df["Portfolio_Value_USD"].reindex(all_dates, method="ffill").fillna(0)
            inv_krw = df["Total_Invested_KRW"].reindex(all_dates, method="ffill").fillna(0)
            inv_usd = df["Total_Invested_USD"].reindex(all_dates, method="ffill").fillna(0)
            buy_f = df["Buy_Flag"].reindex(all_dates).fillna(0).astype(int)

            # 배당 데이터 통합
            if "Cum_Dividend_USD" in df.columns:
                cd_usd = df["Cum_Dividend_USD"].reindex(all_dates, method="ffill").fillna(0)
                cd_krw = df["Cum_Dividend_KRW"].reindex(all_dates, method="ffill").fillna(0)
                total_cum_div_usd += cd_usd
                total_cum_div_krw += cd_krw

            # 각 종목의 Close 가격 저장 (가격 차트용)
            combined[f"Close_{ticker}"] = df["Close"].reindex(all_dates, method="ffill")

            total_portfolio_value_krw += pv_krw
            total_portfolio_value_usd += pv_usd
            total_invested_krw += inv_krw
            total_invested_usd += inv_usd
            total_buy_flag = total_buy_flag | buy_f

        combined["Portfolio_Value_KRW"] = total_portfolio_value_krw
        combined["Portfolio_Value_USD"] = total_portfolio_value_usd
        combined["Total_Invested_KRW"] = total_invested_krw
        combined["Total_Invested_USD"] = total_invested_usd
        combined["Profit_KRW"] = total_portfolio_value_krw - total_invested_krw
        combined["Profit_USD"] = total_portfolio_value_usd - total_invested_usd
        combined["Return_Pct"] = np.where(
            total_invested_krw > 0,
            (combined["Profit_KRW"] / total_invested_krw) * 100,
            0.0,
        )
        combined["Buy_Flag"] = total_buy_flag
        combined["Cum_Dividend_USD"] = total_cum_div_usd
        combined["Cum_Dividend_KRW"] = total_cum_div_krw

        # 환율 (첫 번째 종목에서 가져오기)
        first_result = next(iter(per_ticker_results.values()))
        fx = first_result.daily_data["Exchange_Rate"].reindex(all_dates, method="ffill")
        combined["Exchange_Rate"] = fx

        # 요약 통계
        last_inv_krw = float(total_invested_krw.iloc[-1])
        last_inv_usd = float(total_invested_usd.iloc[-1])
        last_pv_usd = float(total_portfolio_value_usd.iloc[-1])

        # 현재 환율로 최종 KRW 재평가
        final_value_krw = last_pv_usd * current_exchange_rate
        final_value_usd = last_pv_usd
        total_profit_krw = final_value_krw - last_inv_krw
        total_profit_usd = final_value_usd - last_inv_usd
        total_return_pct = (
            (total_profit_krw / last_inv_krw * 100) if last_inv_krw > 0 else 0.0
        )

        # MDD (KRW 기준)
        pv_for_mdd = total_portfolio_value_krw.copy()
        # 현재 환율로 보정 (마지막 구간)
        running_max = pv_for_mdd.expanding().max()
        drawdown = (pv_for_mdd - running_max) / running_max * 100
        drawdown = drawdown.replace([np.inf, -np.inf], 0).fillna(0)
        max_drawdown_pct = abs(drawdown.min())

        num_buys = sum(r.num_buys for r in per_ticker_results.values())
        portfolio_div_usd = sum(r.total_dividend_usd for r in per_ticker_results.values())
        portfolio_div_krw = sum(r.total_dividend_krw for r in per_ticker_results.values())

        tickers_str = " + ".join(
            f"{item['ticker']}({item['ratio']}%)" for item in portfolio
            if item['ticker'] in per_ticker_results
        )
        logger.info(
            f"[포트폴리오 백테스트 완료] {tickers_str} | "
            f"투자: ₩{last_inv_krw:,.0f} → 자산: ₩{final_value_krw:,.0f} | "
            f"수익률: {total_return_pct:.1f}% | MDD: {max_drawdown_pct:.1f}%"
        )

        return PortfolioBacktestResult(
            portfolio=portfolio,
            strategy_name=strategy_name,
            per_ticker_results=per_ticker_results,
            daily_data=combined,
            total_invested_krw=round(last_inv_krw, 0),
            total_invested_usd=round(last_inv_usd, 2),
            final_value_krw=round(final_value_krw, 0),
            final_value_usd=round(final_value_usd, 2),
            total_profit_krw=round(total_profit_krw, 0),
            total_profit_usd=round(total_profit_usd, 2),
            total_return_pct=round(total_return_pct, 2),
            max_drawdown_pct=round(max_drawdown_pct, 2),
            num_buys=num_buys,
            current_exchange_rate=round(current_exchange_rate, 2),
            total_dividend_usd=round(portfolio_div_usd, 2),
            total_dividend_krw=round(portfolio_div_krw, 0),
        )
