from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

SPREADSHEET_ID = "1_FUDeCBMXBabuZjK1gvCMJcfK1_VpKHwKwLc-m1csBc"
REQ_SHEET_NAME = "FINAL REQUIREMENT"
BUYING_SHEET_NAME = "FINAL BUYING"

PRIMARY_SIEVE_COUNT = 18  # Rows 4..21 => 6 (0) through 6.5

QUALITY_BLOCKS = [
    {
        "code": "M1",
        "grade": "VVS/DEF",
        "label": "M1 · VVS/DEF",
        "accent": "#2563eb",
        "sieve_col": 1,     # A
        "req_col": 2,       # B
        "bagging_col": 3,   # C
        "assort_col": 4,    # D
        "final_col": 5,     # E
        "urgency_col": 6,   # F
        "buying_col": 32,   # AF
    },
    {
        "code": "M2",
        "grade": "VVS-VS/GH",
        "label": "M2 · VVS-VS/GH",
        "accent": "#7c3aed",
        "sieve_col": 8,     # H
        "req_col": 9,       # I
        "bagging_col": 10,  # J
        "assort_col": 11,   # K
        "final_col": 12,    # L
        "urgency_col": 13,  # M
        "buying_col": 33,   # AG
    },
    {
        "code": "H1",
        "grade": "VVS-EF",
        "label": "H1 · VVS-EF",
        "accent": "#0891b2",
        "sieve_col": 15,    # O
        "req_col": 16,      # P
        "bagging_col": 17,  # Q
        "assort_col": 18,   # R
        "final_col": 19,    # S
        "urgency_col": 20,  # T
        "buying_col": 34,   # AH
    },
    {
        "code": "M3",
        "grade": "SI/GH",
        "label": "M3 · SI/GH",
        "accent": "#d97706",
        "sieve_col": 22,    # V
        "req_col": 23,      # W
        "bagging_col": 24,  # X
        "assort_col": 25,   # Y
        "final_col": 26,    # Z
        "urgency_col": 27,  # AA
        "buying_col": 35,   # AI
    },
]

ROLE_PERMISSIONS = {
    "Guest": {"pin": "", "can_assort": False, "can_bagging": False},
    "Assort": {"pin": "1111", "can_assort": True, "can_bagging": False},
    "Bagging": {"pin": "2222", "can_assort": False, "can_bagging": True},
    "Developer": {"pin": "9999", "can_assort": True, "can_bagging": True},
}

THEMES = {
    "Light": {
        "bg_app": "#f1f5f9",
        "card_bg": "#ffffff",
        "card_shadow": "0 2px 8px rgba(15, 23, 42, 0.06)",
        "text": "#0f172a",
        "muted": "#64748b",
        "border": "#cbd5e1",
        "border_soft": "#e2e8f0",
        "hdr_bg": "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        "hdr_solid": "#0f172a",
        "hdr_fg": "#ffffff",
        "sub_bg": "#f8fafc",
        "row_hover": "#f1f5f9",
        "btn_bg": "#ffffff",
        "btn_fg": "#1e293b",
        "btn_hover_bg": "#f1f5f9",
        "btn_hover_fg": "#0f172a",
        "btn_border": "#cbd5e1",
        "pri_bg": "#2563eb",
        "pri_fg": "#ffffff",
        "bag_bg": "#f0fdf4",
        "ass_bg": "#eff6ff",
        "urg_bg": "#fef2f2",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a",
        "track_bg": "#0f172a",
        "track_border": "#334155",
        "knob_bg": "#cbd5e1",
        "short_fg": "#dc2626",
        "surplus_fg": "#16a34a",
    },
    "Dark": {
        "bg_app": "#090e1a",
        "card_bg": "#111827",
        "card_shadow": "0 4px 14px rgba(0, 0, 0, 0.35)",
        "text": "#f8fafc",
        "muted": "#94a3b8",
        "border": "#334155",
        "border_soft": "#1e293b",
        "hdr_bg": "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
        "hdr_solid": "#020617",
        "hdr_fg": "#f8fafc",
        "sub_bg": "#1e293b",
        "row_hover": "#1e293b",
        "btn_bg": "#1e293b",
        "btn_fg": "#f1f5f9",
        "btn_hover_bg": "#334155",
        "btn_hover_fg": "#ffffff",
        "btn_border": "#475569",
        "pri_bg": "#2563eb",
        "pri_fg": "#ffffff",
        "bag_bg": "#052e16",
        "ass_bg": "#172554",
        "urg_bg": "#450a0a",
        "input_bg": "#1e293b",
        "input_fg": "#f8fafc",
        "track_bg": "#020617",
        "track_border": "#475569",
        "knob_bg": "#e2e8f0",
        "short_fg": "#f87171",
        "surplus_fg": "#4ade80",
    },
}

