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
        "bg_app": "#eef2f6",
        "card_bg": "#ffffff",
        "text": "#0f172a",
        "muted": "#475569",
        "border": "#94a3b8",
        "hdr_bg": "#0f172a",
        "hdr_fg": "#ffffff",
        "sub_bg": "#e2e8f0",
        "btn_bg": "#ffffff",
        "btn_fg": "#0f172a",
        "btn_hover_bg": "#e2e8f0",
        "btn_hover_fg": "#0f172a",
        "btn_border": "#64748b",
        "pri_bg": "#1d4ed8",
        "pri_fg": "#ffffff",
        "bag_bg": "#f0fdf4",
        "ass_bg": "#eff6ff",
        "urg_bg": "#fef2f2",
        "input_bg": "#ffffff",
        "input_fg": "#0f172a",
    },
    "Dark": {
        "bg_app": "#0b1120",
        "card_bg": "#111827",
        "text": "#f8fafc",
        "muted": "#cbd5e1",
        "border": "#475569",
        "hdr_bg": "#020617",
        "hdr_fg": "#f8fafc",
        "sub_bg": "#1e293b",
        "btn_bg": "#1e293b",
        "btn_fg": "#f8fafc",
        "btn_hover_bg": "#334155",
        "btn_hover_fg": "#ffffff",
        "btn_border": "#94a3b8",
        "pri_bg": "#2563eb",
        "pri_fg": "#ffffff",
        "bag_bg": "#052e16",
        "ass_bg": "#172554",
        "urg_bg": "#450a0a",
        "input_bg": "#1e293b",
        "input_fg": "#f8fafc",
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
    padding-top: 2.9rem !important;
    padding-bottom: 1.2rem !important;
    padding-left: 0.6rem !important;
    padding-right: 0.6rem !important;
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}}

/* Sidebar expanded vs collapsed — eliminates blank left gap on collapse */
section[data-testid="stSidebar"] {{
    background-color: {t["card_bg"]} !important;
    color: {t["text"]} !important;
}}
section[data-testid="stSidebar"][aria-expanded="true"] {{
    min-width: 245px !important;
    max-width: 265px !important;
    border-right: 1.5px solid {t["border"]} !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"] {{
    min-width: 0px !important;
    width: 0px !important;
    max-width: 0px !important;
    border-right: none !important;
    overflow: hidden !important;
}}

/* Bigger, high-contrast sidebar expand & collapse arrow buttons */
[data-testid="stExpandSidebarButton"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"] {{
    opacity: 1 !important;
    visibility: visible !important;
    z-index: 9999 !important;
}}
[data-testid="stExpandSidebarButton"] button,
[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button {{
    background-color: {t["pri_bg"]} !important;
    color: {t["pri_fg"]} !important;
    border: 2px solid {t["pri_fg"]} !important;
    border-radius: 8px !important;
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    min-height: 38px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35) !important;
    opacity: 1 !important;
}}
[data-testid="stExpandSidebarButton"] button:hover,
[data-testid="collapsedControl"] button:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover {{
    filter: brightness(1.15) !important;
}}
[data-testid="stExpandSidebarButton"] button svg,
[data-testid="collapsedControl"] button svg,
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg {{
    width: 22px !important;
    height: 22px !important;
    fill: {t["pri_fg"]} !important;
    stroke: {t["pri_fg"]} !important;
    color: {t["pri_fg"]} !important;
}}
[data-testid="stExpandSidebarButton"] button span,
[data-testid="collapsedControl"] button span,
[data-testid="stSidebarCollapsedControl"] button span,
[data-testid="stSidebarCollapseButton"] button span {{
    font-size: 24px !important;
    font-weight: 900 !important;
    color: {t["pri_fg"]} !important;
    line-height: 1 !important;
}}

/* Clean sidebar spacing and typography */
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0.75rem !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    padding: 0.5rem 0.9rem 1.2rem 0.9rem !important;
}}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
    gap: 0.65rem !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label p {{
    color: {t["text"]} !important;
    line-height: 1.4 !important;
    margin: 0 !important;
    overflow: visible !important;
}}
[data-testid="stSidebar"] hr {{
    margin: 10px 0 !important;
    border-color: {t["border"]} !important;
}}
.sb-brand {{
    font-size: 16px;
    font-weight: 900;
    letter-spacing: 0.4px;
    color: {t["text"]};
    padding-bottom: 4px;
    margin-bottom: 4px;
}}
.sb-section-title {{
    font-size: 11px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: {t["muted"]};
    margin-top: 4px;
    margin-bottom: 2px;
    display: block;
}}

.block-container div[data-testid="stVerticalBlock"] {{
    gap: 0.3rem !important;
}}
.block-container div[data-testid="stMarkdownContainer"] {{
    width: 100% !important;
    max-width: 100% !important;
}}
.block-container div[data-testid="stMarkdownContainer"] p {{
    margin-bottom: 0 !important;
}}

