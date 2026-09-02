# Sunbird Trust — Inventory Management
# Editable Streamlit inventory dashboard with monthly tracking.
# 
# Run:
#     pip install -r requirements.txt
#     streamlit run inventory_app.py
# 
# Data lives in inventory_data.json next to this file. Every edit made in the
# app (new months, quantity changes, POC updates, new locations) is written
# straight back to that file, so your changes persist between sessions.

import json
import os
import copy
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory_data.json")

MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]

COLORS = {
    "paper": "#F5F0E4", "paper_deep": "#EDE5D3", "card": "#FDFBF6",
    "ink": "#26241D", "ink_soft": "#5B5748",
    "indigo": "#33456B", "indigo_deep": "#1F2C47",
    "rust": "#B54A2C", "sage": "#5C7A5A", "gold": "#B3872B",
    "line": "#DDD2B8",
}

NOTE_LABEL = {"loss": "Loss / damage", "transfer": "Transfer",
              "consumption": "Consumption", "other": "Other"}
NOTE_COLOR = {"loss": COLORS["rust"], "transfer": COLORS["indigo"],
              "consumption": COLORS["gold"], "other": "#8a8371"}
NOTE_BG_COLOR = {
    "loss": "rgba(181, 74, 44, 0.1)",
    "transfer": "rgba(51, 69, 107, 0.1)",
    "consumption": "rgba(179, 135, 43, 0.1)",
    "other": "rgba(138, 131, 113, 0.1)"
}

EMPTY_RECORD = {
    "opening_new": 0, "opening_used": 0, "opening_total": 0,
    "add_new": 0, "del_new": 0, "add_used": 0, "del_used": 0,
    "closing_new": 0, "closing_used": 0, "closing_total": 0, "notes": "",
}

# ----------------------------------------------------------------------
# DATA LAYER
# ----------------------------------------------------------------------

def load_data():
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)


def init_state():
    if "data" not in st.session_state:
        st.session_state.data = load_data()
    if "selected_location_key" not in st.session_state:
        st.session_state.selected_location_key = None
    if "current_item" not in st.session_state:
        items = list(st.session_state.data["items"].keys())
        st.session_state.current_item = items[0] if items else None
    if "log_filter" not in st.session_state:
        st.session_state.log_filter = "all"


def loc_key(loc):
    return f"{loc.get('location_name','')}|{loc.get('address','')}"


def display_name(loc):
    return loc.get("location_name") or loc.get("address") or "Unnamed location"


def item_order():
    return list(st.session_state.data["items"].keys())


def months_for_item(item):
    recs = st.session_state.data["items"].get(item, [])
    present = {r["month"] for r in recs}
    return [m for m in MONTH_ORDER if m in present]


def latest_month_for_item(item):
    months = months_for_item(item)
    return months[-1] if months else None


def classify_note(text):
    t = (text or "").lower()
    if "eaten" in t or "unusable" in t or "damage" in t:
        return "loss"
    if "taken to" in t or "sent" in t or "received" in t or "office" in t:
        return "transfer"
    if "hostel use" in t or "used for" in t:
        return "consumption"
    return "other"


def all_events():
    out = []
    for item in item_order():
        for r in st.session_state.data["items"][item]:
            if str(r.get("notes", "")).strip():
                out.append({
                    "item": item, "month": r["month"], "year": r.get("year", ""),
                    "location": r.get("location_name") or r.get("address"),
                    "address": r.get("address"), "notes": r["notes"],
                    "type": classify_note(r["notes"]),
                    "closing_total": r.get("closing_total", 0),
                    "month_idx": MONTH_ORDER.index(r["month"]) if r["month"] in MONTH_ORDER else -1,
                })
    out.sort(key=lambda e: e["month_idx"], reverse=True)
    return out


def stock_total_for_location(loc):
    total = 0
    for item in item_order():
        lm = latest_month_for_item(item)
        for r in st.session_state.data["items"][item]:
            if r["month"] == lm and r.get("address") == loc.get("address") \
               and (r.get("location_name") or "") == (loc.get("location_name") or ""):
                total += r.get("closing_total", 0) or 0
    return total

# ----------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------