st.set_page_config(
    page_title="Diamond Portal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)


def parse_num(val):
    if val is None:
        return None
    s = str(val).replace(",", "").strip()
    if s in ("", "--", "-", "None", "nan", "NaN"):
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def fmt_num(val, show_zero=True):
    if val is None or pd.isna(val):
        return "--"
    fval = round(float(val), 2)
    if not show_zero and abs(fval) < 0.005:
        return "--"
    return f"{fval:.2f}"


def sum_negative(series: pd.Series) -> float:
    return round(float(series.fillna(0.0).clip(upper=0.0).sum()), 2)


def sum_positive(series: pd.Series) -> float:
    return round(float(series.fillna(0.0).clip(lower=0.0).sum()), 2)


def inject_css(theme_name: str):
    t = THEMES.get(theme_name, THEMES["Light"])

    st.markdown(
        f"""<style>
html, body, [class*="css"] {{
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}}

header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 2.8rem !important;
}}
[data-testid="stToolbar"] {{
    right: 0.5rem !important;
}}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
    background-color: {t["bg_app"]} !important;
    color: {t["text"]} !important;
    width: 100% !important;
    max-width: 100% !important;
}}
[data-testid="stMain"] {{
    flex: 1 1 auto !important;
    min-width: 0 !important;
}}
[data-testid="stMainBlockContainer"],
.block-container {{
    padding-top: 2.8rem !important;
    padding-bottom: 3.8rem !important;
    padding-left: 0.65rem !important;
    padding-right: 0.65rem !important;
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}}

/* Sidebar expanded vs collapsed — clean zero-gap collapse */
section[data-testid="stSidebar"] {{
    background-color: {t["card_bg"]} !important;
    color: {t["text"]} !important;
}}
section[data-testid="stSidebar"][aria-expanded="true"] {{
    min-width: 225px !important;
    max-width: 245px !important;
    border-right: 1px solid {t["border"]} !important;
    box-shadow: 2px 0 12px rgba(15, 23, 42, 0.06) !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"] {{
    min-width: 0px !important;
    width: 0px !important;
    max-width: 0px !important;
    border-right: none !important;
    overflow: hidden !important;
}}

/* ALWAYS-VISIBLE Sidebar Expand (>>) & Collapse (<<) buttons across Streamlit versions */
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"] {{
    opacity: 1 !important;
    visibility: visible !important;
    z-index: 9999 !important;
}}
button[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button,
button[data-testid="collapsedControl"],
[data-testid="collapsedControl"] button,
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
button[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button {{
    background: {t["pri_bg"]} !important;
    color: {t["pri_fg"]} !important;
    border: 1.5px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 9px !important;
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    min-height: 34px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35) !important;
    opacity: 1 !important;
    visibility: visible !important;
    transition: transform 0.15s ease, filter 0.15s ease !important;
}}
button[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stExpandSidebarButton"] button:hover,
[data-testid="collapsedControl"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover {{
    filter: brightness(1.12) !important;
    transform: scale(1.04) !important;
}}
button[data-testid="stExpandSidebarButton"] *,
[data-testid="stExpandSidebarButton"] button *,
[data-testid="collapsedControl"] button *,
[data-testid="stSidebarCollapsedControl"] button *,
[data-testid="stSidebarCollapseButton"] button * {{
    color: {t["pri_fg"]} !important;
    fill: {t["pri_fg"]} !important;
    stroke: {t["pri_fg"]} !important;
    opacity: 1 !important;
}}
button[data-testid="stExpandSidebarButton"] span,
[data-testid="stExpandSidebarButton"] button span,
[data-testid="stSidebarCollapseButton"] button span {{
    font-size: 20px !important;
    font-weight: 800 !important;
    line-height: 1 !important;
}}

/* Sleek sidebar spacing — fixes cut-off section headers */
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0.5rem !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    padding: 0.4rem 0.85rem 1.2rem 0.85rem !important;
}}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
    gap: 0.45rem !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {{
    overflow: visible !important;
}}
[data-testid="stSidebar"] hr {{
    margin: 8px 0 !important;
    border-color: {t["border_soft"]} !important;
}}
.sb-brand {{
    font-size: 14.5px;
    font-weight: 900;
    letter-spacing: 0.5px;
    color: {t["text"]};
    padding: 4px 0 8px 0;
    border-bottom: 1px solid {t["border_soft"]};
    margin-bottom: 4px;
}}
.sb-section-title {{
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: {t["muted"]};
    padding: 4px 2px 6px 2px;
    line-height: 1.45;
    display: block;
    overflow: visible;
}}

/* Sleek, slim buttons (sidebar & page) */
.stButton > button,
.stDownloadButton > button {{
    background-color: {t["btn_bg"]} !important;
    color: {t["btn_fg"]} !important;
    border: 1px solid {t["btn_border"]} !important;
    font-weight: 700 !important;
    font-size: 12px !important;
    min-height: 32px !important;
    height: 34px !important;
    padding: 4px 12px !important;
    border-radius: 8px !important;
    white-space: nowrap !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
    transition: all 0.15s ease !important;
}}
.stButton > button *,
.stButton > button p,
.stButton > button span {{
    color: {t["btn_fg"]} !important;
    font-weight: 700 !important;
    font-size: 12px !important;
}}
.stButton > button:hover {{
    background-color: {t["btn_hover_bg"]} !important;
    border-color: {t["pri_bg"]} !important;
}}
.stButton > button[kind="primary"] {{
    background: {t["pri_bg"]} !important;
    color: {t["pri_fg"]} !important;
    border-color: {t["pri_bg"]} !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.28) !important;
}}
.stButton > button[kind="primary"] *,
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span {{
    color: {t["pri_fg"]} !important;
}}

/* Selectbox & text input theme consistency (fixes dark box in Light theme) */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {{
    background-color: {t["input_bg"]} !important;
    color: {t["input_fg"]} !important;
    border-color: {t["btn_border"]} !important;
    border-radius: 8px !important;
    min-height: 34px !important;
    font-size: 12.5px !important;
    font-weight: 700 !important;
}}
[data-baseweb="select"] span,
[data-baseweb="select"] div,
[data-baseweb="select"] svg {{
    color: {t["input_fg"]} !important;
    fill: {t["input_fg"]} !important;
}}
[data-testid="stTextInput"] input {{
    background-color: {t["input_bg"]} !important;
    color: {t["input_fg"]} !important;
    border: 1px solid {t["btn_border"]} !important;
    border-radius: 8px !important;
    height: 34px !important;
    font-size: 12.5px !important;
    font-weight: 700 !important;
}}

/* Tighter main vertical gaps */
.block-container div[data-testid="stVerticalBlock"] {{
    gap: 0.35rem !important;
}}
.block-container div[data-testid="stMarkdownContainer"] {{
    width: 100% !important;
    max-width: 100% !important;
}}
.block-container div[data-testid="stMarkdownContainer"] p {{
    margin-bottom: 0 !important;
}}

/* Top Executive Header Bar */
.portal-banner {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 10px;
    padding: 8px 14px;
    box-shadow: {t["card_shadow"]};
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    box-sizing: border-box;
}}
.portal-title {{
    font-size: 15px;
    font-weight: 900;
    letter-spacing: -0.2px;
    color: {t["text"]};
}}
.role-pill {{
    font-size: 10.5px;
    font-weight: 800;
    padding: 2px 9px;
    border-radius: 999px;
    background: {t["sub_bg"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
    vertical-align: middle;
}}
.banner-meta {{
    font-size: 11px;
    font-weight: 700;
    color: {t["muted"]};
}}

/* CUSTOM 3-WAY PILL SLIDE SWITCH (Left = Excess, Center = All, Right = Shortage) */
.slider-shell {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    width: 100%;
}}
[data-testid="stRadio"] {{
    display: flex !important;
    justify-content: flex-end !important;
    margin: 0 !important;
    padding: 0 !important;
}}
@media (max-width: 768px) {{
    [data-testid="stRadio"] {{
        justify-content: center !important;
    }}
}}
[data-testid="stRadio"] > div[role="radiogroup"] {{
    position: relative !important;
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 0 !important;
    width: 246px !important;
    height: 46px !important;
    padding: 0 !important;
    margin: 0 !important;
    user-select: none !important;
}}
/* Pill Track */
[data-testid="stRadio"] > div[role="radiogroup"]::before {{
    content: "" !important;
    position: absolute !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    height: 26px !important;
    border-radius: 999px !important;
    background: {t["track_bg"]} !important;
    border: 1.5px solid {t["track_border"]} !important;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.45) !important;
    z-index: 0 !important;
    pointer-events: none !important;
    transition: background 0.25s ease, border-color 0.25s ease !important;
}}
/* Sliding Circular Thumb Knob */
[data-testid="stRadio"] > div[role="radiogroup"]::after {{
    content: "" !important;
    position: absolute !important;
    bottom: 3px !important;
    left: 113px !important;
    width: 20px !important;
    height: 20px !important;
    border-radius: 50% !important;
    background: {t["knob_bg"]} !important;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.45) !important;
    z-index: 1 !important;
    pointer-events: none !important;
    transition: left 0.22s cubic-bezier(0.4, 0, 0.2, 1), background 0.22s ease !important;
}}
/* State 1 (Left): Excess */
[data-testid="stRadio"] > div[role="radiogroup"]:has(label:nth-of-type(1) input:checked)::before {{
    background: #064e3b !important;
    border-color: #22c55e !important;
}}
[data-testid="stRadio"] > div[role="radiogroup"]:has(label:nth-of-type(1) input:checked)::after {{
    left: 4px !important;
    background: #4ade80 !important;
}}
/* State 2 (Center): All */
[data-testid="stRadio"] > div[role="radiogroup"]:has(label:nth-of-type(2) input:checked)::after {{
    left: 113px !important;
    background: {t["knob_bg"]} !important;
}}
/* State 3 (Right): Shortage */
[data-testid="stRadio"] > div[role="radiogroup"]:has(label:nth-of-type(3) input:checked)::before {{
    background: #450a0a !important;
    border-color: #ef4444 !important;
}}
[data-testid="stRadio"] > div[role="radiogroup"]:has(label:nth-of-type(3) input:checked)::after {{
    left: 222px !important;
    background: #f87171 !important;
}}

/* Clickable labels spanning text + track underneath */
[data-testid="stRadio"] label[data-baseweb="radio"] {{
    position: relative !important;
    z-index: 2 !important;
    display: flex !important;
    align-items: flex-start !important;
    justify-content: center !important;
    width: 100% !important;
    height: 46px !important;
    margin: 0 !important;
    padding: 1px 0 0 0 !important;
    cursor: pointer !important;
    background: transparent !important;
}}
/* Hide native BaseWeb radio circle without touching text */
[data-testid="stRadio"] label[data-baseweb="radio"] > div:not(:has([data-testid="stMarkdownContainer"])) {{
    display: none !important;
}}
[data-testid="stRadio"] label[data-baseweb="radio"] p {{
    font-size: 10.5px !important;
    font-weight: 800 !important;
    letter-spacing: 0.3px !important;
    text-transform: uppercase !important;
    color: {t["muted"]} !important;
    margin: 0 !important;
    line-height: 1.2 !important;
    transition: color 0.2s ease !important;
}}
[data-testid="stRadio"] label[data-baseweb="radio"]:nth-of-type(1):has(input:checked) p {{
    color: {t["surplus_fg"]} !important;
}}
[data-testid="stRadio"] label[data-baseweb="radio"]:nth-of-type(2):has(input:checked) p {{
    color: {t["text"]} !important;
}}
[data-testid="stRadio"] label[data-baseweb="radio"]:nth-of-type(3):has(input:checked) p {{
    color: {t["short_fg"]} !important;
}}

/* Expander styling */
[data-testid="stExpander"] {{
    background-color: {t["card_bg"]} !important;
    border: 1px solid {t["border"]} !important;
    border-radius: 10px !important;
    box-shadow: {t["card_shadow"]} !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary * {{
    color: {t["text"]} !important;
    font-weight: 800 !important;
    font-size: 12.5px !important;
}}

/* Auto-adjusting 4 -> 2 -> 1 Responsive Grid */
.four-block-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    width: 100%;
    max-width: 100%;
    align-items: start;
    box-sizing: border-box;
}}
@media (max-width: 1080px), (max-aspect-ratio: 5/4) and (max-width: 1200px) {{
    .four-block-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}
@media (max-width: 620px), (max-aspect-ratio: 3/4) {{
    .four-block-grid {{
        grid-template-columns: minmax(0, 1fr);
        gap: 10px;
    }}
}}

/* Sleek Quality Cards */
.q-card {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 10px;
    box-shadow: {t["card_shadow"]};
    min-width: 0;
    width: 100%;
    overflow: hidden;
    box-sizing: border-box;
}}
.q-card-scroll {{
    width: 100%;
    overflow-x: auto;
}}
.q-card-hdr {{
    background: {t["hdr_bg"]};
    color: {t["hdr_fg"]};
    padding: 5px 8px;
    font-size: clamp(10.5px, 0.85vw, 12px);
    font-weight: 800;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 4px;
}}
.q-card-sub {{
    font-size: 10.5px;
    font-weight: 700;
    padding: 3px 8px;
    background: {t["sub_bg"]};
    color: {t["muted"]};
    border-bottom: 1px solid {t["border"]};
    display: flex;
    justify-content: space-between;
    gap: 4px;
}}
.q-card-sub b {{
    color: {t["text"]};
}}

table.compact-tbl {{
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
}}
table.compact-tbl th {{
    background: {t["sub_bg"]};
    color: {t["muted"]};
    font-size: 9.5px;
    font-weight: 800;
    letter-spacing: 0.3px;
    padding: 3px 3px;
    text-align: right;
    border-bottom: 1px solid {t["border"]};
    border-right: 1px solid {t["border_soft"]};
}}
table.compact-tbl th:first-child {{
    text-align: left;
    padding-left: 6px;
}}
table.compact-tbl th:last-child {{
    border-right: none;
    padding-right: 6px;
}}
table.compact-tbl td {{
    font-size: clamp(10.5px, 0.88vw, 12px);
    font-weight: 700;
    padding: 2.5px 3px;
    line-height: 1.25;
    text-align: right;
    border-bottom: 1px solid {t["border_soft"]};
    border-right: 1px solid {t["border_soft"]};
    white-space: nowrap;
}}
@media (max-width: 620px) {{
    table.compact-tbl td {{
        font-size: 12.5px;
        padding: 4px 5px;
    }}
}}
table.compact-tbl td:first-child {{
    text-align: left;
    padding-left: 6px;
    font-weight: 800;
}}
table.compact-tbl td:last-child {{
    border-right: none;
    padding-right: 6px;
}}
table.compact-tbl tbody tr:hover td {{
    background-color: {t["row_hover"]};
}}
table.compact-tbl td.cell-bag {{
    background: {t["bag_bg"]};
}}
table.compact-tbl td.cell-ass {{
    background: {t["ass_bg"]};
}}
table.compact-tbl tr.row-urgent td {{
    background: {t["urg_bg"]};
}}
table.compact-tbl tr.row-subtotal td {{
    background: {t["sub_bg"]};
    font-weight: 900;
    border-top: 1.5px solid {t["border"]};
    border-bottom: none;
    padding-top: 4px;
    padding-bottom: 4px;
}}

.val-short {{
    color: {t["short_fg"]} !important;
    font-weight: 800 !important;
}}
.val-surplus {{
    color: {t["surplus_fg"]} !important;
    font-weight: 800 !important;
}}
.urg-tag {{
    display: inline-block;
    background: #dc2626;
    color: #ffffff;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 0.3px;
    padding: 1px 4px;
    border-radius: 4px;
    margin-left: 3px;
    vertical-align: middle;
}}

/* Grand Total Footer Card */
.gt-bar {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 10px;
    box-shadow: {t["card_shadow"]};
    margin-top: 6px;
    padding: 7px 12px;
    font-size: 11.5px;
    font-weight: 700;
    color: {t["text"]};
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
}}

/* Buying Table */
.buy-wrap {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 10px;
    box-shadow: {t["card_shadow"]};
    overflow-x: auto;
    width: 100%;
    box-sizing: border-box;
}}
table.buy-tbl {{
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
}}
table.buy-tbl th {{
    background: {t["hdr_solid"]};
    color: {t["hdr_fg"]};
    font-size: 11.5px;
    font-weight: 800;
    padding: 7px 10px;
    text-align: right;
    border-right: 1px solid rgba(255, 255, 255, 0.14);
}}
table.buy-tbl th:first-child {{ text-align: left; }}
table.buy-tbl th:last-child {{ border-right: none; }}
table.buy-tbl td {{
    font-size: 13px;
    font-weight: 700;
    padding: 4px 10px;
    line-height: 1.3;
    text-align: right;
    border-bottom: 1px solid {t["border_soft"]};
    border-right: 1px solid {t["border_soft"]};
}}
table.buy-tbl td:first-child {{
    text-align: left;
    font-weight: 800;
}}
table.buy-tbl td:last-child {{ border-right: none; }}
table.buy-tbl tbody tr:hover td {{
    background: {t["row_hover"]};
}}
table.buy-tbl tr.row-subtotal td {{
    background: {t["sub_bg"]};
    font-weight: 900;
    border-top: 1.5px solid {t["border"]};
    border-bottom: 1.5px solid {t["border"]};
}}
table.buy-tbl tfoot td {{
    background: {t["hdr_solid"]};
    color: {t["hdr_fg"]};
    font-weight: 900;
    padding: 7px 10px;
}}
</style>""",
        unsafe_allow_html=True,
    )


@st.cache_resource
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=120, show_spinner=False)
def load_requirement_sheet() -> pd.DataFrame:
    ws = get_gsheet_client().open_by_key(SPREADSHEET_ID).worksheet(REQ_SHEET_NAME)
    raw = ws.get("A4:AN33")

    records = []
    for idx, r in enumerate(raw):
        sieve = str(r[0]).strip() if len(r) > 0 and r[0] is not None else ""
        if not sieve:
            continue
        rec = {
            "_sheet_row": idx + 4,
            "Sieve": sieve,
            "Tier": "Primary" if idx < PRIMARY_SIEVE_COUNT else "Large",
        }
        for blk in QUALITY_BLOCKS:
            q = blk["code"]
            req = parse_num(r[blk["req_col"] - 1] if len(r) >= blk["req_col"] else None) or 0.0
            bag = parse_num(r[blk["bagging_col"] - 1] if len(r) >= blk["bagging_col"] else None)
            ass = parse_num(r[blk["assort_col"] - 1] if len(r) >= blk["assort_col"] else None)
            sheet_fin = parse_num(r[blk["final_col"] - 1] if len(r) >= blk["final_col"] else None)
            calc_fin = round(((bag or 0.0) + (ass or 0.0)) - req, 2)
            fin = sheet_fin if sheet_fin is not None else calc_fin
            urg_raw = (
                str(r[blk["urgency_col"] - 1]).strip().upper()
                if len(r) >= blk["urgency_col"] and r[blk["urgency_col"] - 1]
                else ""
            )
            buy_sheet = parse_num(r[blk["buying_col"] - 1] if len(r) >= blk["buying_col"] else None)

            rec[f"{q}_req"] = round(req, 2)
            rec[f"{q}_bag"] = bag
            rec[f"{q}_ass"] = ass
            rec[f"{q}_fin"] = round(fin, 2)
            rec[f"{q}_urg"] = urg_raw
            rec[f"{q}_buy"] = buy_sheet if buy_sheet is not None else round(max(0.0, -fin), 2)
        records.append(rec)

    return pd.DataFrame(records)


