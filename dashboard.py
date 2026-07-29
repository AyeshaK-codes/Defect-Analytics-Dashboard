import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import StringIO

# =====================================================================
# >>> PASTE YOUR GOOGLE SHEET LINK HERE <<<
# How to get it:
#   1. Open your Google Sheet
#   2. Click "Share" -> "General access" -> "Anyone with the link" (Viewer)
#   3. Copy the normal URL from the address bar, e.g.:
#      https://docs.google.com/spreadsheets/d/1AbCDefGhIjKLmnoPQRstuVWxyz/edit#gid=0
#   4. Paste that FULL url as a string below (no need to modify it yourself,
#      the code converts it to a CSV export link automatically).
# =====================================================================
GOOGLE_SHEET_URL = ""

# If your data is on a specific tab/sheet (not the first one), put its
# gid number here. You can find it in the URL after "gid=". Leave as
# None to just use the first sheet/tab.
SHEET_GID = None

# How often (in seconds) the dashboard checks the sheet for updates.
REFRESH_INTERVAL_SECONDS = 30


def build_csv_export_url(sheet_url: str, gid=None) -> str:
    """Converts a normal Google Sheets edit URL into a CSV export URL."""
    try:
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
    except IndexError:
        raise ValueError(
            "Could not find a valid Sheet ID in GOOGLE_SHEET_URL. "
            "Make sure you pasted the full Google Sheets URL."
        )
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid is not None:
        base += f"&gid={gid}"
    return base


# 1. INITIALIZE APPLICATION ENVIRONMENT
st.set_page_config(
    page_title="Colgate SIT Defect Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-refresh the whole app every REFRESH_INTERVAL_SECONDS so that
# updates made in the Google Sheet show up automatically.
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=REFRESH_INTERVAL_SECONDS * 1000, key="sheet_autorefresh")
except ImportError:
    st.sidebar.warning(
        "Auto-refresh package not installed. Run:\n\n"
        "pip install streamlit-autorefresh\n\n"
        "For now, use the manual refresh button in the sidebar."
    )
    if st.sidebar.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()

# 2. STATE ENGINE CONFIGURATION
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None

def trigger_logout():
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.rerun()

# 3. APPLICATION CORE HYBRID THEME STYLES
scroll_dynamic_css = """
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #070412 !important;
        background-image: radial-gradient(circle at 50% 45%, #2D124D 0%, #070412 70%) !important;
        color: #FFFFFF !important;
        overflow-y: auto !important; 
    }
    
    .stApp { background: transparent !important; }
    [data-testid="stHeader"], footer { display: none !important; visibility: hidden !important; }
    
    [data-testid="stMainBlockContainer"] {
        max-height: none !important;
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        overflow-y: auto !important; 
    }

    [data-testid="stMetricValue"] { 
        font-size: 28px !important; 
        font-weight: bold; 
        color: #FFFFFF !important;
    }

    .login-plain-container {
        max-width: 460px !important; 
        margin: 6% auto 0 auto !important;
        text-align: center;
    }

    div[data-testid="stForm"] {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }

    .custom-input-label {
        display: block !important;
        color: #BDB9D0 !important;
        font-size: 14px !important; 
        font-weight: 500 !important;
        margin-bottom: 6px !important;
        text-align: left;
    }

    div.stButton > button {
        background: linear-gradient(90deg, #7B2CBF 0%, #9D4EDD 100%) !important;
        border: none !important; border-radius: 12px !important; color: #FFFFFF !important;
        padding: 10px 20px !important; font-size: 14px !important; font-weight: 700 !important;
        box-shadow: 0 4px 15px rgba(157, 78, 221, 0.3) !important;
        transition: all 0.2s ease !important;
        height: 44px !important;
    }
    div.stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 20px rgba(157, 78, 221, 0.5) !important;
    }
</style>
"""
st.markdown(scroll_dynamic_css, unsafe_allow_html=True)

def display_colgate_logo():
    st.markdown(
        '<div style="text-align: center;">'
        '<h2 style="color: #E11B22; font-weight: 800; letter-spacing: 1px; margin: 0; display:inline-block;">Colgate</h2>'
        '</div>', 
        unsafe_allow_html=True
    )

