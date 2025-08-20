import os
import pandas as pd
import numpy as np
from datetime import datetime
from urllib.error import URLError
import dash
from dash import Dash, dcc, html, Input, Output, State, dash_table
import plotly.graph_objects as go
import plotly.express as px

SNAPSHOT_PATH = os.path.join("data", "earthquakes_snapshot.csv")

def load_snapshot():
    return pd.read_csv(SNAPSHOT_PATH, parse_dates=["time"])

def try_load_usgs(days=30):
    import pandas as pd
    import urllib.request
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.csv"
    tmp = pd.read_csv(url, parse_dates=["time"])
    keep = ["time","latitude","longitude","depth","mag","place","type","id"]
    tmp = tmp[keep].copy()
    tmp["region"] = tmp["place"].str.split(",").str[-1].str.strip().fillna("Unknown")
    tmp = tmp.sort_values("time")
    return tmp

def load_data(source_mode="snapshot"):
    if source_mode == "live":
        try:
            df = try_load_usgs()
            return df
        except Exception as e:
            print("Live load failed; falling back to snapshot. Reason:", e)
            return load_snapshot()
    else:
        return load_snapshot()

# ---------- App ----------
app = Dash(__name__, title="QuakeScope: Earthquake Explorer", suppress_callback_exceptions=True)
server = app.server

# Initial load
df_init = load_snapshot()
min_date = df_init["time"].min().date()
max_date = df_init["time"].max().date()

regions = ["All"] + sorted(df_init["region"].dropna().unique().tolist())
types = sorted(df_init["type"].dropna().unique().tolist())

app.layout = html.Div([
    # Header / Navbar
    html.Div([
        html.Div([
            html.H1("QuakeScope", className="app-title"),
            html.P("Interactive dashboard to explore recent global earthquakes. "
                   "Filter by date, magnitude, depth, region, and type; then view patterns on a map and charts.",
                   className="subtitle"),
        ], className="header-left"),
        html.Div([
            html.A("About", href="#about", className="nav-link"),
            html.A("How to use", href="#usage", className="nav-link"),
            html.A("Data", href="#data", className="nav-link"),
        ], className="header-right")
    ], className="header"),

    # Controls + KPIs
    html.Div([
        html.Div([
            html.Label("Data Source", className="control-label"),
            dcc.RadioItems(
                id="source-mode", 
                options=[
                    {"label":"Snapshot (included)", "value":"snapshot"},
                    {"label":"Live (USGS, if available)", "value":"live"}
                ],
                value="snapshot",
                labelStyle={"display":"block"}
            ),
            html.Label("Date Range", className="control-label"),
            dcc.DatePickerRange(
                id="date-range",
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                start_date=min_date,
                end_date=max_date,
                display_format="YYYY-MM-DD"
            ),
            html.Label("Magnitude Range", className="control-label"),
            dcc.RangeSlider(
                id="mag-range",
                min=0, max=10, step=0.1, value=[3.0, 7.0],
                allowCross=False,
                tooltip={"placement":"bottom", "always_visible":False}
            ),
            html.Label("Depth (km)", className="control-label"),
            dcc.RangeSlider(
                id="depth-range",
                min=0, max=700, step=5, value=[0, 200],
                allowCross=False
            ),
            html.Label("Region", className="control-label"),
            dcc.Dropdown(
                id="region-dd",
                options=[{"label":r, "value":r} for r in regions],
                value=["All"],
                multi=True,
                placeholder="Select regions"
            ),
            html.Label("Type", className="control-label"),
            dcc.Checklist(
                id="type-ck",
                options=[{"label":t, "value":t} for t in types],
                value=types,
                inline=False
            ),
            html.Label("Keyword in Place", className="control-label"),
            dcc.Input(id="keyword", type="text", placeholder="e.g., offshore, Ankara, trench", debounce=True),
            html.Div([
                html.Button("Apply Filters", id="apply-btn", n_clicks=0, className="primary-btn"),
                html.Button("Reset", id="reset-btn", n_clicks=0, className="ghost-btn"),
            ], className="button-row"),
            html.Div(id="status-msg", className="status-msg")
        ], className="controls"),

        html.Div([
            html.Div([
                html.Div([html.H4("Events"), html.H2(id="kpi-count")], className="kpi-card"),
                html.Div([html.H4("Avg Mag"), html.H2(id="kpi-avg-mag")], className="kpi-card"),
                html.Div([html.H4("Max Mag"), html.H2(id="kpi-max-mag")], className="kpi-card"),
                html.Div([html.H4("Median Depth (km)"), html.H2(id="kpi-med-depth")], className="kpi-card"),
            ], className="kpi-grid")
        ], className="kpi-panel")
    ], className="top-panel"),

    # Tabs for visuals
    dcc.Tabs(id="tabs", value="tab-map", children=[
        dcc.Tab(label="Map", value="tab-map", className="tab", selected_className="tab--selected"),
        dcc.Tab(label="Trends", value="tab-trends", className="tab", selected_className="tab--selected"),
        dcc.Tab(label="Distribution", value="tab-dist", className="tab", selected_className="tab--selected"),
        dcc.Tab(label="Table", value="tab-table", className="tab", selected_className="tab--selected"),
    ]),
    html.Div(id="tab-content"),

    # Info sections
    html.Div([
        html.H2("How to use", id="usage"),
        html.Ul([
            html.Li("Choose your data source: the included snapshot (fast & offline) or live USGS feed (if available)."),
            html.Li("Use the controls to filter by date range, magnitude, depth, region, event type, or keyword."),
            html.Li("Switch tabs to explore on the map, follow time trends, inspect distributions, or browse the table."),
            html.Li("Hover, zoom, and select in the plots to reveal details. Legends can be clicked to isolate series."),
        ]),
        html.H2("Data", id="data"),
        html.P("Fields include time, latitude, longitude, depth (km), magnitude, place (free text), type, id, and derived region. "
               "The live option (if permitted) attempts to load the USGS recent earthquakes feed."),
        html.H2("About", id="about"),
        html.P("QuakeScope is an explanatory, decision-support dashboard. It helps users understand when and where earthquakes occur, "
               "how strong they are, and how they are distributed across regions and time.")
    ], className="info")
], className="container")


