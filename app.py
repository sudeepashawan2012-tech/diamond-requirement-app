from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

SPREADSHEET_ID = "1_FUDeCBMXBabuZjK1gvCMJcfK1_VpKHwKwLc-m1csBc"
REQ_SHEET_NAME = "FINAL REQUIREMENT"
BUYING_SHEET_NAME = "FINAL BUYING"
LOG_SHEET_NAME = "SHORTAGE_LOG"

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
    "Midnight Slate": {
        "bg_app": "#0b1120",
        "card_bg": "#111827",
        "text": "#f8fafc",
        "border": "#334155",
        "hdr_bg": "#020617",
        "hdr_fg": "#f8fafc",
        "sub_bg": "#1e293b",
        "btn_bg": "#1e293b",
        "btn_fg": "#f8fafc",
        "btn_hover_bg": "#334155",
        "btn_hover_fg": "#ffffff",
        "btn_border": "#475569",
        "pri_bg": "#2563eb",
        "pri_fg": "#ffffff",
        "bag_bg": "#052e16",
        "ass_bg": "#172554",
        "urg_bg": "#450a0a",
    },
    "Crisp Daylight": {
        "bg_app": "#eef2f6",
        "card_bg": "#ffffff",
        "text": "#0f172a",
        "border": "#cbd5e1",
        "hdr_bg": "#0f172a",
        "hdr_fg": "#ffffff",
        "sub_bg": "#e2e8f0",
        "btn_bg": "#ffffff",
        "btn_fg": "#0f172a",
        "btn_hover_bg": "#e2e8f0",
        "btn_hover_fg": "#0f172a",
        "btn_border": "#94a3b8",
        "pri_bg": "#1d4ed8",
        "pri_fg": "#ffffff",
        "bag_bg": "#f0fdf4",
        "ass_bg": "#eff6ff",
        "urg_bg": "#fef2f2",
    },
    "Warm Ivory": {
        "bg_app": "#f7f4ee",
        "card_bg": "#ffffff",
        "text": "#1c1917",
        "border": "#d6cfc2",
        "hdr_bg": "#1c1917",
        "hdr_fg": "#ffffff",
        "sub_bg": "#e7e5e4",
        "btn_bg": "#ffffff",
        "btn_fg": "#1c1917",
        "btn_hover_bg": "#e7e5e4",
        "btn_hover_fg": "#1c1917",
        "btn_border": "#a8a29e",
        "pri_bg": "#b45309",
        "pri_fg": "#ffffff",
        "bag_bg": "#f0fdf4",
        "ass_bg": "#eff6ff",
        "urg_bg": "#fef2f2",
    },
}