@st.cache_data(ttl=120, show_spinner=False)
def load_buying_sheet() -> pd.DataFrame:
    ws = get_gsheet_client().open_by_key(SPREADSHEET_ID).worksheet(BUYING_SHEET_NAME)
    vals = ws.get_all_values()
    records = []
    for r in vals:
        if not r:
            continue
        sieve = str(r[0]).strip()
        if sieve in ("", "QUALITY CODE", "QUALITY", "SEIVE SIZE", "TOTAL"):
            continue
        records.append(
            {
                "Sieve": sieve,
                "M1": parse_num(r[1] if len(r) > 1 else None),
                "M2": parse_num(r[2] if len(r) > 2 else None),
                "H1": parse_num(r[3] if len(r) > 3 else None),
                "M3": parse_num(r[4] if len(r) > 4 else None),
            }
        )
    df_b = pd.DataFrame(records)
    if not df_b.empty:
        df_b["Tier"] = [
            "Primary" if i < PRIMARY_SIEVE_COUNT else "Large" for i in range(len(df_b))
        ]
    return df_b


def save_edits_to_sheet(
    edited_df: pd.DataFrame,
    original_df: pd.DataFrame,
    can_bagging: bool,
    can_assort: bool,
):
    ws = get_gsheet_client().open_by_key(SPREADSHEET_ID).worksheet(REQ_SHEET_NAME)
    batch_updates = []

    for idx in range(len(edited_df)):
        sheet_row = int(original_df.loc[idx, "_sheet_row"])
        for blk in QUALITY_BLOCKS:
            q = blk["code"]
            if can_bagging:
                old_b = original_df.loc[idx, f"{q}_bag"]
                new_b = edited_df.loc[idx, f"{q}_bag"]
                new_b_clean = None if pd.isna(new_b) else round(float(new_b), 2)
                if old_b != new_b_clean:
                    a1 = gspread.utils.rowcol_to_a1(sheet_row, blk["bagging_col"])
                    batch_updates.append(
                        {"range": f"{REQ_SHEET_NAME}!{a1}", "values": [["" if new_b_clean is None else new_b_clean]]}
                    )

            if can_assort:
                old_a = original_df.loc[idx, f"{q}_ass"]
                new_a = edited_df.loc[idx, f"{q}_ass"]
                new_a_clean = None if pd.isna(new_a) else round(float(new_a), 2)
                if old_a != new_a_clean:
                    a1 = gspread.utils.rowcol_to_a1(sheet_row, blk["assort_col"])
                    batch_updates.append(
                        {"range": f"{REQ_SHEET_NAME}!{a1}", "values": [["" if new_a_clean is None else new_a_clean]]}
                    )

    if batch_updates:
        ws.batch_update(batch_updates, value_input_option="USER_ENTERED")
        load_requirement_sheet.clear()
    return len(batch_updates)


