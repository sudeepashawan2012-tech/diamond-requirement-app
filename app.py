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
        "label": "M1",
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
        "label": "M2",
        "accent": "#8b5cf6",
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
        "label": "H1",
        "accent": "#06b6d4",
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
        "label": "M3",
        "accent": "#f59e0b",
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
    "Alabaster": {
        "bg_app": "#f6f7f9",
        "sidebar_bg": "#ffffff",
        "card_bg": "#ffffff",
        "card_shadow": "0 1px 3px rgba(15, 23, 42, 0.06), 0 4px 12px rgba(15, 23, 42, 0.03)",
        "text": "#111827",
        "muted": "#6b7280",
        "border": "#e2e6ec",
        "border_soft": "#eef1f5",
        "hdr_bg": "#f9fafb",
        "hdr_fg": "#111827",
        "sub_bg": "#f3f4f6",
        "row_hover": "#f8fafc",
        "accent": "#111827",
        "accent_soft": "#eef2ff",
        "accent_fg": "#ffffff",
        "btn_bg": "#f8fafc",
        "btn_fg": "#374151",
        "btn_hover": "#eef2f6",
        "bag_bg": "rgba(16, 185, 129, 0.06)",
        "ass_bg": "rgba(59, 130, 246, 0.06)",
        "urg_bg": "rgba(239, 68, 68, 0.07)",
        "urg_pill_bg": "rgba(220, 38, 38, 0.12)",
        "urg_pill_fg": "#b91c1c",
        "input_bg": "#ffffff",
        "input_fg": "#111827",
        "short_fg": "#dc2626",
        "surplus_fg": "#059669",
    },
    "Platinum": {
        "bg_app": "#eef1f6",
        "sidebar_bg": "#f8fafc",
        "card_bg": "#ffffff",
        "card_shadow": "0 2px 10px rgba(15, 23, 42, 0.05)",
        "text": "#0f172a",
        "muted": "#64748b",
        "border": "#d6dde8",
        "border_soft": "#e8edf4",
        "hdr_bg": "#f1f5f9",
        "hdr_fg": "#0f172a",
        "sub_bg": "#f8fafc",
        "row_hover": "#f1f5f9",
        "accent": "#2563eb",
        "accent_soft": "#eff6ff",
        "accent_fg": "#ffffff",
        "btn_bg": "#ffffff",
        "btn_fg": "#334155",
        "btn_hover": "#e2e8f0",
        "bag_bg": "rgba(16, 185, 129, 0.07)",
        "ass_bg": "rgba(37, 99, 235, 0.06)",
        "urg_bg": "rgba(239, 68, 68, 0.07)",
        "urg_pill_bg": "rgba(220, 38, 38, 0.12)",
        "urg_pill_fg": "#b91c1c",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a",
        "short_fg": "#dc2626",
        "surplus_fg": "#059669",
    },
    "Obsidian": {
        "bg_app": "#0b0d12",
        "sidebar_bg": "#11141c",
        "card_bg": "#141821",
        "card_shadow": "0 4px 18px rgba(0, 0, 0, 0.45)",
        "text": "#f3f4f6",
        "muted": "#9ca3af",
        "border": "#252b3b",
        "border_soft": "#1d2230",
        "hdr_bg": "#191e2a",
        "hdr_fg": "#f9fafb",
        "sub_bg": "#1a202d",
        "row_hover": "#1d2433",
        "accent": "#d4af37",
        "accent_soft": "rgba(212, 175, 55, 0.14)",
        "accent_fg": "#0b0d12",
        "btn_bg": "#191e2a",
        "btn_fg": "#e5e7eb",
        "btn_hover": "#232a3a",
        "bag_bg": "rgba(16, 185, 129, 0.09)",
        "ass_bg": "rgba(96, 165, 250, 0.09)",
        "urg_bg": "rgba(248, 113, 113, 0.11)",
        "urg_pill_bg": "rgba(248, 113, 113, 0.18)",
        "urg_pill_fg": "#fca5a5",
        "input_bg": "#191e2a",
        "input_fg": "#f9fafb",
        "short_fg": "#f87171",
        "surplus_fg": "#34d399",
    },
    "Midnight": {
        "bg_app": "#070b14",
        "sidebar_bg": "#0c1220",
        "card_bg": "#0f172a",
        "card_shadow": "0 4px 18px rgba(0, 0, 0, 0.5)",
        "text": "#f1f5f9",
        "muted": "#94a3b8",
        "border": "#1e293b",
        "border_soft": "#162033",
        "hdr_bg": "#141f35",
        "hdr_fg": "#f8fafc",
        "sub_bg": "#152238",
        "row_hover": "#192842",
        "accent": "#38bdf8",
        "accent_soft": "rgba(56, 189, 248, 0.14)",
        "accent_fg": "#070b14",
        "btn_bg": "#141f35",
        "btn_fg": "#e2e8f0",
        "btn_hover": "#1e2d4a",
        "bag_bg": "rgba(52, 211, 153, 0.08)",
        "ass_bg": "rgba(56, 189, 248, 0.08)",
        "urg_bg": "rgba(248, 113, 113, 0.12)",
        "urg_pill_bg": "rgba(248, 113, 113, 0.18)",
        "urg_pill_fg": "#fca5a5",
        "input_bg": "#141f35",
        "input_fg": "#f8fafc",
        "short_fg": "#f87171",
        "surplus_fg": "#34d399",
    },
}