def inject_css():
    st.markdown(f"""<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; color: {COLORS['ink']}; }}
.stApp, div[data-testid="stAppViewContainer"] {{ background-color: {COLORS['paper']} !important; }}
h1, h2, h3 {{ font-family: 'Fraunces', serif !important; }}
.block-container, div[data-testid="stAppViewBlockContainer"] {{ padding-top: 3.5rem !important; max-width: 1180px; }}
.eyebrow {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: {COLORS['sage']}; margin-bottom: 4px; }}
.masthead-title {{ font-family:'Fraunces',serif; font-weight:600; font-size:36px; margin:0; }}
.masthead-sub {{ color:{COLORS['ink_soft']}; font-size:13px; margin-top:2px; }}
.masthead-separator {{ margin: 14px 0 20px; }}
.masthead-separator .solid-line {{ height: 1px; background-color: {COLORS['ink']}; opacity: 0.15; margin-bottom: 8px; }}
.masthead-separator .dashed-line {{ height: 1px; border-top: 1px dashed {COLORS['ink']}; opacity: 0.25; }}
.kpi-card {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; padding:14px 16px; border-left:3px solid {COLORS['indigo']}; }}
.kpi-card.warn {{ border-left-color:{COLORS['rust']}; }}
.kpi-card.good {{ border-left-color:{COLORS['sage']}; }}
.kpi-card.gold {{ border-left-color:{COLORS['gold']}; }}
.kpi-label {{ font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:{COLORS['ink_soft']}; margin-bottom:6px; }}
.kpi-value {{ font-family:'Fraunces',serif; font-size:28px; font-weight:600; line-height:1; }}
.kpi-foot {{ font-size:11px; color:{COLORS['ink_soft']}; margin-top:6px; font-family:'JetBrains Mono',monospace; }}
div[data-baseweb="tab-list"] {{ gap: 12px !important; border-bottom: none !important; padding-bottom: 8px !important; }}
button[data-baseweb="tab"] {{ font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; font-weight: 500 !important; letter-spacing: .03em !important; background-color: transparent !important; border: 1px solid {COLORS['line']} !important; border-radius: 999px !important; padding: 8px 18px !important; color: {COLORS['ink_soft']} !important; transition: all 0.2s ease !important; height: auto !important; }}
button[data-baseweb="tab"]:hover {{ background-color: {COLORS['paper_deep']} !important; color: {COLORS['ink']} !important; border-color: {COLORS['ink_soft']} !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{ background-color: {COLORS['indigo']} !important; color: white !important; border-color: {COLORS['indigo']} !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; }}
button[data-baseweb="tab"] > div {{ border-bottom: none !important; }}
div[data-baseweb="tab-highlight-container"] {{ display: none !important; }}
div[data-baseweb="tab-border"] {{ display: none !important; }}
div[role="tablist"] {{ border-bottom: none !important; }}
div[role="tablist"] > div {{ border-bottom: none !important; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background-color: {COLORS['card']} !important; border: 1px solid {COLORS['line']} !important; border-radius: 10px !important; padding: 20px 24px !important; margin-bottom: 16px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important; }}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {{ padding: 12px 14px !important; margin-bottom: 0px !important; }}
.panel-title {{ font-family:'Fraunces',serif; font-size:17px; font-weight:600; margin-bottom:2px; color: {COLORS['ink']}; }}
.panel-sub {{ color:{COLORS['ink_soft']}; font-size:12px; margin-bottom:14px; }}
.loc-card {{ background:{COLORS['card']}; border:1px solid {COLORS['line']}; border-radius:10px; padding:16px 18px; margin-bottom:12px; box-shadow: 0 1px 2px rgba(0,0,0,0.01); }}
.loc-card .name {{ font-family:'Fraunces',serif; font-weight:600; font-size:16px; color:{COLORS['ink']}; }}
.loc-card .addr {{ color:{COLORS['ink_soft']}; font-size:12px; margin-top:2px; margin-bottom:14px; }}
.loc-card .poc-row {{ display:flex; justify-content:space-between; align-items:center; font-size:12px; color:{COLORS['ink']}; margin-bottom:6px; }}
.loc-card .poc-row a {{ color:{COLORS['ink_soft']}; text-decoration:none; }}
.loc-card .poc-row a:hover {{ color:{COLORS['indigo']}; text-decoration:underline; }}
.loc-card .stock-total {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:{COLORS['sage']}; margin-top:4px; }}
.no-poc {{ color:{COLORS['rust']}; font-size:11px; font-family:'JetBrains Mono',monospace; }}
.tag {{ display:inline-block; font-family:'JetBrains Mono',monospace; font-size:10px; font-weight:600; padding:2px 8px; border-radius:999px; letter-spacing:.03em; }}
.log-item {{ padding: 10px 0; border-bottom: 1px solid {COLORS['paper_deep']}; font-size:13px; }}
.log-item:last-child {{ border-bottom: none; }}
.log-when {{ font-family:'JetBrains Mono',monospace; font-size:10.5px; color:{COLORS['ink_soft']}; }}
.custom-table {{ width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; }}
.custom-table th {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500; letter-spacing: .08em; color: {COLORS['ink_soft']}; text-align: left; padding: 8px 0; border-bottom: 1px solid {COLORS['line']}; }}
.custom-table td {{ padding: 10px 0; border-bottom: 1px solid {COLORS['paper_deep']}; vertical-align: middle; }}
.custom-table tr:last-child td {{ border-bottom: none; }}
.custom-table .loc-name {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 14px; color: {COLORS['ink']}; }}
.custom-table .loc-addr {{ font-family: 'Inter', sans-serif; font-size: 12px; color: {COLORS['ink_soft']}; margin-top: 2px; }}
.custom-table .val {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; font-weight: 500; color: {COLORS['ink']}; }}

/* Style horizontal radio buttons as modern pill selectors */
div[data-testid="stRadio"] > div[role="radiogroup"] {{ gap: 8px !important; border-bottom: none !important; }}
div[data-testid="stRadio"] label[data-baseweb="radio"] {{ background-color: transparent !important; border: 1px solid {COLORS['line']} !important; border-radius: 999px !important; padding: 6px 14px !important; color: {COLORS['ink_soft']} !important; transition: all 0.2s ease !important; margin-right: 0px !important; }}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {{ background-color: {COLORS['paper_deep']} !important; color: {COLORS['ink']} !important; border-color: {COLORS['ink_soft']} !important; }}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{ background-color: {COLORS['indigo']} !important; color: white !important; border-color: {COLORS['indigo']} !important; }}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div {{ color: white !important; }}
div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{ display: none !important; }}
</style>
    """, unsafe_allow_html=True)


