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
from collections import defaultdict

st.set_page_config(
    page_title="ELEGANZA | Furniture & Home Accessories ERP",
    page_icon="🛋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTS & HEADERS ---
_REQ_HDRS = [
    "Request_ID", "Submitted_Date", "Submitted_By", "Supplier_Preference",
    "Item_Code", "Item_Name", "Measure", "Requested_Qty", "Est_Unit_Cost", "Status", "Notes"
]
REP_SHEET = "Purchase_Reports"
REQ_SHEET = "Purchase_Requests"
REP_HEADERS = [
    "Report_ID", "Submitted_Date", "Supplier_Name",
    "Payment_Type", "Item_Code", "Item_Name", "Measure",
    "Qty", "Unit_Cost", "Total", "Status", "Approver", "Approved_Date", "Notes"
]
ACCOUNTS = ["Company Account", "Owner 1 Account", "Owner 2 Account"]
ETH_MONTHS = [
    "Meskerem", "Tikimt", "Hidar", "Tahsas", "Tir", "Yekatit",
    "Megabit", "Miazia", "Ginbot", "Sene", "Hamle", "Nehase", "Pagume"
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

# --- MODERN LUXURY DARK-NAVY & GOLD UI THEME ---
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at top right, #111b2e 0%, #090d16 100%);
        color: #F0F2F6;
    }
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(90deg, rgba(31,56,100,0.85) 0%, rgba(15,23,42,0.95) 100%);
        padding: 12px 24px;
        border-radius: 12px;
        border-left: 5px solid #D4AF37;
        border-bottom: 1px solid rgba(212, 175, 55, 0.35);
        margin-bottom: 18px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.45);
    }
    .brand-left {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .brand-logo-badge {
        width: 42px;
        height: 42px;
        border-radius: 10px;
        background: linear-gradient(135deg, #D4AF37 0%, #AA821B 100%);
        color: #0F172A;
        font-weight: 900;
        font-size: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 8px rgba(212, 175, 55, 0.4);
    }
    .brand-title {
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 24px !important;
        font-weight: 800 !important;
        color: #D4AF37 !important;
        letter-spacing: 3px;
        margin: 0 !important;
        line-height: 1.1;
    }
    .brand-sub {
        font-size: 11px;
        color: #CBD5E1;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 2px;
    }
    .brand-date-pill {
        background: rgba(212, 175, 55, 0.14);
        border: 1px solid rgba(212, 175, 55, 0.45);
        color: #FDE68A;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-align: right;
    }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        padding: 16px 18px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #D4AF37;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
    }
    div[data-testid="stMetric"] label {
        color: #94A3B8 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-size: 22px !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="tab-list"] {
        gap: 6px !important;
        background: rgba(15, 23, 42, 0.6);
        padding: 6px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 8px 14px !important;
        color: #CBD5E1 !important;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1F3864 0%, #2B4C8C 100%) !important;
        color: #D4AF37 !important;
        font-weight: 700 !important;
        border: 1px solid rgba(212, 175, 55, 0.4) !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #0B111E;
        border-right: 1px solid rgba(212, 175, 55, 0.2);
    }
    .user-badge {
        background: linear-gradient(135deg, #1F3864 0%, #0F172A 100%);
        color: #D4AF37;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 12px;
        border: 1px solid rgba(212, 175, 55, 0.45);
    }
    .treasury-card {
        background: linear-gradient(145deg, #162238 0%, #0D1524 100%);
        border: 1px solid rgba(212, 175, 55, 0.35);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .catalog-card {
        background: linear-gradient(145deg, #162238 0%, #0D1524 100%);
        border: 1px solid rgba(212, 175, 55, 0.3);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

# --- ETHIOPIAN CALENDAR & DATA HELPERS ---
def to_ethiopian(date_val):
    if pd.isna(date_val): return ""
    try:
        dt = date_val.date() if hasattr(date_val, 'date') else date_val
        eth = Kenat(dt).get_ethiopian()
        return f"{eth['day']:02d}/{eth['month']:02d}/{eth['year']} EC ({ETH_MONTHS[eth['month']-1]})"
    except Exception:
        return str(date_val)

def to_ethiopian_short(date_val):
    if pd.isna(date_val): return ""
    try:
        dt = date_val.date() if hasattr(date_val, 'date') else date_val
        eth = Kenat(dt).get_ethiopian()
        return f"{eth['day']:02d}/{eth['month']:02d}/{eth['year']}"
    except Exception:
        return str(date_val)

def get_eth_month_label(y, m):
    try:
        y_int, m_int = int(y), int(m)
        if y_int > 0 and 1 <= m_int <= 13:
            return f"{ETH_MONTHS[m_int-1]} {y_int} EC"
    except Exception:
        pass
    return "Unknown Date"

def get_greg_from_eth(eth_y, eth_m, eth_d):
    try:
        g = Kenat(f"{eth_y}/{eth_m}/{eth_d}").get_gregorian()
        return pd.to_datetime(datetime.date(g['year'], g['month'], g['day']))
    except Exception:
        return pd.NaT

def parse_smart_eth_or_greg_date(val):
    if pd.isna(val) or str(val).strip() in ('', 'DATE', 'date', 'Date'):
        return pd.NaT
    s = str(val).strip()
    parts = s.split('/')
    if len(parts) == 3:
        try:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            if 1990 <= y <= 2021:
                g = Kenat(f"{y}/{m}/{d}").get_gregorian()
                return pd.to_datetime(datetime.date(g['year'], g['month'], g['day']))
            return pd.to_datetime(datetime.date(y, m, d))
        except Exception:
            pass
    return pd.to_datetime(s, dayfirst=True, errors='coerce')

def clean_num(val):
    if pd.isna(val): return 0.0
    try:
        s = str(val).replace(',', '').replace('ETB', '').replace('$', '').strip()
        if s in ('', '-', 'None', 'nan', '#REF!', '#N/A', '#VALUE!'): return 0.0
        return float(s)
    except Exception:
        return 0.0

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
    except Exception:
        return []

def _find_all_matching_rows(ws, match_fn):
    out = []
    try:
        all_vals = ws.get_all_values()
        if not all_vals or len(all_vals) < 2: return out
        headers = all_vals[0]
        for i, row in enumerate(all_vals[1:], start=2):
            padded = list(row) + [''] * (len(headers) - len(row))
            rec = dict(zip(headers, padded))
            try:
                if match_fn(rec): out.append(i)
            except Exception:
                continue
    except Exception:
        pass
    return out

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
        seen = {}
        unique_headers = []
        for h in headers:
            if h in seen:
                seen[h] += 1
                unique_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                unique_headers.append(h)

        rows = raw[header_idx + 1:]
        df = pd.DataFrame(rows, columns=unique_headers)
        df = df.replace('', pd.NA).dropna(how='all')
        df = df[df[anchor_col].astype(str).str.strip() != anchor_col]
        return df.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()

# =====================================================================
# PROFESSIONAL PDF REPORT SUITE (EXECUTIVE, TREASURY, STOCK, SALES, EXPENSES)
# =====================================================================
class EleganzaReportPDF(FPDF):
    def __init__(self, font_name='Helvetica'):
        super().__init__()
        self.font_name = font_name
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(10, 10, 10)

    def footer(self):
        self.set_y(self.h - 14)
        self.set_draw_color(212, 175, 55)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.set_y(self.h - 11)
        self.set_font(self.font_name, '', 7)
        self.set_text_color(130, 130, 130)
        self.cell(0, 5, f"ELEGANZA Furniture & Home Accessories  |  Addis Ababa, Ethiopia  |  Page {self.page_no()}", align='C')

def _init_pdf():
    if font_ready:
        try:
            pdf = EleganzaReportPDF('DejaVu')
            pdf.add_font('DejaVu', '', 'DejaVuSans.ttf')
            pdf.add_font('DejaVu', 'B', 'DejaVuSans-Bold.ttf')
            return pdf
        except Exception:
            pass
    return EleganzaReportPDF('Helvetica')

def _draw_pdf_header(pdf, title, subtitle):
    f_name = pdf.font_name
    NAVY, GOLD = (31, 56, 100), (212, 175, 55)
    LIGHT_GRAY = (245, 247, 250)

    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, pdf.w, 20, 'F')
    pdf.set_fill_color(*GOLD)
    pdf.rect(0, 20, pdf.w, 1.5, 'F')

    text_x = 10
    if os.path.exists('logo.jpg'):
        try:
            pdf.image('logo.jpg', x=10, y=3, w=14, h=14)
            text_x = 27
        except Exception:
            text_x = 10

    pdf.set_xy(text_x, 4)
    pdf.set_font(f_name, 'B', 14)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 7, "ELEGANZA", ln=True, align='L')

    pdf.set_xy(text_x, 11)
    pdf.set_font(f_name, '', 8)
    pdf.set_text_color(230, 230, 230)
    pdf.cell(0, 4, "Furniture & Home Accessories Trading  |  Ethiopia", align='L')

    pdf.set_xy(10, 6)
    pdf.set_font(f_name, 'B', 8)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 6, "OFFICIAL STATEMENT", align='R')

    pdf.set_y(26)
    pdf.set_font(f_name, 'B', 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, title, ln=True, align='C')

    pdf.set_font(f_name, '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, subtitle, ln=True, align='C')
    pdf.ln(2)

    meta_y = pdf.get_y()
    pdf.set_fill_color(*LIGHT_GRAY)
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.3)
    pdf.rect(10, meta_y, pdf.w - 20, 7, 'DF')

    pdf.set_y(meta_y + 1.5)
    pdf.set_x(10)
    pdf.set_font(f_name, '', 8)
    pdf.set_text_color(50, 50, 50)
    gen_eth = to_ethiopian(pd.Timestamp.now())
    gen_greg = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.cell(0, 4, f"Ethiopian Date: {gen_eth}    |    Gregorian: {gen_greg}", ln=True, align='C')
    pdf.ln(4)

def _draw_pdf_table(pdf, headers, rows, font_size=6.5, col_widths=None):
    f_name = pdf.font_name
    NAVY, WHITE = (31, 56, 100), (255, 255, 255)
    LIGHT_GRAY, DARK = (245, 247, 250), (45, 45, 45)
    usable_w = pdf.w - 20
    if not col_widths:
        col_widths = [usable_w / len(headers)] * len(headers)

    def _hdr():
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.set_font(f_name, 'B', font_size + 0.5)
        pdf.set_x(10)
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 6, str(h), border=0, align='C', fill=True)
        pdf.ln()

    _hdr()
    if not rows:
        pdf.set_font(f_name, '', font_size + 1)
        pdf.set_text_color(140, 140, 140)
        pdf.cell(0, 9, "No records found for this selection.", ln=True, align='C')
        return

    pdf.set_font(f_name, '', font_size)
    pdf.set_text_color(*DARK)

    for i, row in enumerate(rows):
        if pdf.get_y() + 5 > pdf.h - pdf.b_margin - 5:
            pdf.add_page()
            _hdr()
            pdf.set_font(f_name, '', font_size)
            pdf.set_text_color(*DARK)
        pdf.set_fill_color(*(LIGHT_GRAY if i % 2 == 0 else WHITE))
        pdf.set_x(10)
        for item, w in zip(row, col_widths):
            s = str(item).strip().replace('\n', ' ')
            if s.lower() in ('nan', 'none'): s = ''
            while pdf.get_string_width(s) > (w - 1.5) and len(s) > 1:
                s = s[:-1]
            pdf.cell(w, 5.2, s, border=0, align='C', fill=True)
        pdf.ln()

def _draw_total_banner(pdf, label, amount):
    f_name = pdf.font_name
    NAVY, GOLD, WHITE = (31, 56, 100), (212, 175, 55), (255, 255, 255)
    pdf.ln(5)
    if pdf.get_y() + 18 > pdf.h - pdf.b_margin:
        pdf.add_page()
    box_w = 95
    box_x = pdf.w - 10 - box_w
    box_y = pdf.get_y()
    pdf.set_fill_color(*GOLD)
    pdf.rect(box_x, box_y, 3, 14, 'F')
    pdf.set_fill_color(*NAVY)
    pdf.rect(box_x + 3, box_y, box_w - 3, 14, 'F')
    pdf.set_xy(box_x + 7, box_y + 1.5)
    pdf.set_font(f_name, 'B', 7.5)
    pdf.set_text_color(*GOLD)
    pdf.cell(box_w - 10, 4, label.upper(), ln=True, align='L')
    pdf.set_xy(box_x + 7, box_y + 6.5)
    pdf.set_font(f_name, 'B', 11.5)
    pdf.set_text_color(*WHITE)
    pdf.cell(box_w - 10, 6, f"ETB {amount:,.2f}", ln=True, align='R')

# 1. Executive P&L PDF
def generate_executive_pnl_pdf(period_label, rev, cogs, gross_p, opex, net_p, stock_val, asset_val):
    pdf = _init_pdf()
    pdf.add_page()
    _draw_pdf_header(pdf, "Executive Profit & Loss Statement", f"Reporting Period: {period_label}")
    f_name = pdf.font_name
    NAVY = (31, 56, 100)

    pdf.set_font(f_name, 'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "1. Merchandising Income Statement (ETB)", ln=True)

    pnl_rows = [
        ["Gross Retail & Wholesale Revenue", f"ETB {rev:,.2f}"],
        ["Cost of Goods Sold (COGS / Import & Local Sourcing)", f"(ETB {cogs:,.2f})"],
        ["Gross Merchandising Profit", f"ETB {gross_p:,.2f}"],
        ["Operating Expenses (Showroom Rent, Delivery, Staff, Utilities)", f"(ETB {opex:,.2f})"],
        ["Net Operating Profit", f"ETB {net_p:,.2f}"],
    ]
    _draw_pdf_table(pdf, ["Financial Line Item", "Amount (ETB)"], pnl_rows, font_size=8.5, col_widths=[130, 60])

    pdf.ln(6)
    pdf.set_font(f_name, 'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "2. Inventory & Asset Summary", ln=True)
    bal_rows = [
        ["Closing Showroom & Warehouse Stock Value", f"ETB {stock_val:,.2f}"],
        ["Total Showroom & Office Fixed Assets", f"ETB {asset_val:,.2f}"],
    ]
    _draw_pdf_table(pdf, ["Balance Sheet Metric", "Amount (ETB)"], bal_rows, font_size=8.5, col_widths=[130, 60])
    _draw_total_banner(pdf, "Net Operating Profit", net_p)
    return bytes(pdf.output())

# 2. Multi-Owner 3-Account Treasury Statement PDF
def generate_treasury_pdf(period_label, summary_rows, ledger_df):
    pdf = _init_pdf()
    pdf.add_page()
    _draw_pdf_header(pdf, "3-Account Treasury & Co-Owner Balance Statement", f"Period: {period_label}")
    f_name = pdf.font_name
    NAVY = (31, 56, 100)

    pdf.set_font(f_name, 'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "Account Balances Breakdown (Company vs. Owner 1 vs. Owner 2)", ln=True)

    headers = ["Account Name", "Capital/Transfers", "Sales In", "Purchases Out", "Expenses Out", "Net Balance (ETB)"]
    _draw_pdf_table(pdf, headers, summary_rows, font_size=7.5, col_widths=[36, 30, 30, 30, 30, 34])

    pdf.ln(6)
    pdf.set_font(f_name, 'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "Recent Treasury Capital & Inter-Account Transfers", ln=True)

    l_rows = []
    if not ledger_df.empty:
        for _, r in ledger_df.head(40).iterrows():
            l_rows.append([
                str(r.get('Date_EC', r.get('Date', ''))),
                str(r.get('Account', '')),
                str(r.get('Type', '')),
                str(r.get('Category', '')),
                f"{clean_num(r.get('Amount', 0)):,.2f}",
                str(r.get('Notes', ''))
            ])
    _draw_pdf_table(pdf, ["Date (EC)", "Account", "Type", "Category", "Amount", "Notes"], l_rows, font_size=6.5, col_widths=[28, 32, 20, 30, 26, 54])

    total_cash = sum(clean_num(r[-1]) for r in summary_rows if r[0] != "TOTAL ALL 3 ACCOUNTS")
    _draw_total_banner(pdf, "Combined Cash Position", total_cash)
    return bytes(pdf.output())

# 3. Stock Audit & Physical Count Sheet PDF
def generate_stock_audit_pdf(period_label, in_qty, out_qty, clo_qty, clo_val, per_item_df, sig_sk, sig_mgr):
    pdf = _init_pdf()
    pdf.add_page()
    _draw_pdf_header(pdf, "Showroom & Warehouse Stock Audit Sheet", f"Period: {period_label}")
    f_name = pdf.font_name
    NAVY = (31, 56, 100)

    _draw_total_banner(pdf, "Total Inventory Valuation", clo_val)
    pdf.ln(6)
    pdf.set_font(f_name, 'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, f"Total Imported/Purchased: {in_qty:,.0f}  |  Total Sold: {out_qty:,.0f}  |  On Hand: {clo_qty:,.0f}", ln=True)

    headers = ["SKU", "Item Name", "Category", "In", "Out", "Avail", "Price", "Total (ETB)", "Status"]
    rows = []
    if not per_item_df.empty:
        for _, r in per_item_df.iterrows():
            rows.append([
                str(r.get('ITEM CODE', '')), str(r.get('ITEM NAME', '')), str(r.get('CATEGORY', '')),
                f"{clean_num(r.get('STOCK IN', 0)):,.0f}", f"{clean_num(r.get('STOCK OUT', 0)):,.0f}",
                f"{clean_num(r.get('STOCK AVAILABLE', 0)):,.0f}", f"{clean_num(r.get('price', 0)):,.2f}",
                f"{clean_num(r.get('total price', 0)):,.2f}", str(r.get('STATUS', ''))
            ])
    _draw_pdf_table(pdf, headers, rows, font_size=6.2, col_widths=[18, 42, 24, 14, 14, 16, 20, 22, 20])

    pdf.ln(14)
    sig_y = pdf.get_y()
    if sig_y > pdf.h - 35:
        pdf.add_page()
        sig_y = pdf.get_y() + 8
    pdf.set_font(f_name, '', 9)
    pdf.set_xy(15, sig_y); pdf.cell(80, 5, f"Store Keeper: {sig_sk}")
    pdf.set_xy(15, sig_y + 8); pdf.cell(80, 5, "Signature: ______________________")
    pdf.set_xy(110, sig_y); pdf.cell(80, 5, f"Audited By: {sig_mgr}")
    pdf.set_xy(110, sig_y + 8); pdf.cell(80, 5, "Signature: ______________________")
    return bytes(pdf.output())

# 4. Customer Sales & Receivables Ledger PDF
def generate_sales_ledger_pdf(period_label, df_sales):
    pdf = _init_pdf()
    pdf.add_page()
    _draw_pdf_header(pdf, "Customer Sales & Revenue Report", f"Period: {period_label}")
    rows = []
    tot_rev = 0.0
    if not df_sales.empty:
        for _, r in df_sales.iterrows():
            amt = clean_num(r.get('TOTAL PRICE', 0))
            tot_rev += amt
            rows.append([
                str(r.get('Date_EC', '')),
                str(r.get('customer name ab', '')),
                str(r.get('ITEM NAME', '')),
                f"{clean_num(r.get('STOCK OUT', 0)):,.0f}",
                f"{clean_num(r.get('PRICE', 0)):,.2f}",
                f"{amt:,.2f}",
                str(r.get('Account', ''))
            ])
    _draw_pdf_table(pdf, ["Date (EC)", "Customer", "Item", "Qty", "Price", "Total (ETB)", "Account"], rows, font_size=6.5, col_widths=[26, 36, 40, 14, 22, 26, 26])
    _draw_total_banner(pdf, "Total Sales Revenue", tot_rev)
    return bytes(pdf.output())

# 5. Operating Expenses & Supplier Credit Payable PDF
def generate_expense_credit_pdf(period_label, df_expenses, df_credit):
    pdf = _init_pdf()
    pdf.add_page()
    _draw_pdf_header(pdf, "Operating Expenses & Supplier Payables Report", f"Period: {period_label}")
    f_name = pdf.font_name
    NAVY = (31, 56, 100)

    pdf.set_font(f_name, 'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "1. Operating Expenses Log", ln=True)
    exp_rows = []
    tot_exp = 0.0
    if not df_expenses.empty:
        for _, r in df_expenses.iterrows():
            amt = clean_num(r.get('amount', 0))
            tot_exp += amt
            exp_rows.append([
                str(r.get('Date_EC', '')),
                str(r.get('Category', '')),
                str(r.get('Description', '')),
                str(r.get('Account', '')),
                f"{amt:,.2f}"
            ])
    _draw_pdf_table(pdf, ["Date (EC)", "Category", "Description", "Paid From", "Amount (ETB)"], exp_rows, font_size=6.8, col_widths=[28, 32, 66, 34, 30])

    pdf.ln(6)
    pdf.set_font(f_name, 'B', 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "2. Local & Import Supplier Credit Purchases (Unpaid Payables)", ln=True)
    cred_rows = []
    tot_cred = 0.0
    if not df_credit.empty:
        for _, r in df_credit.iterrows():
            camt = clean_num(r.get('total credit price', 0))
            if camt > 0:
                tot_cred += camt
                cred_rows.append([
                    str(r.get('Date_EC', '')),
                    str(r.get('suppliers', '')),
                    str(r.get('ITEM NUMBER', '')),
                    f"{clean_num(r.get('STOCK IN', 0)):,.0f}",
                    f"{camt:,.2f}"
                ])
    _draw_pdf_table(pdf, ["Date (EC)", "Supplier", "Item", "Qty", "Credit Owed (ETB)"], cred_rows, font_size=6.8, col_widths=[28, 46, 56, 24, 36])
    _draw_total_banner(pdf, "Total Expenses + Credit Payables", tot_exp + tot_cred)
    return bytes(pdf.output())

# --- AUTHENTICATION ---
def authenticate():
    if "user" in st.session_state:
        return True

    st.markdown("""
        <div class="brand-header" style="max-width: 520px; margin: 30px auto;">
            <div class="brand-left">
                <div class="brand-logo-badge">E</div>
                <div>
                    <div class="brand-title">ELEGANZA</div>
                    <div class="brand-sub">Furniture & Home Accessories ERP</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    users_secrets = st.secrets.get("users", None)
    col_sp1, col_form, col_sp2 = st.columns([1, 1.4, 1])
    with col_form:
        if not users_secrets:
            pwd = st.text_input("Master Access Password", type="password")
            if st.button("Sign In", type="primary", use_container_width=True):
                if pwd == st.secrets.get("app_password", "ELEGANZA2026"):
                    st.session_state.user = {"username": "manager", "name": "General Manager", "role": "manager"}
                    st.rerun()
                else:
                    st.error("❌ Incorrect password")
            return False

        user_options = {f"{udata.get('name', uname)} ({udata.get('role', 'viewer').title()})": uname for uname, udata in users_secrets.items()}
        with st.form("login_form"):
            selected_display = st.selectbox("Select User Profile:", list(user_options.keys()))
            password = st.text_input("Password", type="password")
            if st.form_submit_button("🔐 Sign In to ERP", type="primary", use_container_width=True):
                uname = user_options[selected_display]
                udata = users_secrets[uname]
                if udata.get("password", "") == password:
                    st.session_state.user = {"username": uname, "name": udata.get("name", uname), "role": udata.get("role", "viewer")}
                    st.rerun()
                else:
                    st.error("❌ Invalid password for this profile.")
    return False

# --- STYLERS ---
def style_stock_status(val):
    s = str(val).strip().lower()
    if 'out of stock' in s: return 'color: #FF6B6B; font-weight: bold;'
    if 'minimum' in s: return 'color: #FBBF24; font-weight: bold;'
    return 'color: #34D399; font-weight: bold;'

# =====================================================================
# MAIN APPLICATION
# =====================================================================
if authenticate():
    user = st.session_state.user
    role = str(user.get("role", "")).strip().lower()
    user_name = user.get("name", user.get("username", "Guest"))

    # Current Ethiopian & Gregorian Date Header
    today_greg = datetime.date.today()
    eth_today = Kenat(today_greg).get_ethiopian()
    curr_eth_y, curr_eth_m, curr_eth_d = eth_today['year'], eth_today['month'], eth_today['day']
    eth_today_str = f"{ETH_MONTHS[curr_eth_m-1]} {curr_eth_d}, {curr_eth_y} EC"
    greg_today_str = today_greg.strftime("%b %d, %Y")

    # Compact Header with Small Logo Badge
    logo_html = '<div class="brand-logo-badge">E</div>'
    if os.path.exists('logo.jpg'):
        with open('logo.jpg', 'rb') as img_f:
            b64_logo = base64.b64encode(img_f.read()).decode()
            logo_html = f'<img src="data:image/jpeg;base64,{b64_logo}" style="width:42px; height:42px; border-radius:8px; border:1px solid #D4AF37; object-fit:cover;">'

    st.markdown(f"""
        <div class="brand-header">
            <div class="brand-left">
                {logo_html}
                <div>
                    <div class="brand-title">ELEGANZA</div>
                    <div class="brand-sub">Furniture & Home Accessories ERP • Ethiopia (Google Sheets DB)</div>
                </div>
            </div>
            <div class="brand-date-pill">
                📅 {eth_today_str}<br>
                <span style="font-size:10px; color:#CBD5E1;">GC: {greg_today_str}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR: USER PROFILE & ETHIOPIAN CALENDAR SYSTEM ---
    with st.sidebar:
        st.markdown(f'<div class="user-badge">👤 {user_name}<br><span style="font-size:11px; color:#FDE68A;">{role.upper()} ACCESS</span></div>', unsafe_allow_html=True)
        col_sb1, col_sb2 = st.columns(2)
        if col_sb1.button("🔄 Sync", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if col_sb2.button("🚪 Logout", use_container_width=True):
            del st.session_state.user
            st.rerun()

        st.divider()
        st.markdown("### 📅 Ethiopian Calendar Filter")
        cal_mode = st.radio(
            "Reporting Period (EC):",
            ["All Time", "This Month (EC)", "Last Month (EC)", "This Fiscal Year (Hamle–Sene)", "Custom Range (EC)"]
        )

        if cal_mode == "This Month (EC)":
            start_date = get_greg_from_eth(curr_eth_y, curr_eth_m, 1)
            end_date = pd.to_datetime(today_greg)
            period_label = f"{ETH_MONTHS[curr_eth_m-1]} {curr_eth_y} EC"
        elif cal_mode == "Last Month (EC)":
            py, pm = (curr_eth_y - 1, 13) if curr_eth_m == 1 else (curr_eth_y, curr_eth_m - 1)
            start_date = get_greg_from_eth(py, pm, 1)
            end_date = get_greg_from_eth(curr_eth_y, curr_eth_m, 1) - datetime.timedelta(days=1)
            period_label = f"{ETH_MONTHS[pm-1]} {py} EC"
        elif cal_mode == "This Fiscal Year (Hamle–Sene)":
            fy_start_y = curr_eth_y if curr_eth_m >= 11 else curr_eth_y - 1
            start_date = get_greg_from_eth(fy_start_y, 11, 1)
            end_date = pd.to_datetime(today_greg)
            period_label = f"EFY {fy_start_y}/{fy_start_y+1} (Hamle 1 – Today)"
        elif cal_mode == "Custom Range (EC)":
            st.caption("From (Ethiopian Date):")
            c1, c2, c3 = st.columns(3)
            sy = c1.selectbox("Yr", range(curr_eth_y - 4, curr_eth_y + 2), index=4, key="sy")
            sm = c2.selectbox("Mo", range(1, 14), index=curr_eth_m - 1, format_func=lambda x: ETH_MONTHS[x-1][:3], key="sm")
            sd = c3.selectbox("Day", range(1, 31), index=0, key="sd")
            st.caption("To (Ethiopian Date):")
            c4, c5, c6 = st.columns(3)
            ey = c4.selectbox("Yr", range(curr_eth_y - 4, curr_eth_y + 2), index=4, key="ey")
            em = c5.selectbox("Mo", range(1, 14), index=curr_eth_m - 1, format_func=lambda x: ETH_MONTHS[x-1][:3], key="em")
            ed = c6.selectbox("Day", range(1, 31), index=min(curr_eth_d - 1, 29), key="ed")
            start_date = get_greg_from_eth(sy, sm, sd)
            end_date = get_greg_from_eth(ey, em, ed)
            period_label = f"{sd}/{sm}/{sy} – {ed}/{em}/{ey} EC"
        else:
            start_date = pd.to_datetime('2000-01-01')
            end_date = pd.to_datetime('2100-01-01')
            period_label = "All Time (EC)"

        if pd.isna(start_date): start_date = pd.to_datetime('2000-01-01')
        if pd.isna(end_date): end_date = pd.to_datetime('2100-01-01')
        st.info(f"Active Filter: **{period_label}**")

        with st.expander("🔄 EC ↔ GC Date Converter"):
            conv_g = st.date_input("Pick Gregorian Date:", value=today_greg)
            st.success(f"**EC:** {to_ethiopian(conv_g)}")

    # --- LOAD GOOGLE SHEETS DATA ---
    @st.cache_data(ttl=60)
    def load_all_erp_data():
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

    data = load_all_erp_data()
    df_mgmt = data["Stock_Mgmt"]
    df_in = data["Stock_In"]
    df_out = data["Stock_Out"]
    df_sup = data["Suppliers"]
    df_cost = data["Costs"]
    df_cash = data["Cash"]
    df_assets = data["Assets"]
    df_office = data["Office_Assets"]

    # --- CLEAN & PARSE DATAFRAMES ---
    if not df_mgmt.empty:
        for c in ['MIN STOCK', 'STOCK IN', 'STOCK OUT', 'STOCK AVAILABLE', 'price', 'total price']:
            if c in df_mgmt.columns:
                df_mgmt[c] = df_mgmt[c].apply(clean_num)
        df_mgmt = df_mgmt[df_mgmt['ITEM CODE'].notna() & (df_mgmt['ITEM CODE'].astype(str).str.strip() != '')]

    if not df_in.empty:
        df_in['Parsed_Date'] = df_in['DATE'].apply(parse_smart_eth_or_greg_date) if 'DATE' in df_in.columns else pd.NaT
        df_in['Date_EC'] = df_in['Parsed_Date'].apply(to_ethiopian_short)
        for c in ['STOCK IN', 'PRICE', 'credit price', 'TOTAL PRICE', 'total credit price']:
            if c in df_in.columns:
                df_in[c] = df_in[c].apply(clean_num)
        df_in = df_in[df_in['STOCK IN'] > 0]

    if not df_out.empty:
        d_col = 'DATE' if 'DATE' in df_out.columns else ('date' if 'date' in df_out.columns else None)
        df_out['Parsed_Date'] = df_out[d_col].apply(parse_smart_eth_or_greg_date) if d_col else pd.NaT
        df_out['Date_EC'] = df_out['Parsed_Date'].apply(to_ethiopian_short)
        for c in ['STOCK OUT', 'PRICE', 'TOTAL PRICE']:
            if c in df_out.columns:
                df_out[c] = df_out[c].apply(clean_num)
        df_out = df_out[df_out['STOCK OUT'] > 0]

    if not df_cost.empty:
        df_cost['Parsed_Date'] = df_cost['DATE'].apply(parse_smart_eth_or_greg_date) if 'DATE' in df_cost.columns else pd.NaT
        df_cost['Date_EC'] = df_cost['Parsed_Date'].apply(to_ethiopian_short)
        if 'amount' in df_cost.columns:
            df_cost['amount'] = df_cost['amount'].apply(clean_num)
        df_cost = df_cost[df_cost['amount'] > 0]

    if not df_cash.empty:
        df_cash['Parsed_Date'] = df_cash['Date'].apply(parse_smart_eth_or_greg_date) if 'Date' in df_cash.columns else pd.NaT
        df_cash['Date_EC'] = df_cash['Parsed_Date'].apply(to_ethiopian_short)
        if 'Amount' in df_cash.columns:
            df_cash['Amount'] = df_cash['Amount'].apply(clean_num)
        df_cash = df_cash[df_cash['Amount'] > 0]

    def filter_by_ec_range(df):
        if df.empty or 'Parsed_Date' not in df.columns:
            return df
        return df[(df['Parsed_Date'].isna()) | ((df['Parsed_Date'] >= start_date) & (df['Parsed_Date'] <= end_date))].copy()

    df_in_filt = filter_by_ec_range(df_in)
    df_out_filt = filter_by_ec_range(df_out)
    df_cost_filt = filter_by_ec_range(df_cost)
    df_cash_filt = filter_by_ec_range(df_cash)

    # Unit Cost Map for COGS & Gross Profit
    unit_cost_map = {}
    if not df_in.empty:
        for _, r in df_in.iterrows():
            code = str(r.get('ITEM NAME', '')).strip().upper()
            p = clean_num(r.get('PRICE', 0)) or clean_num(r.get('credit price', 0))
            if code and p > 0:
                unit_cost_map[code] = p

    if not df_out_filt.empty:
        df_out_filt['Code_Clean'] = df_out_filt['ITEM NUMBER'].astype(str).str.strip().str.upper()
        df_out_filt['Est_Unit_Cost'] = df_out_filt['Code_Clean'].map(unit_cost_map).fillna(0)
        df_out_filt['Est_COGS'] = df_out_filt['STOCK OUT'] * df_out_filt['Est_Unit_Cost']
        df_out_filt['Gross_Profit'] = df_out_filt['TOTAL PRICE'] - df_out_filt['Est_COGS']

    # Compute 3-Account Live Treasury Balances
    treasury_summary = []
    tot_cap_net, tot_sales_in, tot_purch_out, tot_exp_out, tot_net_cash = 0.0, 0.0, 0.0, 0.0, 0.0
    for acc in ACCOUNTS:
        c_in = df_cash_filt[(df_cash_filt['Account'] == acc) & (df_cash_filt['Type'] == 'Cash In')]['Amount'].sum() if not df_cash_filt.empty else 0.0
        c_out = df_cash_filt[(df_cash_filt['Account'] == acc) & (df_cash_filt['Type'] == 'Cash Out')]['Amount'].sum() if not df_cash_filt.empty else 0.0
        cap_net = c_in - c_out
        s_in = df_out_filt[df_out_filt['Account'] == acc]['TOTAL PRICE'].sum() if not df_out_filt.empty and 'Account' in df_out_filt.columns else 0.0
        p_out = df_in_filt[df_in_filt['Account'] == acc]['TOTAL PRICE'].sum() if not df_in_filt.empty and 'Account' in df_in_filt.columns else 0.0
        e_out = df_cost_filt[df_cost_filt['Account'] == acc]['amount'].sum() if not df_cost_filt.empty and 'Account' in df_cost_filt.columns else 0.0
        net_b = cap_net + s_in - p_out - e_out

        tot_cap_net += cap_net
        tot_sales_in += s_in
        tot_purch_out += p_out
        tot_exp_out += e_out
        tot_net_cash += net_b
        treasury_summary.append([acc, f"{cap_net:,.2f}", f"{s_in:,.2f}", f"{p_out:,.2f}", f"{e_out:,.2f}", f"{net_b:,.2f}"])

    treasury_summary.append(["TOTAL ALL 3 ACCOUNTS", f"{tot_cap_net:,.2f}", f"{tot_sales_in:,.2f}", f"{tot_purch_out:,.2f}", f"{tot_exp_out:,.2f}", f"{tot_net_cash:,.2f}"])

    # =====================================================================
    # ROLE-BASED NAVIGATION TABS (INCLUDING NEW PRODUCT CATALOG)
    # =====================================================================
    ALL_TABS = [
        ("exec", "📊 Exec Summary"),
        ("catalog", "🛋️ Product Catalog"),
        ("treasury", "🏦 3-Account Cash"),
        ("import_calc", "🚢 Import & Pricing Calc"),
        ("inv", "📦 Inventory Control"),
        ("sales", "🛒 Sales (Stock Out)"),
        ("stock_in", "📥 Purchases (Stock In)"),
        ("expenses", "💸 Operating Expenses"),
        ("pdf_hub", "📄 PDF Report Center"),
        ("request", "📝 Purchase Request"),
        ("purch", "✅ Purchaser & Approver")
    ]

    if role == "manager":
        allowed_keys = [k for k, _ in ALL_TABS]
    elif role == "maker":
        allowed_keys = ["request", "catalog", "inv", "import_calc", "pdf_hub"]
    elif role == "purchaser":
        allowed_keys = ["purch", "stock_in", "catalog"]
    elif role == "approver":
        allowed_keys = ["purch", "treasury", "pdf_hub", "catalog"]
    else:
        allowed_keys = [k for k, _ in ALL_TABS]

    visible = [(k, l) for k, l in ALL_TABS if k in allowed_keys]
    tabs_objs = st.tabs([l for _, l in visible])
    tab_map = {k: t for (k, _), t in zip(visible, tabs_objs)}

    # =====================================================================
    # TAB 1: EXECUTIVE SUMMARY
    # =====================================================================
    if "exec" in tab_map:
        with tab_map["exec"]:
            rev = df_out_filt['TOTAL PRICE'].sum() if not df_out_filt.empty else 0.0
            cogs = df_out_filt['Est_COGS'].sum() if not df_out_filt.empty and 'Est_COGS' in df_out_filt.columns else 0.0
            gross_p = rev - cogs
            opex = df_cost_filt['amount'].sum() if not df_cost_filt.empty else 0.0
            net_p = gross_p - opex
            stock_val = df_mgmt['total price'].sum() if not df_mgmt.empty else 0.0
            cred_owed = df_in_filt['total credit price'].sum() if not df_in_filt.empty and 'total credit price' in df_in_filt.columns else 0.0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Sales Revenue", f"ETB {rev:,.2f}")
            k2.metric("Gross Profit", f"ETB {gross_p:,.2f}")
            k3.metric("Operating Expenses", f"ETB {opex:,.2f}")
            k4.metric("Net Operating Profit", f"ETB {net_p:,.2f}")

            k5, k6, k7, k8 = st.columns(4)
            k5.metric("Combined Cash (3 Accts)", f"ETB {tot_net_cash:,.2f}")
            k6.metric("Showroom & Stock Value", f"ETB {stock_val:,.2f}")
            k7.metric("Supplier Credit Payable", f"ETB {cred_owed:,.2f}")
            low_cnt = len(df_mgmt[df_mgmt['STOCK AVAILABLE'] <= df_mgmt['MIN STOCK']]) if not df_mgmt.empty and 'MIN STOCK' in df_mgmt.columns else 0
            k8.metric("Low / Out of Stock", f"{low_cnt} SKUs")

            st.divider()
            c_left, c_right = st.columns(2)
            with c_left:
                st.subheader("📈 Monthly Revenue vs. Profit (Ethiopian Calendar)")
                if not df_out_filt.empty and df_out_filt['Parsed_Date'].notna().any():
                    df_t = df_out_filt.dropna(subset=['Parsed_Date']).copy()
                    df_t['EY'] = df_t['Parsed_Date'].apply(lambda x: Kenat(x).get_ethiopian()['year'])
                    df_t['EM'] = df_t['Parsed_Date'].apply(lambda x: Kenat(x).get_ethiopian()['month'])
                    tr = df_t.groupby(['EY', 'EM']).agg({'TOTAL PRICE': 'sum', 'Gross_Profit': 'sum'}).reset_index()
                    tr['Month'] = tr.apply(lambda r: get_eth_month_label(r['EY'], r['EM']), axis=1)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=tr['Month'], y=tr['TOTAL PRICE'], name='Revenue (ETB)', marker_color='#1F3864'))
                    fig.add_trace(go.Scatter(x=tr['Month'], y=tr['Gross_Profit'], name='Gross Profit (ETB)', mode='lines+markers', line=dict(color='#D4AF37', width=3)))
                    fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=340)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Add dated sales entries in Stock OUT to view Ethiopian monthly trends.")

            with c_right:
                st.subheader("🏦 Cash Position Across 3 Accounts")
                acc_names = [r[0] for r in treasury_summary[:-1]]
                acc_vals = [clean_num(r[-1]) for r in treasury_summary[:-1]]
                fig_pie = px.pie(
                    names=acc_names, values=[max(0, v) for v in acc_vals], hole=0.45,
                    color_discrete_sequence=['#D4AF37', '#2B4C8C', '#10B981']
                )
                fig_pie.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', height=340)
                st.plotly_chart(fig_pie, use_container_width=True)

    # =====================================================================
    # TAB 2: PRODUCT CATALOG (SHOWROOM GALLERY WITH GOOGLE SHEETS BACKEND)
    # =====================================================================
    if "catalog" in tab_map:
        with tab_map["catalog"]:
            st.subheader("🛋️ Eleganza Furniture & Home Accessories Catalog")
            st.caption("Visual showroom catalog pulling item codes, categories, prices, and stock levels directly from your Google Sheets database.")

            if not df_mgmt.empty:
                cat_filter_col1, cat_filter_col2 = st.columns([2, 2])
                cat_search = cat_filter_col1.text_input("🔍 Search Catalog by Item Name or SKU:", "")
                all_cats = ["All Categories"] + sorted(df_mgmt['CATEGORY'].dropna().unique().tolist()) if 'CATEGORY' in df_mgmt.columns else ["All Categories"]
                sel_cat_filter = cat_filter_col2.selectbox("Filter by Category:", all_cats)

                cat_df = df_mgmt.copy()
                if cat_search:
                    cat_df = cat_df[cat_df['ITEM CODE'].astype(str).str.contains(cat_search, case=False, na=False) | cat_df['ITEM NAME'].astype(str).str.contains(cat_search, case=False, na=False)]
                if sel_cat_filter != "All Categories":
                    cat_df = cat_df[cat_df['CATEGORY'] == sel_cat_filter]

                # Render responsive product cards in a 3-column grid
                cols = st.columns(3)
                for i, row in cat_df.iterrows():
                    sku = str(row.get('ITEM CODE', ''))
                    name = str(row.get('ITEM NAME', ''))
                    category = str(row.get('CATEGORY', 'Furniture'))
                    price = clean_num(row.get('price', 0))
                    stock = clean_num(row.get('STOCK AVAILABLE', 0))
                    status = str(row.get('STATUS', 'Available'))

                    col_idx = i % 3
                    with cols[col_idx]:
                        # Default high-end furniture imagery placeholder based on category
                        img_url = "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=600&q=80"
                        if 'lighting' in category.lower() or 'chandelier' in name.lower():
                            img_url = "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?auto=format&fit=crop&w=600&q=80"
                        elif 'decor' in category.lower() or 'accessory' in name.lower():
                            img_url = "https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?auto=format&fit=crop&w=600&q=80"
                        elif 'bedroom' in category.lower() or 'bed' in name.lower():
                            img_url = "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=600&q=80"

                        st.markdown(f"""
                            <div class="catalog-card">
                                <img src="{img_url}" style="width:100%; height:160px; object-fit:cover; border-radius:8px; margin-bottom:10px;">
                                <div style="font-size:11px; color:#D4AF37; font-weight:700; text-transform:uppercase; letter-spacing:1px;">{category} • SKU: {sku}</div>
                                <div style="font-size:16px; color:#FFFFFF; font-weight:800; margin:4px 0;">{name}</div>
                                <div style="font-size:18px; color:#34D399; font-weight:700; margin:6px 0;">ETB {price:,.2f}</div>
                                <div style="font-size:12px; color:#CBD5E1;">In Stock: <b>{stock:,.0f} units</b> | <span style="color:#FBBF24;">{status}</span></div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No items found in Stock Management Google Sheet.")

    # =====================================================================
    # TAB 3: 3-ACCOUNT CASH TREASURY
    # =====================================================================
    if "treasury" in tab_map:
        with tab_map["treasury"]:
            st.subheader("🏦 Multi-Owner 3-Account Cash Treasury")
            st.caption("Live reconciliation across Company Account, Owner 1 Account, and Owner 2 Account.")

            tc1, tc2, tc3 = st.columns(3)
            for idx, col in enumerate([tc1, tc2, tc3]):
                row = treasury_summary[idx]
                with col:
                    st.markdown(f"""
                        <div class="treasury-card">
                            <div style="color:#D4AF37; font-weight:700; font-size:15px;">{row[0]}</div>
                            <div style="color:#FFFFFF; font-size:24px; font-weight:800; margin:6px 0;">ETB {row[5]}</div>
                            <div style="font-size:12px; color:#94A3B8;">
                                Capital/Transfers: <b>{row[1]}</b><br>
                                Sales In: <span style="color:#34D399;">+{row[2]}</span> | Outflows: <span style="color:#F87171;">-{clean_num(row[3])+clean_num(row[4]):,.2f}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

            st.dataframe(
                pd.DataFrame(treasury_summary, columns=["Account", "Capital / Net Transfers", "Sales Collected", "Purchases Paid", "Operating Expenses", "NET LIVE BALANCE"]),
                use_container_width=True, hide_index=True
            )

            st.divider()
            with st.expander("➕ Record Capital Injection, Owner Withdrawal, or Inter-Account Transfer"):
                with st.form("cash_tx_form", clear_on_submit=True):
                    f1, f2, f3 = st.columns(3)
                    tx_acc = f1.selectbox("Account:", ACCOUNTS)
                    tx_type = f2.selectbox("Transaction Type:", ["Cash In", "Cash Out"])
                    tx_cat = f3.selectbox("Category:", ["Capital Injection", "Owner Drawing / Dividend", "Internal Transfer", "Forex / LC Deposit", "Loan / Other"])
                    f4, f5 = st.columns([1, 2])
                    tx_amt = f4.number_input("Amount (ETB):", min_value=0.0, step=100.0)
                    tx_note = f5.text_input("Reference / Notes:")
                    if st.form_submit_button("💾 Save to Cash_Accounts Sheet", type="primary"):
                        if tx_amt > 0:
                            try:
                                ws_cash = _ensure_sheet("Cash_Accounts", ["Date", "Account", "Type", "Category", "Amount", "Notes"])
                                ws_cash.append_row([to_ethiopian_short(today_greg), tx_acc, tx_type, tx_cat, float(tx_amt), tx_note], value_input_option='USER_ENTERED')
                                st.success(f"✅ Recorded ETB {tx_amt:,.2f} ({tx_type}) in {tx_acc}!")
                                load_all_erp_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving transaction: {e}")
                        else:
                            st.warning("Enter an amount greater than 0.")

            if not df_cash_filt.empty:
                st.markdown("### 📋 Cash & Capital Ledger (`Cash_Accounts`)")
                disp_c = [c for c in ['Date_EC', 'Account', 'Type', 'Category', 'Amount', 'Notes'] if c in df_cash_filt.columns]
                st.dataframe(df_cash_filt[disp_c], use_container_width=True, hide_index=True)

    # =====================================================================
    # TAB 4: IMPORT LANDED COST & PRICING CALCULATOR
    # =====================================================================
    if "import_calc" in tab_map:
        with tab_map["import_calc"]:
            st.subheader("🚢 Import Landed Cost & Furniture/Accessory Retail Pricing")
            st.caption("Calculate true landed cost in ETB for imported furniture & home accessories (FX rate, freight, customs duty) or local supplier markups.")

            sourcing_mode = st.radio("Sourcing Type:", ["🌍 Imported Shipment (FX + Customs + Freight)", "🇪🇹 Local Supplier Purchase (ETB Markup)"], horizontal=True)

            ic1, ic2 = st.columns([1.25, 1])
            if sourcing_mode.startswith("🌍"):
                with ic1:
                    item_label = st.text_input("Furniture / Home Accessory Item:", "Luxury Imported Chandelier / Sofa Set")
                    imp_qty = st.number_input("Shipment Quantity (Units):", min_value=1, value=10, step=1)
                    fob_usd = st.number_input("Supplier Invoice Price per Unit (USD $):", min_value=0.0, value=180.0, step=5.0)
                    fx_rate = st.number_input("Exchange Rate (ETB per 1 USD):", min_value=1.0, value=128.0, step=0.5)
                    freight_ins_etb = st.number_input("Sea/Air Freight, Djibouti Port & Inland Transport (Total ETB):", min_value=0.0, value=45000.0, step=1000.0)
                    customs_pct = st.number_input("Total Customs Duty, Excise & Surtax Rate (%):", min_value=0.0, max_value=150.0, value=35.0, step=1.0)
                    retail_margin = st.slider("Target Gross Profit Margin (%):", min_value=10, max_value=75, value=40)

                with ic2:
                    total_fob_etb = fob_usd * imp_qty * fx_rate
                    customs_etb = total_fob_etb * (customs_pct / 100.0)
                    total_landed_etb = total_fob_etb + freight_ins_etb + customs_etb
                    unit_landed_etb = total_landed_etb / imp_qty
                    sell_price = unit_landed_etb / (1 - (retail_margin / 100.0))
                    total_batch_profit = (sell_price * imp_qty) - total_landed_etb

                    st.metric("Total Shipment Landed Cost", f"ETB {total_landed_etb:,.2f}", f"Customs & Duty: ETB {customs_etb:,.0f}")
                    st.metric("Landed Cost per Unit", f"ETB {unit_landed_etb:,.2f} / unit")
                    st.metric("Showroom Selling Price", f"ETB {sell_price:,.2f}", f"Net Batch Profit: ETB {total_batch_profit:,.2f}")
            else:
                with ic1:
                    loc_item = st.text_input("Local Furniture / Accessory Item:", "Local Hardwood Coffee Table / Decor")
                    loc_qty = st.number_input("Purchase Quantity (Units):", min_value=1, value=15, step=1)
                    loc_unit_cost = st.number_input("Local Supplier Unit Cost (ETB):", min_value=0.0, value=4500.0, step=100.0)
                    loc_transport = st.number_input("Local Delivery & Handling Cost (Total ETB):", min_value=0.0, value=3000.0, step=200.0)
                    loc_margin = st.slider("Target Retail Margin (%):", min_value=10, max_value=75, value=35, key="loc_m")

                with ic2:
                    tot_loc_cost = (loc_unit_cost * loc_qty) + loc_transport
                    net_unit_cost = tot_loc_cost / loc_qty
                    loc_sell = net_unit_cost / (1 - (loc_margin / 100.0))
                    loc_profit = (loc_sell * loc_qty) - tot_loc_cost

                    st.metric("Total Local Purchase Cost", f"ETB {tot_loc_cost:,.2f}")
                    st.metric("Net Cost per Unit (Incl. Delivery)", f"ETB {net_unit_cost:,.2f} / unit")
                    st.metric("Showroom Selling Price", f"ETB {loc_sell:,.2f}", f"Total Profit: ETB {loc_profit:,.2f}")

            st.divider()
            st.markdown("### 🏢 Showroom & Warehouse Fixed Assets (`ASSET VALUE` & `OFFICE ASSET`)")
            a_c1, a_c2 = st.columns(2)
            with a_c1:
                st.caption("Warehouse & Display Equipment (`ASSET VALUE`)")
                if not df_assets.empty:
                    st.dataframe(df_assets, use_container_width=True, hide_index=True)
                else:
                    st.info("No entries in ASSET VALUE.")
            with a_c2:
                st.caption("Showroom & Office IT Assets (`OFFICE ASSET`)")
                if not df_office.empty:
                    st.dataframe(df_office, use_container_width=True, hide_index=True)
                else:
                    st.info("No entries in OFFICE ASSET.")

    # =====================================================================
    # TAB 5: INVENTORY CONTROL
    # =====================================================================
    if "inv" in tab_map:
        with tab_map["inv"]:
            st.subheader("📦 Furniture & Home Accessories Inventory (`Stock Management`)")
            if not df_mgmt.empty:
                f1, f2, f3 = st.columns([2, 1, 1])
                q = f1.text_input("🔍 Search SKU or Item Name:", "")
                cats = ["All"] + sorted(df_mgmt['CATEGORY'].dropna().unique().tolist()) if 'CATEGORY' in df_mgmt.columns else ["All"]
                sel_cat = f2.selectbox("Category:", cats)
                st_f = f3.selectbox("Status:", ["All", "Available", "Minimum Amount", "Out of Stock"])

                dv = df_mgmt.copy()
                if q:
                    dv = dv[dv['ITEM CODE'].astype(str).str.contains(q, case=False, na=False) | dv['ITEM NAME'].astype(str).str.contains(q, case=False, na=False)]
                if sel_cat != "All":
                    dv = dv[dv['CATEGORY'] == sel_cat]
                if st_f != "All" and 'STATUS' in dv.columns:
                    dv = dv[dv['STATUS'].astype(str).str.lower() == st_f.lower()]

                cols_show = [c for c in ['ITEM CODE', 'ITEM NAME', 'CATEGORY', 'Measure', 'MIN STOCK', 'STOCK IN', 'STOCK OUT', 'STOCK AVAILABLE', 'price', 'total price', 'STATUS'] if c in dv.columns]
                st.dataframe(
                    dv[cols_show].style.format({
                        'MIN STOCK': '{:,.0f}', 'STOCK IN': '{:,.0f}', 'STOCK OUT': '{:,.0f}',
                        'STOCK AVAILABLE': '{:,.0f}', 'price': 'ETB {:,.2f}', 'total price': 'ETB {:,.2f}'
                    }).map(style_stock_status, subset=['STATUS'] if 'STATUS' in cols_show else []),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("No items in Stock Management.")

    # =====================================================================
    # TAB 6: SALES (STOCK OUT)
    # =====================================================================
    if "sales" in tab_map:
        with tab_map["sales"]:
            st.subheader("🛒 Customer Sales & Showroom Dispatch (`Stock OUT`)")
            with st.expander("➕ Record New Customer Sale"):
                with st.form("new_sale_form", clear_on_submit=True):
                    s1, s2, s3 = st.columns(3)
                    c_code = s1.text_input("Client Code:", "CL-001")
                    c_name = s2.text_input("Customer / Interior Client Name:", "")
                    s_acc = s3.selectbox("Deposit Account:", ACCOUNTS)

                    item_opts = df_mgmt['ITEM CODE'].tolist() if not df_mgmt.empty else ["SKU-101"]
                    s4, s5, s6 = st.columns(3)
                    sel_sku = s4.selectbox("Item SKU:", item_opts)
                    s_qty = s5.number_input("Quantity Sold:", min_value=1, value=1, step=1)
                    default_p = float(df_mgmt[df_mgmt['ITEM CODE'] == sel_sku]['price'].iloc[0]) if not df_mgmt.empty and sel_sku in df_mgmt['ITEM CODE'].values else 0.0
                    s_price = s6.number_input("Unit Selling Price (ETB):", min_value=0.0, value=default_p, step=10.0)

                    if st.form_submit_button("✅ Post Sale to Stock OUT", type="primary"):
                        if c_name.strip() and s_qty > 0:
                            try:
                                item_row = df_mgmt[df_mgmt['ITEM CODE'] == sel_sku].iloc[0] if not df_mgmt.empty else {}
                                iname = str(item_row.get('ITEM NAME', sel_sku))
                                meas = str(item_row.get('Measure', 'Pcs'))
                                ws_out = _get_sheets_global().worksheet("Stock OUT")
                                ws_out.append_row([
                                    to_ethiopian_short(today_greg), c_code, c_name.strip(), sel_sku, iname,
                                    meas, float(s_qty), float(s_price), float(s_qty * s_price), s_acc
                                ], value_input_option='USER_ENTERED')
                                st.success(f"✅ Sale of {s_qty} x {iname} posted to {s_acc}!")
                                load_all_erp_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to record sale: {e}")
                        else:
                            st.warning("Please enter a customer name.")

            if not df_out_filt.empty:
                show_s = [c for c in ['Date_EC', 'CLINT CODE', 'customer name ab', 'ITEM NUMBER', 'ITEM NAME', 'STOCK OUT', 'PRICE', 'TOTAL PRICE', 'Account'] if c in df_out_filt.columns]
                st.dataframe(df_out_filt[show_s], use_container_width=True, hide_index=True)

    # =====================================================================
    # TAB 7: PURCHASES (STOCK IN)
    # =====================================================================
    if "stock_in" in tab_map:
        with tab_map["stock_in"]:
            st.subheader("📥 Imports & Local Supplier Purchases (`STOCK IN`)")
            if not df_in_filt.empty:
                show_i = [c for c in ['REF NO', 'Date_EC', 'ITEM NAME', 'ITEM NUMBER', 'STOCK IN', 'PRICE', 'TOTAL PRICE', 'total credit price', 'suppliers', 'Account'] if c in df_in_filt.columns]
                st.dataframe(df_in_filt[show_i], use_container_width=True, hide_index=True)
            else:
                st.info("No import or local purchase records in this Ethiopian date range.")

    # =====================================================================
    # TAB 8: OPERATING EXPENSES
    # =====================================================================
    if "expenses" in tab_map:
        with tab_map["expenses"]:
            st.subheader("💸 Operating Expenses (`cost`)")

            with st.expander("➕ Log New Operating Expense"):
                with st.form("new_exp_form", clear_on_submit=True):
                    e1, e2, e3 = st.columns(3)
                    e_cat = e1.selectbox("Category:", ["Showroom & Warehouse Rent", "Customs & Clearing Fees", "Utilities & Internet", "Salaries & Commissions", "Customer Delivery & Transport", "Social Media & Marketing", "Maintenance", "License & Fees"])
                    e_acc = e2.selectbox("Paid From Account:", ACCOUNTS)
                    e_amt = e3.number_input("Amount (ETB):", min_value=0.0, step=50.0)
                    e_desc = st.text_input("Expense Description:")
                    if st.form_submit_button("💾 Save Expense", type="primary"):
                        if e_amt > 0:
                            try:
                                ws_cost = _get_sheets_global().worksheet("cost")
                                ws_cost.append_row([
                                    to_ethiopian_short(today_greg), e_cat, e_desc, "Cash / Transfer", float(e_amt), user_name, e_acc
                                ], value_input_option='USER_ENTERED')
                                st.success(f"✅ Expense of ETB {e_amt:,.2f} recorded under {e_acc}!")
                                load_all_erp_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving expense: {e}")

            if not df_cost_filt.empty:
                show_e = [c for c in ['Date_EC', 'Category', 'Description', 'amount', 'Approved By', 'Account'] if c in df_cost_filt.columns]
                st.dataframe(df_cost_filt[show_e], use_container_width=True, hide_index=True)

    # =====================================================================
    # TAB 9: PDF REPORT CENTER (EXECUTIVE PDF REPORTS)
    # =====================================================================
    if "pdf_hub" in tab_map:
        with tab_map["pdf_hub"]:
            st.subheader("📄 Executive & Audit PDF Report Center")
            st.caption(f"All PDFs automatically use the active Ethiopian Calendar filter: **{period_label}**")

            rev = df_out_filt['TOTAL PRICE'].sum() if not df_out_filt.empty else 0.0
            cogs = df_out_filt['Est_COGS'].sum() if not df_out_filt.empty and 'Est_COGS' in df_out_filt.columns else 0.0
            gross_p = rev - cogs
            opex = df_cost_filt['amount'].sum() if not df_cost_filt.empty else 0.0
            net_p = gross_p - opex
            stock_val = df_mgmt['total price'].sum() if not df_mgmt.empty else 0.0
            asset_val = (df_assets['Total Value'].apply(clean_num).sum() if not df_assets.empty and 'Total Value' in df_assets.columns else 0.0) +                         (df_office['Total Cost'].apply(clean_num).sum() if not df_office.empty and 'Total Cost' in df_office.columns else 0.0)

            r1, r2 = st.columns(2)
            with r1:
                st.markdown("#### 1️⃣ Executive P&L Report")
                st.write("Includes Revenue, Import/Local COGS, Gross Profit, Operating Expenses, and Net Operating Profit.")
                pnl_bytes = generate_executive_pnl_pdf(period_label, rev, cogs, gross_p, opex, net_p, stock_val, asset_val)
                st.download_button("📥 Download Executive P&L PDF", data=pnl_bytes, file_name=f"Eleganza_PnL_{curr_eth_y}_{curr_eth_m}.pdf", mime="application/pdf", type="primary", use_container_width=True)

                st.markdown("---")
                st.markdown("#### 2️⃣ 3-Account Treasury & Co-Owner Balance PDF")
                st.write("Complete cash reconciliation for Company Account, Owner 1 Account, and Owner 2 Account.")
                trs_bytes = generate_treasury_pdf(period_label, treasury_summary, df_cash_filt)
                st.download_button("📥 Download 3-Account Treasury PDF", data=trs_bytes, file_name=f"Eleganza_3Account_Treasury_{curr_eth_y}_{curr_eth_m}.pdf", mime="application/pdf", type="primary", use_container_width=True)

                st.markdown("---")
                st.markdown("#### 3️⃣ Customer Sales Ledger PDF")
                st.write("Itemized showroom & wholesale sales, quantities, prices, and deposit accounts.")
                sls_bytes = generate_sales_ledger_pdf(period_label, df_out_filt)
                st.download_button("📥 Download Sales Ledger PDF", data=sls_bytes, file_name=f"Eleganza_Sales_Report_{curr_eth_y}_{curr_eth_m}.pdf", mime="application/pdf", use_container_width=True)

            with r2:
                st.markdown("#### 4️⃣ Showroom & Warehouse Stock Audit PDF")
                st.write("Physical inventory count sheet with Store Keeper & Manager signature blocks.")
                sig1 = st.text_input("Store Keeper Name:", user_name, key="pdf_sk")
                sig2 = st.text_input("Manager Name:", "General Manager", key="pdf_mgr")
                in_q = df_mgmt['STOCK IN'].sum() if not df_mgmt.empty else 0
                out_q = df_mgmt['STOCK OUT'].sum() if not df_mgmt.empty else 0
                clo_q = df_mgmt['STOCK AVAILABLE'].sum() if not df_mgmt.empty else 0
                aud_bytes = generate_stock_audit_pdf(period_label, in_q, out_q, clo_q, stock_val, df_mgmt, sig1, sig2)
                st.download_button("📥 Download Stock Audit PDF", data=aud_bytes, file_name=f"Eleganza_Stock_Audit_{curr_eth_y}_{curr_eth_m}.pdf", mime="application/pdf", type="primary", use_container_width=True)

                st.markdown("---")
                st.markdown("#### 5️⃣ Operating Expenses & Supplier Payables PDF")
                st.write("Full breakdown of operational costs and unpaid credit balances owed to suppliers.")
                exp_bytes = generate_expense_credit_pdf(period_label, df_cost_filt, df_in_filt)
                st.download_button("📥 Download Expenses & Payables PDF", data=exp_bytes, file_name=f"Eleganza_Expenses_Payables_{curr_eth_y}_{curr_eth_m}.pdf", mime="application/pdf", use_container_width=True)

    # =====================================================================
    # TAB 10: PURCHASE REQUEST (MAKER)
    # =====================================================================
    if "request" in tab_map:
        with tab_map["request"]:
            st.subheader("📝 Create Restock / Import Request")
            if "el_pr_cart" not in st.session_state:
                st.session_state.el_pr_cart = []

            if not df_mgmt.empty:
                df_bulk = pd.DataFrame({
                    'Code': df_mgmt['ITEM CODE'].values,
                    'Item Name': df_mgmt['ITEM NAME'].values,
                    'In Stock': df_mgmt['STOCK AVAILABLE'].values,
                    'Select': [False] * len(df_mgmt),
                    'Qty': [1] * len(df_mgmt)
                })
                edited = st.data_editor(
                    df_bulk,
                    column_config={
                        'Select': st.column_config.CheckboxColumn('Select', default=False),
                        'Code': st.column_config.TextColumn('Code', disabled=True),
                        'Item Name': st.column_config.TextColumn('Item Name', disabled=True),
                        'In Stock': st.column_config.NumberColumn('In Stock', disabled=True, format="%.0f"),
                        'Qty': st.column_config.NumberColumn('Request Qty', min_value=1, step=1)
                    },
                    hide_index=True, use_container_width=True, num_rows="fixed"
                )
                if st.button("➕ Add Selected to Request Cart", type="primary"):
                    for idx, r in edited.iterrows():
                        if r['Select']:
                            orig = df_mgmt.iloc[idx]
                            icode = str(orig['ITEM CODE']).strip()
                            est_c = unit_cost_map.get(icode.upper(), clean_num(orig.get('price', 0)))
                            st.session_state.el_pr_cart.append({
                                'Item_Code': icode, 'Item_Name': str(orig['ITEM NAME']).strip(),
                                'Measure': str(orig.get('Measure', 'Pcs')), 'Qty': int(r['Qty']), 'Unit_Cost': est_c
                            })
                    st.rerun()

            if st.session_state.el_pr_cart:
                df_cart = pd.DataFrame(st.session_state.el_pr_cart)
                st.dataframe(df_cart, use_container_width=True, hide_index=True)
                sup_list = df_sup['Name'].dropna().tolist() if not df_sup.empty and 'Name' in df_sup.columns else []
                sel_sup = st.selectbox("Preferred Local / Import Supplier:", ["Any Supplier"] + sup_list)
                req_note = st.text_input("Notes / Urgency:")
                c_sub1, c_sub2 = st.columns(2)
                if c_sub1.button("📤 Submit Purchase Request", type="primary", use_container_width=True):
                    try:
                        ws_req = _ensure_sheet(REQ_SHEET, _REQ_HDRS)
                        rid = f"EL-REQ-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                        rows = [[rid, to_ethiopian_short(today_greg), user_name, sel_sup, x['Item_Code'], x['Item_Name'], x['Measure'], float(x['Qty']), float(x['Unit_Cost']), "Pending", req_note] for x in st.session_state.el_pr_cart]
                        ws_req.append_rows(rows, value_input_option='USER_ENTERED')
                        st.session_state.el_pr_cart = []
                        st.success(f"✅ Request {rid} submitted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")
                if c_sub2.button("🗑️ Clear Cart", use_container_width=True):
                    st.session_state.el_pr_cart = []
                    st.rerun()

    # =====================================================================
    # TAB 11: PURCHASER & APPROVER
    # =====================================================================
    if "purch" in tab_map:
        with tab_map["purch"]:
            st.subheader("✅ Purchaser & Finance Approver Workflow")
            mode = "purch" if role == "purchaser" else ("appr" if role == "approver" else st.radio("Mode:", ["🛒 Purchaser", "✅ Approver"], horizontal=True))

            if str(mode).startswith("🛒") or mode == "purch":
                ws_req = _ensure_sheet(REQ_SHEET, _REQ_HDRS)
                all_req = _get_all_records_robust(ws_req)
                pend = [r for r in all_req if str(r.get("Status", "")).strip().lower() == "pending"]
                if not pend:
                    st.info("No pending purchase requests.")
                else:
                    grp = defaultdict(list)
                    for r in pend: grp[r.get("Request_ID", "")].append(r)
                    sel_r = st.selectbox("Select Request ID:", sorted(grp.keys(), reverse=True))
                    if sel_r:
                        sup_all = df_sup['Name'].dropna().tolist() if not df_sup.empty and 'Name' in df_sup.columns else ["Local / Import Supplier"]
                        with st.form(f"purch_form_{sel_r}"):
                            inputs = {}
                            for idx, it in enumerate(grp[sel_r]):
                                st.markdown(f"**[{it.get('Item_Code')}] {it.get('Item_Name')}** (Req: {it.get('Requested_Qty')})")
                                c1, c2, c3, c4 = st.columns(4)
                                aq = c1.number_input("Actual Qty", min_value=0.0, value=clean_num(it.get('Requested_Qty', 1)), key=f"aq_{idx}")
                                ac = c2.number_input("Unit Landed Cost (ETB)", min_value=0.0, value=clean_num(it.get('Est_Unit_Cost', 0)), key=f"ac_{idx}")
                                pay = c3.selectbox("Payment", ["Cash", "Credit"], key=f"pay_{idx}")
                                sup = c4.selectbox("Supplier", sup_all, key=f"sup_{idx}")
                                acc_paid = st.selectbox("Paid From Account (if Cash):", ACCOUNTS, key=f"acc_{idx}")
                                inputs[idx] = (it, aq, ac, pay, sup, acc_paid)
                            if st.form_submit_button("🚀 Submit Purchase Report", type="primary"):
                                ws_rep = _ensure_sheet(REP_SHEET, REP_HEADERS)
                                batch = f"EL-RPT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                                rows = []
                                for idx, (it, aq, ac, pay, sup, acc_paid) in inputs.items():
                                    if aq > 0:
                                        rows.append([
                                            f"{batch}-{idx+1:02d}", to_ethiopian_short(today_greg), sup, pay,
                                            it.get('Item_Code', ''), it.get('Item_Name', ''), it.get('Measure', 'Pcs'),
                                            float(aq), float(ac), float(aq * ac), "Pending", "", "",
                                            f"Account:{acc_paid} | From {sel_r} | By {user_name}"
                                        ])
                                if rows:
                                    ws_rep.append_rows(rows, value_input_option='USER_ENTERED')
                                    st.success("✅ Submitted for manager approval!")
                                    st.rerun()
            else:
                ws_rep = _ensure_sheet(REP_SHEET, REP_HEADERS)
                recs = _get_all_records_robust(ws_rep)
                pend = [r for r in recs if str(r.get("Status", "")).strip().lower() == "pending"]
                if not pend:
                    st.info("No pending purchase reports awaiting approval.")
                else:
                    groups = defaultdict(list)
                    for r in recs if str(r.get("Status", "")).strip().lower() == "pending" else []:
                        pass
                    # Group pending reports
                    groups = defaultdict(list)
                    for r in pend: groups[str(r.get("Report_ID", ""))[:22]].append(r)
                    for bid, items in groups.items():
                        with st.expander(f"📦 Batch {bid} ({len(items)} items)", expanded=True):
                            st.dataframe(pd.DataFrame(items)[['Supplier_Name', 'Item_Code', 'Item_Name', 'Qty', 'Unit_Cost', 'Payment_Type', 'Total', 'Notes']], use_container_width=True, hide_index=True)
                            if st.button("✅ Approve & Post to STOCK IN", key=f"app_{bid}", type="primary"):
                                try:
                                    stock_in_ws = _get_sheets_global().worksheet("STOCK IN")
                                    eth_d = to_ethiopian_short(today_greg)
                                    post_rows = []
                                    for it in items:
                                        qv = clean_num(it.get("Qty", 0))
                                        uc = clean_num(it.get("Unit_Cost", 0))
                                        tot = qv * uc
                                        is_cred = str(it.get("Payment_Type", "Cash")).strip().lower() == "credit"
                                        note_str = str(it.get("Notes", ""))
                                        acc_used = "Company Account"
                                        for a in ACCOUNTS:
                                            if a in note_str:
                                                acc_used = a
                                                break
                                        post_rows.append([
                                            it.get("Report_ID", ""), eth_d, it.get("Item_Code", ""), it.get("Item_Name", ""),
                                            it.get("Measure", "Pcs"), qv, "" if is_cred else uc, uc if is_cred else "",
                                            0.0 if is_cred else tot, tot if is_cred else 0.0, it.get("Supplier_Name", ""),
                                            True if is_cred else False, "" if is_cred else acc_used
                                        ])
                                    stock_in_ws.append_rows(post_rows, value_input_option='USER_ENTERED')

                                    hdr = ws_rep.row_values(1)
                                    c_st = hdr.index("Status") + 1
                                    c_ap = hdr.index("Approver") + 1
                                    c_dt = hdr.index("Approved_Date") + 1
                                    t_ids = {it.get("Report_ID", "") for it in items}
                                    t_rows = _find_all_matching_rows(ws_rep, lambda rec: rec.get("Report_ID", "") in t_ids)
                                    updates = [gspread.Cell(r, c, v) for r in t_rows for c, v in [(c_st, "Approved"), (c_ap, user_name), (c_dt, eth_d)]]
                                    if updates: ws_rep.update_cells(updates)
                                    st.success(f"✅ Approved and posted {len(items)} items to STOCK IN!")
                                    load_all_erp_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Approval error: {e}")