st.set_page_config(
    page_title="Diamond Portal",
    page_icon="◆",
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
        return "—"
    fval = round(float(val), 2)
    if not show_zero and abs(fval) < 0.005:
        return "—"
    return f"{fval:.2f}"


def sum_negative(series: pd.Series) -> float:
    return round(float(series.fillna(0.0).clip(upper=0.0).sum()), 2)


def sum_positive(series: pd.Series) -> float:
    return round(float(series.fillna(0.0).clip(lower=0.0).sum()), 2)


def inject_css(theme_name: str, filter_mode: str):
    t = THEMES.get(theme_name, THEMES["Alabaster"])

    ex_bg = "#10b981" if filter_mode == "Excess" else "transparent"
    ex_fg = "#ffffff" if filter_mode == "Excess" else "#10b981"
    ex_ring = "0 0 0 4px rgba(16, 185, 129, 0.25)" if filter_mode == "Excess" else "none"

    all_bg = t["accent"] if filter_mode == "All" else "transparent"
    all_fg = t["accent_fg"] if filter_mode == "All" else t["muted"]
    all_ring = f"0 0 0 4px {t['accent_soft']}" if filter_mode == "All" else "none"

    sh_bg = "#ef4444" if filter_mode == "Shortage" else "transparent"
    sh_fg = "#ffffff" if filter_mode == "Shortage" else "#ef4444"
    sh_ring = "0 0 0 4px rgba(239, 68, 68, 0.25)" if filter_mode == "Shortage" else "none"

    st.markdown(
        f"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}}

header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 2.7rem !important;
}}
[data-testid="stToolbar"] {{
    right: 0.6rem !important;
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
    padding-top: 2.65rem !important;
    padding-bottom: 3.8rem !important;
    padding-left: 0.75rem !important;
    padding-right: 0.75rem !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
}}

/* Sidebar container — clean zero-gap collapse */
section[data-testid="stSidebar"] {{
    background-color: {t["sidebar_bg"]} !important;
    color: {t["text"]} !important;
}}
section[data-testid="stSidebar"][aria-expanded="true"] {{
    min-width: 215px !important;
    max-width: 230px !important;
    border-right: 1px solid {t["border"]} !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"] {{
    min-width: 0px !important;
    width: 0px !important;
    max-width: 0px !important;
    border-right: none !important;
    overflow: hidden !important;
}}

/* ALWAYS-VISIBLE Sidebar Expand (>>) & Collapse (<<) Controls */
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
    background: {t["accent"]} !important;
    color: {t["accent_fg"]} !important;
    border: 1px solid {t["border"]} !important;
    border-radius: 8px !important;
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18) !important;
    opacity: 1 !important;
    visibility: visible !important;
}}
button[data-testid="stExpandSidebarButton"] *,
[data-testid="stExpandSidebarButton"] button *,
[data-testid="collapsedControl"] button *,
[data-testid="stSidebarCollapsedControl"] button *,
[data-testid="stSidebarCollapseButton"] button * {{
    color: {t["accent_fg"]} !important;
    fill: {t["accent_fg"]} !important;
    stroke: {t["accent_fg"]} !important;
    opacity: 1 !important;
}}

