"""
티커 데이터베이스
- 인기 미국 주식/ETF 목록 (티커 + 종목명)
- 검색/자동완성용
"""

# (티커, 종목명) 리스트 - 인기순 정렬
TICKER_DATABASE: list[tuple[str, str]] = [
    # ── 주요 지수 ETF ──
    ("SPY", "SPDR S&P 500 ETF"),
    ("VOO", "Vanguard S&P 500 ETF"),
    ("IVV", "iShares Core S&P 500 ETF"),
    ("QQQ", "Invesco QQQ (Nasdaq-100)"),
    ("QQQM", "Invesco Nasdaq-100 ETF"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF"),
    ("IWM", "iShares Russell 2000 ETF"),
    ("VTI", "Vanguard Total Stock Market ETF"),
    ("VT", "Vanguard Total World Stock ETF"),

    # ── 섹터/테마 ETF ──
    ("XLK", "Technology Select Sector SPDR"),
    ("XLF", "Financial Select Sector SPDR"),
    ("XLE", "Energy Select Sector SPDR"),
    ("XLV", "Health Care Select Sector SPDR"),
    ("XLI", "Industrial Select Sector SPDR"),
    ("XLP", "Consumer Staples Select Sector SPDR"),
    ("XLY", "Consumer Discretionary Select Sector SPDR"),
    ("XLU", "Utilities Select Sector SPDR"),
    ("XLRE", "Real Estate Select Sector SPDR"),
    ("XLB", "Materials Select Sector SPDR"),
    ("XLC", "Communication Services Select Sector SPDR"),
    ("VGT", "Vanguard Information Technology ETF"),
    ("ARKK", "ARK Innovation ETF"),
    ("ARKG", "ARK Genomic Revolution ETF"),
    ("SOXX", "iShares Semiconductor ETF"),
    ("SMH", "VanEck Semiconductor ETF"),
    ("TAN", "Invesco Solar ETF"),
    ("LIT", "Global X Lithium & Battery Tech ETF"),
    ("BOTZ", "Global X Robotics & AI ETF"),
    ("HACK", "ETFMG Prime Cyber Security ETF"),
    ("KWEB", "KraneShares CSI China Internet ETF"),

    # ── 채권 ETF ──
    ("TLT", "iShares 20+ Year Treasury Bond ETF"),
    ("IEF", "iShares 7-10 Year Treasury Bond ETF"),
    ("SHY", "iShares 1-3 Year Treasury Bond ETF"),
    ("BND", "Vanguard Total Bond Market ETF"),
    ("AGG", "iShares Core US Aggregate Bond ETF"),
    ("LQD", "iShares iBoxx $ Investment Grade Corporate Bond ETF"),
    ("HYG", "iShares iBoxx $ High Yield Corporate Bond ETF"),
    ("TIP", "iShares TIPS Bond ETF"),
    ("GOVT", "iShares US Treasury Bond ETF"),
    ("EDV", "Vanguard Extended Duration Treasury ETF"),

    # ── 배당 ETF ──
    ("VYM", "Vanguard High Dividend Yield ETF"),
    ("SCHD", "Schwab US Dividend Equity ETF"),
    ("DVY", "iShares Select Dividend ETF"),
    ("HDV", "iShares Core High Dividend ETF"),
    ("JEPI", "JPMorgan Equity Premium Income ETF"),
    ("JEPQ", "JPMorgan Nasdaq Equity Premium Income ETF"),
    ("DIVO", "Amplify CWP Enhanced Dividend Income ETF"),

    # ── 원자재/실물자산 ETF ──
    ("GLD", "SPDR Gold Shares"),
    ("IAU", "iShares Gold Trust"),
    ("SLV", "iShares Silver Trust"),
    ("USO", "United States Oil Fund"),
    ("DBC", "Invesco DB Commodity Index"),
    ("VNQ", "Vanguard Real Estate ETF"),
    ("PDBC", "Invesco Optimum Yield Diversified Commodity Strategy"),

    # ── 레버리지/인버스 ETF ──
    ("TQQQ", "ProShares UltraPro QQQ (3x)"),
    ("SQQQ", "ProShares UltraPro Short QQQ (-3x)"),
    ("SPXL", "Direxion Daily S&P 500 Bull 3x"),
    ("UPRO", "ProShares UltraPro S&P 500 (3x)"),
    ("SSO", "ProShares Ultra S&P 500 (2x)"),
    ("QLD", "ProShares Ultra QQQ (2x)"),
    ("TMF", "Direxion Daily 20+ Year Treasury Bull 3x"),
    ("TBF", "ProShares Short 20+ Year Treasury"),
    ("SOXL", "Direxion Daily Semiconductor Bull 3x"),
    ("SOXS", "Direxion Daily Semiconductor Bear 3x"),

    # ── 국제 ETF ──
    ("EFA", "iShares MSCI EAFE ETF"),
    ("EEM", "iShares MSCI Emerging Markets ETF"),
    ("VWO", "Vanguard FTSE Emerging Markets ETF"),
    ("VXUS", "Vanguard Total International Stock ETF"),
    ("VEA", "Vanguard FTSE Developed Markets ETF"),
    ("EWJ", "iShares MSCI Japan ETF"),
    ("EWY", "iShares MSCI South Korea ETF"),
    ("FXI", "iShares China Large-Cap ETF"),
    ("INDA", "iShares MSCI India ETF"),
    ("EWZ", "iShares MSCI Brazil ETF"),

    # ── 미국 대형 기술주 (Magnificent 7 등) ──
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corp."),
    ("GOOGL", "Alphabet Inc. (Class A)"),
    ("GOOG", "Alphabet Inc. (Class C)"),
    ("AMZN", "Amazon.com Inc."),
    ("NVDA", "NVIDIA Corp."),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),

    # ── 반도체 ──
    ("AMD", "Advanced Micro Devices Inc."),
    ("INTC", "Intel Corp."),
    ("AVGO", "Broadcom Inc."),
    ("QCOM", "Qualcomm Inc."),
    ("MU", "Micron Technology Inc."),
    ("AMAT", "Applied Materials Inc."),
    ("LRCX", "Lam Research Corp."),
    ("KLAC", "KLA Corp."),
    ("MRVL", "Marvell Technology Inc."),
    ("ARM", "Arm Holdings plc"),
    ("TSM", "Taiwan Semiconductor (ADR)"),
    ("ASML", "ASML Holding NV (ADR)"),

    # ── 소프트웨어/클라우드 ──
    ("CRM", "Salesforce Inc."),
    ("ADBE", "Adobe Inc."),
    ("ORCL", "Oracle Corp."),
    ("NOW", "ServiceNow Inc."),
    ("SNOW", "Snowflake Inc."),
    ("PLTR", "Palantir Technologies Inc."),
    ("NET", "Cloudflare Inc."),
    ("DDOG", "Datadog Inc."),
    ("CRWD", "CrowdStrike Holdings Inc."),
    ("PANW", "Palo Alto Networks Inc."),
    ("ZS", "Zscaler Inc."),
    ("MDB", "MongoDB Inc."),
    ("SHOP", "Shopify Inc."),
    ("SQ", "Block Inc. (Square)"),
    ("COIN", "Coinbase Global Inc."),

    # ── 금융 ──
    ("JPM", "JPMorgan Chase & Co."),
    ("BAC", "Bank of America Corp."),
    ("WFC", "Wells Fargo & Co."),
    ("GS", "Goldman Sachs Group Inc."),
    ("MS", "Morgan Stanley"),
    ("C", "Citigroup Inc."),
    ("BRK-B", "Berkshire Hathaway Inc. (Class B)"),
    ("V", "Visa Inc."),
    ("MA", "Mastercard Inc."),
    ("AXP", "American Express Co."),
    ("BLK", "BlackRock Inc."),
    ("SCHW", "Charles Schwab Corp."),

    # ── 헬스케어 ──
    ("JNJ", "Johnson & Johnson"),
    ("UNH", "UnitedHealth Group Inc."),
    ("PFE", "Pfizer Inc."),
    ("MRK", "Merck & Co. Inc."),
    ("ABBV", "AbbVie Inc."),
    ("LLY", "Eli Lilly & Co."),
    ("TMO", "Thermo Fisher Scientific Inc."),
    ("ABT", "Abbott Laboratories"),
    ("BMY", "Bristol-Myers Squibb Co."),
    ("AMGN", "Amgen Inc."),
    ("GILD", "Gilead Sciences Inc."),
    ("ISRG", "Intuitive Surgical Inc."),
    ("MRNA", "Moderna Inc."),
    ("NVO", "Novo Nordisk A/S (ADR)"),

    # ── 소비재/유통 ──
    ("WMT", "Walmart Inc."),
    ("COST", "Costco Wholesale Corp."),
    ("HD", "Home Depot Inc."),
    ("NKE", "Nike Inc."),
    ("SBUX", "Starbucks Corp."),
    ("MCD", "McDonald's Corp."),
    ("KO", "Coca-Cola Co."),
    ("PEP", "PepsiCo Inc."),
    ("PG", "Procter & Gamble Co."),
    ("TGT", "Target Corp."),
    ("LOW", "Lowe's Companies Inc."),

    # ── 산업재/방산 ──
    ("BA", "Boeing Co."),
    ("CAT", "Caterpillar Inc."),
    ("GE", "GE Aerospace"),
    ("RTX", "RTX Corp. (Raytheon)"),
    ("LMT", "Lockheed Martin Corp."),
    ("NOC", "Northrop Grumman Corp."),
    ("HON", "Honeywell International Inc."),
    ("UPS", "United Parcel Service Inc."),
    ("DE", "Deere & Co."),
    ("UNP", "Union Pacific Corp."),

    # ── 에너지 ──
    ("XOM", "Exxon Mobil Corp."),
    ("CVX", "Chevron Corp."),
    ("COP", "ConocoPhillips"),
    ("SLB", "Schlumberger NV"),
    ("EOG", "EOG Resources Inc."),
    ("OXY", "Occidental Petroleum Corp."),
    ("PSX", "Phillips 66"),

    # ── 통신/미디어 ──
    ("T", "AT&T Inc."),
    ("VZ", "Verizon Communications Inc."),
    ("CMCSA", "Comcast Corp."),
    ("DIS", "Walt Disney Co."),
    ("NFLX", "Netflix Inc."),
    ("TMUS", "T-Mobile US Inc."),

    # ── 유틸리티/리얼티 ──
    ("NEE", "NextEra Energy Inc."),
    ("DUK", "Duke Energy Corp."),
    ("SO", "Southern Company"),
    ("D", "Dominion Energy Inc."),
    ("AMT", "American Tower Corp. (REIT)"),
    ("PLD", "Prologis Inc. (REIT)"),
    ("CCI", "Crown Castle Inc. (REIT)"),
    ("O", "Realty Income Corp. (REIT)"),

    # ── 기타 인기 종목 ──
    ("UBER", "Uber Technologies Inc."),
    ("ABNB", "Airbnb Inc."),
    ("RIVN", "Rivian Automotive Inc."),
    ("LCID", "Lucid Group Inc."),
    ("SOFI", "SoFi Technologies Inc."),
    ("HOOD", "Robinhood Markets Inc."),
    ("RBLX", "Roblox Corp."),
    ("PYPL", "PayPal Holdings Inc."),
    ("ROKU", "Roku Inc."),
    ("U", "Unity Software Inc."),
    ("SE", "Sea Limited (ADR)"),
    ("GRAB", "Grab Holdings Ltd."),
    ("BABA", "Alibaba Group (ADR)"),
    ("JD", "JD.com Inc. (ADR)"),
    ("PDD", "PDD Holdings Inc. (ADR)"),
    ("NIO", "NIO Inc. (ADR)"),
    ("LI", "Li Auto Inc. (ADR)"),

    # ── 크립토 관련 ──
    ("MSTR", "MicroStrategy Inc."),
    ("MARA", "Marathon Digital Holdings"),
    ("RIOT", "Riot Platforms Inc."),
    ("IBIT", "iShares Bitcoin Trust ETF"),
    ("BITO", "ProShares Bitcoin Strategy ETF"),
]


def search_tickers(query: str, limit: int = 20) -> list[tuple[str, str]]:
    """
    티커 또는 종목명으로 검색. 대소문자 무시.

    Returns
    -------
    list of (ticker, name) tuples
    """
    if not query:
        return TICKER_DATABASE[:limit]

    query = query.upper().strip()
    results = []

    # 1) 티커 정확 매치 우선
    for ticker, name in TICKER_DATABASE:
        if ticker == query:
            results.append((ticker, name))
            break

    # 2) 티커 접두사 매치
    for ticker, name in TICKER_DATABASE:
        if ticker.startswith(query) and (ticker, name) not in results:
            results.append((ticker, name))

    # 3) 종목명 포함 매치
    for ticker, name in TICKER_DATABASE:
        if query in name.upper() and (ticker, name) not in results:
            results.append((ticker, name))

    return results[:limit]


def get_display_text(ticker: str, name: str) -> str:
    """드롭다운에 표시할 텍스트"""
    return f"{ticker}  -  {name}"


def parse_ticker_from_display(display_text: str) -> str:
    """표시 텍스트에서 티커만 추출"""
    return display_text.split("  -  ")[0].strip().upper()
