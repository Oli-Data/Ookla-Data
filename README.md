# Ookla Mobile Broadband Equity Analysis
### A CO³ Labs Study | Christian Olivares-Rodriguez
> Exploring observed mobile broadband performance across California using Ookla Open Data, 2020–2025.

## Overview

This project compares mobile download speed, upload speed, and latency in the **Central Valley**, **Bay Area**, and **Southern California**. It combines Ookla speed-test aggregates with Census geography and demographic data to explore regional trends and potential disparities.

Ookla provides measurements from participating users, not a representative survey of every resident or a complete coverage map. The results describe the sampled locations and periods; they do not establish universal access, affordability, or the cause of speed changes.

**Current notebook status:** The main regional comparison uses a corrected, deduplicated, county-assigned sample. The demographic comparisons and regression still use the earlier regional bounding-box extracts. Those are separate analysis populations and should not be treated as interchangeable. This README follows the notebook's saved numerical outputs rather than its older concluding “Key Findings” prose, which still needs updating.

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python / Jupyter | Notebook workflow |
| pandas, NumPy | Data processing and numerical analysis |
| GeoPandas, Shapely | Spatial joins and geographic analysis |
| Folium | Interactive maps |
| Matplotlib | Charts |
| statsmodels | Exploratory ordinary least squares (OLS) regression |
| Census Python client, python-dotenv | Demographic API access and configuration |
| Parquet engine and S3 filesystem support | Reading cached extracts and Ookla Open Data |

## Data Sources

