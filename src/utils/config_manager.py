"""
설정 관리 모듈
- JSON 파일로 사용자 설정 저장/불러오기
- 마지막 사용 설정을 자동 저장하여 다음 실행 시 복원
- 향후 확장: 프로필별 설정 저장, 설정 내보내기/가져오기
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = CONFIG_DIR / "config.json"

# 기본 설정값
DEFAULT_CONFIG = {
    "ticker": "QQQ",
    "portfolio": [{"ticker": "QQQ", "ratio": 50}, {"ticker": "VOO", "ratio": 50}],
    "start_date": "2020-01-01",
    "end_date": "2025-12-31",
    "buy_frequency": "monthly",  # 'monthly' 또는 'weekly'
    "buy_day": 20,
    "buy_weekday": 0,  # 0=월, 1=화, 2=수, 3=목, 4=금
    "monthly_amount": 500000,
    "annual_increase_pct": 0.0,
    "holiday_rule": "before",  # 'before' 또는 'after'
    "strategy": "Pure DCA",
    "theme": "dark",
    "window_width": 1600,
    "window_height": 900,
}


class ConfigManager:
    """JSON 기반 설정 관리자"""

    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self._config: dict[str, Any] = {}
        self.load()

    def load(self):
        """설정 파일 로드. 없으면 기본값 사용."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # 기본값에 저장된 값을 덮어씌움 (새 키가 추가돼도 안전)
                self._config = {**DEFAULT_CONFIG, **saved}
                logger.info(f"설정 로드 완료: {self.config_path}")
            except Exception as e:
                logger.warning(f"설정 로드 실패, 기본값 사용: {e}")
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self.save()  # 최초 실행 시 기본 설정 파일 생성

    def save(self):
        """현재 설정을 JSON 파일로 저장"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info("설정 저장 완료")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        self._config[key] = value

    def get_all(self) -> dict[str, Any]:
        return self._config.copy()

    def update(self, data: dict[str, Any]):
        """여러 설정을 한번에 업데이트"""
        self._config.update(data)
        self.save()
