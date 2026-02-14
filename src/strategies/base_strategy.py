"""
전략 베이스 클래스
- 모든 커스텀 전략은 이 클래스를 상속해서 구현
- 향후 확장: 새 전략 파일을 strategies/ 폴더에 추가하기만 하면 됨
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class TradeSignal:
    """매수/매도 신호 데이터"""
    date: pd.Timestamp
    action: str          # 'BUY', 'SELL', 'HOLD'
    amount_krw: float    # 투입 금액 (KRW)
    reason: str = ""     # 신호 발생 이유 (로그용)


class BaseStrategy(ABC):
    """
    전략 추상 베이스 클래스.
    새 전략을 만들려면 이 클래스를 상속하고 generate_signals()를 구현.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    def generate_signals(
        self,
        price_data: pd.DataFrame,
        buy_day: int,
        monthly_amount: float,
        annual_increase_pct: float,
        start_date: str,
        end_date: str,
        holiday_rule: str,  # 'before' 또는 'after'
    ) -> list[TradeSignal]:
        """
        주어진 가격 데이터와 파라미터로 매수 신호 리스트를 생성.

        Parameters
        ----------
        price_data         : OHLCV DataFrame (index=Date)
        buy_day            : 매월 매수일 (1~28)
        monthly_amount     : 월 투자금 (KRW)
        annual_increase_pct: 매년 투자금 증가율 (%)
        start_date         : 백테스트 시작일
        end_date           : 백테스트 종료일
        holiday_rule       : 휴장일 처리 ('before'=직전 거래일, 'after'=직후 거래일)

        Returns
        -------
        list[TradeSignal]
        """
        pass

    def __repr__(self):
        return f"Strategy({self.name})"