| Source | Use |
|--------|-----|
| [Ookla Open Data](https://github.com/teamookla/ookla-open-data) | Quarterly mobile performance tiles, 2020–2025, from public AWS S3 |
| [Census ACS 5-Year Estimates](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Tract median household income, population, and poverty population |
| [Census TIGER/Line Shapefiles](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | 2023 California tract boundaries and county identifiers |

The notebook labels the demographic data as **2023 ACS**, but its current Census API call does not explicitly pass a year. Pin and verify the ACS vintage before claiming a reproducible 2023 extract. The demographic analysis restricts Ookla observations to **2022–2024**.

## Main Regional Methodology

1. Load cached regional Parquet extracts originally selected with latitude/longitude bounding boxes.
2. Retain observations with **at least 20 tests**, pool the extracts, and deduplicate by `quadkey`, `year`, and `quarter`.
3. Spatially join tile coordinates to California Census tracts and derive county FIPS codes.
4. Assign counties to mutually exclusive study regions and exclude unmatched locations and other counties.
5. Calculate annual medians of tile-quarter average speeds and latency. Convert kbps to Mbps by dividing by 1,000.

The saved audit starts with **57,153** unique qualifying cached records: **55,703** match a California tract, **1,450** are unmatched, and none have multiple tract matches. Of the matched records, **2,109** lie outside the selected study counties, leaving **53,594** study records. A separate state-boundary check identifies 859 unmatched records in Nevada; the remaining 591 have no state match in that check.

### County definitions

- **Bay Area (9 counties):** Alameda, Contra Costa, Marin, Napa, San Francisco, San Mateo, Santa Clara, Solano, Sonoma.
- **Central Valley (17 counties):** Shasta, Tehama, Glenn, Butte, Colusa, Sutter, Yuba, Yolo, Sacramento, San Joaquin, Stanislaus, Merced, Madera, Fresno, Kings, Tulare, Kern.
- **Southern California (8 counties):** Imperial, Los Angeles, Orange, Riverside, San Bernardino, San Diego, Santa Barbara, Ventura.

These are whole-county *assignment rules*, not a claim that the cached data cover every part of each county. County assignment cannot recover locations excluded by the original bounding boxes.

### Interpretation limits

- One record is a **tile-quarter aggregate**, not an individual test, person, device, or unique location across the full time series. A tile can recur in several quarters.
- Annual statistics are unweighted medians of those records' averages, not medians of individual users' tests or population-weighted regional speeds.
- The 20-test threshold reduces reliance on sparsely tested observations; it does not make the sample representative or guarantee independence.
- Locations and record counts change over time. The notebook labels **2021 as excluding Q3**.
- The saved quarter audit contains **all four quarters of 2025** in all three cached extracts. Lower final-year record counts alone are not evidence of a partial year.

## Regional Results: Corrected County-Assigned Sample

### Median tile-quarter average download speed (Mbps)

| Year | Central Valley | Bay Area | Southern California | Bay Area − Central Valley (Mbps) |
|------|---------------:|---------:|--------------------:|--------------------------------:|
| 2020 | 34.92 | 52.06 | 43.94 | 17.13 |
| 2021 | 74.76 | 76.36 | 73.85 | 1.60 |
| 2022 | 131.70 | 142.95 | 156.89 | 11.25 |
| 2023 | 176.21 | 184.33 | 196.26 | 8.12 |
| 2024 | 257.68 | 255.14 | 249.43 | -2.54 |
| 2025 | 267.47 | 263.76 | 276.49 | -3.71 |

Differences are computed before rounding, so subtracting displayed speeds can differ by 0.01 Mbps.

The observed Bay Area advantage narrows markedly, but not monotonically. The Central Valley median is slightly higher in **2024 and 2025** in this corrected sample. The 2020 Bay Area advantage is **49.1% relative to Central Valley speed**; in 2025 it is **−1.4%** on the same denominator. These results do not show that every Central Valley community caught up or identify infrastructure investment as the cause.

Median latency also converges: Central Valley versus Bay Area is **32 versus 30 ms** in 2020 and **22 versus 24 ms** in 2025. Lower latency is better.

### Qualifying tile-quarter record counts

| Year | Central Valley | Bay Area | Southern California |
|------|---------------:|---------:|--------------------:|
| 2020 | 1,245 | 2,657 | 8,688 |
| 2021 | 1,279 | 2,431 | 7,407 |
| 2022 | 1,323 | 2,598 | 7,738 |
| 2023 | 1,077 | 1,693 | 5,096 |
| 2024 | 864 | 1,448 | 3,647 |
| 2025 | 651 | 1,014 | 2,738 |
| **Total** | **6,439** | **11,841** | **35,314** |

## Exploratory Demographic Results: Original Bounding-Box Extracts

**Scope warning:** These cells build `equity_results` from the original `region_dfs`, rather than the corrected county-assigned sample. California tract matching supplies the demographics, but the regional labels still come from bounding boxes and may overlap. The results below are saved exploratory outputs, not a rerun using the corrected regional definitions.

### Rural/urban proxy and income comparisons

The notebook assigns an area-based proxy using projected **tract polygon area**: Urban <10 km², Suburban 10–<100 km², and Rural ≥100 km². This is not an official Census urban/rural classification or a direct population-density measure.

For 2022–2024 observations with income and classification data:

| Original regional extract | Urban median Mbps | Suburban median Mbps | Rural median Mbps | Rural records / total |
|---------------------------|------------------:|---------------------:|------------------:|----------------------:|
| Central Valley | 193.283 | 141.584 | 65.817 | 619 / 6,230 (9.9%) |
| Southern California | 193.540 | 153.640 | 56.185 | 269 / 15,846 (1.7%) |
| Bay Area | 189.449 | 161.923 | 138.090 | 124 / 5,937 (2.1%) |

Rural-classified records have the lowest median speeds in all three extracts. Income and poverty bracket medians do not follow one consistent pattern across regions. Some brackets are small, and observations can repeat locations over time; these are not counts of independent households.

### Exploratory regression

The notebook now includes saved OLS results for each original regional extract:

```text
log(speed) ~ log(income) + urban_class + poverty_rate
```

Rural is the reference category. The model log-transforms speed and income, clipping nonpositive values before transformation.

| Extract | Urban vs rural coefficient | Log-income coefficient | Income p-value | R² |
|---------|---------------------------:|-----------------------:|---------------:|---:|
| Central Valley | 0.9309 | 0.2187 | <0.001 | 0.082 |
| Southern California | 1.2621 | 0.1317 | <0.001 | 0.044 |
| Bay Area | 0.6143 | 0.0333 | 0.374 | 0.013 |

Urban coefficients are positive in all three models, with reported p-values below 0.001. Thus, **rural-classified areas have lower modeled speeds even after accounting for income and poverty in these exploratory models**.

This does **not** formally establish that geography is a “much stronger predictor” than income: categorical and log-income coefficients have different interpretations and scales. No held-out predictive-importance comparison is shown, and the models explain only **1.3%–8.2%** of log-speed variation. The fits use default OLS uncertainty estimates without clustering repeated locations, spatial-dependence adjustment, or year controls. Treat the reported p-values as exploratory, not definitive evidence of independent or causal effects. The models do not measure affordability or establish why the differences exist.

## How to Run

```bash
git clone https://github.com/Oli-Data/Ookla-Data.git
cd Ookla-Data
python -m pip install jupyter pandas numpy geopandas shapely folium matplotlib python-dotenv census statsmodels pyarrow s3fs
```

This is a dependency starting point, not a pinned or newly validated environment.

1. Obtain a [Census API key](https://api.census.gov/data/key_signup.html) and create `.env` in the project root:

   ```dotenv
   CENSUS_API_KEY=your_key_here
   ```

2. Open `ookla_data_project.ipynb` in Jupyter or VS Code. Provide the expected regional Parquet files in the notebook's working directory, or run the AWS extraction cell to generate them:
   - `central_valley_mobile_historical_2020_2025.parquet`
   - `socal_mobile_historical_2020_2025.parquet`
   - `bay_area_mobile_historical_2020_2025.parquet`

3. The extraction cell intentionally raises `SystemExit` by default. Skip it when using cached files; remove that guard only when intentionally rebuilding the extracts. It loads a global year's mobile data at a time and can require substantial RAM. A fresh pull may differ from the saved analysis.
4. Replace the hard-coded local state-shapefile path in the unmatched-location diagnostic with a valid path on your machine. California tract boundaries are fetched from the Census TIGER server.
5. Explicitly pin the intended ACS year in the API call, then rerun and verify demographic results. Before presenting those results as part of the corrected county study, rebuild the demographic join from `county_equity_df` and rerun its charts and models.

**Reproducibility status:** This README was checked against existing notebook code and saved outputs; the full data pipeline was not rerun. The notebook is not yet a portable, clean-run pipeline. Its older concluding findings, overlap-sensitivity narrative, and some headings also need reconciliation with the current county-based workflow.

## Charts and Maps

The notebook generates annual comparisons, distributions, demographic charts, and interactive maps. Existing static files are linked below; regenerate and inspect them before reuse, because not every chart is automatically overwritten (the distribution cell currently has `SAVE_PNG = False`).

- [Annual download, upload, and latency chart](charts/yoy_equity_cv_vs_bay.png)
- [Download-speed gap chart](charts/download_gap_bar.png)
- [Regional download distribution](charts/download_distribution_by_region.png)
- [Income-bracket comparison](charts/equity_income_vs_speed.png)
- [Rural/urban proxy and poverty comparisons](charts/equity_rural_poverty.png)

The county-assigned mapping cells display fastest/slowest **observed tile-quarter** markers and save `central_valley_county_map.html`. The below-median and upper-quartile exploratory cells do not establish dead zones or consistently fast service: those thresholds identify approximately one half and one quarter of the sampled records by construction.

---
*Analysis by Christian Olivares | CO³ Labs LLC*
