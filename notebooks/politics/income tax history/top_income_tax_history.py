# /// script
# requires-python = ">=3.11"
# dependencies = ["marimo>=0.14,<1", "pandas>=2.2,<3", "matplotlib>=3.8,<4", "requests>=2.32,<3"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import matplotlib.pyplot as plt
    import io
    import json
    import hashlib
    import datetime
    from pathlib import Path
    import requests

    return Path, datetime, hashlib, io, json, mo, pd, plt, requests


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # US top income-tax brackets, 1913–2025
    (initial version from [Perplexity](https://www.perplexity.ai/search/cbabd880-b0cc-4294-a744-2486f61ed6d9?preview=1))

    A reproducible, **partial historical dataset**, with source downloads and explicit missingness.
    Thresholds use joint filing from 1948. Before then, the ordinary schedule generally
    did not distinguish filing statuses. Thresholds refer to the statutory income base,
    not earnings or AGI. [web:25]

    **Important:** the embedded table is a manually transcribed starting dataset from the
    preceding analysis, not a machine-extracted, fully audited historical series.
    Downloaded sources are retained for checking; this notebook does not pretend that
    downloading a document validates or extracts its numbers.
    Population shares and group contributions to federal outlays remain missing.
    The 1963 return-share illustration is separate from population share. [web:8]

    Coverage starts with the continuous modern tax in 1913, not the earlier Civil War tax.
    Source IDs below correspond to the source manifest.
    """)
    return


@app.cell(hide_code=True)
def _(io, pd):
    # Embedded snapshot makes graphing independent of network availability.
    embedded_csv = 'year,top_regular_rate_pct,threshold_nominal_usd,annual_cpi,threshold_2025_usd,population_share_pct,top_bracket_returns_share_pct,income_tax_from_group_share_of_federal_outlays_pct,bracket_source,cpi_source,notes\n1913,7.0,500000,9.9,16257576,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1914,7.0,500000,10.0,16095000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1915,7.0,500000,10.1,15935644,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1916,15.0,2000000,10.9,59064220,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1917,67.0,2000000,12.8,50296875,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1918,77.0,1000000,15.0,21460000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1919,73.0,1000000,17.3,18606936,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1920,73.0,1000000,20.0,16095000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1921,73.0,1000000,17.9,17983240,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1922,58.0,200000,16.8,3832143,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1923,43.5,200000,17.1,3764912,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1924,46.0,500000,17.1,9412281,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1925,25.0,100000,17.5,1839429,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1926,25.0,100000,17.7,1818644,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1927,25.0,100000,17.4,1850000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1928,25.0,100000,17.2,1871512,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1929,24.0,100000,17.2,1871512,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1930,25.0,100000,16.7,1927545,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1931,25.0,100000,15.2,2117763,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1932,63.0,1000000,13.6,23669118,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1933,63.0,1000000,12.9,24953488,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1934,63.0,1000000,13.4,24022388,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1935,63.0,1000000,13.7,23496350,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1936,79.0,5000000,13.9,115791367,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1937,79.0,5000000,14.4,111770833,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1938,79.0,5000000,14.1,114148936,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1939,79.0,5000000,13.9,115791367,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1940,81.1,5000000,14.0,114964286,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1941,81.0,5000000,14.7,109489796,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1942,88.0,200000,16.3,3949693,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1943,88.0,200000,17.3,3721387,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1944,94.0,200000,17.6,3657955,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1945,94.0,200000,18.0,3576667,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1946,86.45,200000,19.5,3301538,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1947,86.45,200000,22.3,2886996,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1948,82.13,400000,24.0,5365000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1949,82.13,400000,23.8,5410084,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1950,84.36,400000,24.1,5342739,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1951,91.0,400000,26.0,4952308,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1952,92.0,400000,26.6,4840602,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1953,92.0,400000,26.8,4804478,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1954,91.0,400000,26.9,4786617,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1955,91.0,400000,26.8,4804478,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1956,91.0,400000,27.2,4733824,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1957,91.0,400000,28.1,4582206,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1958,91.0,400000,28.9,4455363,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1959,91.0,400000,29.2,4409589,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1960,91.0,400000,29.6,4350000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1961,91.0,400000,29.9,4306355,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1962,91.0,400000,30.3,4249505,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1963,91.0,400000,30.6,4207843,,0.0007828125000000001,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1964,77.0,400000,31.0,4153548,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1965,70.0,200000,31.5,2043810,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1966,70.0,200000,32.5,1980923,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1967,70.0,200000,33.4,1927545,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1968,75.25,200000,34.8,1850000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1969,77.0,200000,36.7,1754223,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1970,71.75,200000,38.8,1659278,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1971,70.0,200000,40.5,1589630,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1972,70.0,200000,41.8,1540191,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1973,70.0,200000,44.4,1450000,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1974,70.0,200000,49.3,1305882,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1975,70.0,200000,53.8,1196654,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1976,70.0,200000,56.9,1131459,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1977,70.0,203200,60.6,1079374,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1978,70.0,203200,65.2,1003222,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1979,70.0,215400,72.6,955059,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1980,70.0,215400,82.4,841472,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1981,69.125,215400,90.9,762786,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1982,50.0,85600,96.5,285540,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1983,50.0,109400,99.6,353573,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1984,50.0,162400,103.9,503143,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1985,50.0,169020,107.6,505646,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1986,50.0,175250,109.6,514717,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1987,38.5,90000,113.6,255026,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1988,28.0,29750,118.3,80951,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown. 33% recapture bubble; highest-income bracket 28%.\n1989,28.0,30950,124.0,80345,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown. 33% recapture bubble; highest-income bracket 28%.\n1990,28.0,32450,130.7,79921,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown. 33% recapture bubble; highest-income bracket 28%.\n1991,31.0,82150,136.2,194156,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1992,31.0,86500,140.3,198463,,,,[web:25],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1993,39.6,250000,144.5,556920,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1994,39.6,250000,148.2,543016,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1995,39.6,256500,152.4,541781,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1996,39.6,263750,156.9,541116,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1997,39.6,271050,160.5,543620,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1998,39.6,278450,163.0,549896,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n1999,39.6,283150,166.6,547095,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2000,39.6,288350,172.2,539024,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2001,39.1,297350,177.1,540468,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2002,38.6,307050,179.9,549413,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2003,35.0,311950,184.0,545743,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2004,35.0,319100,188.9,543771,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2005,35.0,326450,195.3,538066,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2006,35.0,336550,201.6,537378,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2007,35.0,349700,207.3,543022,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2008,35.0,357700,215.3,534806,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2009,35.0,372950,214.5,559686,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2010,35.0,373650,218.1,551481,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2011,35.0,379150,224.9,542678,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2012,35.0,388350,229.6,544468,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2013,39.6,450000,233.0,621695,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2014,39.6,457600,236.7,622313,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2015,39.6,464850,237.0,631372,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2016,39.6,466950,240.0,626297,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2017,39.6,470700,245.1,618190,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2018,37.0,600000,251.1,769176,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2019,37.0,612350,255.7,770886,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2020,37.0,622050,258.8,773717,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2021,37.0,628300,271.0,746309,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2022,37.0,647850,292.7,712480,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2023,37.0,693750,304.7,732911,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2024,37.0,731200,313.7,750313,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n2025,37.0,751600,321.9,751600,,,,[web:9],[web:15],Manual transcription; not independently audited. Joint thresholds from 1948; missing shares are unknown.\n'
    raw = pd.read_csv(io.StringIO(embedded_csv))
    assert raw.year.is_unique and raw.year.tolist() == list(range(1913, 2026))
    assert raw.annual_cpi.gt(0).all()
    assert raw.top_regular_rate_pct.between(0, 100).all()
    return (raw,)


@app.cell(hide_code=True)
def _(pd):
    source_manifest = pd.DataFrame([{'id': 'web:25', 'name': 'IRS historical brackets, 1913–2002', 'url': 'https://www.irs.gov/pub/irs-soi/02inpetr.pdf', 'filename': 'irs_brackets_1913_2002.pdf'}, {'id': 'web:9', 'name': 'Tax Foundation historical brackets', 'url': 'https://taxfoundation.org/data/all/federal/historical-income-tax-rates-brackets/', 'filename': 'tax_foundation_brackets.html'}, {'id': 'web:15', 'name': 'Minneapolis Fed annual CPI', 'url': 'https://www.minneapolisfed.org/about-us/monetary-policy/inflation-calculator/consumer-price-index-1913-', 'filename': 'annual_cpi.html'}, {'id': 'web:8', 'name': 'Income Tax Paid at Each Tax Rate, 1958–2009', 'url': 'https://www.urban.org/sites/default/files/publication/27921/901456-Income-Tax-Paid-at-Each-Tax-Rate---Updated-.PDF', 'filename': 'tax_at_each_rate.pdf'}, {'id': 'web:1', 'name': 'IRS historical statistical tables', 'url': 'https://www.irs.gov/statistics/soi-tax-stats-historical-data-tables', 'filename': 'irs_historical_tables.html'}, {'id': 'web:26', 'name': 'OMB historical budget tables (archived)', 'url': 'https://obamawhitehouse.archives.gov/omb/budget/Historicals', 'filename': 'omb_historical_tables.html'}])
    return (source_manifest,)


@app.cell(hide_code=True)
def _(mo, source_manifest):
    mo.vstack([mo.md("## Source documents\nDownloads include the cited PDFs and HTML landing pages; linked spreadsheets are not automatically crawled."), mo.ui.table(source_manifest)])
    return


@app.cell(hide_code=True)
def _(mo):
    # No network writes occur until this button is clicked.
    download_sources = mo.ui.run_button(label="Download / verify cached source documents")
    mo.vstack([mo.md("Downloads go to a source cache beside the notebook (or the current directory if no script path is available). Existing files are reused; delete a cached file to fetch a fresh copy. Failures are recorded rather than hidden."), download_sources])
    return (download_sources,)


@app.cell(hide_code=True)
def _(Path):
    import sys
    _script = Path(sys.argv[0]).resolve()
    workspace = _script.parent if _script.suffix == ".py" and _script.exists() else Path.cwd()
    return (workspace,)


@app.cell(hide_code=True)
def _(
    datetime,
    download_sources,
    hashlib,
    json,
    mo,
    pd,
    requests,
    source_manifest,
    workspace,
):
    mo.stop(not download_sources.value, mo.md("Source download has not been requested. Embedded data and graphs still work offline."))
    _cache = workspace / "sources"
    _cache.mkdir(parents=True, exist_ok=True)
    _records = []
    for _source in source_manifest.to_dict("records"):
        _path = _cache / _source["filename"]
        _record = dict(_source)
        _record["checked_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            if _path.exists():
                _body = _path.read_bytes()
                _record["status"] = "cached"
            else:
                _response = requests.get(_source["url"], timeout=(10, 90), headers={"User-Agent": "HistoricalTaxResearchNotebook/1.0"})
                _response.raise_for_status()
                _body = _response.content
                if not _body:
                    raise ValueError("Empty response")
                if _path.suffix == ".pdf" and not _body.lstrip().startswith(b"%PDF"):
                    raise ValueError("Expected PDF; server returned a different document")
                _tmp = _path.with_suffix(_path.suffix + ".tmp")
                _tmp.write_bytes(_body)
                _tmp.replace(_path)
                _record.update(status="downloaded", final_url=_response.url, content_type=_response.headers.get("Content-Type"), retrieved_at_utc=_record["checked_at_utc"])
            _record.update(bytes=len(_body), sha256=hashlib.sha256(_body).hexdigest())
        except Exception as _error:
            _record.update(status="failed", error=str(_error))
        _records.append(_record)
    (_cache / "download_manifest.json").write_text(json.dumps(_records, indent=2), encoding="utf-8")
    download_report = pd.DataFrame(_records)
    mo.ui.table(download_report)
    return


@app.cell(hide_code=True)
def _(mo):
    year_window = mo.ui.range_slider(start=1913, stop=2025, value=(1913, 2025), step=1, label="Tax years")
    base_year = mo.ui.dropdown(options=[1913, 1963, 1980, 2000, 2025], value=2025, label="Dollar purchasing-power year")
    log_scale = mo.ui.checkbox(value=True, label="Logarithmic threshold axis")
    mo.hstack([year_window, base_year, log_scale])
    return base_year, log_scale, year_window


@app.cell(hide_code=True)
def _(base_year, raw, year_window):
    # CPI values in the snapshot are rounded annual averages. Do not imply more
    # precision than these inputs support, even when displaying dollar-level results.
    base_cpi = float(raw.loc[raw.year.eq(base_year.value), "annual_cpi"].iloc[0])
    calculated = raw.copy()
    calculated["threshold_constant_usd"] = calculated.threshold_nominal_usd * base_cpi / calculated.annual_cpi
    selected = calculated.loc[calculated.year.between(*year_window.value)].copy()
    return calculated, selected


@app.cell(hide_code=True)
def _(base_year, log_scale, mo, plt, selected):
    # Separate panels avoid suggesting a causal relationship via a dual y-axis.
    _fig, _axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, constrained_layout=True)
    _axes[0].step(selected.year, selected.top_regular_rate_pct, where="mid", color="#355C9A")
    _axes[0].set(ylabel="Top regular statutory rate (%)", ylim=(0, 100), title="Top rate and inflation-adjusted entry threshold")
    _axes[1].plot(selected.year, selected.threshold_constant_usd / 1e6, color="#B34F35")
    if log_scale.value:
        _axes[1].set_yscale("log")
    _axes[1].set(xlabel="Tax year", ylabel=f"Threshold (millions of {base_year.value} dollars)")
    for _ax in _axes:
        _ax.grid(alpha=.25)
    mo.vstack([_fig, mo.md("Sources: historical brackets [web:25][web:9], annual CPI [web:15]. The 1988–1990 highest-income bracket is 28%; a 33% recapture bubble existed below it. Rate limits, income definitions, deductions and credits complicate comparisons. [web:25]" )])
    return


@app.cell(hide_code=True)
def _(base_year, log_scale, mo, plt, selected):
    _fig, _ax = plt.subplots(figsize=(12, 4), constrained_layout=True)
    _ax.plot(selected.year, selected.threshold_nominal_usd / 1e6, label="Nominal dollars", color="#777777")
    _ax.plot(selected.year, selected.threshold_constant_usd / 1e6, label=f"{base_year.value} dollars", color="#3A8060")
    if log_scale.value:
        _ax.set_yscale("log")
    _ax.set(title="How inflation changes the apparent bracket threshold", xlabel="Tax year", ylabel="Threshold (millions of dollars)")
    _ax.grid(alpha=.25)
    _ax.legend()
    mo.vstack([_fig, mo.md("Constant-dollar threshold = nominal threshold × CPI(base year) / CPI(tax year). CPI source [web:15]. Changing filing status in 1948 introduces a comparability break. [web:25]" )])
    return


@app.cell(hide_code=True)
def _(mo, plt, selected):
    # Missingness is plotted explicitly; unavailable shares are never filled with zero.
    _cols = ["top_regular_rate_pct", "threshold_nominal_usd", "population_share_pct", "top_bracket_returns_share_pct", "income_tax_from_group_share_of_federal_outlays_pct"]
    _labels = ["Top rate", "Entry threshold", "Population share", "Return share", "Group tax / outlays"]
    _fig, _ax = plt.subplots(figsize=(12, 3.5), constrained_layout=True)
    _matrix = selected[_cols].notna().to_numpy().T.astype(int)
    _ax.imshow(_matrix, aspect="auto", interpolation="nearest", cmap="Greys", vmin=0, vmax=1)
    _ticks = sorted(set([0, len(selected)//2, len(selected)-1]))
    _ax.set_xticks(_ticks, [str(selected.year.iloc[_i]) for _i in _ticks])
    _ax.set_yticks(range(len(_labels)), _labels)
    _ax.set(title="Data availability: black = present; white = missing", xlabel="Tax year")
    mo.vstack([_fig, mo.md("The lone 1963 return-share observation is about 0.000783% (501 / approximately 64 million returns). It is not a population share. [web:8] No population or budget-share series has been established here; those graphs cannot responsibly be drawn." )])
    return


@app.cell(hide_code=True)
def _(mo, selected):
    mo.vstack([mo.md("## Annual data\nBlank cells are unknown, not zero. Filtered table can be inspected independently of the plots."), mo.ui.table(selected)])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Completing the missing series
    A tax return is not a person. The more readily tabulated measure is:
    \[\text{return share}_t=\frac{\text{returns reaching top bracket}_t}{\text{all returns}_t}.\]
    For the requested spending measure, use the **entire income-tax liability of those returns**:
    \[\text{spending contribution}_t=\frac{\text{total income tax of top-bracket returns}_t}{\text{federal outlays}_t}.\]
    Do not substitute taxes on just the income slice in the top bracket, or taxes paid
    by the top 1% of AGI. The historical tax-rate analysis distinguishes return-based
    and bracket-slice tabulations. [web:8]

    Resolve fiscal-year versus calendar-year alignment before joining OMB outlays.
    Also decide whether 'paid' means assessed liability or cash collections.
    This notebook uses individual income tax only, not the incidence of every federal tax.

    **Audit workflow:** download sources; check each transcribed threshold and rate;
    extract highest-rate return counts and total liabilities from the annual IRS tables;
    retain source table/page and extraction method with each new observation;
    merge only after harmonizing definitions. Do not infer missing values.
    """)
    return


@app.cell(hide_code=True)
def _(calculated, json, mo, source_manifest):
    mo.hstack([
        mo.download(data=calculated.to_csv(index=False).encode("utf-8"), filename="calculated_tax_history.csv", label="Export full calculated table"),
        mo.download(data=json.dumps(source_manifest.to_dict("records"), indent=2).encode("utf-8"), filename="source_manifest.json", label="Export source manifest")
    ])
    return


if __name__ == "__main__":
    app.run()
