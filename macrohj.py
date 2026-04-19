# ================================
# 📊 유진투자증권 나효정 대리 모닝브리핑 (완전 최종본)
# ================================
import time
import warnings
from io import StringIO

import pandas as pd
import streamlit as st
import yfinance as yf

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

warnings.filterwarnings("ignore", category=FutureWarning)

st.set_page_config(page_title="모닝브리핑", layout="wide")
HEADLESS = True

# =========================
# 스타일
# =========================
st.markdown("""
<style>
.main {background: linear-gradient(135deg, #e9f5ff 0%, #f6fbff 100%);}

.title-box {text-align:center; margin-bottom:20px;}
.main-title {font-size:34px; font-weight:900; color:#1f2c3b;}
.sub-title {font-size:16px; font-weight:700; color:#4a6572;}

.card {
    background:#ffffff;
    border-radius:16px;
    padding:14px;
    border:1px solid #d9e6f2;
    box-shadow:0 2px 6px rgba(0,0,0,0.05);
    min-height:110px;
}

.card-title {font-size:14px; font-weight:800; color:#3b556b;}
.card-value {font-size:24px; font-weight:900;}

.up {color:#d9463b;}
.down {color:#2f7ed8;}
.flat {color:#6c7a89;}
</style>
""", unsafe_allow_html=True)

# =========================
# 제목
# =========================
st.markdown("""
<div class="title-box">
    <div class="main-title">📊 유진투자증권 나효정 대리</div>
    <div class="sub-title">모닝 브리핑</div>
</div>
""", unsafe_allow_html=True)

# =========================
# 티커
# =========================
tickers = {
    "S&P500": "^GSPC",
    "다우": "^DJI",
    "나스닥": "^IXIC",
    "필라델피아 반도체": "^SOX",

    "미국 10년": "^TNX",
    "미국 2년": "^IRX",
    "달러/원": "KRW=X",
    "달러/엔": "JPY=X",

    "금": "GC=F",
    "은": "SI=F",
    "구리": "HG=F",
    "WTI유가": "CL=F",
    "비트코인": "BTC-USD",

    "코스피": "^KS11",
    "코스닥": "^KQ11",
    "EWY": "EWY",
}

# =========================
# 글로벌 데이터
# =========================
@st.cache_data(ttl=600)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="1mo", progress=False, auto_adjust=False)
        if df is None or df.empty:
            return None, None

        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        close = close.dropna()
        if len(close) < 2:
            return None, None

        last = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        pct = (last - prev) / prev * 100 if prev != 0 else 0

        return round(last, 2), round(pct, 2)
    except Exception:
        return None, None

def draw_card(name):
    val, pct = get_data(tickers[name])

    if val is None:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">{name}</div>
            <div class="card-value flat">데이터 없음</div>
        </div>
        """, unsafe_allow_html=True)
        return

    color = "up" if pct > 0 else "down" if pct < 0 else "flat"

    st.markdown(f"""
    <div class="card">
        <div class="card-title">{name}</div>
        <div class="card-value {color}">{val:,.2f}</div>
        <div class="{color}">{pct:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

def section(title, items):
    st.markdown(f"### {title}")
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        with col:
            draw_card(item)

# =========================
# ETF
# =========================
def get_driver():
    options = webdriver.ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1600,2200")
    options.add_argument("--lang=ko-KR")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

def parse_etf(df, ascending=False):
    work = df[["종목명", "등락률"]].copy()
    work["종목명"] = work["종목명"].astype(str).str.strip()
    work = work[~work["종목명"].isin(["", "종목명", "nan", "None", "NaN"])]

    work["등락률"] = (
        work["등락률"].astype(str)
        .str.replace("%", "", regex=False)
        .str.replace("+", "", regex=False)
        .str.replace("−", "-", regex=False)
        .str.replace("▲", "", regex=False)
        .str.replace("▼", "", regex=False)
        .str.strip()
    )
    work["등락률"] = pd.to_numeric(work["등락률"], errors="coerce")
    work = work.dropna(subset=["등락률"])
    work = work.drop_duplicates(subset=["종목명"])

    work = work.sort_values("등락률", ascending=ascending).head(5).copy()
    work["등락률"] = work["등락률"].apply(lambda x: f"{x:+.2f}%")
    work.index = range(1, len(work) + 1)
    return work

@st.cache_data(ttl=600)
def load_etf():
    driver = None
    try:
        driver = get_driver()
        driver.get("https://finance.naver.com/sise/etf.naver")
        time.sleep(2)

        tables = pd.read_html(StringIO(driver.page_source))
        if not tables:
            return pd.DataFrame(), pd.DataFrame()

        df = tables[0]
        return parse_etf(df, ascending=False), parse_etf(df, ascending=True)
    except Exception:
        return pd.DataFrame(), pd.DataFrame()
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass

# =========================
# 매크로 일정 정렬용
# =========================
def parse_macro_date(date_str):
    s = str(date_str).replace(" ", "")
    try:
        if "~" in s:
            s = s.split("~")[0]
        s = s.replace("월", "-").replace("일", "")
        month, day = s.split("-")
        return pd.Timestamp(year=2026, month=int(month), day=int(day))
    except Exception:
        return pd.Timestamp.max

# =========================
# 출력
# =========================
section("📈 미국증시", ["S&P500", "다우", "나스닥", "필라델피아 반도체"])
section("💱 금리 / 환율", ["미국 10년", "미국 2년", "달러/원", "달러/엔"])
section("🛢️ 원자재 / 비트코인", ["금", "은", "구리", "WTI유가", "비트코인"])
section("🇰🇷 국내증시 및 ETF", ["코스피", "코스닥", "EWY"])

try:
    etf_up, etf_down = load_etf()

    col1, col2 = st.columns(2)
    with col1:
        st.write("ETF 상승률 TOP 5")
        st.dataframe(etf_up, width="stretch")

    with col2:
        st.write("ETF 하락률 TOP 5")
        st.dataframe(etf_down, width="stretch")

except Exception as e:
    st.warning(f"ETF 로딩 오류: {e}")

# =========================
# 매크로 일정
# =========================
st.markdown("### 🗓️ 매크로 일정")

macro = pd.DataFrame([
    ["미국", "기준금리", "4월 28~29일"],
    ["미국", "실업률", "5월 8일"],
    ["미국", "CPI", "5월 12일"],
    ["한국", "실업률", "5월 13일"],
    ["미국", "PPI", "5월 13일"],
    ["한국", "옵션만기일", "5월 14일"],
    ["미국", "옵션만기일", "5월 15일"],
    ["한국", "기준금리", "5월 28일"],
], columns=["국가", "지표", "발표시기"])

macro["정렬용"] = macro["발표시기"].apply(parse_macro_date)
macro = macro.sort_values("정렬용").drop(columns=["정렬용"]).reset_index(drop=True)

st.table(macro)

# =========================
# 새로고침
# =========================
if st.button("새로고침"):
    st.cache_data.clear()
    st.rerun()

st.caption("데이터: Yahoo Finance / Naver Finance")