/* Buttons */
.stButton > button,
.stDownloadButton > button {{
    background-color: {t["btn_bg"]} !important;
    color: {t["btn_fg"]} !important;
    border: 1.5px solid {t["btn_border"]} !important;
    font-weight: 800 !important;
    font-size: 12.5px !important;
    min-height: 38px !important;
    padding: 5px 10px !important;
    border-radius: 7px !important;
    white-space: nowrap !important;
}}
.stButton > button *,
.stButton > button p,
.stButton > button span,
.stButton > button div {{
    color: {t["btn_fg"]} !important;
    font-weight: 800 !important;
}}
.stButton > button:hover {{
    background-color: {t["btn_hover_bg"]} !important;
    color: {t["btn_hover_fg"]} !important;
}}
.stButton > button:hover *,
.stButton > button:hover p,
.stButton > button:hover span {{
    color: {t["btn_hover_fg"]} !important;
}}
.stButton > button[kind="primary"] {{
    background-color: {t["pri_bg"]} !important;
    color: {t["pri_fg"]} !important;
    border-color: {t["pri_bg"]} !important;
}}
.stButton > button[kind="primary"] *,
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span {{
    color: {t["pri_fg"]} !important;
}}

/* Inputs & Selectboxes in both themes */
[data-baseweb="select"] > div {{
    background-color: {t["input_bg"]} !important;
    color: {t["input_fg"]} !important;
    border-color: {t["btn_border"]} !important;
    font-weight: 800 !important;
    min-height: 38px !important;
}}
[data-baseweb="select"] span,
[data-baseweb="select"] svg {{
    color: {t["input_fg"]} !important;
    fill: {t["input_fg"]} !important;
}}
[data-testid="stTextInput"] input {{
    background-color: {t["input_bg"]} !important;
    color: {t["input_fg"]} !important;
    border: 1.5px solid {t["btn_border"]} !important;
    font-weight: 700 !important;
}}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary * {{
    color: {t["text"]} !important;
    font-weight: 900 !important;
}}
[data-testid="stExpander"] {{
    background-color: {t["card_bg"]} !important;
    border: 1.5px solid {t["border"]} !important;
    border-radius: 7px !important;
}}

.portal-banner {{
    background: {t["card_bg"]};
    border: 1.5px solid {t["border"]};
    border-radius: 7px;
    padding: 6px 12px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    width: 100%;
    box-sizing: border-box;
}}
.portal-title {{
    font-size: 15px;
    font-weight: 900;
}}
.role-pill {{
    font-size: 11px;
    font-weight: 900;
    padding: 2px 8px;
    border-radius: 999px;
    background: {t["sub_bg"]};
    border: 1px solid {t["border"]};
}}