# ---------- Filtering & Callbacks ----------

def apply_filters(df, start_date, end_date, mag_lo, mag_hi, depth_lo, depth_hi, regions, types, keyword):
    # filter by date
    mask = (
        (df["time"] >= pd.to_datetime(start_date)) &
        (df["time"] <= pd.to_datetime(end_date)) &
        (df["mag"].between(mag_lo, mag_hi)) &
        (df["depth"].between(depth_lo, depth_hi)) &
        (df["type"].isin(types))
    )
    if regions and ("All" not in regions):
        mask &= df["region"].isin(regions)
    if keyword and len(keyword.strip()) > 0:
        kw = keyword.strip().lower()
        mask &= df["place"].str.lower().str.contains(kw)
    return df.loc[mask].copy()

@app.callback(
    Output("status-msg", "children"),
    Output("kpi-count", "children"),
    Output("kpi-avg-mag", "children"),
    Output("kpi-max-mag", "children"),
    Output("kpi-med-depth", "children"),
    Output("tab-content", "children"),
    Input("apply-btn", "n_clicks"),
    Input("reset-btn", "n_clicks"),
    State("source-mode", "value"),
    State("date-range", "start_date"),
    State("date-range", "end_date"),
    State("mag-range", "value"),
    State("depth-range", "value"),
    State("region-dd", "value"),
    State("type-ck", "value"),
    State("keyword", "value"),
    State("tabs", "value"),
    prevent_initial_call=False
)
def update_dashboard(n_apply, n_reset, source_mode, start_date, end_date, mag_range, depth_range, regions_sel, types_sel, keyword, active_tab):
    ctx = dash.callback_context
    # Handle reset: restore defaults from snapshot
    if ctx.triggered and "reset-btn" in ctx.triggered[0]["prop_id"]:
        # Reset values
        _df = load_data(source_mode="snapshot")
        _status = "Filters reset to defaults using the snapshot."
        start_date = _df["time"].min().date()
        end_date = _df["time"].max().date()
        mag_range = [3.0, 7.0]
        depth_range = [0, 200]
        regions_sel = ["All"]
        types_sel = sorted(_df["type"].dropna().unique().tolist())
        keyword = ""
    else:
        _df = load_data(source_mode=source_mode)
        _status = f"Loaded {source_mode} data."

    # Apply filters
    flt = apply_filters(
        _df,
        start_date, end_date,
        mag_range[0], mag_range[1],
        depth_range[0], depth_range[1],
        regions_sel, types_sel, keyword
    )

    # KPIs
    count = f"{len(flt):,}"
    avg_mag = f"{flt['mag'].mean():.2f}" if len(flt) else "—"
    max_mag = f"{flt['mag'].max():.1f}" if len(flt) else "—"
    med_depth = f"{flt['depth'].median():.1f}" if len(flt) else "—"

    # Build tab content
    content = None
    if active_tab == "tab-map":
        # Scattergeo map
        fig = px.scatter_geo(
            flt, lat="latitude", lon="longitude",
            color="region", size="mag",
            hover_name="place",
            hover_data={"time":True, "mag":True, "depth":True, "latitude":False, "longitude":False},
            projection="natural earth",
            title="Earthquakes Map"
        )
        fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), legend_title_text="Region")
        content = dcc.Graph(figure=fig, id="map-fig")
    elif active_tab == "tab-trends":
        # Time series: daily counts & avg magnitude
        if len(flt):
            ts = flt.resample("D", on="time").agg(count=("id", "count"), avg_mag=("mag", "mean")).reset_index()
        else:
            ts = pd.DataFrame({"time": [], "count": [], "avg_mag": []})
        fig1 = px.line(ts, x="time", y="count", title="Daily Earthquake Count")
        fig1.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        fig2 = px.line(ts, x="time", y="avg_mag", title="Daily Average Magnitude")
        fig2.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        content = html.Div([dcc.Graph(figure=fig1, id="trend-count"), dcc.Graph(figure=fig2, id="trend-avg")], className="grid-2")
    elif active_tab == "tab-dist":
        # Distributions: histogram of magnitude, box of depth by region, scatter mag vs depth
        fig_hist = px.histogram(flt, x="mag", nbins=30, title="Magnitude Distribution", marginal="rug")
        fig_hist.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        # Box plot for depth by region (top N regions by count)
        top_regions = flt["region"].value_counts().nlargest(6).index.tolist() if len(flt) else []
        box_df = flt[flt["region"].isin(top_regions)]
        fig_box = px.box(box_df, x="region", y="depth", title="Depth by Top Regions", points="suspectedoutliers")
        fig_box.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        fig_scatter = px.scatter(flt, x="depth", y="mag", color="region", title="Magnitude vs Depth", trendline="lowess")
        fig_scatter.update_layout(margin=dict(l=10, r=10, t=50, b=10))
        content = html.Div([
            dcc.Graph(figure=fig_hist, id="hist-mag"),
            dcc.Graph(figure=fig_box, id="box-depth"),
            dcc.Graph(figure=fig_scatter, id="scatter-mag-depth"),
        ], className="grid-3")
    else:
        # Table view
        columns = [
            {"name":"Time", "id":"time"},
            {"name":"Magnitude", "id":"mag"},
            {"name":"Depth (km)", "id":"depth"},
            {"name":"Region", "id":"region"},
            {"name":"Place", "id":"place"},
            {"name":"Type", "id":"type"},
            {"name":"ID", "id":"id"},
        ]
        tbl = dash_table.DataTable(
            data=flt.sort_values("time", ascending=False).to_dict("records"),
            columns=columns,
            page_size=12,
            filter_action="native",
            sort_action="native",
            style_table={"overflowX":"auto"},
            style_cell={"minWidth":"100px", "maxWidth":"240px", "whiteSpace":"normal"}
        )
        content = html.Div([tbl], className="table-wrap")

    return _status, count, avg_mag, max_mag, med_depth, content

if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), debug=False)
