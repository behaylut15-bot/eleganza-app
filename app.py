import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import datetime
import gspread
import json
import base64
import io
import os
import urllib.request
from google.oauth2 import service_account
from fpdf import FPDF
from kenat import Kenat
from collections import defaultdict

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="eleganza HOMES | Evolved Elegance ERP",
    page_icon="🛋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 🎨 GLOBAL COLORFUL CHART THEME  (change colors here once)
# ============================================================
ELEGANZA_COLORS = [
    "#E63946",  # red
    "#F4A261",  # orange
    "#2A9D8F",  # teal
    "#457B9D",  # blue
    "#9B5DE5",  # purple
    "#F15BB5",  # pink
    "#00BBF9",  # cyan
    "#FEE440",  # yellow
    "#06D6A0",  # green
    "#EF476F",  # magenta
]

pio.templates["eleganza"] = pio.templates["plotly_white"]
pio.templates["eleganza"].layout.colorway = ELEGANZA_COLORS
pio.templates["eleganza"].layout.font.family = "Arial, sans-serif"
pio.templates["eleganza"].layout.title.font.size = 18
pio.templates["eleganza"].layout.title.font.color = "#222"
pio.templates["eleganza"].layout.paper_bgcolor = "rgba(0,0,0,0)"
pio.templates["eleganza"].layout.plot_bgcolor = "rgba(0,0,0,0)"
pio.templates.default = "eleganza"

# ============================================================
# EMBEDDED LOGOS (paste your full base64 back in)
# ============================================================
B64_MAIN_LOGO = ""  # <-- paste your full base64 string here
B64_SMALL_LOGO = "" # <-- optional

def b64_to_img(b64_str, width=200):
    if not b64_str:
        return
    try:
        st.image(base64.b64decode(b64_str), width=width)
    except Exception:
        pass