/* Automatic layout adaptation by screen width and aspect ratio */
.four-block-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 6px;
    width: 100%;
    max-width: 100%;
    align-items: start;
    box-sizing: border-box;
}}
@media (max-aspect-ratio: 5/4) and (max-width: 1200px) {{
    .four-block-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}
@media (max-width: 620px), (max-aspect-ratio: 3/4) {{
    .four-block-grid {{
        grid-template-columns: minmax(0, 1fr);
    }}
}}

.q-card {{
    background: {t["card_bg"]};
    border: 1.5px solid {t["border"]};
    border-radius: 6px;
    min-width: 0;
    width: 100%;
    overflow-x: auto;
    box-sizing: border-box;
}}
.q-card-hdr {{
    background: {t["hdr_bg"]};
    color: {t["hdr_fg"]};
    padding: 4px 6px;
    font-size: 11.5px;
    font-weight: 900;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 4px;
}}
.q-card-sub {{
    font-size: 10.5px;
    font-weight: 800;
    padding: 2px 6px;
    background: {t["sub_bg"]};
    color: {t["text"]};
    border-bottom: 1.5px solid {t["border"]};
    display: flex;
    justify-content: space-between;
    gap: 4px;
}}

table.compact-tbl {{
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
}}
table.compact-tbl th {{
    background: {t["sub_bg"]};
    color: {t["text"]};
    font-size: 10px;
    font-weight: 900;
    padding: 2px 2.5px;
    text-align: right;
    border-bottom: 1.5px solid {t["border"]};
    border-right: 1px solid {t["border"]};
}}
table.compact-tbl th:first-child {{
    text-align: left;
    padding-left: 4px;
}}
table.compact-tbl th:last-child {{
    border-right: none;
}}
table.compact-tbl td {{
    font-size: 11.5px;
    font-weight: 900;
    padding: 2px 2.5px;
    line-height: 1.2;
    text-align: right;
    border-bottom: 1px solid {t["border"]};
    border-right: 1px solid {t["border"]};
    white-space: nowrap;
}}
table.compact-tbl td:first-child {{
    text-align: left;
    padding-left: 4px;
    font-weight: 900;
}}
table.compact-tbl td:last-child {{
    border-right: none;
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
    border-top: 1.5px solid {t["hdr_bg"]};
    border-bottom: 1.5px solid {t["hdr_bg"]};
}}
.val-short {{
    color: #ef4444 !important;
    font-weight: 900 !important;
}}
.val-surplus {{
    color: #22c55e !important;
    font-weight: 900 !important;
}}
.urg-tag {{
    display: inline-block;
    background: #dc2626;
    color: #ffffff;
    font-size: 8.5px;
    font-weight: 900;
    padding: 0px 2.5px;
    border-radius: 3px;
    margin-left: 2px;
    vertical-align: middle;
}}

.buy-wrap {{
    background: {t["card_bg"]};
    border: 1.5px solid {t["border"]};
    border-radius: 7px;
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
    color: {t["hdr_fg"]};
    font-size: 12px;
    font-weight: 900;
    padding: 4px 8px;
    text-align: right;
    border-right: 1px solid rgba(255,255,255,0.2);
}}
table.buy-tbl th:first-child {{ text-align: left; }}
table.buy-tbl th:last-child {{ border-right: none; }}
table.buy-tbl td {{
    font-size: 13.5px;
    font-weight: 900;
    padding: 2px 8px;
    line-height: 1.25;
    text-align: right;
    border-bottom: 1px solid {t["border"]};
    border-right: 1px solid {t["border"]};
}}
table.buy-tbl td:first-child {{
    text-align: left;
    font-weight: 900;
}}
table.buy-tbl td:last-child {{ border-right: none; }}
table.buy-tbl tr.row-subtotal td {{
    background: {t["sub_bg"]};
    font-weight: 900;
    border-top: 1.5px solid {t["hdr_bg"]};
    border-bottom: 1.5px solid {t["hdr_bg"]};
}}
table.buy-tbl tfoot td {{
    background: {t["hdr_bg"]};
    color: {t["hdr_fg"]};
    font-weight: 900;
    padding: 4px 8px;
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
if "filter_mode" not in st.session_state or st.session_state.filter_mode not in ("All", "Shortage", "Excess"):
    st.session_state.filter_mode = "All"
if "refresh_notice" not in st.session_state:
    st.session_state.refresh_notice = ""

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="sb-brand">💎 DIAMOND REQ</div>', unsafe_allow_html=True)
    st.markdown('<span class="sb-section-title">Views</span>', unsafe_allow_html=True)

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
    st.markdown('<span class="sb-section-title">Role Selector</span>', unsafe_allow_html=True)
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
        pin_in = st.text_input("PIN", type="password", placeholder="Enter PIN")
        if st.button("🔓 Unlock Role", use_container_width=True):
            if pin_in.strip() == ROLE_PERMISSIONS[sel_role]["pin"]:
                st.session_state.role = sel_role
                st.success(f"Active: {sel_role}")
                st.rerun()
            else:
                st.error("Invalid PIN")

    st.markdown("---")
    st.markdown('<span class="sb-section-title">Appearance</span>', unsafe_allow_html=True)
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
    st.markdown('<span class="sb-section-title">Data Sync</span>', unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", use_container_width=True):
        load_requirement_sheet.clear()
        load_buying_sheet.clear()
        ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%I:%M:%S %p")
        st.session_state.refresh_notice = f"Data refreshed from Google Sheets at {ist_now}"
        st.rerun()

    if st.session_state.refresh_notice:
        st.success(f"✅ {st.session_state.refresh_notice}")

inject_css(st.session_state.theme)

if st.session_state.refresh_notice:
    st.toast(f"✅ {st.session_state.refresh_notice}", icon="🔄")
    st.session_state.refresh_notice = ""

role = st.session_state.role
perms = ROLE_PERMISSIONS[role]
filter_mode = st.session_state.filter_mode

banner_note = (
    "Final Req Sum = Positive Only (Excess)"
    if (st.session_state.view == "M1, M2, H1 & M3" and filter_mode == "Excess")
    else "Final Req Sum = Negative Only"
)

st.markdown(
    f'<div class="portal-banner"><div><span class="portal-title">💎 {st.session_state.view}</span>'
    f'&nbsp;<span class="role-pill">Role: {role}</span></div>'
    f'<div style="font-size:11px;font-weight:800;opacity:0.85;">{banner_note} · Primary Sieves 6(0)–6.5</div></div>',
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

        # Filter rows for this quality block based on mode
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
            hdr_sum_html = f'<span style="color:#4ade80;">Pos Final +{fin_sum:.2f}</span>'
        else:
            fin_sum = sum_negative(sub_df[f"{q}_fin"])
            fin_sum_cls = "val-short" if fin_sum < -0.001 else ""
            urg_cnt = int((sub_df[f"{q}_urg"].fillna("") != "").sum())
            urg_pill = f' · <span style="color:#fca5a5;">{urg_cnt} URG</span>' if urg_cnt > 0 else ""
            hdr_sum_html = f'<span>Neg Final {fin_sum:.2f}{urg_pill}</span>'

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
                f'<tr><td colspan="5" style="text-align:center;opacity:0.65;">{empty_msg}</td></tr>'
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
            f'<div class="q-card">'
            f'<div class="q-card-hdr"><span>{blk["label"]}</span>{hdr_sum_html}</div>'
            f'<div class="q-card-sub"><span>Req: <b>{req_sum:.1f}</b></span><span>Bag+Ass: <b>{(bag_sum + ass_sum):.1f}</b></span></div>'
            f'<table class="compact-tbl"><thead>{thead}</thead><tbody>{"".join(body_rows)}{sub_row}</tbody></table>'
            f"</div>"
        )

    return f'<div class="four-block-grid">{"".join(cards)}</div>'


if st.session_state.view == "M1, M2, H1 & M3":
    # Two-sided filter switch: Shortage <-> All <-> Excess (clearly visible in Light & Dark modes)
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        if st.button(
            "🔴 Shortage / URG",
            use_container_width=True,
            type="primary" if filter_mode == "Shortage" else "secondary",
        ):
            st.session_state.filter_mode = "Shortage"
            st.rerun()
    with f_col2:
        if st.button(
            "📋 All Sizes",
            use_container_width=True,
            type="primary" if filter_mode == "All" else "secondary",
        ):
            st.session_state.filter_mode = "All"
            st.rerun()
    with f_col3:
        if st.button(
            "🟢 Excess Only",
            use_container_width=True,
            type="primary" if filter_mode == "Excess" else "secondary",
        ):
            st.session_state.filter_mode = "Excess"
            st.rerun()

    primary_df = df[df["Tier"] == "Primary"]
    large_df = df[df["Tier"] == "Large"]

    st.markdown(
        build_four_cards_full_html(primary_df, "SUB (6–6.5)", mode=filter_mode),
        unsafe_allow_html=True,
    )

    if not large_df.empty:
        if filter_mode == "Excess":
            large_total = sum(sum_positive(large_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
            exp_label = f"▶ Sieves Below 6.5 (7 to 12.5) · {len(large_df)} sizes · Pos Final: +{large_total:.2f} ct"
        else:
            large_total = sum(sum_negative(large_df[f"{b['code']}_fin"]) for b in QUALITY_BLOCKS)
            exp_label = f"▶ Sieves Below 6.5 (7 to 12.5) · {len(large_df)} sizes · Neg Final: {large_total:.2f} ct"

        with st.expander(exp_label, expanded=False):
            st.markdown(
                build_four_cards_full_html(large_df, "SUB (7–12.5)", mode=filter_mode),
                unsafe_allow_html=True,
            )

        gt_parts = []
        if filter_mode == "Excess":
            gt_title = "GRAND TOTAL (POSITIVE / EXCESS SUM)"
            for blk in QUALITY_BLOCKS:
                q = blk["code"]
                g_pos = sum_positive(df[f"{q}_fin"])
                gt_parts.append(f'<b>{q}</b>: Pos Final <span class="val-surplus">+{g_pos:.2f}</span>')
        else:
            gt_title = "GRAND TOTAL (NEGATIVE SUM)"
            for blk in QUALITY_BLOCKS:
                q = blk["code"]
                g_neg = sum_negative(df[f"{q}_fin"])
                gt_parts.append(f'<b>{q}</b>: Neg Final <span class="val-short">{g_neg:.2f}</span>')

        st.markdown(
            f'<div class="q-card-sub" style="border:1.5px solid;border-radius:6px;margin-top:4px;padding:5px 8px;">'
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
        with st.expander(f"▶ Sieves Below 6.5 (7 to 12.5) · {len(b_large)} sizes", expanded=False):
            st.markdown(build_buying_html(b_large, "SUBTOTAL (7–12.5)", show_grand_total=False), unsafe_allow_html=True)

        gt_cells = ["<td>GRAND TOTAL</td>"]
        for qc in ["M1", "M2", "H1", "M3"]:
            gt_cells.append(f"<td>{float(df_buy[qc].fillna(0.0).sum()):.2f}</td>")
        st.markdown(
            f'<div class="buy-wrap" style="margin-top:4px;"><table class="buy-tbl"><tfoot><tr>{"".join(gt_cells)}</tr></tfoot></table></div>',
            unsafe_allow_html=True,
        )
