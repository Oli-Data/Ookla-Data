# Ookla Mobile Broadband Equity Analysis
> Analyzing the mobile broadband divide across California using real-world speed data from Ookla Open Data (2020–2025)

---

## Overview

This project investigates mobile broadband performance disparities across three California regions — the **Central Valley**, **Bay Area**, and **Southern California** — using Ookla's open-source speed test dataset. Unlike ISP-reported coverage maps, Ookla data reflects actual speeds measured by real users, making it a more accurate picture of broadband access on the ground.

The analysis layers in **U.S. Census demographic data** (median income, poverty rate, urban/rural classification) to understand whether broadband inequity tracks with socioeconomic factors — or something else entirely.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.13 | Core language |
| pandas | Data manipulation |
| geopandas | Spatial joins and geographic analysis |
| folium | Interactive maps |
| matplotlib | Charts and visualizations |
| AWS S3 (Ookla Open Data) | Source data pipeline |
| U.S. Census API | Demographic data |
| Census TIGER/Line Shapefiles | Census tract boundaries |

---

## How to Run

### 1. Clone the repo
```bash
git clone https://github.com/Oli-Data/ookla-broadband-equity.git
cd ookla-broadband-equity
```

### 2. Install dependencies
```bash
pip install pandas geopandas folium matplotlib numpy python-dotenv census
```

### 3. Set up your Census API key
Get a free API key at https://api.census.gov/data/key_signup.html

Create a `.env` file in the project root:
```
CENSUS_API_KEY=your_key_here
```

### 4. Run the notebook
Open `ookla_data_project.ipynb` in Jupyter or VS Code.

> **Note:** The AWS pipeline cell (pulls raw Ookla data) is set to skip by default since the processed parquet files are large. To re-run the full pipeline, remove the `raise SystemExit` line at the top of that cell.

---

## Data Sources

| Source | Description |
|--------|-------------|
| [Ookla Open Data](https://github.com/teamookla/ookla-open-data) | Mobile performance tiles, 2020–2025, pulled from AWS S3 |
| [U.S. Census ACS 5-Year Estimates (2023)](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Median household income, poverty rate by census tract |
| [Census TIGER/Line Shapefiles (2023)](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | Census tract boundaries for spatial join |

### Regions Covered
- **Central Valley** — Bakersfield to Redding (35.4°N–40.6°N)
- **Bay Area** — San Jose to Santa Rosa (36.9°N–38.9°N)
- **Southern California** — San Diego to Santa Barbara (32.5°N–34.8°N)

### Methodology Notes
- All analysis filtered to tiles with **≥20 tests** for statistical robustness
- Speed converted from kbps to Mbps throughout
- Median used instead of mean for speed aggregations (more robust to outliers)
- Census demographic overlay scoped to **2022–2024** to minimize temporal mismatch with 2023 ACS vintage
- Urban/Rural classification derived from Census tract area as a density proxy

---

## Key Findings

### 1. The Central Valley Closed the Download Gap
From 2020 to 2024, the Central Valley went from **73.5% slower** than the Bay Area to actually **outpacing** it by 12.1%. This suggests aggressive 5G infrastructure investment in the region over the 5-year period. However, latency gaps persist, meaning real-world usability still lags behind.

### 2. Rural Location Is the Dominant Equity Factor — Not Income
Across all three regions, urban/rural classification was a far stronger predictor of mobile broadband performance than median household income or poverty rate:
- Central Valley rural tiles averaged **65.8 Mbps** vs 193.3 Mbps urban — a 3x penalty
- SoCal rural tiles averaged **56.2 Mbps** vs 193.5 Mbps urban
- Bay Area rural tiles averaged **138.1 Mbps** — even rural Bay Area benefits from proximity to dense infrastructure

### 3. Income Has Little Relationship With Mobile Speed
Contrary to expectations, lower income tracts did not consistently have slower speeds. In some regions, the lowest income brackets had the highest median speeds, likely because low-income tracts tend to cluster in dense urban areas with stronger tower coverage.

### 4. The Real Divide Is Geographic, Not Socioeconomic
California's mobile broadband equity problem is primarily a **rural infrastructure gap**, not an affordability or income-based gap. Policy interventions focused purely on affordability may miss the communities most underserved by mobile networks.

---

## Charts

### Year-Over-Year: Download, Upload & Latency
![YoY Equity Chart](charts/yoy_equity_cv_vs_bay.png)

### Download Speed Gap: Bay Area vs Central Valley
![Download Gap Bar Chart](charts/download_gap_bar.png)

### Download Speed Distribution by Region
![Distribution Chart](charts/download_distribution_by_region.png)

### Speed vs Median Household Income
![Income vs Speed](charts/equity_income_vs_speed.png)

### Rural/Urban Classification & Poverty Rate
![Rural Poverty Chart](charts/equity_rural_poverty.png)

---

*Analysis by Christian Olivares | CO³ Labs LLC*