# --- SESSION STATE DEFAULTS ---
if "role" not in st.session_state or st.session_state.role not in ROLE_PERMISSIONS:
    st.session_state.role = "Guest"
if "theme" not in st.session_state or st.session_state.theme not in THEMES:
    st.session_state.theme = "Light"
if "view" not in st.session_state or st.session_state.view not in ("M1, M2, H1 & M3", "Buying"):
    st.session_state.view = "M1, M2, H1 & M3"
if "filter_mode" not in st.session_state or st.session_state.filter_mode not in ("Excess", "All", "Shortage"):
    st.session_state.filter_mode = "All"
if "refresh_notice" not in st.session_state:
    st.session_state.refresh_notice = ""


def _sync_filter_slider():
    st.session_state.filter_mode = st.session_state._filter_slider


# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="sb-brand">💎 DIAMOND PORTAL</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-section-title">Views</div>', unsafe_allow_html=True)
    if st.button(
        "M1, M2, H1 & M3",
        use_container_width=True,
        type="primary" if st.session_state.view == "M1, M2, H1 & M3" else "secondary",
    ):
        st.session_state.view = "M1, M2, H1 & M3"
        st.rerun()

    if st.button(
        "Buying",
        use_container_width=True,
        type="primary" if st.session_state.view == "Buying" else "secondary",
    ):
        st.session_state.view = "Buying"
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="sb-section-title">Role Access</div>', unsafe_allow_html=True)
    sel_role = st.selectbox(
        "Select Role",
        list(ROLE_PERMISSIONS.keys()),
        index=list(ROLE_PERMISSIONS.keys()).index(st.session_state.role),
        label_visibility="collapsed",
    )
    if sel_role == "Guest":
        if st.session_state.role != "Guest":
            st.session_state.role = "Guest"
            st.rerun()
    else:
        pin_in = st.text_input("PIN", type="password", placeholder="Enter PIN", label_visibility="collapsed")
        if st.button("🔓 Unlock Role", use_container_width=True):
            if pin_in.strip() == ROLE_PERMISSIONS[sel_role]["pin"]:
                st.session_state.role = sel_role
                st.success(f"Active: {sel_role}")
                st.rerun()
            else:
                st.error("Invalid PIN")

    st.markdown("---")
    st.markdown('<div class="sb-section-title">Theme</div>', unsafe_allow_html=True)
    theme_choice = st.selectbox(
        "Select Theme",
        ["Light", "Dark"],
        index=["Light", "Dark"].index(st.session_state.theme),
        label_visibility="collapsed",
    )
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="sb-section-title">Data Sync</div>', unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        load_requirement_sheet.clear()
        load_buying_sheet.clear()
        ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%I:%M:%S %p")
        st.session_state.refresh_notice = f"Refreshed at {ist_now}"
        st.rerun()

    if st.session_state.refresh_notice:
        st.success(f"✅ {st.session_state.refresh_notice}")

