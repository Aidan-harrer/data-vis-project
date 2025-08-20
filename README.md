# QuakeScope: Earthquake Explorer (Dash + Plotly)

QuakeScope is an interactive Dash application that lets users explore recent earthquakes.
It is designed to be explanatory and purpose-driven: users can filter by date, magnitude, depth, region, event type,
and keyword to understand when/where earthquakes occur and how strong they are.

## Features

- **At least four Dash Core Components**: DatePickerRange, RangeSlider (magnitude), RangeSlider (depth), Dropdown (region), Checklist (type), RadioItems (data source), Input (keyword), Tabs — more than four.
- **Interactivity via callbacks**: A single callback wires filters + tab selection to update KPIs and the active view.
- **Three+ Plotly visuals**:
  - Map (scatter_geo)
  - Time series (two line charts: daily count, daily average magnitude)
  - Histogram (magnitude distribution)
  - Box plot (depth by region)
  - Scatter plot (mag vs depth)
- **Navigation & explanations**: Header links, tabs, and in-app "How to use", "Data", and "About" sections.

## Running locally

1. Clone or download this repository.
2. (Optional but recommended) Create a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app:

```bash
python app.py
```

5. Open your browser at http://127.0.0.1:8050

## Data

By default, the app loads the included snapshot `data/earthquakes_snapshot.csv` (synthetic data shaped like USGS feed).
If you choose **Live (USGS, if available)**, the app attempts to fetch the public CSV feed
(`all_month.csv`) and will automatically fall back to the snapshot if the fetch fails.

### Snapshot schema

- `time` (ISO8601)
- `latitude` (float degrees)
- `longitude` (float degrees)
- `depth` (km)
- `mag` (magnitude)
- `place` (free-text location)
- `type` (event type)
- `id` (event id)
- `region` (derived region)

## Project structure

```
DashEarthquakeExplorer/
├── app.py
├── assets/
│   └── style.css
├── data/
│   └── earthquakes_snapshot.csv
├── requirements.txt
└── README.md
```

## Notes

- No Mapbox token is required (using `scatter_geo` projection).
- The code avoids any non-standard styling beyond simple CSS for clean aesthetics.
- If you deploy to a platform like Render, Railway, or Heroku, set
  `web` command to `python app.py` and ensure the `PORT` env var is supported (the code reads it).