/* Sleek Sidebar Layout & Generous Label Spacing */
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0.4rem !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    padding: 0.4rem 0.85rem 1.2rem 0.85rem !important;
}}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
    gap: 0.4rem !important;
}}
.sb-brand-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 2px 12px 2px;
    border-bottom: 1px solid {t["border_soft"]};
    margin-bottom: 6px;
}}
.sb-brand-text {{
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.9px;
    color: {t["text"]};
}}
.sb-label {{
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: {t["muted"]};
    padding: 12px 2px 4px 2px;
    line-height: 1.4;
    display: block;
}}
.sb-meta {{
    font-size: 10.5px;
    font-weight: 600;
    color: {t["muted"]};
    padding: 4px 2px;
}}

/* Slim, Minimal Sidebar Buttons (No Bulky Boxes) */
[data-testid="stSidebar"] .stButton > button {{
    background-color: {t["btn_bg"]} !important;
    color: {t["btn_fg"]} !important;
    border: 1px solid {t["border"]} !important;
    font-weight: 600 !important;
    font-size: 11.5px !important;
    min-height: 28px !important;
    height: 30px !important;
    padding: 0 10px !important;
    border-radius: 7px !important;
    box-shadow: none !important;
    transition: all 0.14s ease !important;
}}
[data-testid="stSidebar"] .stButton > button *,
[data-testid="stSidebar"] .stButton > button p {{
    color: {t["btn_fg"]} !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    line-height: 1 !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background-color: {t["btn_hover"]} !important;
    border-color: {t["accent"]} !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background-color: {t["accent"]} !important;
    color: {t["accent_fg"]} !important;
    border-color: {t["accent"]} !important;
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"] *,
[data-testid="stSidebar"] .stButton > button[kind="primary"] p {{
    color: {t["accent_fg"]} !important;
    font-weight: 700 !important;
}}

/* Navigation links in sidebar — left-aligned minimalist style */
.st-key-sb_nav .stButton > button {{
    justify-content: flex-start !important;
    padding-left: 11px !important;
    height: 32px !important;
    border-color: transparent !important;
    background-color: transparent !important;
}}
.st-key-sb_nav .stButton > button:hover {{
    background-color: {t["btn_hover"]} !important;
    border-color: transparent !important;
}}
.st-key-sb_nav .stButton > button[kind="primary"] {{
    background-color: {t["accent_soft"]} !important;
    border-left: 3px solid {t["accent"]} !important;
    border-radius: 6px !important;
}}
.st-key-sb_nav .stButton > button[kind="primary"] *,
.st-key-sb_nav .stButton > button[kind="primary"] p {{
    color: {t["text"]} !important;
    font-weight: 800 !important;
}}

/* Keep 2x2 sidebar grids compact side-by-side */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    gap: 6px !important;
}}
[data-testid="stSidebar"] [data-testid="stColumn"] {{
    min-width: 0 !important;
    flex: 1 1 50% !important;
}}

/* Text input (PIN) */
[data-testid="stTextInput"] input {{
    background-color: {t["input_bg"]} !important;
    color: {t["input_fg"]} !important;
    border: 1px solid {t["border"]} !important;
    border-radius: 7px !important;
    height: 30px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
}}

/* Main Page Spacing */
.block-container div[data-testid="stVerticalBlock"] {{
    gap: 0.4rem !important;
}}
.block-container div[data-testid="stMarkdownContainer"] {{
    width: 100% !important;
    max-width: 100% !important;
}}
.block-container div[data-testid="stMarkdownContainer"] p {{
    margin-bottom: 0 !important;
}}

/* Top Main Header Bar */
.app-topbar {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 12px;
    padding: 9px 14px;
    box-shadow: {t["card_shadow"]};
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    box-sizing: border-box;
}}
.brand-group {{
    display: flex;
    align-items: center;
    gap: 9px;
    flex-wrap: wrap;
}}
.brand-name {{
    font-size: 15px;
    font-weight: 800;
    letter-spacing: 0.4px;
    color: {t["text"]};
}}
.brand-sep {{
    color: {t["border"]};
    font-weight: 600;
}}
.view-tag {{
    font-size: 12.5px;
    font-weight: 700;
    color: {t["muted"]};
}}
.role-chip {{
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    padding: 3px 9px;
    border-radius: 999px;
    background: {t["accent_soft"]};
    color: {t["text"]};
    border: 1px solid {t["border"]};
}}
.mode-note {{
    font-size: 11px;
    font-weight: 600;
    color: {t["muted"]};
}}

