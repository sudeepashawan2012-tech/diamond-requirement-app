import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1_FUDeCBMXBabuZjK1gvCMJcfK1_VpKHwKwLc-m1csBc"
SHEET_NAME = "FINAL REQUIREMENT"

QUALITY_CONFIG = {
    "M1": {"label": "M1 VVS/DEF",   "req_col": 2,  "assort_col": 3,  "bagging_col": 4,  "final_col": 5},
    "M2": {"label": "M2 VVS-VS/GH", "req_col": 6,  "assort_col": 7,  "bagging_col": 8,  "final_col": 9},
    "M3": {"label": "M3 SI/GH",     "req_col": 10, "assort_col": 11, "bagging_col": 12, "final_col": 13},
    "H1": {"label": "H1 VVS-EF",    "req_col": 14, "assort_col": 15, "bagging_col": 16, "final_col": 17},
}

ROLE_PERMISSIONS = {
    "Guest":     {"pin": "",     "can_assort": False, "can_bagging": False},
    "Assort":    {"pin": "1111", "can_assort": True,  "can_bagging": False},
    "Bagging":   {"pin": "2222", "can_assort": False, "can_bagging": True},
    "Developer": {"pin": "9999", "can_assort": True,  "can_bagging": True},
}

st.set_page_config(
    page_title="Diamond Requirement Portal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

def inject_compact_css(theme_mode: str):
    if theme_mode == "Midnight Slate":
        bg_app, card_bg, text_main, border_col, hdr_bg, hdr_fg = (
            "#0f172a", "#1e293b", "#f8fafc", "#475569", "#020617", "#f8fafc"
        )
        assort_bg, bagging_bg, lock_bg, total_bg = "#172554", "#052e16", "#1e293b", "#334155"
    elif theme_mode == "Warm Ivory":
        bg_app, card_bg, text_main, border_col, hdr_bg, hdr_fg = (
            "#faf7f2", "#ffffff", "#1c1917", "#c7bfb3", "#1e293b", "#ffffff"
        )
        assort_bg, bagging_bg, lock_bg, total_bg = "#eff6ff", "#f0fdf4", "#f5f5f4", "#e7e5e4"
    else:  # Crisp Daylight (Default)
        bg_app, card_bg, text_main, border_col, hdr_bg, hdr_fg = (
            "#eef2f6", "#ffffff", "#0f172a", "#cbd5e1", "#0b1a2f", "#ffffff"
        )
        assort_bg, bagging_bg, lock_bg, total_bg = "#eff6ff", "#f0fdf4", "#f8fafc", "#cbd5e1"

    st.markdown(f"""
    <style>
        .stApp {{
            background-color: {bg_app};
            color: {text_main};
        }}
        .block-container {{
            padding-top: 1.1rem !important;
            padding-bottom: 1.2rem !important;
            padding-left: 1.2rem !important;
            padding-right: 1.2rem !important;
            max-width: 1120px;
        }}
        /* Compact KPI strip */
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin: 8px 0 12px 0;
        }}
        @media (max-width: 768px) {{
            .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        .kpi-box {{
            background: {card_bg};
            border: 1.5px solid {border_col};
            border-radius: 8px;
            padding: 7px 10px;
        }}
        .kpi-lbl {{
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            opacity: 0.75;
        }}
        .kpi-val {{
            font-size: 17px;
            font-weight: 900;
            font-variant-numeric: tabular-nums;
        }}
        /* Compact HTML summary table with clear column borders */
        .compact-table-wrap {{
            overflow-x: auto;
            border: 1.5px solid {hdr_bg};
            border-radius: 8px;
            background: {card_bg};
            margin-bottom: 12px;
        }}
        table.req-grid {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            font-weight: 700;
        }}
        table.req-grid th {{
            background: {hdr_bg};
            color: {hdr_fg};
            padding: 8px 10px;
            text-align: right;
            font-size: 13px;
            font-weight: 800;
            border-right: 1px solid rgba(255,255,255,0.22);
        }}
        table.req-grid th:first-child {{ text-align: left; }}
        table.req-grid th:last-child {{ border-right: none; }}
        table.req-grid td {{
            padding: 5px 10px;
            text-align: right;
            font-size: 14px;
            font-weight: 700;
            border-bottom: 1px solid {border_col};
            border-right: 1px solid {border_col};
            font-variant-numeric: tabular-nums;
        }}
        table.req-grid td:last-child {{ border-right: none; }}
        table.req-grid td:first-child {{
            text-align: left;
            font-weight: 800;
            background: {lock_bg};
            white-space: nowrap;
        }}
        table.req-grid td.col-assort {{ background: {assort_bg}; }}
        table.req-grid td.col-bagging {{ background: {bagging_bg}; }}
        table.req-grid tfoot td {{
            background: {total_bg};
            font-weight: 900;
            border-top: 2px solid {hdr_bg};
            padding: 7px 10px;
        }}
        .pos-req {{ color: #dc2626; font-weight: 900; }}
        .neg-req {{ color: #16a34a; font-weight: 900; }}
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def get_gsheet_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    return gspread.authorize(creds)

@st.cache_data(ttl=120, show_spinner=False)
def load_requirement_data() -> pd.DataFrame:
    client = get_gsheet_client()
    ws = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    # Rows 4 to 33 (30 sieve rows), Columns A to R
    raw = ws.get("A4:R33")

    def num_or_zero(row, idx):
        if idx >= len(row) or row[idx] in ("", None):
            return 0.0
        try:
            return round(float(str(row[idx]).replace(",", "").strip()), 2)
        except ValueError:
            return 0.0

    def val_or_none(row, idx):
        if idx >= len(row) or row[idx] in ("", None):
            return None
        try:
            return round(float(str(row[idx]).replace(",", "").strip()), 2)
        except ValueError:
            return None

    records = []
    for i, r in enumerate(raw):
        sieve = str(r[0]).strip() if len(r) > 0 and r[0] is not None else ""
        if not sieve:
            continue
        rec = {"_sheet_row": i + 4, "Sieve": sieve}
        for q, cfg in QUALITY_CONFIG.items():
            rec[f"{q}_req"] = num_or_zero(r, cfg["req_col"] - 1)
            rec[f"{q}_assort"] = val_or_none(r, cfg["assort_col"] - 1)
            rec[f"{q}_bagging"] = val_or_none(r, cfg["bagging_col"] - 1)
        records.append(rec)

    return pd.DataFrame(records)

def write_quality_edits(q_code: str, edited_df: pd.DataFrame, original_df: pd.DataFrame, can_assort: bool, can_bagging: bool):
    cfg = QUALITY_CONFIG[q_code]
    client = get_gsheet_client()
    ws = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

    batch_updates = []
    for idx in range(len(edited_df)):
        sheet_row = int(original_df.loc[idx, "_sheet_row"])
        if can_assort:
            old_a = original_df.loc[idx, f"{q_code}_assort"]
            new_a = edited_df.loc[idx, f"{q_code}_assort"]
            new_a_clean = None if pd.isna(new_a) else round(float(new_a), 2)
            if old_a != new_a_clean:
                col_letter = gspread.utils.rowcol_to_a1(sheet_row, cfg["assort_col"])
                batch_updates.append({"range": f"{SHEET_NAME}!{col_letter}", "values": [["" if new_a_clean is None else new_a_clean]]})

        if can_bagging:
            old_b = original_df.loc[idx, f"{q_code}_bagging"]
            new_b = edited_df.loc[idx, f"{q_code}_bagging"]
            new_b_clean = None if pd.isna(new_b) else round(float(new_b), 2)
            if old_b != new_b_clean:
                col_letter = gspread.utils.rowcol_to_a1(sheet_row, cfg["bagging_col"])
                batch_updates.append({"range": f"{SHEET_NAME}!{col_letter}", "values": [["" if new_b_clean is None else new_b_clean]]})

    if batch_updates:
        ws.batch_update(batch_updates, value_input_option="USER_ENTERED")
        load_requirement_data.clear()
    return len(batch_updates)

# Session state defaults
if "role" not in st.session_state:
    st.session_state.role = "Guest"
if "theme" not in st.session_state:
    st.session_state.theme = "Crisp Daylight"
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "M1"

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 💎 DIAMOND REQ")
    st.session_state.theme = st.selectbox(
        "Theme",
        ["Crisp Daylight", "Midnight Slate", "Warm Ivory"],
        index=["Crisp Daylight", "Midnight Slate", "Warm Ivory"].index(st.session_state.theme),
    )

    st.markdown("---")
    st.markdown("**User Role**")
    selected_role = st.selectbox(
        "Select Role",
        list(ROLE_PERMISSIONS.keys()),
        index=list(ROLE_PERMISSIONS.keys()).index(st.session_state.role),
        label_visibility="collapsed",
    )
    if selected_role != "Guest":
        entered_pin = st.text_input("PIN", type="password", placeholder="Enter PIN")
        if st.button("Unlock Role", use_container_width=True):
            if entered_pin.strip() == ROLE_PERMISSIONS[selected_role]["pin"]:
                st.session_state.role = selected_role
                st.success(f"Active: {selected_role}")
            else:
                st.error("Invalid PIN")
    else:
        st.session_state.role = "Guest"

    st.markdown("---")
    st.markdown("**Quality Views**")
    for q_key, q_info in QUALITY_CONFIG.items():
        if st.button(q_info["label"], key=f"nav_{q_key}", use_container_width=True,
                     type="primary" if st.session_state.active_tab == q_key else "secondary"):
            st.session_state.active_tab = q_key
            st.rerun()

    st.button("Final Buying (Soon)", disabled=True, use_container_width=True)

    st.markdown("---")
    if st.button("🔄 Refresh Sheet", use_container_width=True):
        load_requirement_data.clear()
        st.rerun()

inject_compact_css(st.session_state.theme)

role = st.session_state.role
perms = ROLE_PERMISSIONS[role]
q = st.session_state.active_tab
q_cfg = QUALITY_CONFIG[q]

try:
    df = load_requirement_data()
except Exception as e:
    st.error(f"Could not load Google Sheet data: {e}")
    st.info("Ensure your Streamlit secrets (`gcp_service_account`) are configured and the sheet is shared with the service account email.")
    st.stop()

# Compute live final requirement = REQ - ASSORT - BAGGING
req_s = df[f"{q}_req"].fillna(0.0)
assort_s = df[f"{q}_assort"].fillna(0.0)
bagging_s = df[f"{q}_bagging"].fillna(0.0)
final_s = (req_s - assort_s - bagging_s).round(2)

st.markdown(f"### **{q_cfg['label']}** &nbsp;|&nbsp; Role: **{role}**")

st.markdown(f"""
<div class="kpi-row">
    <div class="kpi-box"><div class="kpi-lbl">Required</div><div class="kpi-val">{req_s.sum():.2f}</div></div>
    <div class="kpi-box"><div class="kpi-lbl">Assort ({q})</div><div class="kpi-val">{assort_s.sum():.2f}</div></div>
    <div class="kpi-box"><div class="kpi-lbl">Bagging ({q})</div><div class="kpi-val">{bagging_s.sum():.2f}</div></div>
    <div class="kpi-box"><div class="kpi-lbl">Final Req ({q})</div><div class="kpi-val">{final_s.sum():.2f}</div></div>
</div>
""", unsafe_allow_html=True)

# Compact high-contrast column-separated view
rows_html = []
for i, r in df.iterrows():
    r_val = float(req_s.iloc[i])
    a_val = float(assort_s.iloc[i])
    b_val = float(bagging_s.iloc[i])
    f_val = float(final_s.iloc[i])
    f_cls = "pos-req" if f_val > 0.001 else ("neg-req" if f_val < -0.001 else "")
    rows_html.append(
        f"<tr>"
        f"<td>{r['Sieve']}</td>"
        f"<td>{r_val:.2f}</td>"
        f"<td class='col-assort'>{'' if pd.isna(r[f'{q}_assort']) else f'{a_val:.2f}'}</td>"
        f"<td class='col-bagging'>{'' if pd.isna(r[f'{q}_bagging']) else f'{b_val:.2f}'}</td>"
        f"<td class='{f_cls}'>{f_val:.2f}</td>"
        f"</tr>"
    )

st.markdown(f"""
<div class="compact-table-wrap">
  <table class="req-grid">
    <thead>
      <tr>
        <th>SIEVE</th>
        <th>REQ (LOCKED)</th>
        <th>ASSORT ({q})</th>
        <th>BAGGING ({q})</th>
        <th>FINAL REQ ({q})</th>
      </tr>
    </thead>
    <tbody>{''.join(rows_html)}</tbody>
    <tfoot>
      <tr>
        <td>TOTAL</td>
        <td>{req_s.sum():.2f}</td>
        <td>{assort_s.sum():.2f}</td>
        <td>{bagging_s.sum():.2f}</td>
        <td>{final_s.sum():.2f}</td>
      </tr>
    </tfoot>
  </table>
</div>
""", unsafe_allow_html=True)

# Editable grid for authorized roles
if perms["can_assort"] or perms["can_bagging"]:
    st.markdown(f"**Quick Entry ({role})** — edit allowed columns below, then click **Save to Sheet**:")
    edit_cols = ["Sieve", f"{q}_req"]
    col_config = {
        "Sieve": st.column_config.TextColumn("Sieve", disabled=True),
        f"{q}_req": st.column_config.NumberColumn("Req (Locked)", disabled=True, format="%.2f"),
    }
    if perms["can_assort"]:
        edit_cols.append(f"{q}_assort")
        col_config[f"{q}_assort"] = st.column_config.NumberColumn(f"Assort ({q})", disabled=False, format="%.2f")
    if perms["can_bagging"]:
        edit_cols.append(f"{q}_bagging")
        col_config[f"{q}_bagging"] = st.column_config.NumberColumn(f"Bagging ({q})", disabled=False, format="%.2f")

    edited_df = st.data_editor(
        df[edit_cols],
        hide_index=True,
        use_container_width=True,
        height=380,
        column_config=col_config,
        key=f"editor_{q}_{role}",
    )

    if st.button("💾 Save to Sheet", type="primary"):
        full_edited = df.copy()
        for c in edit_cols:
            if c != "Sieve":
                full_edited[c] = edited_df[c]
        count = write_quality_edits(q, full_edited, df, perms["can_assort"], perms["can_bagging"])
        st.success(f"Updated {count} cell(s) in {SHEET_NAME}.")
        st.rerun()
else:
    st.caption("Guest mode is view-only. Unlock **Assort**, **Bagging**, or **Developer** from the sidebar to enter values.")