# ==========================================
# PHASE A: LANDING SCREEN GATEWAY (AUTHENTICATION)
# ==========================================
if not st.session_state["logged_in"]:
    st.markdown('<div class="login-plain-container">', unsafe_allow_html=True)
    display_colgate_logo()
    st.markdown("<h2 style='text-align: center; margin: 20px 0 25px 0; font-size: 22px; font-weight: 600; color: #FFFFFF;'>SIT Defect Analytics Gateway</h2>", unsafe_allow_html=True)
    
    with st.form(key="unified_credential_form"):
        st.markdown('<label class="custom-input-label">User Identifier / Username</label>', unsafe_allow_html=True)
        user_input = st.text_input("Username", label_visibility="collapsed", placeholder="Enter your ID", key="auth_user")
        
        st.markdown('<label class="custom-input-label">Security Access Key</label>', unsafe_allow_html=True)
        pwd_input = st.text_input("Password", label_visibility="collapsed", type="password", placeholder="Enter password", key="auth_pwd")
        
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
        if st.form_submit_button("Verify Credentials & Enter", use_container_width=True):
            if user_input == "admin" and pwd_input == "admin":
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = "admin"
                st.rerun()
            elif user_input in ["user", "user2"] and pwd_input == user_input:
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = "user"
                st.rerun()
            else:
                st.error("Authentication failed. Please verify your identification attributes.")
            
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PHASE B: PLATFORM SECURED CORE INTERFACE
# ==========================================
else:
    # Top-tier App Branding Header layout
    header_col1, header_col2 = st.columns([8, 2])
    with header_col1:
        st.title("Colgate SIT Defect Analytics Dashboard")
        st.caption(f"Active Session: User: **{st.session_state['user_role'].upper()}** | Live workspace monitoring workspace trends.")
    with header_col2:
        st.write("##")
        if st.button("🚪 Log Out", key="top_navbar_logout_trigger", use_container_width=True):
            trigger_logout()

    st.divider()

    # --- Streamlined One-Pass Processing Engine ---
    # ttl matches REFRESH_INTERVAL_SECONDS so cached data is dropped and
    # re-fetched from Google Sheets on each refresh cycle.
    @st.cache_data(ttl=REFRESH_INTERVAL_SECONDS)
    def process_google_sheet(csv_url):
        try:
            resp = requests.get(csv_url, timeout=15)
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text), header=None)

            header_row_idx = 0
            for idx in range(min(20, len(df))):
                row_values = [str(x).strip().lower() for x in df.iloc[idx].values if pd.notna(x)]
                if any("module" in val or "defect id" in val or "status" in val for val in row_values):
                    header_row_idx = idx
                    break

            df.columns = df.iloc[header_row_idx]
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)

            df = df.fillna("").astype(str)

            new_cols = []
            for i, c in enumerate(df.columns):
                c_str = str(c).strip() if pd.notna(c) and str(c).strip() != "" else f"Column_{i}"
                new_cols.append(f"{c_str}_idx_{i}")
            df.columns = new_cols

            for col in df.columns:
                df[col] = df[col].str.strip()

            col_mapping = {}
            found_id, found_mod, found_prio, found_stat = False, False, False, False

            for col in df.columns:
                c_clean = col.lower().split('_idx_')[0].strip()
                if ("defect id" in c_clean or "defect #" in c_clean) and not found_id:
                    col_mapping[col] = "Defect ID"
                    found_id = True
                elif ("module" in c_clean and "assign" not in c_clean) and not found_mod:
                    col_mapping[col] = "Module"
                    found_mod = True
                elif "priority" in c_clean and not found_prio:
                    col_mapping[col] = "Priority of Defect"
                    found_prio = True
                elif "status" in c_clean and not found_stat:
                    col_mapping[col] = "Status by Colgate"
                    found_stat = True
                elif "description" in c_clean:
                    col_mapping[col] = "Defect Description"
                elif "defect type" in c_clean:
                    col_mapping[col] = "Defect Type"

            df = df.rename(columns=col_mapping)

            if "Module" not in df.columns: df["Module"] = "Unknown"
            if "Priority of Defect" not in df.columns: df["Priority of Defect"] = "Medium"
            if "Status by Colgate" not in df.columns: df["Status by Colgate"] = "Open"
            if "Defect ID" not in df.columns: df["Defect ID"] = df.index.astype(str)

            df = df[df["Defect ID"] != ""]
            df = df[df["Defect ID"].str.lower() != "nan"]
            df = df[df["Module"].str.lower() != "nan"]
            df = df[df["Module"].str.lower() != "module"]

            final_cols = []
            final_counts = {}
            for c in df.columns:
                if c in final_counts:
                    final_counts[c] += 1
                    final_cols.append(f"{c} ({final_counts[c]})")
                else:
                    final_counts[c] = 1
                    final_cols.append(c)
            df.columns = final_cols

            return df, None
        except Exception as e:
            return None, str(e)

    # --- Live Google Sheet connection status ---
    st.write("### Live Data Source: Google Sheet")

    if GOOGLE_SHEET_URL == "PASTE_YOUR_GOOGLE_SHEET_URL_HERE":
        st.warning(
            "⚠️ No Google Sheet connected yet. Open this file and paste your "
            "sheet's URL into the `GOOGLE_SHEET_URL` variable near the top."
        )
        df, error_msg = None, None
    else:
        csv_url = build_csv_export_url(GOOGLE_SHEET_URL, SHEET_GID)
        df, error_msg = process_google_sheet(csv_url)
        st.caption(f"🔄 Auto-refreshing every {REFRESH_INTERVAL_SECONDS} seconds from the connected sheet.")

    if df is None:
        if error_msg:
            st.error("### Live Processing Error")
            st.info(f"**Details:** {error_msg}")
        else:
            st.info("💡 **Awaiting Data Source:** Connect your Google Sheet above to instantly display live metrics.")
    else:
        # --- SIDEBAR FILTERS ---
        st.sidebar.header("Dashboard Filter Panel")

        def get_true_col(base_name, columns):
            for c in columns:
                if c == base_name or c.startswith(f"{base_name} ("):
                    return c
            return None

        mod_col = get_true_col("Module", df.columns) or df.columns[1]
        prio_col = get_true_col("Priority of Defect", df.columns) or df.columns[2]
        status_col = get_true_col("Status by Colgate", df.columns) or df.columns[4]

        all_modules = sorted(list(set(df[mod_col].unique())))
        selected_modules = st.sidebar.multiselect("Select Functional Module(s)", options=all_modules, default=all_modules)

        all_priorities = sorted(list(set(df[prio_col].unique())))
        selected_priorities = st.sidebar.multiselect("Select Priority Level(s)", options=all_priorities, default=all_priorities)

        all_statuses = sorted(list(set(df[status_col].unique())))
        selected_statuses = st.sidebar.multiselect("Select Defect Status", options=all_statuses, default=all_statuses)

        filtered_df = df[
            (df[mod_col].isin(selected_modules)) &
            (df[prio_col].isin(selected_priorities)) &
            (df[status_col].isin(selected_statuses))
        ]

        # --- KPI SCORECARDS ---
        st.write("### Live Analytics Overview")
        st.divider()

        total_defects = len(filtered_df)
        closed_defects = len(filtered_df[filtered_df[status_col].str.lower() == "closed"])
        open_defects = total_defects - closed_defects
        fix_rate = (closed_defects / total_defects * 100) if total_defects > 0 else 0.0

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1: st.metric("Total Logged Defects", f"{total_defects}")
        with m_col2: st.metric("Open Backlog Items", f"{open_defects}", delta=f"{open_defects} Pending", delta_color="inverse" if open_defects > 0 else "normal")
        with m_col3: st.metric("Resolved / Closed Cases", f"{closed_defects}")
        with m_col4: st.metric("SIT Fix Rate Percentage", f"{fix_rate:.1f}%")

        st.write("###")

        # --- CHARTS ---
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("Defect Volume by Functional Module")
            if not filtered_df.empty:
                module_counts = filtered_df[mod_col].value_counts().reset_index()
                module_counts.columns = ["Module", "Defect Count"]
                fig_mod = px.bar(module_counts, x="Module", y="Defect Count", text="Defect Count", color="Module", color_discrete_sequence=px.colors.qualitative.Bold)
                fig_mod.update_layout(showlegend=False, margin=dict(t=15, b=15, l=15, r=15), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mod, use_container_width=True)
            else:
                st.info("No matching module trends meet selections.")

        with chart_col2:
            st.subheader("Defect Distribution by Severity/Priority")
            if not filtered_df.empty:
                priority_counts = filtered_df[prio_col].value_counts().reset_index()
                priority_counts.columns = ["Priority", "Count"]
                fig_prio = px.pie(priority_counts, values="Count", names="Priority", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_prio.update_layout(margin=dict(t=15, b=15, l=15, r=15), paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_prio, use_container_width=True)
            else:
                st.info("No priority metrics match combinations.")

        st.divider()

        # --- DATATABLE WITH INLINE FILTER SEARCH ---
        st.subheader("Filtered Defect Detailed Ledger")

        ideal_cols = ["Defect ID", "Module", "Priority of Defect", "Defect Description", "Status by Colgate", "Defect Type"]
        existing_display_cols = []
        for c in ideal_cols:
            matched = get_true_col(c, filtered_df.columns)
            if matched:
                existing_display_cols.append(matched)

        if not filtered_df.empty:
            search_query = st.text_input("🔍 Search ledger contents directly (type keywords, descriptions, or IDs):", "").strip().lower()

            final_display_df = filtered_df[existing_display_cols]

            if search_query:
                mask = final_display_df.apply(lambda row: row.astype(str).str.lower().str.contains(search_query).any(), axis=1)
                final_display_df = final_display_df[mask]

            st.dataframe(
                final_display_df, 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning("No entries match selections.")