/* 3 SMALL ROUND DOT BUTTONS WITH LABELS BELOW (Excess · All · Shortage) */
.st-key-filter_pod {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 12px;
    padding: 6px 12px 5px 12px;
    box-shadow: {t["card_shadow"]};
}}
.st-key-filter_pod [data-testid="stHorizontalBlock"] {{
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: flex-start !important;
    justify-content: space-around !important;
    gap: 8px !important;
}}
.st-key-filter_pod [data-testid="stColumn"] {{
    min-width: 0 !important;
    flex: 1 1 33.33% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
}}
.st-key-filter_pod [data-testid="stColumn"] [data-testid="stVerticalBlock"] {{
    gap: 3px !important;
    align-items: center !important;
}}
.st-key-filter_pod .stButton {{
    display: flex !important;
    justify-content: center !important;
    width: auto !important;
}}
.st-key-filter_pod .stButton > button {{
    width: 26px !important;
    height: 26px !important;
    min-width: 26px !important;
    min-height: 26px !important;
    max-width: 26px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
    transition: transform 0.14s ease, box-shadow 0.14s ease !important;
}}
.st-key-filter_pod .stButton > button:hover {{
    transform: scale(1.1) !important;
}}
.st-key-filter_pod .stButton > button p {{
    font-size: 12px !important;
    font-weight: 800 !important;
    line-height: 1 !important;
    margin: 0 !important;
}}

.st-key-btn_excess button {{
    background-color: {ex_bg} !important;
    border: 2px solid #10b981 !important;
    box-shadow: {ex_ring} !important;
}}
.st-key-btn_excess button * {{
    color: {ex_fg} !important;
}}

.st-key-btn_all button {{
    background-color: {all_bg} !important;
    border: 2px solid {t["accent"]} !important;
    box-shadow: {all_ring} !important;
}}
.st-key-btn_all button * {{
    color: {all_fg} !important;
}}

.st-key-btn_shortage button {{
    background-color: {sh_bg} !important;
    border: 2px solid #ef4444 !important;
    box-shadow: {sh_ring} !important;
}}
.st-key-btn_shortage button * {{
    color: {sh_fg} !important;
}}

.dot-lbl {{
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: {t["muted"]};
    text-align: center;
    line-height: 1.15;
    white-space: nowrap;
}}
.dot-lbl.active-ex {{ color: {t["surplus_fg"]}; font-weight: 800; }}
.dot-lbl.active-all {{ color: {t["text"]}; font-weight: 800; }}
.dot-lbl.active-sh {{ color: {t["short_fg"]}; font-weight: 800; }}

/* Slim Executive KPI Micro-Strip */
.kpi-strip {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    width: 100%;
    box-sizing: border-box;
}}
@media (max-width: 720px) {{
    .kpi-strip {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 6px;
    }}
}}
.kpi-chip {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 10px;
    padding: 6px 12px;
    box-shadow: {t["card_shadow"]};
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 6px;
}}
.kpi-lbl {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: {t["muted"]};
}}
.kpi-val {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13.5px;
    font-weight: 700;
    color: {t["text"]};
}}

/* Auto-Adjusting Responsive Grid: 4 (Desktop) -> 2 (Tablet) -> 1 (Mobile) */
.four-block-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 9px;
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

/* Refined Quality Cards */
.q-card {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 11px;
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
    padding: 7px 10px 5px 10px;
    border-bottom: 1px solid {t["border_soft"]};
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
}}
.q-title-wrap {{
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
}}
.q-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}}
.q-code {{
    font-size: 12.5px;
    font-weight: 800;
    color: {t["text"]};
}}
.q-grade {{
    font-size: 10px;
    font-weight: 700;
    color: {t["muted"]};
}}
.q-hdr-metric {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    font-weight: 700;
    white-space: nowrap;
}}
.q-card-sub {{
    font-size: 10px;
    font-weight: 600;
    padding: 3px 10px;
    background: {t["card_bg"]};
    color: {t["muted"]};
    border-bottom: 1px solid {t["border_soft"]};
    display: flex;
    justify-content: space-between;
    gap: 6px;
}}
.q-card-sub b {{
    font-family: 'JetBrains Mono', monospace;
    color: {t["text"]};
    font-weight: 700;
}}