# ============================================================
# GOOGLE SHEETS CONNECTION
# ============================================================
@st.cache_resource(show_spinner=False)
def get_gsheet_client():
    """Connect using Streamlit secrets. Falls back to local json file."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
    except Exception:
        # fallback: local file
        with open("service_account.json", "r") as f:
            creds_dict = json.load(f)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_workbook():
    try:
        sheet_id = st.secrets["SHEET_ID"]
    except Exception:
        sheet_id = os.environ.get("SHEET_ID", "")
    client = get_gsheet_client()
    return client.open_by_key(sheet_id)

def load_df(sheet_name, default_cols=None):
    """Load a sheet as DataFrame. Creates header if empty."""
    try:
        wb = get_workbook()
        try:
            ws = wb.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            ws = wb.add_worksheet(title=sheet_name, rows=1000, cols=20)
            if default_cols:
                ws.append_row(default_cols)
        values = ws.get_all_values()
        if not values:
            return pd.DataFrame(columns=default_cols or [])
        header, *rows = values
        return pd.DataFrame(rows, columns=header)
    except Exception as e:
        st.error(f"Sheet load error ({sheet_name}): {e}")
        return pd.DataFrame(columns=default_cols or [])

def save_df(sheet_name, df):
    """Overwrite entire sheet with df."""
    wb = get_workbook()
    try:
        ws = wb.worksheet(sheet_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(title=sheet_name, rows=1000, cols=20)
    ws.update([df.columns.tolist()] + df.astype(str).values.tolist())

def append_row(sheet_name, row_dict, default_cols):
    wb = get_workbook()
    try:
        ws = wb.worksheet(sheet_name)
        values = ws.get_all_values()
        if not values:
            ws.append_row(default_cols)
            values = [default_cols]
        header = values[0]
        row = [str(row_dict.get(col, "")) for col in header]
        ws.append_row(row)
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(title=sheet_name, rows=1000, cols=20)
        ws.append_row(default_cols)
        ws.append_row([str(row_dict.get(c, "")) for c in default_cols])

def delete_row_by_id(sheet_name, id_col, id_value):
    """Delete the row where id_col == id_value."""
    wb = get_workbook()
    ws = wb.worksheet(sheet_name)
    values = ws.get_all_values()
    if not values:
        return
    header = values[0]
    if id_col not in header:
        return
    id_idx = header.index(id_col)
    for i, row in enumerate(values[1:], start=2):
        if len(row) > id_idx and row[id_idx] == str(id_value):
            ws.delete_rows(i)
            return

def update_row_by_id(sheet_name, id_col, id_value, updates: dict):
    """Update cells for a given id. Updates = {col_name: new_value}."""
    wb = get_workbook()
    ws = wb.worksheet(sheet_name)
    values = ws.get_all_values()
    if not values:
        return
    header = values[0]
    if id_col not in header:
        return
    id_idx = header.index(id_col)
    for i, row in enumerate(values[1:], start=2):
        if len(row) > id_idx and row[id_idx] == str(id_value):
            for col_name, new_val in updates.items():
                if col_name in header:
                    col_idx = header.index(col_name) + 1
                    ws.update_cell(i, col_idx, str(new_val))
            return

# ============================================================
# SCHEMA DEFINITIONS
# ============================================================
CATALOG_COLS = ["ID", "Name", "Category", "Price", "Stock", "ImageURL", "Description"]
ORDERS_COLS = ["ID", "Date", "Customer", "Product", "Qty", "Amount", "Status"]
EXPENSES_COLS = ["ID", "Date", "Category", "Description", "Amount"]

# ============================================================
# HELPERS
# ============================================================
def new_id(prefix="ID"):
    return f"{prefix}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}"

def render_logo_header():
    col1, col2 = st.columns([1, 5])
    with col1:
        b64_to_img(B64_MAIN_LOGO, width=140)
    with col2:
        st.markdown(
            "<h1 style='margin-bottom:0'>eleganza <span style='color:#E63946'>HOMES</span></h1>"
            "<p style='margin-top:0;color:#555'>Evolved Elegance ERP</p>",
            unsafe_allow_html=True,
        )

# ============================================================
# SIDEBAR NAV
# ============================================================
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Catalog", "Orders", "Expenses", "Reports"],
)

# ============================================================
# PAGE: DASHBOARD
# ============================================================
if page == "Dashboard":
    render_logo_header()
    st.markdown("---")

    catalog_df = load_df("Catalog", CATALOG_COLS)
    orders_df = load_df("Orders", ORDERS_COLS)
    expenses_df = load_df("Expenses", EXPENSES_COLS)

    # KPIs
    total_products = len(catalog_df)
    total_orders = len(orders_df)
    try:
        revenue = pd.to_numeric(orders_df.get("Amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    except Exception:
        revenue = 0
    try:
        expense_total = pd.to_numeric(expenses_df.get("Amount", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
    except Exception:
        expense_total = 0
    profit = revenue - expense_total

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🛋️ Products", total_products)
    c2.metric("📦 Orders", total_orders)
    c3.metric("💰 Revenue", f"{revenue:,.0f} ETB")
    c4.metric("📈 Profit", f"{profit:,.0f} ETB")

    st.markdown("---")
    colA, colB = st.columns(2)

    with colA:
        st.subheader("Revenue vs Expenses")
        fig = go.Figure(data=[
            go.Bar(name="Revenue", x=["Total"], y=[revenue], marker_color="#2A9D8F"),
            go.Bar(name="Expenses", x=["Total"], y=[expense_total], marker_color="#E63946"),
        ])
        fig.update_layout(barmode="group", height=350)
        st.plotly_chart(fig, use_container_width=True)

    with colB:
        st.subheader("Catalog by Category")
        if not catalog_df.empty and "Category" in catalog_df:
            cat_counts = catalog_df["Category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]
            fig = px.pie(
                cat_counts, names="Category", values="Count",
                color_discrete_sequence=ELEGANZA_COLORS, hole=0.35,
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No catalog data yet.")

    st.markdown("---")
    st.subheader("Orders Timeline")
    if not orders_df.empty and "Date" in orders_df and "Amount" in orders_df:
        try:
            odf = orders_df.copy()
            odf["Amount"] = pd.to_numeric(odf["Amount"], errors="coerce").fillna(0)
            odf["Date"] = pd.to_datetime(odf["Date"], errors="coerce")
            odf = odf.dropna(subset=["Date"]).sort_values("Date")
            fig = px.line(odf, x="Date", y="Amount", markers=True,
                          color_discrete_sequence=["#9B5DE5"])
            fig.update_traces(line=dict(width=3), marker=dict(size=9))
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not build timeline: {e}")
    else:
        st.info("No orders yet.")

# ============================================================
# PAGE: CATALOG  (with Edit name / image / details + Delete)
# ============================================================
elif page == "Catalog":
    render_logo_header()
    st.markdown("---")
    st.subheader("🛋️ Product Catalog")

    catalog_df = load_df("Catalog", CATALOG_COLS)

    tab_view, tab_add, tab_edit = st.tabs(["📋 View", "➕ Add Product", "✏️ Edit / Delete"])

    # ---------- VIEW ----------
    with tab_view:
        if catalog_df.empty:
            st.info("No products yet. Add one in the 'Add Product' tab.")
        else:
            st.dataframe(catalog_df, use_container_width=True, hide_index=True)

            # thumbnails
            st.markdown("### Product Gallery")
            cols = st.columns(4)
            for i, (_, row) in enumerate(catalog_df.iterrows()):
                with cols[i % 4]:
                    img = row.get("ImageURL", "")
                    if img:
                        try:
                            st.image(img, caption=row.get("Name", ""), use_container_width=True)
                        except Exception:
                            st.write("🖼️ image error")
                    else:
                        st.markdown(
                            f"<div style='border:1px dashed #bbb;border-radius:8px;"
                            f"height:120px;display:flex;align-items:center;"
                            f"justify-content:center;color:#888'>No image</div>",
                            unsafe_allow_html=True,
                        )
                    st.caption(f"**{row.get('Name','')}** — {row.get('Price','')} ETB")

    # ---------- ADD ----------
    with tab_add:
        with st.form("add_product_form", clear_on_submit=True):
            name = st.text_input("Product name")
            category = st.text_input("Category")
            price = st.number_input("Price (ETB)", min_value=0.0, step=1.0)
            stock = st.number_input("Stock", min_value=0, step=1)
            image_url = st.text_input("Image URL (Google Drive / direct link)")
            description = st.text_area("Description")
            submitted = st.form_submit_button("➕ Add Product")
            if submitted:
                if not name.strip():
                    st.error("Name is required.")
                else:
                    row = {
                        "ID": new_id("PRD"),
                        "Name": name.strip(),
                        "Category": category.strip(),
                        "Price": price,
                        "Stock": stock,
                        "ImageURL": image_url.strip(),
                        "Description": description.strip(),
                    }
                    try:
                        append_row("Catalog", row, CATALOG_COLS)
                        st.success(f"Added '{name}'. Refresh to see it.")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"Save failed: {e}")

    # ---------- EDIT / DELETE ----------
    with tab_edit:
        if catalog_df.empty:
            st.info("Nothing to edit yet.")
        else:
            ids = catalog_df["ID"].tolist()
            labels = [f"{r['Name']}  ({r['ID']})" for _, r in catalog_df.iterrows()]
            selection = st.selectbox("Select a product", options=range(len(ids)),
                                     format_func=lambda i: labels[i])
            chosen_id = ids[selection]
            chosen = catalog_df[catalog_df["ID"] == chosen_id].iloc[0]

            with st.form("edit_product_form"):
                st.markdown("**Edit fields** (leave unchanged to keep current value)")
                new_name = st.text_input("Name", value=chosen.get("Name", ""))
                new_category = st.text_input("Category", value=chosen.get("Category", ""))
                new_price = st.number_input(
                    "Price (ETB)",
                    min_value=0.0,
                    step=1.0,
                    value=float(chosen.get("Price") or 0),
                )
                new_stock = st.number_input(
                    "Stock",
                    min_value=0,
                    step=1,
                    value=int(float(chosen.get("Stock") or 0)),
                )
                new_image = st.text_input("Image URL", value=chosen.get("ImageURL", ""))
                new_desc = st.text_area("Description", value=chosen.get("Description", ""))
                col_save, col_del = st.columns([1, 1])
                save = col_save.form_submit_button("💾 Save Changes")
                delete = col_del.form_submit_button("🗑️ Delete Product")

            if save:
                try:
                    update_row_by_id("Catalog", "ID", chosen_id, {
                        "Name": new_name.strip(),
                        "Category": new_category.strip(),
                        "Price": new_price,
                        "Stock": new_stock,
                        "ImageURL": new_image.strip(),
                        "Description": new_desc.strip(),
                    })
                    st.success("Saved.")
                    st.cache_resource.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

            if delete:
                try:
                    delete_row_by_id("Catalog", "ID", chosen_id)
                    st.success(f"Deleted '{chosen.get('Name','')}'.")
                    st.cache_resource.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")

            # image preview
            if chosen.get("ImageURL"):
                st.markdown("**Current image preview:**")
                try:
                    st.image(chosen["ImageURL"], width=250)
                except Exception:
                    st.write("Could not load image.")

# ============================================================
# PAGE: ORDERS
# ============================================================
elif page == "Orders":
    render_logo_header()
    st.subheader("📦 Orders")

    orders_df = load_df("Orders", ORDERS_COLS)
    catalog_df = load_df("Catalog", CATALOG_COLS)

    with st.form("add_order", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            customer = st.text_input("Customer name")
            product = st.selectbox(
                "Product",
                catalog_df["Name"].tolist() if not catalog_df.empty else ["—"],
            )
            qty = st.number_input("Quantity", min_value=1, step=1, value=1)
        with col2:
            amount = st.number_input("Amount (ETB)", min_value=0.0, step=1.0)
            status = st.selectbox("Status", ["Pending", "Paid", "Delivered", "Cancelled"])
        if st.form_submit_button("➕ Add Order"):
            row = {
                "ID": new_id("ORD"),
                "Date": datetime.date.today().isoformat(),
                "Customer": customer.strip(),
                "Product": product,
                "Qty": qty,
                "Amount": amount,
                "Status": status,
            }
            try:
                append_row("Orders", row, ORDERS_COLS)
                st.success("Order added.")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Save failed: {e}")

    st.markdown("---")
    if orders_df.empty:
        st.info("No orders yet.")
    else:
        st.dataframe(orders_df, use_container_width=True, hide_index=True)

        if "Status" in orders_df:
            status_counts = orders_df["Status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig = px.bar(status_counts, x="Status", y="Count",
                         color="Status",
                         color_discrete_sequence=ELEGANZA_COLORS)
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE: EXPENSES
# ============================================================
elif page == "Expenses":
    render_logo_header()
    st.subheader("💸 Expenses")

    expenses_df = load_df("Expenses", EXPENSES_COLS)

    with st.form("add_expense", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            category = st.text_input("Category")
            description = st.text_input("Description")
        with col2:
            amount = st.number_input("Amount (ETB)", min_value=0.0, step=1.0)
        if st.form_submit_button("➕ Add Expense"):
            row = {
                "ID": new_id("EXP"),
                "Date": datetime.date.today().isoformat(),
                "Category": category.strip(),
                "Description": description.strip(),
                "Amount": amount,
            }
            try:
                append_row("Expenses", row, EXPENSES_COLS)
                st.success("Expense added.")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Save failed: {e}")

    st.markdown("---")
    if expenses_df.empty:
        st.info("No expenses yet.")
    else:
        st.dataframe(expenses_df, use_container_width=True, hide_index=True)
        exp = expenses_df.copy()
        exp["Amount"] = pd.to_numeric(exp["Amount"], errors="coerce").fillna(0)
        by_cat = exp.groupby("Category", as_index=False)["Amount"].sum()
        if not by_cat.empty:
            fig = px.pie(by_cat, names="Category", values="Amount",
                         color_discrete_sequence=ELEGANZA_COLORS, hole=0.3)
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE: REPORTS
# ============================================================
elif page == "Reports":
    render_logo_header()
    st.subheader("📊 Reports")

    catalog_df = load_df("Catalog", CATALOG_COLS)
    orders_df = load_df("Orders", ORDERS_COLS)
    expenses_df = load_df("Expenses", EXPENSES_COLS)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Top Products by Revenue")
        if not orders_df.empty and "Product" in orders_df and "Amount" in orders_df:
            o = orders_df.copy()
            o["Amount"] = pd.to_numeric(o["Amount"], errors="coerce").fillna(0)
            top = o.groupby("Product", as_index=False)["Amount"].sum().sort_values("Amount", ascending=False).head(10)
            fig = px.bar(top, x="Amount", y="Product", orientation="h",
                         color="Amount", color_continuous_scale="Turbo")
            fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No order data.")

    with col2:
        st.markdown("### Expense Breakdown")
        if not expenses_df.empty:
            e = expenses_df.copy()
            e["Amount"] = pd.to_numeric(e["Amount"], errors="coerce").fillna(0)
            by_cat = e.groupby("Category", as_index=False)["Amount"].sum()
            fig = px.bar(by_cat, x="Category", y="Amount", color="Category",
                         color_discrete_sequence=ELEGANZA_COLORS)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expenses.")

    st.markdown("---")
    st.markdown("### Stock Levels")
    if not catalog_df.empty:
        c = catalog_df.copy()
        c["Stock"] = pd.to_numeric(c["Stock"], errors="coerce").fillna(0)
        fig = px.bar(c, x="Name", y="Stock", color="Category",
                     color_discrete_sequence=ELEGANZA_COLORS)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No products.")

    # Export
    st.markdown("---")
    st.markdown("### Export")
    if st.button("📄 Download Catalog CSV"):
        csv = catalog_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "catalog.csv", "text/csv")
