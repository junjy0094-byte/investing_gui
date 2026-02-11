#!/usr/bin/env python3
"""
Stock DCA Backtester - 적립식 투자 백테스팅 GUI
==================================================
매월 월급날 무지성 적립식 미국 주식(ETF/개별종목) 투자를 위한
백테스트 GUI 프로그램.

실행 방법:
    python run.py

필요 패키지:
    pip install -r requirements.txt
"""

import sys
import os
import logging

# 프로젝트 루트를 PYTHONPATH에 추가
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.gui.main_window import MainWindow


def main():
    # 기본 로깅 설정 (콘솔)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # High DPI 지원
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)

    # 기본 폰트 설정 (시스템에 존재하는 폰트를 탐색하여 적용)
    from PyQt6.QtGui import QFontDatabase
    available = set(QFontDatabase.families())
    font = QFont()
    for family in ["Segoe UI", "Malgun Gothic", "Noto Sans", "DejaVu Sans",
                    "Liberation Sans", "Sans Serif"]:
        if family in available:
            font.setFamily(family)
            break
    font.setPointSize(10)
    app.setFont(font)

    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
