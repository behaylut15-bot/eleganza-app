import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
import gspread
import json
import base64
from google.oauth2 import service_account
from fpdf import FPDF
from kenat import Kenat
import os
import urllib.request

st.set_page_config(page_title="Eleganza Merchandising ERP", layout="wide", initial_sidebar_state="expanded")

# --- CONSTANTS & HEADERS ---
_REQ_HDRS = [
    "Request_ID", "Submitted_Date", "Submitted_By", "Supplier_Preference",
    "Item_Code", "Item_Name", "Measure", "Requested_Qty", "Est_Unit_Cost", "Status", "Notes"
]

# --- AUTO-DOWNLOAD FONTS ---
try:
    if not os.path.exists('DejaVuSans.ttf'):
        urllib.request.urlretrieve("https://unpkg.com/dejavu-fonts-ttf@2.37/ttf/DejaVuSans.ttf", "DejaVuSans.ttf")
    if not os.path.exists('DejaVuSans-Bold.ttf'):
        urllib.request.urlretrieve("https://unpkg.com/dejavu-fonts-ttf@2.37/ttf/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")
    font_ready = True
except Exception:
    font_ready = False

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .golden-title {
        font-family: 'Arial', sans-serif; font-size: clamp(38px, 7vw, 85px) !important; 
        font-weight: 900 !important; color: #D4AF37 !important; text-shadow: 2px 2px 6px rgba(0,0,0,0.8);
        text-align: center; margin-top: 0px; margin-bottom: 0px; line-height: 1.1;
        letter-spacing: 4px;
    }
    .sub-title {
        color: #A0A0A0; font-size: clamp(13px, 1.8vw, 18px); text-align: center; letter-spacing: 2px;
        margin-top: 8px; margin-bottom: 25px; font-weight: bold;
    }
    .stMetric { 
        background: linear-gradient(135deg, #1f3864 0%, #111111 100%); 
        padding: 15px; border-radius: 10px; color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); border-left: 5px solid #D4AF37;
    }
    .stMetric label { color: #E0E0E0 !important; font-size: 14px; font-weight: 600; }
    .stMetric [data-testid="stMetricValue"] { color: #FFFFFF !important; font-size: 22px; font-weight: bold; }
    .user-badge { background: #1f3864; color: #D4AF37; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 10px; border: 1px solid #D4AF37; }
    .purchaser-card { background: #1a1a1a; padding: 12px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def to_ethiopian(date_val):
    if pd.isna(date_val): return ""
    try:
        k = Kenat(date_val.date() if hasattr(date_val, 'date') else date_val)
        return k.format({'lang': 'english'})
    except: return str(date_val)

def clean_num(val):
    if pd.isna(val): return 0.0
    try:
        s = str(val).replace(',', '').replace('ETB', '').strip()
        if s in ('', '-', 'None', 'nan', '#REF!', '#N/A', '#VALUE!'): return 0.0
        return float(s)
    except:
        return 0.0

def parse_eleganza_date(val):
    if pd.isna(val) or str(val).strip() in ('', 'DATE', 'date'):
        return pd.NaT
    s = str(val).strip()
    try:
        return pd.to_datetime(s, errors='coerce')
    except:
        return pd.NaT

def get_sheet_url():
    return st.secrets.get("eleganza_url", st.secrets.get("sofabet_url", ""))

def get_google_creds():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        if "gcp_service_account" in st.secrets:
            secret_data = st.secrets["gcp_service_account"]
            if "key_base64" in secret_data:
                json_str = base64.b64decode(secret_data["key_base64"]).decode('utf-8')
                key_dict = json.loads(json_str)
                return service_account.Credentials.from_service_account_info(key_dict, scopes=scope)
            else:
                return service_account.Credentials.from_service_account_info(secret_data, scopes=scope)
    except Exception:
        return service_account.Credentials.from_service_account_file('key.json', scopes=scope)

def _get_sheets_global():
    creds = get_google_creds()
    return gspread.authorize(creds).open_by_url(get_sheet_url())

def _ensure_sheet(ws_name, headers):
    sh = _get_sheets_global()
    try:
        ws = sh.worksheet(ws_name)
        first_row = ws.row_values(1)
        if not first_row or first_row[0] != headers[0]:
            ws.insert_row(headers, index=1)
        return ws
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=ws_name, rows=2000, cols=len(headers))
        ws.append_row(headers)
        return ws

def _get_all_records_robust(ws):
    try:
        all_vals = ws.get_all_values()
        if not all_vals or len(all_vals) < 2: return []
        headers = all_vals[0]
        if not headers or headers[0] == "": return []
        data = []
        for row in all_vals[1:]:
            if not any(row): continue
            if len(row) < len(headers): row += [''] * (len(headers) - len(row))
            elif len(row) > len(headers): row = row[:len(headers)]
            data.append(dict(zip(headers, row)))
        return data
    except Exception: return []

def get_eleganza_tab(sheet, tab_name, anchor_col):
    try:
        raw = sheet.worksheet(tab_name).get_all_values()
        if not raw: return pd.DataFrame()
        header_idx = None
        for idx, row in enumerate(raw[:15]):
            cleaned = [str(c).strip() for c in row]
            if anchor_col in cleaned:
                header_idx = idx
                break
        if header_idx is None: return pd.DataFrame()
        
        headers = [str(c).strip() if str(c).strip() != '' else f"Col_{i}" for i, c in enumerate(raw[header_idx])]
        rows = raw[header_idx + 1:]
        df = pd.DataFrame(rows, columns=headers)
        df = df.replace('', pd.NA).dropna(how='all')
        return df.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

# --- AUTHENTICATION ---
def authenticate():
    if "user" in st.session_state: return True
    st.markdown("## 🔒 Eleganza ERP — Sign In")
    users_secrets = st.secrets.get("users", None)
    if not users_secrets:
        pwd = st.text_input("Master Password", type="password")
        if st.button("Login", type="primary"):
            if pwd == st.secrets.get("app_password", "ELEGANZA2026"):
                st.session_state.user = {"username": "manager", "name": "Manager", "role": "manager"}
                st.rerun()
            else: st.error("❌ Wrong password")
        return False

    user_options = {f"{udata.get('name', uname)} ({udata.get('role', 'viewer').title()})": uname for uname, udata in users_secrets.items()}
    with st.form("login_form"):
        sel = st.selectbox("Select Profile:", list(user_options.keys()))
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", type="primary", use_container_width=True):
            uname = user_options[sel]
            if users_secrets[uname].get("password", "") == password:
                st.session_state.user = {"username": uname, "name": users_secrets[uname].get("name", uname), "role": users_secrets[uname].get("role", "viewer")}
                st.rerun()
            else: st.error("❌ Invalid password.")
    return False

# =====================================================================
# MAIN APP
# =====================================================================
if authenticate():
    user = st.session_state.user
    role = str(user.get("role", "")).strip().lower()
    user_name = user.get("name", user.get("username", "Guest"))

    with st.sidebar:
        st.markdown(f'<div class="user-badge">👤 {user_name}<br><span style="font-size:12px;">{role.upper()}</span></div>', unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            del st.session_state.user; st.rerun()
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    st.markdown('<p class="golden-title">ELEGANZA</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">EXECUTIVE MERCHANDISING ERP & 3-ACCOUNT TREASURY</p>', unsafe_allow_html=True)
    
    @st.cache_data(ttl=60)
    def load_erp_data():
        creds = get_google_creds()
        client = gspread.authorize(creds)
        sheet = client.open_by_url(get_sheet_url())
        return {
            "Stock_Mgmt": get_eleganza_tab(sheet, "Stock Management", "ITEM CODE"),
            "Stock_In": get_eleganza_tab(sheet, "STOCK IN", "ITEM NAME"),
            "Stock_Out": get_eleganza_tab(sheet, "Stock OUT", "ITEM NUMBER"),
            "Suppliers": get_eleganza_tab(sheet, "suppliers information", "Name"),
            "Costs": get_eleganza_tab(sheet, "cost", "DATE"),
            "Cash": get_eleganza_tab(sheet, "Cash_Accounts", "Date"),
            "Assets": get_eleganza_tab(sheet, "ASSET VALUE", "Materials"),
            "Office_Assets": get_eleganza_tab(sheet, "OFFICE ASSET", "ITEM"),
        }

    data = load_erp_data()
    df_mgmt = data["Stock_Mgmt"]
    df_in = data["Stock_In"]
    df_out = data["Stock_Out"]
    df_sup = data["Suppliers"]
    df_cost = data["Costs"]
    df_cash = data["Cash"]

    # Clean numeric columns
    if not df_mgmt.empty:
        for c in ['STOCK IN', 'STOCK OUT', 'STOCK AVAILABLE', 'price', 'total price']:
            if c in df_mgmt.columns: df_mgmt[c] = df_mgmt[c].apply(clean_num)
    if not df_in.empty:
        for c in ['STOCK IN', 'PRICE', 'credit price', 'TOTAL PRICE', 'total credit price']:
            if c in df_in.columns: df_in[c] = df_in[c].apply(clean_num)
    if not df_out.empty:
        for c in ['STOCK OUT', 'PRICE', 'TOTAL PRICE']:
            if c in df_out.columns: df_out[c] = df_out[c].apply(clean_num)
    if not df_cost.empty:
        if 'amount' in df_cost.columns: df_cost['amount'] = df_cost['amount'].apply(clean_num)
    if not df_cash.empty:
        if 'Amount' in df_cash.columns: df_cash['Amount'] = df_cash['Amount'].apply(clean_num)

    # --- TABS SETUP ---
    ALL_TABS = [
        ("exec", "📊 Exec Summary"),
        ("treasury", "🏦 3-Account Treasury"),
        ("inv", "📦 Stock Management"),
        ("sales", "🛒 Sales (Stock Out)"),
        ("stock_in", "📥 Purchases (Stock In)"),
        ("expenses", "💸 Expenses & Costs"),
        ("request", "📝 Purchase Request"),
        ("purch", "🛒 Purchaser / Approver")
    ]

    tabs_objs = st.tabs([l for _, l in ALL_TABS])
    tab_map = {k: t for (k, _), t in zip(ALL_TABS, tabs_objs)}

    # --- 1. EXEC SUMMARY ---
    with tab_map["exec"]:
        total_rev = df_out['TOTAL PRICE'].sum() if not df_out.empty and 'TOTAL PRICE' in df_out.columns else 0.0
        total_exp = df_cost['amount'].sum() if not df_cost.empty and 'amount' in df_cost.columns else 0.0
        stock_val = df_mgmt['total price'].sum() if not df_mgmt.empty and 'total price' in df_mgmt.columns else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Sales Revenue", f"ETB {total_rev:,.2f}")
        c2.metric("Operating Expenses", f"ETB {total_exp:,.2f}")
        c3.metric("Inventory Asset Value", f"ETB {stock_val:,.2f}")

        st.divider()
        c_l, c_r = st.columns(2)
        with c_l:
            st.subheader("Top Selling Items")
            if not df_out.empty and 'ITEM NAME' in df_out.columns:
                top = df_out.groupby('ITEM NAME')['TOTAL PRICE'].sum().reset_index()
                st.plotly_chart(px.bar(top, x='ITEM NAME', y='TOTAL PRICE', color='TOTAL PRICE', color_continuous_scale='Teal'), use_container_width=True)
            else: st.info("No sales data.")
        with c_r:
            st.subheader("Inventory by Category")
            if not df_mgmt.empty and 'CATEGORY' in df_mgmt.columns:
                cat = df_mgmt.groupby('CATEGORY')['total price'].sum().reset_index()
                st.plotly_chart(px.pie(cat, names='CATEGORY', values='total price', hole=0.4), use_container_width=True)
            else: st.info("No category data.")

    # --- 2. 3-ACCOUNT TREASURY ---
    with tab_map["treasury"]:
        st.subheader("🏦 Multi-Owner 3-Account Cash Treasury")
        st.caption("Real-time cash balances across Company Account, Owner 1 Account, and Owner 2 Account.")
        
        accounts = ["Company Account", "Owner 1 Account", "Owner 2 Account"]
        cols = st.columns(3)

        for i, acc in enumerate(accounts):
            with cols[i]:
                # Calculate inflows & outflows per account from df_cash, df_out, df_in, df_cost
                c_in = df_cash[(df_cash['Account'] == acc) & (df_cash['Type'] == 'Cash In')]['Amount'].sum() if not df_cash.empty else 0
                c_out = df_cash[(df_cash['Account'] == acc) & (df_cash['Type'] == 'Cash Out')]['Amount'].sum() if not df_cash.empty else 0
                sales_in = df_out[df_out.get('Account', '') == acc]['TOTAL PRICE'].sum() if not df_out.empty and 'Account' in df_out.columns else 0
                purch_out = df_in[df_in.get('Account', '') == acc]['TOTAL PRICE'].sum() if not df_in.empty and 'Account' in df_in.columns else 0
                exp_out = df_cost[df_cost.get('Account', '') == acc]['amount'].sum() if not df_cost.empty and 'Account' in df_cost.columns else 0

                net_bal = (c_in - c_out) + sales_in - purch_out - exp_out
                st.metric(acc, f"ETB {net_bal:,.2f}", f"Sales: +{sales_in:,.0f} | Exp: -{exp_out:,.0f}")

        st.divider()
        st.subheader("📋 Treasury Ledger Entries (`Cash_Accounts`)")
        if not df_cash.empty:
            st.dataframe(df_cash, use_container_width=True, hide_index=True)
        else:
            st.info("No cash ledger entries found.")

    # --- 3. STOCK MANAGEMENT ---
    with tab_map["inv"]:
        st.subheader("📦 Live Stock Management")
        if not df_mgmt.empty:
            st.dataframe(df_mgmt, use_container_width=True, hide_index=True)
        else: st.info("No stock items found.")

    # --- 4. SALES (STOCK OUT) ---
    with tab_map["sales"]:
        st.subheader("🛒 Customer Sales & Stock Out")
        if not df_out.empty:
            st.dataframe(df_out, use_container_width=True, hide_index=True)
        else: st.info("No sales transactions found.")

    # --- 5. PURCHASES (STOCK IN) ---
    with tab_map["stock_in"]:
        st.subheader("📥 Stock In & Procurement Log")
        if not df_in.empty:
            st.dataframe(df_in, use_container_width=True, hide_index=True)
        else: st.info("No stock-in records found.")

    # --- 6. EXPENSES & COSTS ---
    with tab_map["expenses"]:
        st.subheader("💸 Operating Expenses")
        if not df_cost.empty:
            st.dataframe(df_cost, use_container_width=True, hide_index=True)
        else: st.info("No expenses recorded.")

    # --- 7. PURCHASE REQUEST ---
    with tab_map["request"]:
        st.subheader("📝 Create Purchase Request")
        st.info("Use this tab to request inventory reorders.")

    # --- 8. PURCHASER / APPROVER ---
    with tab_map["purch"]:
        st.subheader("🛒 Purchaser & Finance Approver Hub")
        st.info("Manage approval queues and post incoming shipments to inventory.")