def tag_html(note_type):
    return f'<span class="tag" style="background:{NOTE_BG_COLOR[note_type]}; color:{NOTE_COLOR[note_type]}; border: 1px solid {NOTE_COLOR[note_type]}33;">{NOTE_LABEL[note_type]}</span>'


def kpi_card(label, value, foot, kind=""):
    st.markdown(f"""
    <div class="kpi-card {kind}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-foot">{foot}</div>
    </div>
    """, unsafe_allow_html=True)


def tag_html(note_type):
    return f'<span class="tag" style="background:{NOTE_COLOR[note_type]}">{NOTE_LABEL[note_type]}</span>'

# ----------------------------------------------------------------------
# OVERVIEW TAB
# ----------------------------------------------------------------------

def render_overview():
    data = st.session_state.data
    items = item_order()
    locations = data["locations"]

    total_stock = 0
    by_item = {}
    for item in items:
        lm = latest_month_for_item(item)
        s = sum(r.get("closing_total", 0) or 0 for r in data["items"][item] if r["month"] == lm)
        by_item[item] = s
        total_stock += s

    events = all_events()
    loss_events = [e for e in events if e["type"] == "loss"]
    poc_count = sum(1 for l in locations if l.get("poc_name"))
    no_poc = len(locations) - poc_count

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        # Changed "good" to "" so it uses default indigo left border color (blue) to match the mockup
        kpi_card("Total units in stock", f"{total_stock:,}", f"across {len(items)} categories, latest month each", "")
    with c2:
        foot = f"{poc_count} with a named POC" + (f" · {no_poc} without" if no_poc else "")
        kpi_card("Partner locations", len(locations), foot)
    with c3:
        kpi_card("Loss / damage events", len(loss_events), f"of {len(events)} logged notes total", "warn" if loss_events else "")
    with c4:
        kpi_card("Categories tracked", len(items), "monthly coverage varies by item", "gold")

    st.write("")
    col_a, col_b = st.columns([1.3, 1])
    with col_a:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Stock on hand, by category</div>'
                        '<div class="panel-sub">Closing stock at each category\'s latest recorded month</div>', unsafe_allow_html=True)
            
            filter_mode = st.selectbox(
                "Select Stock Category",
                ["Both (New & Opened)", "New & Unopened", "Opened & Used"],
                key="overview_stock_filter",
                label_visibility="collapsed"
            )

            if filter_mode == "Both (New & Opened)":
                by_item_new = {item: sum(r.get("closing_new", 0) or 0 for r in data["items"][item] if r["month"] == latest_month_for_item(item)) for item in items}
                by_item_used = {item: sum(r.get("closing_used", 0) or 0 for r in data["items"][item] if r["month"] == latest_month_for_item(item)) for item in items}
                fig = go.Figure()
                fig.add_trace(go.Bar(x=list(items), y=[by_item_new[i] for i in items], name="New & Unopened", marker_color=COLORS["indigo"]))
                fig.add_trace(go.Bar(x=list(items), y=[by_item_used[i] for i in items], name="Opened & Used", marker_color=COLORS["gold"]))
                fig.update_layout(barmode="stack", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0))
            elif filter_mode == "New & Unopened":
                by_item_new = {item: sum(r.get("closing_new", 0) or 0 for r in data["items"][item] if r["month"] == latest_month_for_item(item)) for item in items}
                fig = go.Figure(go.Bar(
                    x=list(items), y=[by_item_new[i] for i in items],
                    marker_color=COLORS["indigo"], name="New & Unopened"
                ))
            else:
                by_item_used = {item: sum(r.get("closing_used", 0) or 0 for r in data["items"][item] if r["month"] == latest_month_for_item(item)) for item in items}
                fig = go.Figure(go.Bar(
                    x=list(items), y=[by_item_used[i] for i in items],
                    marker_color=COLORS["gold"], name="Opened & Used"
                ))

            fig.update_layout(
                height=300, margin=dict(l=20, r=10, t=15, b=15),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="JetBrains Mono", size=11, color=COLORS["ink_soft"]),
                yaxis=dict(
                    gridcolor=COLORS["paper_deep"],
                    zeroline=True,
                    zerolinecolor=COLORS["paper_deep"],
                    tickfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink_soft"]),
                ),
                xaxis=dict(
                    tickfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink_soft"]),
                    linecolor=COLORS["paper_deep"],
                ),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Locations by total stock</div>'
                        '<div class="panel-sub">All categories combined (New vs. Opened stock, latest month)</div>', unsafe_allow_html=True)
            
            # Calculate New, Used, and Total per location
            loc_rows = []
            for l in locations:
                name = display_name(l)
                addr = l.get("address", "")
                
                new_tot = 0
                used_tot = 0
                for item in items:
                    lm = latest_month_for_item(item)
                    for r in data["items"][item]:
                        if r["month"] == lm and r.get("address") == l.get("address") \
                           and (r.get("location_name") or "") == (l.get("location_name") or ""):
                            new_tot += int(r.get("closing_new", 0) or 0)
                            used_tot += int(r.get("closing_used", 0) or 0)
                tot = new_tot + used_tot
                loc_rows.append((name, addr, new_tot, used_tot, tot))
            
            loc_rows.sort(key=lambda x: -x[4])
            
            table_html = '<div style="max-height: 280px; overflow-y: auto;"><table class="custom-table"><thead><tr><th>LOCATION</th><th style="text-align:right;">NEW</th><th style="text-align:right;">OPENED</th><th style="text-align:right;">TOTAL</th></tr></thead><tbody>'
            for name, addr, n_val, u_val, t_val in loc_rows:
                table_html += f'<tr><td><div class="loc-name">{name}</div><div class="loc-addr">{addr}</div></td><td style="text-align:right;" class="val">{n_val:,}</td><td style="text-align:right;" class="val">{u_val:,}</td><td style="text-align:right;" class="val" style="font-weight:600;">{t_val:,}</td></tr>'
            table_html += '</tbody></table></div>'
            st.markdown(table_html, unsafe_allow_html=True)

    col_c, col_d = st.columns([1.3, 1])
    with col_c:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Total stock trend</div>'
                        '<div class="panel-sub">Combined closing stock across all categories, by month</div>', unsafe_allow_html=True)
            months_used = [m for m in MONTH_ORDER if any(m in months_for_item(i) for i in items)]
            trend = []
            for m in months_used:
                s = 0
                for item in items:
                    s += sum(r.get("closing_total", 0) or 0 for r in data["items"][item] if r["month"] == m)
                trend.append(s)
            fig2 = go.Figure(go.Scatter(
                x=months_used, y=trend, mode="lines+markers", fill="tozeroy",
                line=dict(color=COLORS["sage"], width=2.5, shape="spline"),
                marker=dict(size=7, color=COLORS["sage"]),
                fillcolor="rgba(92,122,90,.12)",
            ))
            fig2.update_layout(
                height=280, margin=dict(l=20, r=10, t=15, b=15),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="JetBrains Mono", size=11, color=COLORS["ink_soft"]),
                yaxis=dict(
                    gridcolor=COLORS["paper_deep"],
                    zeroline=True,
                    zerolinecolor=COLORS["paper_deep"],
                    tickfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink_soft"]),
                ),
                xaxis=dict(
                    tickfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink_soft"]),
                    linecolor=COLORS["paper_deep"],
                ),
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    with col_d:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Recent activity</div>'
                        '<div class="panel-sub">Latest logged additions, deletions &amp; transfers</div>', unsafe_allow_html=True)
            if not events:
                st.markdown('<div class="log-item" style="border-bottom:none;">No logged events</div>', unsafe_allow_html=True)
            for e in events[:6]:
                color = NOTE_COLOR[e['type']]
                st.markdown(f"""
                <div class="log-item">
                  <div style="display:flex; align-items:flex-start; gap:8px;">
                    <span style="color:{color}; font-size:12px; margin-top:2px;">●</span>
                    <div>
                      <b>{e['location']}</b> — {e['item']}: {e['notes']}<br>
                      <span class="log-when">{e['month']} {e['year']}</span> &nbsp; {tag_html(e['type'])}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

# ----------------------------------------------------------------------
# LOCATIONS TAB
# ----------------------------------------------------------------------

def render_locations():
    data = st.session_state.data
    locations = data["locations"]

    with st.container(border=True):
        st.markdown('<div class="panel-title">Location directory</div>'
                    '<div class="panel-sub">Point-of-contact register for every partner location. Click a card for the full inventory.</div>', unsafe_allow_html=True)

        search = st.text_input("Search by location, address, or POC name", "", label_visibility="collapsed",
                                placeholder="Search by location, address, or POC name…")
        f = search.strip().lower()
        filtered = [l for l in locations if not f or f in (l.get("location_name") or "").lower()
                    or f in (l.get("address") or "").lower() or f in (l.get("poc_name") or "").lower()]

        if not filtered:
            st.markdown('<div class="log-item" style="border-bottom:none;">No matching locations</div>', unsafe_allow_html=True)
        else:
            cols = st.columns(3)
            for i, loc in enumerate(filtered):
                with cols[i % 3]:
                    total = stock_total_for_location(loc)
                    poc_html = (f'<div class="poc-row"><span>{loc["poc_name"]}</span>'
                                f'<a href="tel:{loc.get("poc_contact","")}">{loc.get("poc_contact","")}</a></div>'
                                if loc.get("poc_name") else '<div class="poc-row"><span class="no-poc">No POC on file</span></div>')
                    st.markdown(f"""
                    <div class="loc-card">
                      <div class="name">{display_name(loc)}</div>
                      <div class="addr">{loc.get('address','')}</div>
                      {poc_html}
                      <div class="stock-total">{total:,} units on hand</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ---- Detail viewer ----
    with st.container(border=True):
        st.markdown('<div class="panel-title">Location detail</div>'
                    '<div class="panel-sub">Select a location to see its full inventory and notes history.</div>', unsafe_allow_html=True)
        options = {display_name(l) + " — " + l.get("address", ""): loc_key(l) for l in locations}
        if options:
            chosen_label = st.selectbox("Select a location", list(options.keys()), label_visibility="collapsed")
            chosen_key = options[chosen_label]
            loc = next(l for l in locations if loc_key(l) == chosen_key)

            col1, col2 = st.columns([1.6, 1])
            with col1:
                st.markdown(f"**{display_name(loc)}**  \n{loc.get('address','')}")
                if loc.get("poc_name"):
                    st.markdown(f"POC: **{loc['poc_name']}** · [{loc.get('poc_contact','')}](tel:{loc.get('poc_contact','')})")
                else:
                    st.markdown('<span class="no-poc">No point of contact on file</span>', unsafe_allow_html=True)

                rows = []
                # Determine all active months present in data
                all_months = [m for m in MONTH_ORDER if any(any(r["month"] == m for r in data["items"][i]) for i in item_order())]
                month_cols = [m[:3] for m in all_months]

                for item in item_order():
                    recs = [r for r in data["items"][item]
                            if r.get("address") == loc.get("address") and (r.get("location_name") or "") == (loc.get("location_name") or "")]
                    if not recs:
                        continue
                    lm = latest_month_for_item(item)
                    lm_rec = next((r for r in recs if r["month"] == lm), None)

                    row = {
                        "Category": item,
                        "Latest (New)": int(lm_rec["closing_new"]) if lm_rec else 0,
                        "Latest (Opened)": int(lm_rec["closing_used"]) if lm_rec else 0,
                        "Latest Total": int(lm_rec["closing_total"]) if lm_rec else 0,
                    }

                    # Add column per month
                    by_m_rec = {r["month"]: r for r in recs}
                    for m in all_months:
                        r_m = by_m_rec.get(m)
                        row[m[:3]] = int(r_m["closing_total"]) if r_m else 0

                    rows.append(row)

                if rows:
                    cols_order = ["Category", "Latest (New)", "Latest (Opened)", "Latest Total"] + month_cols
                    st.dataframe(pd.DataFrame(rows)[cols_order], hide_index=True, use_container_width=True)

            with col2:
                loc_events = [e for e in all_events() if e["address"] == loc.get("address")]
                st.markdown("**Notes & events**")
                if not loc_events:
                    st.markdown('<div class="log-item" style="border-bottom:none;">No notes logged for this location</div>', unsafe_allow_html=True)
                for e in loc_events:
                    color = NOTE_COLOR[e['type']]
                    st.markdown(f"""
                    <div class="log-item">
                      <div style="display:flex; align-items:flex-start; gap:8px;">
                        <span style="color:{color}; font-size:12px; margin-top:2px;">●</span>
                        <div>
                          <b>{e['item']}</b>: {e['notes']}<br>
                          <span class="log-when">{e['month']} {e['year']}</span> &nbsp; {tag_html(e['type'])}
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

    # ---- Editable directory ----
    with st.expander("✎ Edit directory (add locations, update contacts)"):
        df = pd.DataFrame([{
            "location_name": l.get("location_name", ""),
            "address": l.get("address", ""),
            "poc_name": l.get("poc_name", ""),
            "poc_contact": l.get("poc_contact", ""),
        } for l in locations])
        edited = st.data_editor(
            df, num_rows="dynamic", use_container_width=True, key="loc_editor",
            column_config={
                "location_name": "Location Name", "address": "Address",
                "poc_name": "POC Name", "poc_contact": "POC Contact",
            },
        )
        if st.button("Save directory changes", type="primary"):
            new_locations = []
            for _, row in edited.iterrows():
                if not row["address"] and not row["location_name"]:
                    continue
                new_locations.append({
                    "location_name": row["location_name"] or "",
                    "address": row["address"] or "",
                    "poc_name": row["poc_name"] or "",
                    "poc_contact": str(row["poc_contact"]) if pd.notna(row["poc_contact"]) else "",
                })
            st.session_state.data["locations"] = new_locations
            save_data(st.session_state.data)
            st.success("Directory updated.")
            st.rerun()

# ----------------------------------------------------------------------
# INVENTORY TAB
# ----------------------------------------------------------------------

def render_inventory():
    data = st.session_state.data
    items = item_order()

    with st.container(border=True):
        st.markdown('<div class="panel-title">Inventory by category</div>'
                    '<div class="panel-sub">Select a category to see its trend and per-location breakdown</div>', unsafe_allow_html=True)

        current = st.radio("Category", items, horizontal=True,
                            index=items.index(st.session_state.current_item) if st.session_state.current_item in items else 0,
                            label_visibility="collapsed")
        st.session_state.current_item = current

        months = months_for_item(current)
        new_s, used_s, total_s = [], [], []
        for m in months:
            recs = [r for r in data["items"][current] if r["month"] == m]
            new_s.append(sum(r.get("closing_new", 0) or 0 for r in recs))
            used_s.append(sum(r.get("closing_used", 0) or 0 for r in recs))
            total_s.append(sum(r.get("closing_total", 0) or 0 for r in recs))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=months, y=new_s, name="New & unopened", line=dict(color=COLORS["indigo"], shape="spline")))
        fig.add_trace(go.Scatter(x=months, y=used_s, name="Opened & used", line=dict(color=COLORS["gold"], shape="spline")))
        fig.add_trace(go.Scatter(x=months, y=total_s, name="Total", line=dict(color=COLORS["sage"], dash="dash", shape="spline")))
        fig.update_layout(
            height=280, margin=dict(l=20, r=10, t=15, b=15),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="JetBrains Mono", size=11, color=COLORS["ink_soft"]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            yaxis=dict(
                gridcolor=COLORS["paper_deep"],
                zeroline=True,
                zerolinecolor=COLORS["paper_deep"],
                tickfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink_soft"]),
            ),
            xaxis=dict(
                tickfont=dict(family="JetBrains Mono", size=10, color=COLORS["ink_soft"]),
                linecolor=COLORS["paper_deep"],
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ---- Summary tables (segregated: New & Unopened vs Opened & Used vs Total) ----
    with st.container(border=True):
        st.markdown(f'<div class="panel-title">{current} — closing stock by location</div>'
                    f'<div class="panel-sub">Segregated breakdown of New &amp; Unopened stock vs. Opened &amp; Used stock across partner locations</div>', unsafe_allow_html=True)
        
        tab_new, tab_used, tab_tot = st.tabs(["📦 New & Unopened Stock", "📂 Opened & Used Stock", "📊 Total Combined Stock"])
        
        # Build matrices
        by_loc_new = {}
        by_loc_used = {}
        by_loc_tot = {}
        
        for r in data["items"][current]:
            k = (r.get("location_name") or "", r.get("address") or "")
            loc_label = r.get("location_name") or r.get("address")
            poc_label = r.get("poc_name", "")
            
            by_loc_new.setdefault(k, {"Location": loc_label, "POC": poc_label})
            by_loc_used.setdefault(k, {"Location": loc_label, "POC": poc_label})
            by_loc_tot.setdefault(k, {"Location": loc_label, "POC": poc_label})
            
            by_loc_new[k][r["month"][:3]] = int(r.get("closing_new", 0) or 0)
            by_loc_used[k][r["month"][:3]] = int(r.get("closing_used", 0) or 0)
            by_loc_tot[k][r["month"][:3]] = int(r.get("closing_total", 0) or 0)
        
        cols = ["Location", "POC"] + [m[:3] for m in months]
        
        with tab_new:
            rows_new = list(by_loc_new.values())
            if rows_new:
                df_new = pd.DataFrame(rows_new)
                for c in cols:
                    if c not in df_new.columns: df_new[c] = 0
                st.dataframe(df_new[cols], hide_index=True, use_container_width=True)
            else:
                st.info("No data available.")

        with tab_used:
            rows_used = list(by_loc_used.values())
            if rows_used:
                df_used = pd.DataFrame(rows_used)
                for c in cols:
                    if c not in df_used.columns: df_used[c] = 0
                st.dataframe(df_used[cols], hide_index=True, use_container_width=True)
            else:
                st.info("No data available.")

        with tab_tot:
            rows_tot = list(by_loc_tot.values())
            if rows_tot:
                df_tot = pd.DataFrame(rows_tot)
                for c in cols:
                    if c not in df_tot.columns: df_tot[c] = 0
                st.dataframe(df_tot[cols], hide_index=True, use_container_width=True)
            else:
                st.info("No data available.")

    # ---- Monthly data entry (editable) ----
    with st.container(border=True):
        st.markdown('<div class="panel-title">Monthly entry</div>'
                    '<div class="panel-sub">Update an existing month, or add the next one. Closing stock is calculated automatically.</div>', unsafe_allow_html=True)

        remaining_months = [m for m in MONTH_ORDER if m not in months]
        mode = st.radio("Mode", ["Edit an existing month", "Add a new month"], horizontal=True, label_visibility="collapsed")

        if mode == "Edit an existing month" and months:
            target_month = st.selectbox("Month to edit", months, index=len(months) - 1)
            target_year = next(r["year"] for r in data["items"][current] if r["month"] == target_month)
            existing = {(r.get("location_name") or "", r.get("address") or ""): r
                        for r in data["items"][current] if r["month"] == target_month}
            base_locations = data["locations"]
            edit_rows = []
            for loc in base_locations:
                k = (loc.get("location_name") or "", loc.get("address") or "")
                rec = existing.get(k, dict(EMPTY_RECORD))
                edit_rows.append({
                    "location_name": loc.get("location_name", ""), "address": loc.get("address", ""),
                    "opening_new": rec.get("opening_new", 0), "opening_used": rec.get("opening_used", 0),
                    "add_new": rec.get("add_new", 0), "del_new": rec.get("del_new", 0),
                    "add_used": rec.get("add_used", 0), "del_used": rec.get("del_used", 0),
                    "notes": rec.get("notes", ""),
                })
        elif mode == "Add a new month":
            if not remaining_months:
                st.info("All months of the year already have data for this category.")
                edit_rows = []
                target_month, target_year = None, None
            else:
                target_month = st.selectbox("New month", remaining_months)
                target_year = st.text_input("Year", value=(months and next((r["year"] for r in data["items"][current] if r["month"] == months[-1]), "2026")) or "2026")
                prev_month = months[-1] if months else None
                prev_recs = {(r.get("location_name") or "", r.get("address") or ""): r
                             for r in data["items"][current] if r["month"] == prev_month} if prev_month else {}
                edit_rows = []
                for loc in data["locations"]:
                    k = (loc.get("location_name") or "", loc.get("address") or "")
                    prev = prev_recs.get(k)
                    edit_rows.append({
                        "location_name": loc.get("location_name", ""), "address": loc.get("address", ""),
                        "opening_new": prev.get("closing_new", 0) if prev else 0,
                        "opening_used": prev.get("closing_used", 0) if prev else 0,
                        "add_new": 0, "del_new": 0, "add_used": 0, "del_used": 0, "notes": "",
                    })
        else:
            edit_rows = []
            target_month, target_year = None, None

        if edit_rows:
            edit_df = pd.DataFrame(edit_rows)
            edited = st.data_editor(
                edit_df, hide_index=True, use_container_width=True, key=f"entry_{current}_{target_month}_{mode}",
                disabled=["location_name", "address"],
                column_config={
                    "location_name": "Location", "address": "Address",
                    "opening_new": st.column_config.NumberColumn("Open · New", min_value=0),
                    "opening_used": st.column_config.NumberColumn("Open · Used", min_value=0),
                    "add_new": st.column_config.NumberColumn("+ New", min_value=0),
                    "del_new": st.column_config.NumberColumn("− New", min_value=0),
                    "add_used": st.column_config.NumberColumn("+ Used", min_value=0),
                    "del_used": st.column_config.NumberColumn("− Used", min_value=0),
                    "notes": st.column_config.TextColumn("Notes"),
                },
            )
            if st.button(f"Save {target_month} {target_year} for {current}", type="primary"):
                item_recs = data["items"][current]
                # drop any existing record for this month+location, we'll rewrite it
                item_recs = [r for r in item_recs if not (r["month"] == target_month and
                             (r.get("location_name") or "", r.get("address") or "") in
                             {(row["location_name"], row["address"]) for row in edited.to_dict("records")})]
                for row in edited.to_dict("records"):
                    closing_new = (row["opening_new"] or 0) + (row["add_new"] or 0) - (row["del_new"] or 0)
                    closing_used = (row["opening_used"] or 0) + (row["add_used"] or 0) - (row["del_used"] or 0)
                    item_recs.append({
                        "item": current, "location_name": row["location_name"], "address": row["address"],
                        "poc_name": next((l.get("poc_name", "") for l in data["locations"]
                                           if l.get("address") == row["address"]
                                           and (l.get("location_name") or "") == row["location_name"]), ""),
                        "month": target_month, "year": str(target_year),
                        "opening_new": row["opening_new"] or 0, "opening_used": row["opening_used"] or 0,
                        "opening_total": (row["opening_new"] or 0) + (row["opening_used"] or 0),
                        "add_new": row["add_new"] or 0, "del_new": row["del_new"] or 0,
                        "add_used": row["add_used"] or 0, "del_used": row["del_used"] or 0,
                        "closing_new": closing_new, "closing_used": closing_used,
                        "closing_total": closing_new + closing_used,
                        "notes": row["notes"] or "",
                    })
                data["items"][current] = item_recs
                st.session_state.data = data
                save_data(data)
                st.success(f"Saved {target_month} {target_year} for {current}.")
                st.rerun()

# ----------------------------------------------------------------------
# ACTIVITY LOG TAB
# ----------------------------------------------------------------------

def render_log():
    with st.container(border=True):
        st.markdown('<div class="panel-title">Activity log</div>'
                    '<div class="panel-sub">Every note on additions, deletions, transfers and losses across the register</div>', unsafe_allow_html=True)

        types = ["all", "loss", "transfer", "consumption", "other"]
        labels = ["All"] + [NOTE_LABEL[t] for t in types[1:]]
        choice = st.radio("Filter", labels, horizontal=True, label_visibility="collapsed")
        st.session_state.log_filter = types[labels.index(choice)]

        events = all_events()
        if st.session_state.log_filter != "all":
            events = [e for e in events if e["type"] == st.session_state.log_filter]

        if not events:
            st.markdown('<div class="log-item" style="border-bottom:none;">No events of this type</div>', unsafe_allow_html=True)
        for e in events:
            color = NOTE_COLOR[e['type']]
            st.markdown(f"""
            <div class="log-item">
              <div style="display:flex; align-items:flex-start; gap:8px;">
                <span style="color:{color}; font-size:12px; margin-top:2px;">●</span>
                <div>
                  <b>{e['location']}</b> — {e['item']}: {e['notes']}<br>
                  <span class="log-when">{e['month']} {e['year']} · closing total {e['closing_total']}</span> &nbsp; {tag_html(e['type'])}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# GOOGLE SHEET SYNC HELPER
# ----------------------------------------------------------------------

def sync_data_from_google_sheet():
    import urllib.request, urllib.parse, csv
    doc_id = '1LdH9NTofUPr5rUoFOWg4hC7z62JGPsVyrUL-9IwBsP0'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    tab_names = ['Bedsheets (Double)', 'Dohars', 'Mattresses', 'Blankets', 'Pillows', 'Pillow Cover', 'Beds']
    month_order = ["January", "February", "March", "April", "May", "June", "July", "August"]

    def parse_num(v):
        if not v: return 0
        v = str(v).strip().replace(',', '')
        if v in ('—', '-', '', 'None'): return 0
        try:
            val = float(v)
            return int(val) if val.is_integer() else val
        except:
            return 0

    locations_map = {}
    new_items_data = {}

    for item_name in tab_names:
        encoded_name = urllib.parse.quote(item_name)
        gviz_url = f'https://docs.google.com/spreadsheets/d/{doc_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}'
        req = urllib.request.Request(gviz_url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            csv_text = resp.read().decode('utf-8', errors='ignore')
            rows = list(csv.reader(csv_text.splitlines()))

        item_recs = []
        for r_idx in range(1, len(rows)):
            row = rows[r_idx]
            if not row or not any(row): continue
            loc_name = row[0].strip() if len(row) > 0 else ""
            address = row[1].strip() if len(row) > 1 else ""
            poc_name = row[2].strip() if len(row) > 2 else ""
            poc_contact = row[3].strip() if len(row) > 3 else ""
            if loc_name.lower() == 'total' or (not loc_name and not address): continue

            loc_key = (loc_name, address)
            if loc_key not in locations_map:
                locations_map[loc_key] = {
                    "location_name": loc_name, "address": address,
                    "poc_name": poc_name, "poc_contact": poc_contact
                }
            else:
                if poc_name and not locations_map[loc_key]["poc_name"]:
                    locations_map[loc_key]["poc_name"] = poc_name
                if poc_contact and not locations_map[loc_key]["poc_contact"]:
                    locations_map[loc_key]["poc_contact"] = poc_contact

            for m in range(len(month_order)):
                month_name = month_order[m]
                year = "2026"
                base_col = 4 + m * 11
                if base_col + 10 >= len(row): continue

                op_new = parse_num(row[base_col])
                op_used = parse_num(row[base_col+1])
                add_new = parse_num(row[base_col+3])
                del_new = parse_num(row[base_col+4])
                add_used = parse_num(row[base_col+5])
                del_used = parse_num(row[base_col+6])
                cl_new = parse_num(row[base_col+7])
                cl_used = parse_num(row[base_col+8])
                cl_tot = parse_num(row[base_col+9])
                notes = row[base_col+10].strip() if len(row) > base_col+10 else ""

                item_recs.append({
                    "item": item_name, "location_name": loc_name, "address": address,
                    "poc_name": poc_name, "month": month_name, "year": year,
                    "opening_new": op_new, "opening_used": op_used, "opening_total": op_new + op_used,
                    "add_new": add_new, "del_new": del_new, "add_used": add_used, "del_used": del_used,
                    "closing_new": cl_new, "closing_used": cl_used,
                    "closing_total": cl_tot if cl_tot > 0 else (cl_new + cl_used),
                    "notes": notes
                })

        new_items_data[item_name] = item_recs

    synced_data = {
        "items": new_items_data,
        "locations": list(locations_map.values())
    }
    save_data(synced_data)
    st.session_state.data = synced_data
    return True


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Sunbird Trust — Inventory Management",
                        page_icon="🧵", layout="wide")
    init_state()
    inject_css()

    items = item_order()
    months_span = sorted({m for i in items for m in months_for_item(i)}, key=MONTH_ORDER.index)
    # Formatted the span label with a simple dash and 2026 to match mockup "JAN - MAY 2026"
    span_label = f"{months_span[0][:3].upper()} - {months_span[-1][:3].upper()} 2026" if months_span else ""

    left, right = st.columns([3, 1])
    with left:
        st.markdown('<div class="eyebrow">● Sunbird Trust · Locations Stock Details</div>', unsafe_allow_html=True)
        
        t_col1, t_col2 = st.columns([0.65, 0.35], vertical_alignment="center")
        with t_col1:
            st.markdown('<div class="masthead-title">Inventory Management</div>', unsafe_allow_html=True)
        with t_col2:
            if st.button("🔄 Sync Google Sheet", key="sync_gsheet_masthead", help="Sync latest inventory data directly from Google Sheets"):
                with st.spinner("Syncing latest data from Google Sheets..."):
                    try:
                        sync_data_from_google_sheet()
                        st.toast("Successfully synced from Google Sheets!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sync error: {e}")

        st.markdown('<div class="masthead-sub">Stock &amp; contact register across partner locations — FY 2026-27</div>', unsafe_allow_html=True)
    with right:
        st.markdown(f'<div style="text-align:right;font-family:\'JetBrains Mono\',monospace;font-size:11.5px;color:{COLORS["ink_soft"]};padding-top:10px;">{span_label}<br>{len(items)} CATEGORIES</div>', unsafe_allow_html=True)

    # Replaced stitch with double separator lines (solid + dashed) to match the mockup
    st.markdown("""
    <div class="masthead-separator">
      <div class="solid-line"></div>
      <div class="dashed-line"></div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["01 · Overview", "02 · Locations", "03 · Inventory", "04 · Activity Log"])
    with tab1:
        render_overview()
    with tab2:
        render_locations()
    with tab3:
        render_inventory()
    with tab4:
        render_log()

    st.markdown(f'<div style="margin-top:24px;padding-top:10px;border-top:1px solid {COLORS["line"]};font-family:\'JetBrains Mono\',monospace;font-size:10.5px;color:{COLORS["ink_soft"]};display:flex;justify-content:space-between;">'
                 f'<span>Sunbird Trust — Locations Stock Details Register</span>'
                 f'<span>Data file: inventory_data.json</span></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