inject_css(st.session_state.theme)

if st.session_state.refresh_notice:
    st.toast(f"✅ Data {st.session_state.refresh_notice}", icon="🔄")
    st.session_state.refresh_notice = ""

role = st.session_state.role
perms = ROLE_PERMISSIONS[role]
filter_mode = st.session_state.filter_mode

banner_note = (
    "Final Sum = Positive Only (Excess)"
    if (st.session_state.view == "M1, M2, H1 & M3" and filter_mode == "Excess")
    else "Final Sum = Negative Only"
)

if st.session_state.view == "M1, M2, H1 & M3":
    hdr_col, sld_col = st.columns([3.2, 1.2], vertical_alignment="center")
    with hdr_col:
        st.markdown(
            f'<div class="portal-banner">'
            f'<div><span class="portal-title">💎 {st.session_state.view}</span>'
            f'&nbsp;&nbsp;<span class="role-pill">{role}</span></div>'
            f'<div class="banner-meta">{banner_note} · Primary 6(0)–6.5</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with sld_col:
        st.radio(
            "Filter Mode",
            options=["Excess", "All", "Shortage"],
            index=["Excess", "All", "Shortage"].index(filter_mode),
            horizontal=True,
            label_visibility="collapsed",
            key="_filter_slider",
            on_change=_sync_filter_slider,
        )
else:
    st.markdown(
        f'<div class="portal-banner">'
        f'<div><span class="portal-title">💎 {st.session_state.view}</span>'
        f'&nbsp;&nbsp;<span class="role-pill">{role}</span></div>'
        f'<div class="banner-meta">Buying Summary · Primary 6(0)–6.5</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

try:
    df = load_requirement_sheet()
except Exception as e:
    st.error(f"Could not load `{REQ_SHEET_NAME}`: {e}")
    st.stop()


def build_four_cards_full_html(sub_df: pd.DataFrame, sub_label: str, mode: str = "All") -> str:
    cards = []
    for blk in QUALITY_BLOCKS:
        q = blk["code"]

        visible_rows = []
        for _, r in sub_df.iterrows():
            fin = float(r[f"{q}_fin"] or 0.0)
            urg = str(r[f"{q}_urg"] or "").strip()
            if mode == "Shortage" and not (fin < -0.001 or urg != ""):
                continue
            if mode == "Excess" and not (fin > 0.001):
                continue
            visible_rows.append(r)

        vis_df = pd.DataFrame(visible_rows) if visible_rows else sub_df.iloc[0:0]
        req_sum = round(float(vis_df[f"{q}_req"].fillna(0.0).sum()), 2) if not vis_df.empty else 0.0
        bag_sum = round(float(vis_df[f"{q}_bag"].fillna(0.0).sum()), 2) if not vis_df.empty else 0.0
        ass_sum = round(float(vis_df[f"{q}_ass"].fillna(0.0).sum()), 2) if not vis_df.empty else 0.0

        if mode == "Excess":
            fin_sum = sum_positive(sub_df[f"{q}_fin"])
            fin_sum_cls = "val-surplus" if fin_sum > 0.001 else ""
            hdr_sum_html = f'<span style="color:#4ade80;">+{fin_sum:.2f}</span>'
        else:
            fin_sum = sum_negative(sub_df[f"{q}_fin"])
            fin_sum_cls = "val-short" if fin_sum < -0.001 else ""
            urg_cnt = int((sub_df[f"{q}_urg"].fillna("") != "").sum())
            urg_pill = f' · <span style="color:#fca5a5;">{urg_cnt} URG</span>' if urg_cnt > 0 else ""
            hdr_sum_html = f'<span>{fin_sum:.2f}{urg_pill}</span>'

        body_rows = []
        for r in visible_rows:
            sieve = r["Sieve"]
            req = float(r[f"{q}_req"] or 0.0)
            bag_raw = r[f"{q}_bag"]
            ass_raw = r[f"{q}_ass"]
            fin = float(r[f"{q}_fin"] or 0.0)
            urg = str(r[f"{q}_urg"] or "").strip()

            fin_cls = "val-short" if fin < -0.001 else ("val-surplus" if fin > 0.001 else "")
            tr_cls = ' class="row-urgent"' if urg else ""
            urg_badge = f'<span class="urg-tag">{urg}</span>' if urg else ""

            body_rows.append(
                f"<tr{tr_cls}>"
                f"<td>{sieve}{urg_badge}</td>"
                f"<td>{fmt_num(req)}</td>"
                f'<td class="cell-bag">{fmt_num(bag_raw, show_zero=False)}</td>'
                f'<td class="cell-ass">{fmt_num(ass_raw, show_zero=False)}</td>'
                f'<td class="{fin_cls}">{fmt_num(fin)}</td>'
                f"</tr>"
            )

        if not body_rows:
            empty_msg = "No excess stock" if mode == "Excess" else "No negative shortage"
            body_rows.append(
                f'<tr><td colspan="5" style="text-align:center;opacity:0.65;padding:8px;">{empty_msg}</td></tr>'
            )

        thead = "<tr><th>SIEVE</th><th>REQ</th><th>BAG</th><th>ASS</th><th>FINAL</th></tr>"
        fin_sum_disp = f"+{fin_sum:.2f}" if (mode == "Excess" and fin_sum > 0.001) else f"{fin_sum:.2f}"
        sub_row = (
            f'<tr class="row-subtotal">'
            f"<td>{sub_label}</td>"
            f"<td>{req_sum:.2f}</td>"
            f'<td class="cell-bag">{bag_sum:.2f}</td>'
            f'<td class="cell-ass">{ass_sum:.2f}</td>'
            f'<td class="{fin_sum_cls}">{fin_sum_disp}</td>'
            f"</tr>"
        )

        cards.append(
            f'<div class="q-card" style="border-top: 3px solid {blk["accent"]};">'
            f'<div class="q-card-hdr"><span>{blk["label"]}</span>{hdr_sum_html}</div>'
            f'<div class="q-card-sub"><span>Req: <b>{req_sum:.1f}</b></span><span>Stock: <b>{(bag_sum + ass_sum):.1f}</b></span></div>'
            f'<div class="q-card-scroll"><table class="compact-tbl"><thead>{thead}</thead><tbody>{"".join(body_rows)}{sub_row}</tbody></table></div>'
            f"</div>"
        )

    return f'<div class="four-block-grid">{"".join(cards)}</div>'


if st.session_state.view == "M1, M2, H1 & M3":
    primary_df = df[df["Tier"] == "Primary"]
    large_df = df[df["Tier"] == "Large"]

    st.markdown(
        build_four_cards_full_html(primary_df, "SUB (6–6.5)", mode=filter_mode),
        unsafe_allow_html=True,
    )

    if not large_df.empty:
        if filter_mode == "Excess":
            large_total = sum(sum_positive(large_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
            exp_label = f"Sieves Below 6.5 (7 to 12.5) · {len(large_df)} sizes · Excess: +{large_total:.2f} ct"
        else:
            large_total = sum(sum_negative(large_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
            exp_label = f"Sieves Below 6.5 (7 to 12.5) · {len(large_df)} sizes · Shortage: {large_total:.2f} ct"

        with st.expander(exp_label, expanded=False):
            st.markdown(
                build_four_cards_full_html(large_df, "SUB (7–12.5)", mode=filter_mode),
                unsafe_allow_html=True,
            )

        gt_parts = []
        if filter_mode == "Excess":
            gt_title = "GRAND TOTAL · EXCESS (POSITIVE SUM)"
            for blk in QUALITY_BLOCKS:
                q = blk["code"]
                g_pos = sum_positive(df[f"{q}_fin"])
                gt_parts.append(f'<b>{q}</b>: <span class="val-surplus">+{g_pos:.2f}</span>')
        else:
            gt_title = "GRAND TOTAL · SHORTAGE (NEGATIVE SUM)"
            for blk in QUALITY_BLOCKS:
                q = blk["code"]
                g_neg = sum_negative(df[f"{q}_fin"])
                gt_parts.append(f'<b>{q}</b>: <span class="val-short">{g_neg:.2f}</span>')

        st.markdown(
            f'<div class="gt-bar">'
            f'<span><b>{gt_title}</b></span><span>{" &nbsp;|&nbsp; ".join(gt_parts)}</span></div>',
            unsafe_allow_html=True,
        )

    if perms["can_bagging"] or perms["can_assort"]:
        st.markdown("---")
        st.markdown(f"**Quick Entry ({role})** — edit allowed columns below and click **Save to Sheet**:")
        edit_cols = ["Sieve"]
        col_cfg = {"Sieve": st.column_config.TextColumn("Sieve", disabled=True)}
        for blk in QUALITY_BLOCKS:
            q = blk["code"]
            if perms["can_bagging"]:
                c_bag = f"{q}_bag"
                edit_cols.append(c_bag)
                col_cfg[c_bag] = st.column_config.NumberColumn(f"Bag {q}", format="%.2f")
            if perms["can_assort"]:
                c_ass = f"{q}_ass"
                edit_cols.append(c_ass)
                col_cfg[c_ass] = st.column_config.NumberColumn(f"Ass {q}", format="%.2f")

        edited_grid = st.data_editor(
            df[edit_cols],
            hide_index=True,
            use_container_width=True,
            height=340,
            column_config=col_cfg,
            key=f"grid_{role}",
        )
        if st.button("💾 Save to Sheet", type="primary"):
            cells_updated = save_edits_to_sheet(
                edited_grid, df, perms["can_bagging"], perms["can_assort"]
            )
            st.success(f"Updated {cells_updated} sheet cell(s) in `{REQ_SHEET_NAME}`.")
            st.rerun()


elif st.session_state.view == "Buying":
    try:
        df_buy = load_buying_sheet()
    except Exception:
        df_buy = pd.DataFrame()

    if df_buy.empty:
        df_buy = pd.DataFrame(
            [
                {
                    "Sieve": r["Sieve"],
                    "Tier": r["Tier"],
                    "M1": r["M1_buy"],
                    "M2": r["M2_buy"],
                    "H1": r["H1_buy"],
                    "M3": r["M3_buy"],
                }
                for _, r in df.iterrows()
            ]
        )

    def build_buying_html(sub_b: pd.DataFrame, sub_label: str, show_grand_total: bool = False) -> str:
        q_cols = ["M1", "M2", "H1", "M3"]
        body_trs = []
        for _, r in sub_b.iterrows():
            cells = [f"<td>{r['Sieve']}</td>"]
            for qc in q_cols:
                val = r[qc]
                fval = float(val) if val is not None and not pd.isna(val) else 0.0
                cls = ' class="val-short"' if fval > 0.001 else ""
                cells.append(f"<td{cls}>{fmt_num(val, show_zero=False)}</td>")
            body_trs.append(f"<tr>{''.join(cells)}</tr>")

        sub_cells = [f"<td>{sub_label}</td>"]
        for qc in q_cols:
            s_val = float(sub_b[qc].fillna(0.0).sum())
            sub_cells.append(f'<td class="val-short">{s_val:.2f}</td>')
        body_trs.append(f'<tr class="row-subtotal">{"".join(sub_cells)}</tr>')

        foot_html = ""
        if show_grand_total:
            gt_cells = ["<td>GRAND TOTAL</td>"]
            for qc in q_cols:
                gt_cells.append(f"<td>{float(df_buy[qc].fillna(0.0).sum()):.2f}</td>")
            foot_html = f"<tfoot><tr>{''.join(gt_cells)}</tr></tfoot>"

        return (
            f'<div class="buy-wrap"><table class="buy-tbl">'
            f"<thead><tr><th>SEIVE SIZE</th><th>M1 (VVS/DEF)</th><th>M2 (VVS-VS/GH)</th><th>H1 (VVS-EF)</th><th>M3 (SI/GH)</th></tr></thead>"
            f"<tbody>{''.join(body_trs)}</tbody>{foot_html}</table></div>"
        )

    b_prim = df_buy[df_buy["Tier"] == "Primary"]
    b_large = df_buy[df_buy["Tier"] == "Large"]

    st.markdown(build_buying_html(b_prim, "SUBTOTAL (6–6.5)", show_grand_total=b_large.empty), unsafe_allow_html=True)

    if not b_large.empty:
        with st.expander(f"Sieves Below 6.5 (7 to 12.5) · {len(b_large)} sizes", expanded=False):
            st.markdown(build_buying_html(b_large, "SUBTOTAL (7–12.5)", show_grand_total=False), unsafe_allow_html=True)

        gt_cells = ["<td>GRAND TOTAL</td>"]
        for qc in ["M1", "M2", "H1", "M3"]:
            gt_cells.append(f"<td>{float(df_buy[qc].fillna(0.0).sum()):.2f}</td>")
        st.markdown(
            f'<div class="buy-wrap" style="margin-top:6px;"><table class="buy-tbl"><tfoot><tr>{"".join(gt_cells)}</tr></tfoot></table></div>',
            unsafe_allow_html=True,
        )