table.compact-tbl {{
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
}}
table.compact-tbl th {{
    background: {t["sub_bg"]};
    color: {t["muted"]};
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 0.5px;
    padding: 4px 4px;
    text-align: right;
    border-bottom: 1px solid {t["border"]};
    border-right: 1px solid {t["border_soft"]};
}}
table.compact-tbl th:first-child {{
    text-align: left;
    padding-left: 8px;
}}
table.compact-tbl th:last-child {{
    border-right: none;
    padding-right: 8px;
}}
table.compact-tbl td {{
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(10px, 0.82vw, 11.5px);
    font-weight: 600;
    padding: 2.5px 4px;
    line-height: 1.3;
    text-align: right;
    border-bottom: 1px solid {t["border_soft"]};
    border-right: 1px solid {t["border_soft"]};
    white-space: nowrap;
}}
@media (max-width: 620px) {{
    table.compact-tbl td {{
        font-size: 12px;
        padding: 4.5px 6px;
    }}
}}
table.compact-tbl td:first-child {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    text-align: left;
    padding-left: 8px;
    font-weight: 700;
}}
table.compact-tbl td:last-child {{
    border-right: none;
    padding-right: 8px;
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
    font-weight: 700;
    border-top: 1.5px solid {t["border"]};
    border-bottom: none;
    padding-top: 5px;
    padding-bottom: 5px;
}}

.val-short {{
    color: {t["short_fg"]} !important;
    font-weight: 700 !important;
}}
.val-surplus {{
    color: {t["surplus_fg"]} !important;
    font-weight: 700 !important;
}}
.urg-tag {{
    display: inline-block;
    background: {t["urg_pill_bg"]};
    color: {t["urg_pill_fg"]};
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 0.4px;
    padding: 1px 4px;
    border-radius: 4px;
    margin-left: 4px;
    vertical-align: middle;
}}

/* Expander & Footer */
[data-testid="stExpander"] {{
    background-color: {t["card_bg"]} !important;
    border: 1px solid {t["border"]} !important;
    border-radius: 11px !important;
    box-shadow: {t["card_shadow"]} !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary * {{
    color: {t["text"]} !important;
    font-weight: 700 !important;
    font-size: 12px !important;
}}
.gt-bar {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 11px;
    box-shadow: {t["card_shadow"]};
    margin-top: 4px;
    padding: 8px 14px;
    font-size: 11.5px;
    font-weight: 600;
    color: {t["text"]};
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
}}
.gt-nums {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
}}

/* Buying Table */
.buy-wrap {{
    background: {t["card_bg"]};
    border: 1px solid {t["border"]};
    border-radius: 11px;
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
    background: {t["hdr_bg"]};
    color: {t["muted"]};
    font-size: 10.5px;
    font-weight: 800;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 8px 12px;
    text-align: right;
    border-bottom: 1px solid {t["border"]};
    border-right: 1px solid {t["border_soft"]};
}}
table.buy-tbl th:first-child {{ text-align: left; }}
table.buy-tbl th:last-child {{ border-right: none; }}
table.buy-tbl td {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    font-weight: 600;
    padding: 4.5px 12px;
    line-height: 1.3;
    text-align: right;
    border-bottom: 1px solid {t["border_soft"]};
    border-right: 1px solid {t["border_soft"]};
}}
table.buy-tbl td:first-child {{
    font-family: 'Plus Jakarta Sans', sans-serif;
    text-align: left;
    font-weight: 700;
}}
table.buy-tbl td:last-child {{ border-right: none; }}
table.buy-tbl tbody tr:hover td {{
    background: {t["row_hover"]};
}}
table.buy-tbl tr.row-subtotal td {{
    background: {t["sub_bg"]};
    font-weight: 700;
    border-top: 1.5px solid {t["border"]};
    border-bottom: 1.5px solid {t["border"]};
}}
table.buy-tbl tfoot td {{
    background: {t["hdr_bg"]};
    color: {t["text"]};
    font-weight: 800;
    padding: 8px 12px;
    border-top: 1.5px solid {t["border"]};
}}