st.set_page_config(
    page_title="Diamond Portal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed",
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


def inject_css(theme_name: str, screen_mode: str):
    t = THEMES[theme_name]

    if screen_mode == "4-Col (Wide)":
        grid_css = "grid-template-columns: repeat(4, minmax(0, 1fr));"
    elif screen_mode == "2-Col (Tab)":
        grid_css = "grid-template-columns: repeat(2, minmax(0, 1fr));"
    else:
        grid_css = (
            "grid-template-columns: repeat(4, minmax(0, 1fr));"
            "@media (max-width: 1180px) { .four-block-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }"
            "@media (max-width: 600px) { .four-block-grid { grid-template-columns: 1fr; } }"
        )

    st.markdown(
        f"""<style>
[data-testid="stSidebar"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent !important; height: 2.2rem !important; }}
[data-testid="stToolbar"] {{ right: 0.5rem !important; }}

.stApp {{
    background-color: {t["bg_app"]};
    color: {t["text"]};
}}
.block-container {{
    padding-top: 2.5rem !important;
    padding-bottom: 1.2rem !important;
    padding-left: 0.55rem !important;
    padding-right: 0.55rem !important;
    max-width: 100% !important;
}}
div[data-testid="stVerticalBlock"] {{
    gap: 0.28rem !important;
}}
div[data-testid="stMarkdownContainer"] p {{
    margin-bottom: 0 !important;
}}

/* High-contrast button & popover styling for both Dark & Light modes */
.stButton > button,
[data-testid="stPopover"] > div > button,
.stDownloadButton > button {{
    background-color: {t["btn_bg"]} !important;
    color: {t["btn_fg"]} !important;
    border: 1.5px solid {t["btn_border"]} !important;
    font-weight: 800 !important;
    font-size: 12px !important;
    min-height: 34px !important;
    padding: 3px 8px !important;
    border-radius: 6px !important;
}}
.stButton > button *,
[data-testid="stPopover"] > div > button * {{
    color: {t["btn_fg"]} !important;
    font-weight: 800 !important;
}}
.stButton > button:hover,
[data-testid="stPopover"] > div > button:hover {{
    background-color: {t["btn_hover_bg"]} !important;
    color: {t["btn_hover_fg"]} !important;
}}
.stButton > button:hover * {{
    color: {t["btn_hover_fg"]} !important;
}}
.stButton > button[kind="primary"] {{
    background-color: {t["pri_bg"]} !important;
    color: {t["pri_fg"]} !important;
    border-color: {t["pri_bg"]} !important;
}}
.stButton > button[kind="primary"] * {{
    color: {t["pri_fg"]} !important;
}}
.stButton > button:disabled {{
    opacity: 0.55 !important;
}}

/* Expander contrast */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary * {{
    color: {t["text"]} !important;
    font-weight: 800 !important;
}}
[data-testid="stExpander"] {{
    background-color: {t["card_bg"]} !important;
    border: 1.5px solid {t["border"]} !important;
    border-radius: 7px !important;
}}

/* Selectbox & toggle labels */
[data-baseweb="select"] > div {{
    background-color: {t["btn_bg"]} !important;
    color: {t["btn_fg"]} !important;
    border-color: {t["btn_border"]} !important;
    font-weight: 800 !important;
}}
[data-baseweb="select"] span {{
    color: {t["btn_fg"]} !important;
}}
[data-testid="stWidgetLabel"] p,
.stCheckbox label span {{
    color: {t["text"]} !important;
    font-weight: 800 !important;
}}

.portal-banner {{
    background: {t["card_bg"]};
    border: 1.5px solid {t["border"]};
    border-radius: 7px;
    padding: 5px 9px;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
}}
.portal-title {{
    font-size: 15px;
    font-weight: 900;
}}
.role-pill {{
    font-size: 11px;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 999px;
    background: {t["sub_bg"]};
    border: 1px solid {t["border"]};
}}

.four-block-grid {{
    display: grid;
    {grid_css}
    gap: 6px;
    width: 100%;
    align-items: start;
}}

.q-card {{
    background: {t["card_bg"]};
    border: 1.5px solid {t["border"]};
    border-radius: 7px;
    overflow: hidden;
}}
.q-card-hdr {{
    background: {t["hdr_bg"]};
    color: {t["hdr_fg"]};
    padding: 4px 7px;
    font-size: 12px;
    font-weight: 900;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.q-card-sub {{
    font-size: 11px;
    font-weight: 800;
    padding: 2px 7px;
    background: {t["sub_bg"]};
    color: {t["text"]};
    border-bottom: 1px solid {t["border"]};
    display: flex;
    justify-content: space-between;
}}

table.compact-tbl {{
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
}}
table.compact-tbl th {{
    background: {t["sub_bg"]};
    color: {t["text"]};
    font-size: 11px;
    font-weight: 900;
    padding: 2px 4px;
    text-align: right;
    border-bottom: 1.5px solid {t["border"]};
    border-right: 1px solid {t["border"]};
}}
table.compact-tbl th:first-child {{
    text-align: left;
    padding-left: 5px;
}}
table.compact-tbl th:last-child {{
    border-right: none;
}}
table.compact-tbl td {{
    font-size: 13px;
    font-weight: 800;
    padding: 2px 4px;
    line-height: 1.2;
    text-align: right;
    border-bottom: 1px solid {t["border"]};
    border-right: 1px solid {t["border"]};
    white-space: nowrap;
}}
table.compact-tbl td:first-child {{
    text-align: left;
    padding-left: 5px;
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
table.compact-tbl tfoot td {{
    background: {t["hdr_bg"]};
    color: {t["hdr_fg"]};
    font-size: 11px;
    font-weight: 900;
    text-align: left;
    padding: 3px 6px;
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
    font-size: 9px;
    font-weight: 900;
    padding: 0px 3px;
    border-radius: 3px;
    margin-left: 3px;
    vertical-align: middle;
}}

.buy-wrap {{
    background: {t["card_bg"]};
    border: 1.5px solid {t["border"]};
    border-radius: 7px;
    overflow-x: auto;
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
    font-size: 14px;
    font-weight: 800;
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


def load_shortage_log() -> pd.DataFrame:
    try:
        ws = get_gsheet_client().open_by_key(SPREADSHEET_ID).worksheet(LOG_SHEET_NAME)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    rows = ws.get_all_records()
    if not rows:
        return pd.DataFrame()
    df_log = pd.DataFrame(rows)
    for col in ["Required", "Bagging", "Assort", "Final_Req", "Shortage_Carats"]:
        if col in df_log.columns:
            df_log[col] = pd.to_numeric(df_log[col], errors="coerce").fillna(0.0).round(2)
    return df_log


def append_shortage_snapshot(df_after: pd.DataFrame, trigger_label: str):
    now = datetime.now()
    snap_date = now.strftime("%Y-%m-%d")
    snap_time = now.strftime("%H:%M:%S")
    headers = [
        "Snapshot_Date",
        "Snapshot_Time",
        "Quality",
        "Grade",
        "Sieve_Size",
        "Required",
        "Bagging",
        "Assort",
        "Final_Req",
        "Shortage_Carats",
        "Status_Flag",
        "Trigger",
    ]

    log_rows = []
    for _, row in df_after.iterrows():
        sieve = row["Sieve"]
        for blk in QUALITY_BLOCKS:
            q = blk["code"]
            req = float(row[f"{q}_req"] or 0.0)
            bag = float(row[f"{q}_bag"] or 0.0)
            ass = float(row[f"{q}_ass"] or 0.0)
            fin = float(row[f"{q}_fin"] or 0.0)
            urg = str(row[f"{q}_urg"] or "").strip()
            shortage = round(max(0.0, -fin), 2)

            if fin < -0.001 or urg != "":
                log_rows.append(
                    [
                        snap_date,
                        snap_time,
                        q,
                        blk["grade"],
                        sieve,
                        round(req, 2),
                        round(bag, 2),
                        round(ass, 2),
                        round(fin, 2),
                        shortage,
                        urg if urg else "SHORTAGE",
                        trigger_label,
                    ]
                )

    if not log_rows:
        return 0

    sh = get_gsheet_client().open_by_key(SPREADSHEET_ID)
    try:
        ws_log = sh.worksheet(LOG_SHEET_NAME)
        if not ws_log.get("A1:L1"):
            ws_log.append_row(headers, value_input_option="USER_ENTERED")
    except gspread.WorksheetNotFound:
        ws_log = sh.add_worksheet(title=LOG_SHEET_NAME, rows=2000, cols=12)
        ws_log.append_row(headers, value_input_option="USER_ENTERED")

    ws_log.append_rows(log_rows, value_input_option="USER_ENTERED")
    return len(log_rows)


def save_edits_to_sheet(
    edited_df: pd.DataFrame,
    original_df: pd.DataFrame,
    can_bagging: bool,
    can_assort: bool,
    role_name: str,
):
    ws = get_gsheet_client().open_by_key(SPREADSHEET_ID).worksheet(REQ_SHEET_NAME)
    batch_updates = []
    updated_df = original_df.copy()

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
                    updated_df.loc[idx, f"{q}_bag"] = new_b_clean

            if can_assort:
                old_a = original_df.loc[idx, f"{q}_ass"]
                new_a = edited_df.loc[idx, f"{q}_ass"]
                new_a_clean = None if pd.isna(new_a) else round(float(new_a), 2)
                if old_a != new_a_clean:
                    a1 = gspread.utils.rowcol_to_a1(sheet_row, blk["assort_col"])
                    batch_updates.append(
                        {"range": f"{REQ_SHEET_NAME}!{a1}", "values": [["" if new_a_clean is None else new_a_clean]]}
                    )
                    updated_df.loc[idx, f"{q}_ass"] = new_a_clean

            req_val = float(updated_df.loc[idx, f"{q}_req"] or 0.0)
            b_val = float(updated_df.loc[idx, f"{q}_bag"] or 0.0)
            a_val = float(updated_df.loc[idx, f"{q}_ass"] or 0.0)
            updated_df.loc[idx, f"{q}_fin"] = round((b_val + a_val) - req_val, 2)

    if batch_updates:
        ws.batch_update(batch_updates, value_input_option="USER_ENTERED")
        logged_cnt = append_shortage_snapshot(updated_df, f"Edit:{role_name}")
        load_requirement_sheet.clear()
        return len(batch_updates), logged_cnt
    return 0, 0


if "role" not in st.session_state:
    st.session_state.role = "Guest"
if "theme" not in st.session_state:
    st.session_state.theme = "Midnight Slate"
if "screen" not in st.session_state:
    st.session_state.screen = "Auto"
if "view" not in st.session_state:
    st.session_state.view = "4-Block View"
for _blk in QUALITY_BLOCKS:
    k = f"exp_{_blk['code']}"
    if k not in st.session_state:
        st.session_state[k] = False

inject_css(st.session_state.theme, st.session_state.screen)

st.markdown(
    f'<div class="portal-banner"><div><span class="portal-title">💎 DIAMOND PORTAL</span>'
    f'&nbsp;<span class="role-pill">Role: {st.session_state.role}</span></div>'
    f'<div style="font-size:11px;font-weight:700;opacity:0.85;">Fold8 Ultra · Tab M10 HD · Desktop · Sieves 6(0)–6.5</div></div>',
    unsafe_allow_html=True,
)

nav_c1, nav_c2, nav_c3, nav_c4, nav_c5, nav_c6, nav_c7 = st.columns([1.3, 1.2, 1.3, 1.3, 1.2, 1.2, 0.7])
with nav_c1:
    if st.button(
        "📊 4-Block",
        use_container_width=True,
        type="primary" if st.session_state.view == "4-Block View" else "secondary",
    ):
        st.session_state.view = "4-Block View"
        st.rerun()
with nav_c2:
    if st.button(
        "🛒 Buying",
        use_container_width=True,
        type="primary" if st.session_state.view == "Final Buying" else "secondary",
    ):
        st.session_state.view = "Final Buying"
        st.rerun()
with nav_c3:
    if st.button(
        "📋 Shortage Log",
        use_container_width=True,
        type="primary" if st.session_state.view == "Shortage Log" else "secondary",
    ):
        st.session_state.view = "Shortage Log"
        st.rerun()
with nav_c4:
    with st.popover(f"🔐 {st.session_state.role}", use_container_width=True):
        sel_role = st.selectbox(
            "Role",
            list(ROLE_PERMISSIONS.keys()),
            index=list(ROLE_PERMISSIONS.keys()).index(st.session_state.role),
        )
        pin_in = st.text_input("PIN", type="password", placeholder="1111 / 2222 / 9999")
        if st.button("Apply Role", use_container_width=True):
            if sel_role == "Guest":
                st.session_state.role = "Guest"
                st.rerun()
            elif pin_in.strip() == ROLE_PERMISSIONS[sel_role]["pin"]:
                st.session_state.role = sel_role
                st.rerun()
            else:
                st.error("Invalid PIN")
with nav_c5:
    screen_choice = st.selectbox(
        "Screen",
        ["Auto", "2-Col (Tab)", "4-Col (Wide)"],
        index=["Auto", "2-Col (Tab)", "4-Col (Wide)"].index(st.session_state.screen),
        label_visibility="collapsed",
    )
    if screen_choice != st.session_state.screen:
        st.session_state.screen = screen_choice
        st.rerun()
with nav_c6:
    theme_choice = st.selectbox(
        "Theme",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme),
        label_visibility="collapsed",
    )
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()
with nav_c7:
    if st.button("🔄", help="Refresh sheet data", use_container_width=True):
        load_requirement_sheet.clear()
        load_buying_sheet.clear()
        st.rerun()

role = st.session_state.role
perms = ROLE_PERMISSIONS[role]

try:
    df = load_requirement_sheet()
except Exception as e:
    st.error(f"Could not load `{REQ_SHEET_NAME}`: {e}")
    st.stop()


def build_four_cards_html(sub_df: pd.DataFrame, sub_label: str, show_footer: bool = False) -> str:
    cards = []
    for blk in QUALITY_BLOCKS:
        q = blk["code"]
        exp = st.session_state[f"exp_{q}"]
        req_sum = float(sub_df[f"{q}_req"].fillna(0.0).sum())
        bag_sum = float(sub_df[f"{q}_bag"].fillna(0.0).sum())
        ass_sum = float(sub_df[f"{q}_ass"].fillna(0.0).sum())
        fin_sum = float(sub_df[f"{q}_fin"].fillna(0.0).sum())
        short_sum = round(float((-sub_df[f"{q}_fin"].clip(upper=0.0)).sum()), 2)
        urg_cnt = int((sub_df[f"{q}_urg"].fillna("") != "").sum())
        fin_sum_cls = "val-short" if fin_sum < -0.001 else ("val-surplus" if fin_sum > 0.001 else "")

        body_rows = []
        for _, r in sub_df.iterrows():
            sieve = r["Sieve"]
            req = float(r[f"{q}_req"] or 0.0)
            bag_raw = r[f"{q}_bag"]
            ass_raw = r[f"{q}_ass"]
            fin = float(r[f"{q}_fin"] or 0.0)
            urg = str(r[f"{q}_urg"] or "").strip()

            fin_cls = "val-short" if fin < -0.001 else ("val-surplus" if fin > 0.001 else "")
            tr_cls = ' class="row-urgent"' if urg else ""
            urg_badge = f'<span class="urg-tag">{urg}</span>' if urg else ""

            if exp:
                body_rows.append(
                    f"<tr{tr_cls}>"
                    f"<td>{sieve}{urg_badge}</td>"
                    f"<td>{fmt_num(req)}</td>"
                    f'<td class="cell-bag">{fmt_num(bag_raw, show_zero=False)}</td>'
                    f'<td class="cell-ass">{fmt_num(ass_raw, show_zero=False)}</td>'
                    f'<td class="{fin_cls}">{fmt_num(fin)}</td>'
                    f"</tr>"
                )
            else:
                body_rows.append(
                    f"<tr{tr_cls}>"
                    f"<td>{sieve}{urg_badge}</td>"
                    f'<td class="{fin_cls}">{fmt_num(fin)}</td>'
                    f"</tr>"
                )

        if exp:
            thead = "<tr><th>SIEVE</th><th>REQ</th><th>BAG</th><th>ASS</th><th>FINAL</th></tr>"
            sub_row = (
                f'<tr class="row-subtotal">'
                f"<td>{sub_label}</td>"
                f"<td>{req_sum:.2f}</td>"
                f'<td class="cell-bag">{bag_sum:.2f}</td>'
                f'<td class="cell-ass">{ass_sum:.2f}</td>'
                f'<td class="{fin_sum_cls}">{fin_sum:.2f}</td>'
                f"</tr>"
            )
            colspan = 5
        else:
            thead = "<tr><th>SIEVE</th><th>FINAL REQ</th></tr>"
            sub_row = (
                f'<tr class="row-subtotal">'
                f"<td>{sub_label}</td>"
                f'<td class="{fin_sum_cls}">{fin_sum:.2f}</td>'
                f"</tr>"
            )
            colspan = 2

        tfoot_html = ""
        if show_footer:
            tfoot_html = (
                f'<tfoot><tr><td colspan="{colspan}">'
                f"Shortage: {short_sum:.2f} ct · Urgent: {urg_cnt}"
                f"</td></tr></tfoot>"
            )

        urg_pill = f' · <span style="color:#fca5a5;">{urg_cnt} URG</span>' if urg_cnt > 0 else ""
        card_html = (
            f'<div class="q-card">'
            f'<div class="q-card-hdr"><span>{blk["label"]}</span><span>Short {short_sum:.1f}{urg_pill}</span></div>'
            f'<div class="q-card-sub"><span>Req: <b>{req_sum:.1f}</b></span><span>Bag+Ass: <b>{(bag_sum + ass_sum):.1f}</b></span></div>'
            f'<table class="compact-tbl"><thead>{thead}</thead><tbody>{"".join(body_rows)}{sub_row}</tbody>{tfoot_html}</table>'
            f"</div>"
        )
        cards.append(card_html)

    return f'<div class="four-block-grid">{"".join(cards)}</div>'


if st.session_state.view == "4-Block View":
    t_c1, t_c2, t_c3, t_c4, t_c5 = st.columns([1, 1, 1, 1, 1.3])
    for col_box, blk in zip([t_c1, t_c2, t_c3, t_c4], QUALITY_BLOCKS):
        q = blk["code"]
        is_exp = st.session_state[f"exp_{q}"]
        with col_box:
            if st.button(
                f"{'−' if is_exp else '+'} {q} {'Full' if not is_exp else 'Compact'}",
                key=f"btn_exp_{q}",
                use_container_width=True,
            ):
                st.session_state[f"exp_{q}"] = not is_exp
                st.rerun()
    with t_c5:
        only_short_urg = st.toggle("Only Shortage / URGENT", value=False)

    work_df = df.copy()
    if only_short_urg:
        mask = pd.Series(False, index=work_df.index)
        for blk in QUALITY_BLOCKS:
            q = blk["code"]
            mask = (
                mask
                | (work_df[f"{q}_fin"].fillna(0.0) < -0.001)
                | (work_df[f"{q}_urg"].fillna("") != "")
            )
        work_df = work_df[mask].reset_index(drop=True)

    primary_df = work_df[work_df["Tier"] == "Primary"]
    large_df = work_df[work_df["Tier"] == "Large"]

    st.markdown(
        build_four_cards_html(primary_df, "SUB (6–6.5)", show_footer=large_df.empty),
        unsafe_allow_html=True,
    )

    if not large_df.empty:
        large_short_total = sum(
            float((-large_df[f"{b['code']}_fin"].clip(upper=0.0)).sum()) for b in QUALITY_BLOCKS
        )
        with st.expander(
            f"▶ Sieves Below 6.5 (7 to 12.5) · {len(large_df)} sizes · Shortage: {large_short_total:.2f} ct",
            expanded=False,
        ):
            st.markdown(
                build_four_cards_html(large_df, "SUB (7–12.5)", show_footer=False),
                unsafe_allow_html=True,
            )

        gt_parts = []
        for blk in QUALITY_BLOCKS:
            q = blk["code"]
            g_fin = float(work_df[f"{q}_fin"].fillna(0.0).sum())
            g_short = round(float((-work_df[f"{q}_fin"].clip(upper=0.0)).sum()), 2)
            gt_parts.append(f"<b>{q}</b>: Final {g_fin:+.2f} (Buy {g_short:.2f})")
        st.markdown(
            f'<div class="q-card-sub" style="border:1.5px solid;border-radius:6px;margin-top:4px;padding:5px 8px;">'
            f'<span><b>GRAND TOTAL</b></span><span>{" &nbsp;|&nbsp; ".join(gt_parts)}</span></div>',
            unsafe_allow_html=True,
        )

    if perms["can_bagging"] or perms["can_assort"]:
        st.markdown("---")
        st.markdown(f"**Quick Entry ({role})** — edit allowed columns below and click **Save & Log Shortage Snapshot**:")
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
        if st.button("💾 Save & Log Shortage Snapshot", type="primary"):
            cells_updated, log_added = save_edits_to_sheet(
                edited_grid, df, perms["can_bagging"], perms["can_assort"], role
            )
            st.success(f"Updated {cells_updated} sheet cell(s) and logged {log_added} shortage/urgent record(s).")
            st.rerun()


elif st.session_state.view == "Final Buying":
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


elif st.session_state.view == "Shortage Log":
    log_c1, log_c2 = st.columns([2, 1])
    with log_c1:
        st.markdown("**Shortage Log** — date-stamped track record of shortages, `URGENT` flags, `Bagging`, and `Assort` stock.")
    with log_c2:
        if st.button("📸 Capture Live Snapshot Now", use_container_width=True):
            added = append_shortage_snapshot(df, f"Manual:{role}")
            st.success(f"Recorded {added} shortage/urgent row(s) to `{LOG_SHEET_NAME}`.")
            st.rerun()

    df_log = load_shortage_log()
    if df_log.empty:
        st.info(
            f"No historical rows in `{LOG_SHEET_NAME}` yet. Click **📸 Capture Live Snapshot Now** "
            f"(or save edits in **4-Block View**) to record date-stamped shortage history."
        )
    else:
        f1, f2, f3 = st.columns(3)
        with f1:
            q_filter = st.multiselect(
                "Quality",
                options=sorted(df_log["Quality"].dropna().unique().tolist()) if "Quality" in df_log.columns else [],
            )
        with f2:
            sieve_filter = st.multiselect(
                "Sieve Size",
                options=sorted(df_log["Sieve_Size"].astype(str).dropna().unique().tolist()) if "Sieve_Size" in df_log.columns else [],
            )
        with f3:
            flag_filter = st.multiselect(
                "Status Flag",
                options=sorted(df_log["Status_Flag"].astype(str).dropna().unique().tolist()) if "Status_Flag" in df_log.columns else [],
            )

        filtered = df_log.copy()
        if q_filter:
            filtered = filtered[filtered["Quality"].isin(q_filter)]
        if sieve_filter:
            filtered = filtered[filtered["Sieve_Size"].astype(str).isin(sieve_filter)]
        if flag_filter:
            filtered = filtered[filtered["Status_Flag"].astype(str).isin(flag_filter)]

        st.dataframe(filtered, use_container_width=True, hide_index=True, height=420)
