"""
데이터 매니저 모듈
- yfinance를 통한 미국 주식 데이터 다운로드
- 로컬 parquet 캐시로 재요청 최소화
- 향후 확장: 다른 데이터 소스(Alpha Vantage, polygon.io 등) 추가 가능
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# 캐시 디렉토리 (프로젝트 루트/cache)
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


class DataManager:
    """주식 데이터 다운로드 및 캐시 관리 클래스"""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        # 메모리 캐시: 동일 세션 내 재사용
        self._memory_cache: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def get_price_data(
        self,
        ticker: str,
        start: str,
        end: str,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """
        주가 데이터를 가져온다. 캐시 우선, 없으면 다운로드.

        Parameters
        ----------
        ticker : str  -  종목 티커 (예: 'QQQ')
        start  : str  -  시작일 'YYYY-MM-DD'
        end    : str  -  종료일 'YYYY-MM-DD'
        force_download : bool  -  True이면 캐시 무시하고 재다운로드

        Returns
        -------
        pd.DataFrame  -  OHLCV 데이터 (index=Date)
        """
        ticker = ticker.upper().strip()
        cache_key = f"{ticker}_{start}_{end}"

        # 1) 메모리 캐시 확인
        if not force_download and cache_key in self._memory_cache:
            logger.info(f"[메모리캐시] {cache_key} 히트")
            return self._memory_cache[cache_key].copy()

        # 2) 파일 캐시 확인
        cache_path = self._get_cache_path(ticker, start, end)
        if not force_download and cache_path.exists():
            try:
                df = pd.read_parquet(cache_path)
                if not df.empty:
                    logger.info(f"[파일캐시] {cache_path.name} 로드 완료 ({len(df)}행)")
                    self._memory_cache[cache_key] = df
                    return df.copy()
            except Exception as e:
                logger.warning(f"캐시 파일 읽기 실패: {e}")

        # 3) yfinance 다운로드
        df = self._download(ticker, start, end)
        if df is not None and not df.empty:
            self._save_cache(df, cache_path)
            self._memory_cache[cache_key] = df
            return df.copy()

        logger.error(f"데이터 다운로드 실패: {ticker}")
        return pd.DataFrame()

    def clear_cache(self, ticker: Optional[str] = None):
        """캐시 삭제. ticker가 None이면 전체 삭제."""
        if ticker:
            for f in self.cache_dir.glob(f"{ticker.upper()}_*.parquet"):
                f.unlink()
                logger.info(f"캐시 삭제: {f.name}")
        else:
            for f in self.cache_dir.glob("*.parquet"):
                f.unlink()
            logger.info("전체 캐시 삭제 완료")
        self._memory_cache.clear()

    # ------------------------------------------------------------------
    # 내부 메서드
    # ------------------------------------------------------------------
    def _get_cache_path(self, ticker: str, start: str, end: str) -> Path:
        filename = f"{ticker}_{start}_{end}.parquet"
        return self.cache_dir / filename

    def _download(self, ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
        """yfinance를 통해 OHLCV 데이터 다운로드"""
        try:
            logger.info(f"[다운로드] {ticker} ({start} ~ {end}) ...")
            data = yf.download(
                ticker,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
            )
            if data.empty:
                logger.warning(f"yfinance 결과 비어있음: {ticker}")
                return None

            # MultiIndex columns 처리 (yfinance가 단일 티커에도 MultiIndex 줄 수 있음)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            # 인덱스 정리
            data.index = pd.to_datetime(data.index)
            data.index.name = "Date"
            data = data.sort_index()

            logger.info(f"[다운로드 완료] {ticker}: {len(data)}행")
            return data

        except Exception as e:
            logger.error(f"yfinance 다운로드 에러 ({ticker}): {e}")
            return None

    def _save_cache(self, df: pd.DataFrame, path: Path):
        """parquet 형식으로 캐시 저장"""
        try:
            df.to_parquet(path, engine="pyarrow")
            logger.info(f"[캐시 저장] {path.name}")
        except Exception as e:
            logger.warning(f"캐시 저장 실패: {e}")