/* Main-page action buttons (e.g. Save to Sheet) */
.block-container .stButton > button[kind="primary"] {{
    background-color: {t["accent"]} !important;
    color: {t["accent_fg"]} !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 12.5px !important;
    height: 34px !important;
    padding: 0 16px !important;
}}
.block-container .stButton > button[kind="primary"] * {{
    color: {t["accent_fg"]} !important;
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
if "pending_role" not in st.session_state:
    st.session_state.pending_role = None
if "theme" not in st.session_state or st.session_state.theme not in THEMES:
    old_theme = st.session_state.get("theme", "")
    st.session_state.theme = "Obsidian" if old_theme == "Dark" else "Alabaster"
if "view" not in st.session_state or st.session_state.view not in ("M1, M2, H1 & M3", "Buying"):
    st.session_state.view = "M1, M2, H1 & M3"
if "filter_mode" not in st.session_state or st.session_state.filter_mode not in ("Excess", "All", "Shortage"):
    st.session_state.filter_mode = "All"
if "refresh_notice" not in st.session_state:
    st.session_state.refresh_notice = ""
if "last_sync" not in st.session_state:
    st.session_state.last_sync = ""

DIAMOND_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M6 3h12l4 6-10 13L2 9z"/><path d="M2 9h20"/><path d="M12 22 7 9l5-6 5 6-5 13z"/></svg>'
)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(
        f'<div class="sb-brand-row">{DIAMOND_SVG}<span class="sb-brand-text">DIAMOND PORTAL</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<span class="sb-label">Workspace</span>', unsafe_allow_html=True)
    with st.container(key="sb_nav"):
        if st.button(
            "M1, M2, H1 & M3",
            use_container_width=True,
            type="primary" if st.session_state.view == "M1, M2, H1 & M3" else "secondary",
        ):
            st.session_state.view = "M1, M2, H1 & M3"
            st.rerun()

        if st.button(
            "Buying Sheet",
            use_container_width=True,
            type="primary" if st.session_state.view == "Buying" else "secondary",
        ):
            st.session_state.view = "Buying"
            st.rerun()

    st.markdown('<span class="sb-label">Role Access</span>', unsafe_allow_html=True)
    r_c1, r_c2 = st.columns(2, gap="small")
    role_list = list(ROLE_PERMISSIONS.keys())
    for i, r_name in enumerate(role_list):
        target_col = r_c1 if i % 2 == 0 else r_c2
        short_lbl = "Dev" if r_name == "Developer" else r_name
        with target_col:
            if st.button(
                short_lbl,
                key=f"role_{r_name}",
                use_container_width=True,
                type="primary" if st.session_state.role == r_name else "secondary",
            ):
                if r_name == "Guest":
                    st.session_state.role = "Guest"
                    st.session_state.pending_role = None
                    st.rerun()
                elif st.session_state.role != r_name:
                    st.session_state.pending_role = r_name
                    st.rerun()

    if st.session_state.pending_role:
        pr = st.session_state.pending_role
        pin_in = st.text_input(
            f"PIN for {pr}",
            type="password",
            placeholder=f"Enter {pr} PIN",
            label_visibility="collapsed",
        )
        p_c1, p_c2 = st.columns(2, gap="small")
        with p_c1:
            if st.button("Unlock", type="primary", use_container_width=True):
                if pin_in.strip() == ROLE_PERMISSIONS[pr]["pin"]:
                    st.session_state.role = pr
                    st.session_state.pending_role = None
                    st.rerun()
                else:
                    st.error("Wrong PIN")
        with p_c2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.pending_role = None
                st.rerun()

    st.markdown('<span class="sb-label">Palette</span>', unsafe_allow_html=True)
    t_c1, t_c2 = st.columns(2, gap="small")
    for i, t_name in enumerate(THEMES.keys()):
        target_col = t_c1 if i % 2 == 0 else t_c2
        with target_col:
            if st.button(
                t_name,
                key=f"theme_{t_name}",
                use_container_width=True,
                type="primary" if st.session_state.theme == t_name else "secondary",
            ):
                st.session_state.theme = t_name
                st.rerun()

    st.markdown('<span class="sb-label">Data Sync</span>', unsafe_allow_html=True)
    if st.button("↻ Refresh Sheet", use_container_width=True):
        load_requirement_sheet.clear()
        load_buying_sheet.clear()
        ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%I:%M:%S %p")
        st.session_state.last_sync = ist_now
        st.session_state.refresh_notice = f"Synced from Google Sheets at {ist_now}"
        st.rerun()

    if st.session_state.last_sync:
        st.markdown(
            f'<div class="sb-meta">Last synced · {st.session_state.last_sync}</div>',
            unsafe_allow_html=True,
        )

inject_css(st.session_state.theme, st.session_state.filter_mode)

if st.session_state.refresh_notice:
    st.toast(st.session_state.refresh_notice)
    st.session_state.refresh_notice = ""

role = st.session_state.role
perms = ROLE_PERMISSIONS[role]
filter_mode = st.session_state.filter_mode

banner_note = (
    "Positive Sum (Excess)"
    if (st.session_state.view == "M1, M2, H1 & M3" and filter_mode == "Excess")
    else "Negative Sum (Shortage)"
)

# --- TOP HEADER BAR + 3 ROUND DOT FILTER BUTTONS ---
if st.session_state.view == "M1, M2, H1 & M3":
    hdr_col, pod_col = st.columns([3.5, 1.15], vertical_alignment="center")
    with hdr_col:
        st.markdown(
            f'<div class="app-topbar">'
            f'<div class="brand-group">'
            f'{DIAMOND_SVG}'
            f'<span class="brand-name">DIAMOND PORTAL</span>'
            f'<span class="brand-sep">/</span>'
            f'<span class="view-tag">{st.session_state.view}</span>'
            f'<span class="role-chip">{role}</span>'
            f'</div>'
            f'<div class="mode-note">{banner_note} · Primary 6(0)–6.5</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with pod_col:
        with st.container(key="filter_pod"):
            d1, d2, d3 = st.columns(3, gap="small")
            with d1:
                if st.button("✓" if filter_mode == "Excess" else " ", key="btn_excess"):
                    st.session_state.filter_mode = "Excess"
                    st.rerun()
                st.markdown(
                    f'<div class="dot-lbl {"active-ex" if filter_mode == "Excess" else ""}">Excess</div>',
                    unsafe_allow_html=True,
                )
            with d2:
                if st.button("✓" if filter_mode == "All" else " ", key="btn_all"):
                    st.session_state.filter_mode = "All"
                    st.rerun()
                st.markdown(
                    f'<div class="dot-lbl {"active-all" if filter_mode == "All" else ""}">All</div>',
                    unsafe_allow_html=True,
                )
            with d3:
                if st.button("✓" if filter_mode == "Shortage" else " ", key="btn_shortage"):
                    st.session_state.filter_mode = "Shortage"
                    st.rerun()
                st.markdown(
                    f'<div class="dot-lbl {"active-sh" if filter_mode == "Shortage" else ""}">Shortage</div>',
                    unsafe_allow_html=True,
                )
else:
    st.markdown(
        f'<div class="app-topbar">'
        f'<div class="brand-group">'
        f'{DIAMOND_SVG}'
        f'<span class="brand-name">DIAMOND PORTAL</span>'
        f'<span class="brand-sep">/</span>'
        f'<span class="view-tag">Buying Sheet</span>'
        f'<span class="role-chip">{role}</span>'
        f'</div>'
        f'<div class="mode-note">Final Buying · Primary 6(0)–6.5</div>'
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
            hdr_sum_html = f'<span class="q-hdr-metric val-surplus">+{fin_sum:.2f}</span>'
        else:
            fin_sum = sum_negative(sub_df[f"{q}_fin"])
            fin_sum_cls = "val-short" if fin_sum < -0.001 else ""
            urg_cnt = int((sub_df[f"{q}_urg"].fillna("") != "").sum())
            urg_pill = f'<span class="urg-tag">{urg_cnt} URG</span>' if urg_cnt > 0 else ""
            hdr_sum_html = f'<span class="q-hdr-metric {fin_sum_cls}">{fin_sum:.2f}{urg_pill}</span>'

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
                f'<tr><td colspan="5" style="text-align:center;opacity:0.6;padding:10px;font-family:Plus Jakarta Sans,sans-serif;">{empty_msg}</td></tr>'
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
            f'<div class="q-card" style="border-top: 2.5px solid {blk["accent"]};">'
            f'<div class="q-card-hdr">'
            f'<div class="q-title-wrap"><span class="q-dot" style="background:{blk["accent"]};"></span>'
            f'<span class="q-code">{blk["label"]}</span><span class="q-grade">{blk["grade"]}</span></div>'
            f'{hdr_sum_html}</div>'
            f'<div class="q-card-sub"><span>Req <b>{req_sum:.1f}</b></span><span>Stock <b>{(bag_sum + ass_sum):.1f}</b></span></div>'
            f'<div class="q-card-scroll"><table class="compact-tbl"><thead>{thead}</thead><tbody>{"".join(body_rows)}{sub_row}</tbody></table></div>'
            f"</div>"
        )

    return f'<div class="four-block-grid">{"".join(cards)}</div>'


if st.session_state.view == "M1, M2, H1 & M3":
    primary_df = df[df["Tier"] == "Primary"]
    large_df = df[df["Tier"] == "Large"]

    # Slim Executive KPI Strip (All Primary Sieves)
    tot_req = sum(float(primary_df[f"{b['code']}_req"].fillna(0.0).sum()) for b in QUALITY_BLOCKS)
    tot_stk = sum(
        float(primary_df[f"{b['code']}_bag"].fillna(0.0).sum() + primary_df[f"{b['code']}_ass"].fillna(0.0).sum())
        for b in QUALITY_BLOCKS
    )
    tot_urg = sum(int((primary_df[f"{b['code']}_urg"].fillna("") != "").sum()) for b in QUALITY_BLOCKS)
    if filter_mode == "Excess":
        tot_net = sum(sum_positive(primary_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
        net_lbl, net_val, net_cls = "Primary Excess", f"+{tot_net:.2f} ct", "val-surplus"
    else:
        tot_net = sum(sum_negative(primary_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
        net_lbl, net_val, net_cls = "Primary Shortage", f"{tot_net:.2f} ct", "val-short"

    st.markdown(
        f'<div class="kpi-strip">'
        f'<div class="kpi-chip"><span class="kpi-lbl">Primary Req</span><span class="kpi-val">{tot_req:.1f} ct</span></div>'
        f'<div class="kpi-chip"><span class="kpi-lbl">Primary Stock</span><span class="kpi-val">{tot_stk:.1f} ct</span></div>'
        f'<div class="kpi-chip"><span class="kpi-lbl">{net_lbl}</span><span class="kpi-val {net_cls}">{net_val}</span></div>'
        f'<div class="kpi-chip"><span class="kpi-lbl">Urgent Sizes</span><span class="kpi-val {"val-short" if tot_urg > 0 else ""}">{tot_urg}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        build_four_cards_full_html(primary_df, "SUB 6–6.5", mode=filter_mode),
        unsafe_allow_html=True,
    )

    if not large_df.empty:
        if filter_mode == "Excess":
            large_total = sum(sum_positive(large_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
            exp_label = f"Sieves Below 6.5 (7 to 12.5) · {len(large_df)} sizes · Excess +{large_total:.2f} ct"
        else:
            large_total = sum(sum_negative(large_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
            exp_label = f"Sieves Below 6.5 (7 to 12.5) · {len(large_df)} sizes · Shortage {large_total:.2f} ct"

        with st.expander(exp_label, expanded=False):
            st.markdown(
                build_four_cards_full_html(large_df, "SUB 7–12.5", mode=filter_mode),
                unsafe_allow_html=True,
            )

        gt_parts = []
        if filter_mode == "Excess":
            gt_title = "GRAND TOTAL · EXCESS (POSITIVE)"
            for blk in QUALITY_BLOCKS:
                q = blk["code"]
                g_pos = sum_positive(df[f"{q}_fin"])
                gt_parts.append(f'<b>{q}</b> <span class="val-surplus">+{g_pos:.2f}</span>')
        else:
            gt_title = "GRAND TOTAL · SHORTAGE (NEGATIVE)"
            for blk in QUALITY_BLOCKS:
                q = blk["code"]
                g_neg = sum_negative(df[f"{q}_fin"])
                gt_parts.append(f'<b>{q}</b> <span class="val-short">{g_neg:.2f}</span>')

        st.markdown(
            f'<div class="gt-bar">'
            f'<span><b>{gt_title}</b></span>'
            f'<span class="gt-nums">{" &nbsp;·&nbsp; ".join(gt_parts)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if perms["can_bagging"] or perms["can_assort"]:
        st.markdown("---")
        st.markdown(f"**Quick Entry ({role})** — edit allowed columns and save to Google Sheets:")
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
        if st.button("Save to Sheet", type="primary"):
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
            f"<thead><tr><th>SIEVE SIZE</th><th>M1 · VVS/DEF</th><th>M2 · VVS-VS/GH</th><th>H1 · VVS-EF</th><th>M3 · SI/GH</th></tr></thead>"
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
