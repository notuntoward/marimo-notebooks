# /// script
# requires-python = ">=3.10"
# dependencies = ["marimo", "pandas", "requests", "openpyxl", "xlrd", "altair"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import io, json, os, re, zipfile, pathlib
    from html.parser import HTMLParser
    import altair as alt
    import marimo as mo
    import pandas as pd
    import requests

    return HTMLParser, alt, io, json, mo, os, pathlib, pd, re, requests, zipfile


@app.cell
def _(mo):
    mo.md(r"""
    # Reproducing WalletHub's "Tax Burden by State" from primary data

    See the companion [methodology and year-mapping notes](README.md).

    **Method (per [WalletHub](https://wallethub.com/edu/states-with-highest-lowest-tax-burden/20494)):** burden = (property tax, individual income tax, or
    sales and excise tax) / total state personal income. Total = sum of the three.
    Rank 1 = highest burden.

    **Primary sources downloaded by this notebook:**
    - [U.S. Census Bureau, state and local government finances](https://www.census.gov/data/developers/data-sets/govslocalfin.html)
      (tax collections; published source years FY2021–FY2024)
    - [U.S. BEA, SAINC1 state annual personal income](https://apps.bea.gov/regional/zip/SAINC.zip)

    The Census numerator is the combined state-and-local total for each state area:
    property taxes, individual income taxes, and general sales plus selective sales
    taxes. The BEA denominator is SAINC1 LineCode 1 (personal income). Census amounts
    are in thousands of dollars and BEA amounts in millions; the loaders convert both
    to dollars before calculating percentages. The [Tax Policy Center series definitions](https://state-local-finance-data.taxpolicycenter.org/help/revenue.html)
    describe the matching categories: property tax, individual income tax (not corporate
    income tax), and total sales/gross receipts (general plus selective sales).

    For FY2023–FY2024, the Census API has nested labels (for example, sale-of-property
    revenue is not property-tax revenue), so the loader selects Census aggregate codes:
    property LF0009, individual income LF0023, general sales LF0011, and total selective
    sales LF0012. The API omits some state/category rows when no receipts are reported;
    those combinations are represented as $0. Duplicate rows or blank amounts still
    raise errors rather than being silently counted or filled.

    ### Equation and source mapping

    Each tax-type percentage is that tax revenue divided by the state's personal
    income, multiplied by 100. In other words, the denominator is not total tax
    revenue. WalletHub reports three categories: property tax, individual income
    tax, and sales/excise tax. The latest-year stacked bar chart separates the latter
    into its two underlying Census tax types (general sales and selective sales), so
    it displays all four tax types individually. The state tables and selectable
    trend chart below use the independent Census + BEA calculations:

    ```text
    sales_excise_pct[state, year] =
        general_sales_pct[state, year] + selective_sales_pct[state, year]

    total_burden_pct[state, year] =
        property_pct[state, year]
        + individual_income_pct[state, year]
        + sales_excise_pct[state, year]

    tax_type_pct[state, year] =
        100 * tax_type_revenue_usd[state, year]
            / state_personal_income_usd[state, year]
    ```

    The table rows below are tax types being measured, not data-source names. The
    columns identify where each tax-revenue amount comes from in each Census data
    format:

    | Tax type | Census FY2021–FY2022 workbooks | Census FY2023–FY2024 API |
    | --- | --- | --- |
    | Property tax | Table 1 `Property` row; state column | `govslocalfin.AMOUNT`; `AGG_DESC=LF0009` (`Taxes - Property`) |
    | Individual income tax | Table 1 `Individual Income` row; state column | `govslocalfin.AMOUNT`; `AGG_DESC=LF0023` (`Income Taxes - Individual`) |
    | General sales tax | Table 1 `General Sales` row; state column | `govslocalfin.AMOUNT`; `AGG_DESC=LF0011` (`Taxes - General Sales`) |
    | Selective sales tax | Table 1 `Selective Sales` row; state column | `govslocalfin.AMOUNT`; `AGG_DESC=LF0012` (`Total Selective Sales`) |

    Source locations: Census [FY2021 Table 1](https://www2.census.gov/programs-surveys/gov-finances/tables/2021/21slsstab1.xlsx),
    [FY2022 Table 1](https://www2.census.gov/programs-surveys/gov-finances/tables/2022/22slsstab1.xlsx),
    and [FY2023–FY2024 `govslocalfin` API](https://api.census.gov/data/timeseries/govslocalfin).
    BEA source file: [Regional `SAINC.zip`](https://apps.bea.gov/regional/zip/SAINC.zip).

    For each API amount, the other filters are `NAME=state`,
    `GOVTYPE_LABEL=combined state and local`, and `time=Census FY`; the code
    checks the returned `AGG_DESC_LABEL`. Census amounts are in thousands of
    dollars. The common denominator for every tax type and year is BEA Regional
    `SAINC1`: `GeoName=state`, `LineCode=1` (“Personal income”), and the
    year-named column, in millions of dollars.

    For FY2024 specifically, Census API `time=2024` supplies the numerator and
    BEA `SAINC1` column `2024` supplies the denominator. Since Census amounts are
    thousands and BEA values are millions, the tax-type equation in raw units is
    `tax_type_pct = 0.1 * Census_AMOUNT_thousands / BEA_SAINC1_millions`.
    For the WalletHub sales/excise category, add the general-sales and selective-sales
    amounts. The chart instead plots each of those two sales tax types separately;
    its four stacked tax-type shares sum to the same total burden.
    Census FY2024 is a government fiscal year, while BEA column 2024 is a
    calendar year. This is different from the **WalletHub 2024 article edition**,
    which the notebook maps to Census FY2021. Tax-type and total ranks use
    descending values and minimum rank for ties, so rank 1 is highest.

    ### Source fit and limits

    WalletHub cites the [Tax Policy Center (TPC)](https://state-local-finance-data.taxpolicycenter.org/),
    whose state/local finance system republishes Census finance data and reports revenue
    as a fraction of personal income. Using Census and BEA directly is therefore a good
    primary-source match to the *same concepts and underlying programs* WalletHub describes.
    WalletHub does not name its input fiscal year or publish a frozen calculation extract,
    so we cannot verify that it used these exact files, revisions, or aggregations.

    The calculations themselves use only downloaded Census and BEA data. Separately, the
    notebook downloads the complete 50-state WalletHub tables from archived article
    reproductions, then compares each article's figures with the corresponding
    downloaded-data calculation. The article values are comparison-only and never
    calculation inputs. Their source URLs are recorded with the output rows. The
    article-to-data mapping used here is:

    | WalletHub article edition | Census fiscal year used |
    | --- | --- |
    | 2024 | FY2021 |
    | 2025 | FY2022 |
    | 2026 | FY2023 |
    | Latest Census data | FY2024 |

    The complete article tables are archived reproductions published by CPA Practice
    Advisor: [2024](https://www.cpapracticeadvisor.com/2024/12/01/how-the-50-states-rank-by-tax-burden/103495/),
    [2025](https://www.cpapracticeadvisor.com/2025/04/01/how-the-50-states-rank-by-tax-burden-updated-for-2025/158094/),
    and [2026](https://www.cpapracticeadvisor.com/2026/03/31/2026-update-how-the-50-states-rank-by-tax-burden/180445/).
    They reproduce the full WalletHub state tables and are downloaded only for comparison.

    **FY2025 Census data are not available yet.** Census currently documents its
    [State and Local Government Finances time series](https://www.census.gov/data/developers/data-sets/govslocalfin.html)
    as covering 2017–2024; the FY2024 files were released in July 2026. The notebook
    reports FY2025 as unavailable instead of fabricating a value from personal income
    alone. The “2025” in the WalletHub article row above is an article edition and maps
    to Census FY2022; it is not Census FY2025.

    The first column is the WalletHub article edition; the second is the fiscal year of
    the downloaded Census observations. These year assignments are informed estimates,
    not confirmed WalletHub vintages. Census released FY2022 on
    [October 31, 2024](https://www.census.gov/newsroom/press-releases/2024/census-of-governments.html),
    before the 2025 article's April 1 release; FY2023 was not published until
    [July 2025](https://www.census.gov/data/datasets/2023/econ/local/public-use-datasets.html),
    after it (see the [reproduced 2025 table](https://www.cpapracticeadvisor.com/2025/04/01/how-the-50-states-rank-by-tax-burden-updated-for-2025/158094/)).
    FY2024 was released in July 2026, after the 2026 article.

    This is appropriate for reproducing a **tax-revenue-to-personal-income ratio**, not
    for measuring the tax ultimately borne by a typical resident. Census records revenue
    by the location of state/local governments; it does not allocate business-paid taxes
    or other tax incidence to households. Census revenue is reported by government fiscal
    year, while BEA personal income is annual calendar-year income, so the periods are
    close but not perfectly aligned.

    ### Running the Census API years

    FY2021 and FY2022 use Census workbooks and BEA personal income downloads without an API key.
    FY2023 and FY2024 use the Census API, which requires a [free Census API key](https://api.census.gov/data/key_signup.html).
    Census has not published FY2025 finance data; no API key can return those missing observations.
    Set it in the same shell that starts marimo:

    ```powershell
    $env:CENSUS_API_KEY = "paste-your-key"
    marimo edit "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py"
    ```

    ```bash
    export CENSUS_API_KEY="paste-your-key"
    marimo edit "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py"
    ```

    If marimo is already open, restart it after setting the variable. The notebook reads
    the key from the environment; it does not store the key in the notebook or data cache.
    Raw downloads are cached in the local `data_cache/` folder for subsequent runs.

    The visible comparison table puts WalletHub and Census + BEA values side by side,
    one row per state and period. For programmatic use, `comparison_data` contains one
    row per period, state, and source (`WalletHub article` or `Downloaded Census + BEA`).
    Its MultiIndex is (`period`, `census_fy`, `state`, `data_source`) and it can be
    exported with `comparison_data.reset_index().to_csv(...)`. The article's tax-type
    ranks are included only when the published table supplies them.
    """)
    return


@app.cell
def _(pathlib):
    CACHE = pathlib.Path("data_cache")
    CACHE.mkdir(exist_ok=True)
    HEADERS = {"User-Agent": "Mozilla/5.0 (research notebook; contact: local user)"}

    # WalletHub article edition -> source fiscal year available at publication.
    EDITIONS = {
        "WalletHub 2024 article": 2021,
        "WalletHub 2025 article": 2022,
        "WalletHub 2026 article": 2023,
    }
    LATEST_FY = 2024  # Census released FY2024 in July 2026.
    REQUESTED_FY = 2025  # Not yet published in Census' current 2017–2024 series.

    ARTICLE_URLS = {
        "WalletHub 2024 article": (
            "https://www.cpapracticeadvisor.com/2024/12/01/"
            "how-the-50-states-rank-by-tax-burden/103495/"
        ),
        "WalletHub 2025 article": (
            "https://www.cpapracticeadvisor.com/2025/04/01/"
            "how-the-50-states-rank-by-tax-burden-updated-for-2025/158094/"
        ),
        "WalletHub 2026 article": (
            "https://www.cpapracticeadvisor.com/2026/03/31/"
            "2026-update-how-the-50-states-rank-by-tax-burden/180445/"
        ),
    }
    STATES = ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
        "Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas",
        "Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota",
        "Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey",
        "New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
        "Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas",
        "Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"]
    return ARTICLE_URLS, CACHE, EDITIONS, HEADERS, LATEST_FY, REQUESTED_FY, STATES


@app.cell
def _(CACHE, HEADERS, requests):
    def fetch(url, name):
        """Download once; reuse cached copy afterwards (reproducible reruns)."""
        path = CACHE / name
        if path.exists() and path.stat().st_size > 0:
            return path
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)
        return path

    def fetch_first(urls, name):
        errs = []
        for u in urls:
            try:
                return fetch(u, name), u
            except Exception as e:  # try next candidate
                errs.append(f"{u}: {e}")
        raise RuntimeError("No candidate URL worked:\n" + "\n".join(errs))

    return fetch, fetch_first


@app.cell
def _(ARTICLE_URLS, EDITIONS, HTMLParser, STATES, fetch, pd, re):
    class ArticleTableParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tables = []
            self.table = None
            self.row = None
            self.cell = None

        def handle_starttag(self, tag, attrs):
            if tag == "table" and self.table is None:
                self.table = []
            elif tag == "tr" and self.table is not None:
                self.row = []
            elif tag in ("td", "th") and self.row is not None:
                self.cell = []

        def handle_data(self, data):
            if self.cell is not None:
                self.cell.append(data)

        def handle_endtag(self, tag):
            if tag in ("td", "th") and self.cell is not None:
                self.row.append(" ".join(" ".join(self.cell).split()))
                self.cell = None
            elif tag == "tr" and self.row is not None:
                self.table.append(self.row)
                self.row = None
            elif tag == "table" and self.table is not None:
                self.tables.append(self.table)
                self.table = None

    required_headers = {
        "overallrank",
        "state",
        "totaltaxburden",
        "propertytaxburden",
        "individualincometaxburden",
        "totalsalesexcisetaxburden",
    }

    def normalize_header(value):
        return re.sub(r"[^a-z0-9]", "", value.casefold())

    def parse_burden_cell(value):
        match = re.fullmatch(
            r"\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*(?:\(\s*(\d+)\s*\))?\s*",
            str(value),
        )
        if not match:
            raise ValueError(f"Unexpected article percentage cell: {value!r}")
        percentage = float(match.group(1))
        rank = int(match.group(2)) if match.group(2) else pd.NA
        return percentage, rank

    def parse_article_table(html, edition, url):
        parser = ArticleTableParser()
        parser.feed(html)
        column_names = None
        rows = None
        for table in parser.tables:
            if not table:
                continue
            headers = {
                normalize_header(name): i for i, name in enumerate(table[0])
            }
            if required_headers.issubset(headers):
                column_names = headers
                rows = table[1:]
                break
        if rows is None:
            raise ValueError(f"No complete 50-state rankings table found at {url}")

        records = []
        for row in rows:
            if len(row) <= max(column_names.values()):
                continue
            state = row[column_names["state"]].strip()
            if state not in STATES:
                continue
            total, _ = parse_burden_cell(row[column_names["totaltaxburden"]])
            property_pct, property_rank = parse_burden_cell(
                row[column_names["propertytaxburden"]]
            )
            income_pct, income_rank = parse_burden_cell(
                row[column_names["individualincometaxburden"]]
            )
            sales_pct, sales_rank = parse_burden_cell(
                row[column_names["totalsalesexcisetaxburden"]]
            )
            rank_match = re.search(
                r"\d+", row[column_names["overallrank"]]
            )
            if rank_match is None:
                raise ValueError(f"Unexpected overall rank for {state}: {row}")
            records.append({
                "period": edition,
                "census_fy": EDITIONS[edition],
                "state": state,
                "overall_rank": int(rank_match.group()),
                "total_burden_pct": total,
                "property_rank": property_rank,
                "property_burden_pct": property_pct,
                "individual_income_rank": income_rank,
                "individual_income_burden_pct": income_pct,
                "sales_excise_rank": sales_rank,
                "sales_excise_burden_pct": sales_pct,
                "data_source": "WalletHub article",
                "source_url": url,
            })

        article = pd.DataFrame(records)
        if len(article) != 50 or set(article["state"]) != set(STATES):
            raise ValueError(
                f"{edition}: expected 50 unique states, found {len(article)} rows."
            )
        if article["state"].duplicated().any():
            raise ValueError(f"{edition}: duplicate state rows in the article table.")
        for column in (
            "overall_rank",
            "property_rank",
            "individual_income_rank",
            "sales_excise_rank",
        ):
            article[column] = pd.to_numeric(
                article[column], errors="coerce"
            ).astype("Int64")
        return article

    article_frames = []
    article_errors = {}
    for edition, url in ARTICLE_URLS.items():
        try:
            article_year = edition.split()[1]
            article_path = fetch(
                url, f"wallethub_article_rankings_{article_year}.html"
            )
            html = article_path.read_text(encoding="utf-8")
            article_frames.append(parse_article_table(html, edition, url))
        except Exception as exc:
            article_errors[edition] = f"{type(exc).__name__}: {exc}"

    article_columns = [
        "period",
        "census_fy",
        "state",
        "overall_rank",
        "total_burden_pct",
        "property_rank",
        "property_burden_pct",
        "individual_income_rank",
        "individual_income_burden_pct",
        "sales_excise_rank",
        "sales_excise_burden_pct",
        "data_source",
        "source_url",
    ]
    article_rankings = (
        pd.concat(article_frames, ignore_index=True)
        if article_frames
        else pd.DataFrame(columns=article_columns)
    )
    return article_errors, article_rankings


@app.cell
def _(STATES, fetch, io, pd, re, zipfile):
    BEA_URL = "https://apps.bea.gov/regional/zip/SAINC.zip"

    def load_personal_income():
        """BEA SAINC1 line 1: personal income, millions of dollars -> $ by year."""
        z = zipfile.ZipFile(fetch(BEA_URL, "SAINC.zip"))
        names = [n for n in z.namelist() if re.search(r"SAINC1__ALL_AREAS", n)]
        if not names:
            raise RuntimeError(f"SAINC1 file not found in zip: {z.namelist()[:10]}")
        df = pd.read_csv(io.BytesIO(z.read(names[0])), encoding="latin-1", low_memory=False)
        df = df[pd.to_numeric(df["LineCode"], errors="coerce") == 1].copy()
        df["GeoName"] = df["GeoName"].astype(str).str.replace("*", "", regex=False).str.strip()
        df = df[df["GeoName"].isin(STATES)].set_index("GeoName")
        yrs = [c for c in df.columns if str(c).strip().isdigit()]
        out = df[yrs].apply(pd.to_numeric, errors="coerce") * 1_000_000.0
        out.columns = [int(c) for c in out.columns]
        return out

    return BEA_URL, load_personal_income


@app.cell
def _(CACHE, HEADERS, STATES, fetch_first, json, os, pd, requests):
    CENSUS_API_URL = "https://api.census.gov/data/timeseries/govslocalfin"

    def load_recent_census_taxes(fy):
        """Download state-and-local tax collections from Census' official API."""
        if fy not in (2023, 2024):
            raise ValueError(f"Expected a recent Census API year, got {fy}.")

        cache_path = CACHE / f"census_state_local_finance_{fy}.json"
        if cache_path.exists() and cache_path.stat().st_size > 0:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            source_url = CENSUS_API_URL
        else:
            api_key = os.environ.get("CENSUS_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Census FY2023/FY2024 data require a free Census API key. "
                    "Set CENSUS_API_KEY before running this notebook; see "
                    "https://www.census.gov/data/developers/guidance/api-user-guide.html."
                )
            params = {
                "get": "NAME,AGG_DESC,AGG_DESC_LABEL,GOVTYPE,GOVTYPE_LABEL,AMOUNT",
                "for": "state:*",
                "time": str(fy),
                "key": api_key,
            }
            try:
                response = requests.get(
                    CENSUS_API_URL,
                    params=params,
                    headers=HEADERS,
                    timeout=60,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Census API request failed ({type(exc).__name__}); "
                    "check your connection and Census API key."
                ) from None
            if 300 <= response.status_code < 400:
                location = response.headers.get("Location", "")
                if "invalid_key" in location.casefold():
                    raise RuntimeError(
                        "Census rejected the API key and redirected to its "
                        "invalid-key page. Check that CENSUS_API_KEY is copied "
                        "correctly and active, then restart marimo so its kernel "
                        "inherits the updated environment."
                    )
                raise RuntimeError(
                    f"Census API redirected the request (HTTP {response.status_code})."
                )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Census API returned HTTP {response.status_code}: "
                    f"{response.text[:250]}"
                )
            try:
                payload = response.json()
            except ValueError:
                content_type = response.headers.get("Content-Type", "unknown")
                raise RuntimeError(
                    "Census API returned non-JSON data "
                    f"(Content-Type: {content_type}); check the API key or "
                    "whether Census returned an error page."
                ) from None
            if isinstance(payload, dict) and "error" in payload:
                raise RuntimeError(f"Census API error: {payload['error']}")
            cache_path.write_text(
                json.dumps(payload), encoding="utf-8"
            )
            source_url = CENSUS_API_URL

        if not payload or isinstance(payload[0], dict):
            raise RuntimeError(f"Census API returned an invalid FY{fy} response.")
        frame = pd.DataFrame(payload[1:], columns=payload[0])
        required = {"NAME", "AGG_DESC", "AGG_DESC_LABEL", "GOVTYPE_LABEL", "AMOUNT"}
        if not required.issubset(frame.columns):
            raise RuntimeError(
                f"Census FY{fy} response is missing columns: "
                f"{sorted(required - set(frame.columns))}"
            )

        local_level = frame["GOVTYPE_LABEL"].astype(str).str.contains(
            r"state\s*(?:and|&)\s*local", case=False, regex=True, na=False
        )
        frame = frame[local_level & frame["NAME"].isin(STATES)].copy()
        categories = {
            "property": ("LF0009", "taxes - property"),
            "income": ("LF0023", "income taxes - individual"),
            "general_sales": ("LF0011", "taxes - general sales"),
            "selective_sales": ("LF0012", "total selective sales"),
        }

        rows = {}
        for category, (aggregate_code, expected_label) in categories.items():
            selected = frame.loc[
                frame["AGG_DESC"].eq(aggregate_code),
                ["NAME", "AMOUNT", "AGG_DESC_LABEL"],
            ].copy()
            labels = selected["AGG_DESC_LABEL"].astype(str).str.casefold()
            if selected.empty or not labels.str.endswith(expected_label).all():
                raise RuntimeError(
                    f"FY{fy}: Census aggregate {aggregate_code} did not match "
                    f"the expected '{category}' category. Labels: "
                    f"{selected['AGG_DESC_LABEL'].drop_duplicates().tolist()}"
                )
            if selected["NAME"].duplicated().any():
                duplicates = selected.loc[
                    selected["NAME"].duplicated(keep=False), "NAME"
                ].drop_duplicates().tolist()
                raise RuntimeError(
                    f"FY{fy}: Census aggregate {aggregate_code} has duplicate "
                    f"rows for states: {duplicates}"
                )
            values = pd.to_numeric(selected["AMOUNT"], errors="coerce")
            if values.isna().any():
                raise RuntimeError(
                    f"FY{fy}: Census aggregate {aggregate_code} has blank amounts."
                )
            rows[category] = pd.Series(
                values.to_numpy() * 1_000.0,
                index=selected["NAME"],
            ).reindex(STATES, fill_value=0.0)

        taxes = pd.DataFrame(rows).reindex(STATES)
        taxes["sales_excise"] = taxes["general_sales"] + taxes["selective_sales"]
        if taxes.isna().any().any():
            raise RuntimeError(f"FY{fy}: Census categories did not cover all 50 states.")
        return taxes, source_url

    def census_urls(fy):
        yy = str(fy)[-2:]
        base = f"https://www2.census.gov/programs-surveys/gov-finances/tables/{fy}/"
        return [base + f"{yy}slsstab1.xlsx", base + f"{yy}slsstab1.xls"]

    def load_census_taxes(fy):
        """State+local combined tax revenue ($) from ALFIN Table 1 for fiscal year fy."""
        if fy in (2023, 2024):
            return load_recent_census_taxes(fy)
        if fy not in (2021, 2022):
            raise ValueError(f"Unsupported Census fiscal year: {fy}.")
        path, url = fetch_first(census_urls(fy), f"alfin_table1_{fy}{'.xlsx' if 'xlsx' in census_urls(fy)[0] else ''}")
        raw = pd.read_excel(path, header=None)

        desc_col = 1 if raw.shape[1] > 1 and raw.iloc[:50, 1].notna().sum() > 10 else 0

        row_prop, row_gen_sales, row_sel_sales, row_inc = None, None, None, None
        for r in range(len(raw)):
            val = str(raw.iloc[r, desc_col]).strip().lower()
            if val == "property":
                row_prop = r
            elif val == "general sales":
                row_gen_sales = r
            elif val == "selective sales":
                row_sel_sales = r
            elif val == "individual income":
                row_inc = r

        if None in (row_prop, row_gen_sales, row_sel_sales, row_inc):
            raise RuntimeError(
                f"FY{fy}: could not find all tax categories in {url}. "
                f"prop={row_prop}, gen={row_gen_sales}, sel={row_sel_sales}, inc={row_inc}")

        state_cols = {}
        for c in range(raw.shape[1]):
            header_cells = [str(v).strip() for v in raw.iloc[:15, c] if pd.notna(v)]
            for st in STATES:
                if st not in state_cols and st in header_cells:
                    state_cols[st] = c

        if len(state_cols) != 50:
            missing_st = [s for s in STATES if s not in state_cols]
            raise RuntimeError(f"FY{fy}: parsed {len(state_cols)} states from {url}; expected 50. Missing: {missing_st}")

        scale = 1000.0  # Census tables are in $ thousands
        rows = {}
        for st, c in state_cols.items():
            p_val = pd.to_numeric(raw.iloc[row_prop, c], errors="coerce") * scale
            gs_val = pd.to_numeric(raw.iloc[row_gen_sales, c], errors="coerce") * scale
            ss_val = pd.to_numeric(raw.iloc[row_sel_sales, c], errors="coerce") * scale
            inc_val = pd.to_numeric(raw.iloc[row_inc, c], errors="coerce") * scale

            rows[st] = {
                "property": p_val,
                "general_sales": gs_val,
                "selective_sales": ss_val,
                "income": inc_val,
                "sales_excise": gs_val + ss_val,
            }
        df = pd.DataFrame(rows).T
        return df, url

    return (load_census_taxes,)


@app.cell
def _(load_census_taxes, pd):
    def burden_table(fy, pi):
        taxes, url = load_census_taxes(fy)
        denom = pi[fy]  # personal income, same calendar year as the fiscal year
        out = pd.DataFrame({
            "property": taxes["property"] / denom * 100,
            "income": taxes["income"] / denom * 100,
            "general_sales": taxes["general_sales"] / denom * 100,
            "selective_sales": taxes["selective_sales"] / denom * 100,
        })
        out["sales_excise"] = out["general_sales"] + out["selective_sales"]
        out["total"] = out[
            ["property", "income", "general_sales", "selective_sales"]
        ].sum(axis=1)
        for c in [
            "total",
            "property",
            "income",
            "general_sales",
            "selective_sales",
            "sales_excise",
        ]:
            out[f"rank_{c}"] = out[c].rank(ascending=False, method="min").astype(int)
        out["property_tax_revenue_usd"] = taxes["property"]
        out["individual_income_tax_revenue_usd"] = taxes["income"]
        out["general_sales_tax_revenue_usd"] = taxes["general_sales"]
        out["selective_sales_tax_revenue_usd"] = taxes["selective_sales"]
        out["sales_excise_tax_revenue_usd"] = taxes["sales_excise"]
        out["personal_income_usd"] = denom
        return out.sort_values("total", ascending=False), url

    def safe_burden(fy, pi):
        try:
            return burden_table(fy, pi), None
        except Exception as e:
            return None, str(e)

    return (safe_burden,)


@app.cell
def _(BEA_URL, load_personal_income, mo):
    with mo.status.spinner("Downloading BEA personal income..."):
        PI = load_personal_income()
    mo.md(f"BEA personal income loaded: {PI.shape[0]} states, years {PI.columns.min()}–{PI.columns.max()}")
    return BEA_URL, PI


@app.cell
def _(EDITIONS, LATEST_FY, PI, REQUESTED_FY, article_rankings, mo, pd, safe_burden):
    def _():
        results, result_urls, errors, unavailable, rows = {}, {}, {}, {}, []
        all_fy = sorted(set(EDITIONS.values()) | {LATEST_FY, REQUESTED_FY})
        with mo.status.spinner("Downloading Census state & local finance tables..."):
            for _fy in all_fy:
                if _fy > LATEST_FY:
                    unavailable[_fy] = (
                        f"Not published yet. Census' [current State and Local Finance "
                        f"series](https://www.census.gov/data/developers/data-sets/"
                        f"govslocalfin.html) covers 2017–{LATEST_FY}; no FY{_fy} "
                        "tax burden or ranking can be calculated until Census releases "
                        "the tax-revenue observations."
                    )
                    continue
                if _fy not in PI.columns:
                    errors[_fy] = f"BEA personal income not yet available for {_fy}"
                    continue
                res, err = safe_burden(_fy, PI)
                if err:
                    errors[_fy] = err
                else:
                    results[_fy] = res[0]
                    result_urls[_fy] = res[1]

        for ed, _fy in EDITIONS.items():
            article = article_rankings[article_rankings["period"] == ed]
            if _fy not in results or article.empty:
                continue
            t = results[_fy]
            diffs = []
            for row in article.itertuples(index=False):
                diffs.extend([
                    abs(t.loc[row.state, "total"] - row.total_burden_pct),
                    abs(t.loc[row.state, "property"] - row.property_burden_pct),
                    abs(t.loc[row.state, "income"] - row.individual_income_burden_pct),
                    abs(t.loc[row.state, "sales_excise"] - row.sales_excise_burden_pct),
                ])
            if diffs:
                rows.append({
                    "WalletHub edition": ed,
                    "Census fiscal year used": _fy,
                    "max abs. difference (pp)": max(diffs),
                    "mean abs. difference (pp)": sum(diffs) / len(diffs),
                    "states checked": len(article),
                })
        match = pd.DataFrame(rows)
        return results, result_urls, errors, unavailable, match


    results, result_urls, errors, unavailable, match = _()
    return errors, match, results, result_urls, unavailable


@app.cell
def _(article_errors, errors, match, mo, unavailable):
    err_md = "\n".join(f"- FY{k}: `{v[:300]}`" for k, v in errors.items()) or "None"
    article_err_md = "\n".join(
        f"- {edition}: `{message[:300]}`"
        for edition, message in article_errors.items()
    ) or "None"
    unavailable_md = "\n".join(
        f"- FY{k}: {v}" for k, v in unavailable.items()
    ) or "None"
    mo.vstack([
        mo.md(
            "## Article-year check\n"
            "The table compares downloaded-source calculations with all 50 state values "
            "published in each article table. The article does not name its fiscal-year input; "
            "the inferred year is the one used for the full rankings below. Small residual "
            "differences can reflect source revisions and rounding."
        ),
        mo.ui.table(match.round(3), selection=None) if len(match) else mo.md("No benchmark results."),
        mo.md(f"**Article-table download / parse errors:**\n\n{article_err_md}"),
        mo.md(f"**Requested Census year not yet published:**\n\n{unavailable_md}"),
        mo.md(f"**Download / parse errors:**\n\n{err_md}"),
    ])
    return


@app.cell
def _(BEA_URL, EDITIONS, article_rankings, mo, pd, result_urls, results):
    comparison_columns = [
        "period",
        "census_fy",
        "state",
        "data_source",
        "overall_rank",
        "total_burden_pct",
        "property_rank",
        "property_burden_pct",
        "individual_income_rank",
        "individual_income_burden_pct",
        "sales_excise_rank",
        "sales_excise_burden_pct",
        "source_url",
        "income_source_url",
    ]
    comparison_records = []
    for row in article_rankings.to_dict("records"):
        comparison_records.append({
            **{name: row.get(name) for name in comparison_columns},
            "data_source": "WalletHub article",
            "income_source_url": pd.NA,
        })

    article_period_by_fy = {fy: edition for edition, fy in EDITIONS.items()}
    raw_records = []
    for fy, calculated in results.items():
        period = article_period_by_fy.get(fy, "Latest Census data")
        tax_source_url = result_urls[fy]
        for state, values in calculated.iterrows():
            comparison_records.append({
                "period": period,
                "census_fy": fy,
                "state": state,
                "data_source": "Downloaded Census + BEA",
                "overall_rank": values["rank_total"],
                "total_burden_pct": values["total"],
                "property_rank": values["rank_property"],
                "property_burden_pct": values["property"],
                "individual_income_rank": values["rank_income"],
                "individual_income_burden_pct": values["income"],
                "sales_excise_rank": values["rank_sales_excise"],
                "sales_excise_burden_pct": values["sales_excise"],
                "source_url": tax_source_url,
                "income_source_url": BEA_URL,
            })
            raw_records.append({
                "period": period,
                "census_fy": fy,
                "state": state,
                "property_tax_revenue_usd": values["property_tax_revenue_usd"],
                "individual_income_tax_revenue_usd": values[
                    "individual_income_tax_revenue_usd"
                ],
                "general_sales_tax_revenue_usd": values[
                    "general_sales_tax_revenue_usd"
                ],
                "selective_sales_tax_revenue_usd": values[
                    "selective_sales_tax_revenue_usd"
                ],
                "sales_excise_tax_revenue_usd": values[
                    "sales_excise_tax_revenue_usd"
                ],
                "personal_income_usd": values["personal_income_usd"],
                "census_source_url": tax_source_url,
                "bea_source_url": BEA_URL,
            })

    comparison_data = pd.DataFrame(comparison_records, columns=comparison_columns)
    raw_columns = [
        "period",
        "census_fy",
        "state",
        "property_tax_revenue_usd",
        "individual_income_tax_revenue_usd",
        "general_sales_tax_revenue_usd",
        "selective_sales_tax_revenue_usd",
        "sales_excise_tax_revenue_usd",
        "personal_income_usd",
        "census_source_url",
        "bea_source_url",
    ]
    downloaded_inputs = pd.DataFrame(raw_records, columns=raw_columns)

    period_order = [*EDITIONS, "Latest Census data"]
    source_order = ["WalletHub article", "Downloaded Census + BEA"]
    comparison_data["period"] = pd.Categorical(
        comparison_data["period"], categories=period_order, ordered=True
    )
    comparison_data["data_source"] = pd.Categorical(
        comparison_data["data_source"], categories=source_order, ordered=True
    )
    comparison_data["census_fy"] = pd.to_numeric(
        comparison_data["census_fy"], errors="coerce"
    ).astype("Int64")
    for rank_column in (
        "overall_rank",
        "property_rank",
        "individual_income_rank",
        "sales_excise_rank",
    ):
        comparison_data[rank_column] = pd.to_numeric(
            comparison_data[rank_column], errors="coerce"
        ).astype("Int64")
    comparison_data.sort_values(
        ["period", "census_fy", "state", "data_source"],
        inplace=True,
        ignore_index=True,
    )

    downloaded_inputs["period"] = pd.Categorical(
        downloaded_inputs["period"], categories=period_order, ordered=True
    )
    downloaded_inputs["census_fy"] = pd.to_numeric(
        downloaded_inputs["census_fy"], errors="coerce"
    ).astype("Int64")
    downloaded_inputs.sort_values(
        ["period", "census_fy", "state"], inplace=True, ignore_index=True
    )

    comparison_data = comparison_data.set_index(
        ["period", "census_fy", "state", "data_source"]
    )
    downloaded_inputs = downloaded_inputs.set_index(
        ["period", "census_fy", "state"]
    )
    comparison_metrics = [
        "overall_rank",
        "total_burden_pct",
        "property_rank",
        "property_burden_pct",
        "individual_income_rank",
        "individual_income_burden_pct",
        "sales_excise_rank",
        "sales_excise_burden_pct",
    ]
    comparison_view = comparison_data.reset_index().pivot(
        index=["period", "census_fy", "state"],
        columns="data_source",
        values=comparison_metrics,
    )
    source_labels = {
        "WalletHub article": "WalletHub",
        "Downloaded Census + BEA": "Census + BEA",
    }
    comparison_view = comparison_view.reindex(
        columns=pd.MultiIndex.from_product(
            [comparison_metrics, source_labels]
        )
    )
    metric_labels = {
        "overall_rank": "overall rank",
        "total_burden_pct": "total burden (%)",
        "property_rank": "property rank",
        "property_burden_pct": "property burden (%)",
        "individual_income_rank": "income rank",
        "individual_income_burden_pct": "income burden (%)",
        "sales_excise_rank": "sales/excise rank",
        "sales_excise_burden_pct": "sales/excise burden (%)",
    }
    comparison_view.columns = [
        f"{source_labels[source]} {metric_labels[metric]}"
        for metric, source in comparison_view.columns
    ]
    comparison_view = comparison_view.reset_index()
    comparison_view.sort_values(
        ["period", "census_fy", "state"], inplace=True, ignore_index=True
    )
    comparison_view_columns = {
        column: pd.to_numeric(comparison_view[column], errors="coerce").astype(
            "Int64"
        )
        for column in (
            "WalletHub overall rank",
            "WalletHub property rank",
            "WalletHub income rank",
            "WalletHub sales/excise rank",
            "Census + BEA overall rank",
            "Census + BEA property rank",
            "Census + BEA income rank",
            "Census + BEA sales/excise rank",
        )
    }
    for column, values in comparison_view_columns.items():
        comparison_view[column] = values
    burden_columns = [
        column
        for column in comparison_view
        if column.endswith("burden (%)")
    ]
    comparison_view[burden_columns] = comparison_view[burden_columns].round(2)
    input_view = downloaded_inputs.reset_index().drop(
        columns=["census_source_url", "bea_source_url"]
    )
    amount_columns = [
        "property_tax_revenue_usd",
        "individual_income_tax_revenue_usd",
        "general_sales_tax_revenue_usd",
        "selective_sales_tax_revenue_usd",
        "sales_excise_tax_revenue_usd",
        "personal_income_usd",
    ]
    input_view[amount_columns] = input_view[amount_columns].apply(
        lambda column: column.map(
            lambda amount: f"${amount:,.0f}" if pd.notna(amount) else ""
        )
    )
    mo.vstack([
        mo.md(
            "## Complete article and downloaded-data comparison\n"
            "Each state and period occupies one row, with WalletHub and independent "
            "Census + BEA values side by side. Burden percentages are displayed to two "
            "decimals; the underlying `comparison_data` retains full precision. Article "
            "tax-type ranks are blank when the article did not publish them. "
            "`comparison_data` is the long-form MultiIndex DataFrame; use "
            "`comparison_data.reset_index().to_csv(...)` for the full comparison export."
        ),
        mo.ui.table(comparison_view, selection=None, page_size=200),
        mo.md(
            "## Raw downloaded inputs\n"
            "Census revenue amounts and BEA personal income are shown in dollars with "
            "commas; the underlying `downloaded_inputs` DataFrame remains numeric. "
            "The `downloaded_inputs` MultiIndex is `(period, census_fy, state)`; source "
            "URLs remain available in the DataFrame."
        ),
        mo.ui.table(input_view, selection=None, page_size=200),
    ])
    return comparison_data, downloaded_inputs


@app.cell
def _(LATEST_FY, errors, mo, pd, results):
    calculated_columns = {
        "rank_total": "overall_rank",
        "total": "total_burden_pct",
        "property": "property_tax_pct",
        "income": "individual_income_tax_pct",
        "general_sales": "general_sales_tax_pct",
        "selective_sales": "selective_sales_tax_pct",
        "sales_excise": "sales_excise_tax_pct",
        "rank_property": "property_tax_rank",
        "rank_income": "individual_income_tax_rank",
        "rank_sales_excise": "sales_excise_tax_rank",
        "personal_income_usd": "personal_income_usd",
    }
    if results:
        burden_data = (
            pd.concat(
                {
                    fy: frame.rename_axis("state")
                    for fy, frame in results.items()
                },
                names=["census_fy", "state"],
            )
            .reset_index()
            .rename(columns=calculated_columns)
        )
        burden_data["census_fy"] = pd.to_numeric(
            burden_data["census_fy"], errors="raise"
        ).astype(int)
        burden_data["overall_rank"] = pd.to_numeric(
            burden_data["overall_rank"], errors="raise"
        ).astype(int)

        average_ranks = (
            burden_data.groupby("state", as_index=False)["overall_rank"]
            .mean()
            .rename(columns={"overall_rank": "Average rank"})
            .sort_values(["Average rank", "state"], ignore_index=True)
        )
        state_order = average_ranks["state"].tolist()
        year_order = sorted(burden_data["census_fy"].unique())
        burden_data["rank_and_burden"] = (
            burden_data["overall_rank"].astype(str)
            + " / "
            + burden_data["total_burden_pct"].map(lambda value: f"{value:.2f}%")
        )
        yearly_table = burden_data.pivot(
            index="state",
            columns="census_fy",
            values="rank_and_burden",
        ).reindex(index=state_order, columns=year_order)
        yearly_table.columns = [f"FY{year}" for year in year_order]
        yearly_table.insert(
            0,
            "Average rank",
            average_ranks.set_index("state").reindex(state_order)["Average rank"].round(1),
        )
        yearly_table = yearly_table.reset_index().rename(
            columns={"state": "State"}
        )
        yearly_output = mo.ui.table(yearly_table, selection=None, page_size=50)
    else:
        burden_data = pd.DataFrame(
            columns=["census_fy", "state", *calculated_columns.values()]
        )
        yearly_output = mo.md(
            "No Census + BEA state-year calculations succeeded, so the rank table "
            "cannot be built. See the download / parse errors above."
        )

    latest_year_data = burden_data.loc[
        burden_data["census_fy"].eq(LATEST_FY)
    ].copy()
    if latest_year_data.empty:
        latest_error = errors.get(
            LATEST_FY, "No complete Census + BEA calculation was returned."
        ).replace("`", "'")
        latest_output = mo.md(
            f"**FY{LATEST_FY} has no calculated state ranks in this run.** "
            f"FY{LATEST_FY} is the latest Census year configured here, but its "
            f"Census + BEA calculation did not complete: `{latest_error}`. "
            f"The available WalletHub article editions do not provide a rank for FY{LATEST_FY}."
        )
    else:
        latest_table = latest_year_data.sort_values(
            ["overall_rank", "state"]
        )[
            [
                "overall_rank",
                "total_burden_pct",
                "state",
                "property_tax_pct",
                "individual_income_tax_pct",
                "general_sales_tax_pct",
                "selective_sales_tax_pct",
                "personal_income_usd",
            ]
        ].rename(
            columns={
                "overall_rank": "Overall rank",
                "total_burden_pct": "Total burden (%)",
                "state": "State",
                "property_tax_pct": "Property tax (%)",
                "individual_income_tax_pct": "Individual income tax (%)",
                "general_sales_tax_pct": "General sales tax (%)",
                "selective_sales_tax_pct": "Selective sales tax (%)",
                "personal_income_usd": "BEA personal income ($)",
            }
        )
        percentage_columns = [
            "Total burden (%)",
            "Property tax (%)",
            "Individual income tax (%)",
            "General sales tax (%)",
            "Selective sales tax (%)",
        ]
        latest_table[percentage_columns] = latest_table[percentage_columns].apply(
            lambda column: column.map(lambda value: f"{value:.2f}%")
        )
        latest_table["BEA personal income ($)"] = latest_table[
            "BEA personal income ($)"
        ].map(lambda value: f"${value:,.0f}")
        latest_output = mo.ui.table(latest_table, selection=None, page_size=50)

    if LATEST_FY in results:
        latest_status = mo.md(
            f"FY{LATEST_FY} is calculated from Census state-and-local tax "
            f"collections and BEA {LATEST_FY} personal income. This is an "
            "independent Census + BEA rank, not a WalletHub article rank."
        )
    else:
        latest_status = mo.md(
            f"FY{LATEST_FY} is the latest Census year configured in this notebook, "
            "but no rank is available in this run; the reason is shown below."
        )

    mo.vstack(
        [
            mo.md(
                "## Tax-burden rank and value by state\\n"
                "Each fiscal-year column shows **overall rank / total burden (%)**. "
                "States are sorted by their mean overall rank across the available "
                "Census + BEA years (rank 1 is the highest burden)."
            ),
            yearly_output,
            mo.md(f"## FY{LATEST_FY} state tax burden and inputs"),
            latest_status,
            latest_output,
        ]
    )
    return (burden_data,)


@app.cell
def _(burden_data, mo):
    if burden_data.empty:
        state_options = []
        initial_highlights = []
    else:
        mean_rank_order = (
            burden_data.groupby("state", as_index=False)["overall_rank"]
            .mean()
            .rename(columns={"overall_rank": "mean_rank"})
            .sort_values(["mean_rank", "state"], ignore_index=True)
        )
        state_options = sorted(burden_data["state"].unique())
        initial_highlights = [
            *mean_rank_order.head(3)["state"],
            *mean_rank_order.tail(3)["state"],
        ]

    state_picker = mo.ui.multiselect(
        options=state_options,
        value=initial_highlights,
        label="Highlight states (choose a few by name)",
    )
    state_picker
    return (state_picker,)


@app.cell
def _(alt, burden_data, mo, state_picker):
    if burden_data.empty:
        chart_output = mo.md(
            "The state trend chart is unavailable because no Census + BEA "
            "state-year calculations succeeded."
        )
    else:
        highlighted = burden_data.loc[
            burden_data["state"].isin(state_picker.value)
        ].copy()
        last_year = burden_data["census_fy"].max()
        endpoint_labels = highlighted.loc[
            highlighted["census_fy"].eq(last_year)
        ]

        fiscal_year_axis = alt.X(
            "census_fy:O",
            title="Census fiscal year",
            sort="ascending",
            scale=alt.Scale(padding=1.8),
            axis=alt.Axis(labelAngle=0),
        )
        rank_axis = alt.Y(
            "overall_rank:Q",
            title="Overall tax-burden rank (1 = highest)",
            scale=alt.Scale(domain=[1, 50], reverse=True),
            axis=alt.Axis(values=[1, 10, 20, 30, 40, 50]),
        )
        state_color = alt.Color(
            "state:N",
            title="Selected state",
            scale=alt.Scale(scheme="tableau20"),
            legend=None,
        )
        trend_tooltip = [
            alt.Tooltip("state:N", title="State"),
            alt.Tooltip("census_fy:O", title="Census fiscal year"),
            alt.Tooltip("overall_rank:Q", title="Overall rank", format=".0f"),
            alt.Tooltip(
                "total_burden_pct:Q", title="Total burden (%)", format=".2f"
            ),
        ]
        background_lines = alt.Chart(burden_data).mark_line(
            color="#b7b7b7", strokeWidth=1, opacity=0.55
        ).encode(
            x=fiscal_year_axis,
            y=rank_axis,
            detail="state:N",
        )
        selected_lines = alt.Chart(highlighted).mark_line(
            strokeWidth=2.5
        ).encode(
            x=fiscal_year_axis,
            y=rank_axis,
            detail="state:N",
            color=state_color,
        )
        selected_points = alt.Chart(highlighted).mark_point(
            filled=True, size=90, stroke="white", strokeWidth=0.7
        ).encode(
            x=fiscal_year_axis,
            y=rank_axis,
            color=state_color,
            tooltip=trend_tooltip,
        )
        selected_labels = alt.Chart(endpoint_labels).mark_text(
            align="left", dx=7, fontSize=10
        ).encode(
            x=fiscal_year_axis,
            y=rank_axis,
            color=state_color,
            text="state:N",
        )
        trend_chart = (
            alt.layer(
                background_lines,
                selected_lines,
                selected_points,
                selected_labels,
            )
            .properties(
                width=640,
                height=560,
                title=alt.TitleParams(
                    text="Track selected states across Census fiscal years",
                    subtitle=[
                        "Gray lines show all calculated states; choose states by name to highlight their ranks.",
                        f"Labels mark the last available year (FY{last_year}); rank 1 is at the top.",
                    ],
                    anchor="start",
                ),
            )
            .resolve_scale(x="shared", y="shared", color="shared")
        )
        chart_output = mo.vstack(
            [
                mo.md(
                    "## State rank trends\\n"
                    "The chart avoids mouse-based state picking: every state is a "
                    "thin gray reference line, and the multiselect highlights chosen "
                    "states with larger points, tooltips, and labels at the last "
                    "available year. The initial view shows the three lowest and "
                    "three highest mean-rank states; choose a few states for clearer "
                    "labels. All series here are independent Census + BEA calculations."
                ),
                trend_chart,
            ]
        )
    chart_output
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Latest-year tax mix by state

    Both charts show each state's tax burden as stacked horizontal bars, sorted
    by total burden. The first separates individual income, general sales,
    selective sales, and property taxes. The second combines general and
    selective sales into one sales/excise segment, ordered income, sales/excise,
    then property. Every segment is state-and-local revenue divided by that
    state's BEA personal income, multiplied by 100; it is **not** a share of
    total tax revenue. A muted `#rank` at the end of each bar gives its overall
    rank; hover over a segment for its individual tax-type rank.
    """)
    return


@app.cell
def _(LATEST_FY, mo, pd, results):
    mo.stop(LATEST_FY not in results)
    latest_bar_data = results[LATEST_FY].rename_axis("state").reset_index()

    def make_tax_mix_data(tax_types):
        pieces = []
        for order, (tax_type, (value_column, rank_column)) in enumerate(
            tax_types.items()
        ):
            pieces.append(
                latest_bar_data[
                    ["state", "total", "rank_total", value_column, rank_column]
                ]
                .rename(
                    columns={
                        value_column: "burden_pct",
                        rank_column: "tax_type_rank",
                    }
                )
                .assign(tax_type=tax_type, tax_type_order=order)
            )
        return pd.concat(pieces, ignore_index=True)

    separate_sales_tax_mix = make_tax_mix_data(
        {
            "Individual income tax": ("income", "rank_income"),
            "General sales tax": ("general_sales", "rank_general_sales"),
            "Selective sales tax": ("selective_sales", "rank_selective_sales"),
            "Property tax": ("property", "rank_property"),
        }
    )
    combined_sales_tax_mix = make_tax_mix_data(
        {
            "Individual income tax": ("income", "rank_income"),
            "Sales/excise tax": ("sales_excise", "rank_sales_excise"),
            "Property tax": ("property", "rank_property"),
        }
    )
    return combined_sales_tax_mix, separate_sales_tax_mix


@app.cell
def _(alt):
    def tax_mix_chart(data, title):
        tax_type_order = (
            data[["tax_type", "tax_type_order"]]
            .drop_duplicates()
            .sort_values("tax_type_order")["tax_type"]
            .tolist()
        )

        x_scale = alt.Scale(domain=[0, data["total"].max() * 1.16], nice=False)
        state_sort = alt.SortField(field="total", order="descending")
        bars = alt.Chart(data).mark_bar().encode(
            x=alt.X(
                "burden_pct:Q",
                stack="zero",
                scale=x_scale,
                title="Tax revenue as % of state personal income",
            ),
            y=alt.Y("state:N", sort=state_sort, title=None),
            color=alt.Color(
                "tax_type:N",
                sort=tax_type_order,
                title="Tax type",
                legend=alt.Legend(
                    orient="top", direction="horizontal", columns=2
                ),
            ),
            order=alt.Order("tax_type_order:Q", sort="ascending"),
            tooltip=[
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip("tax_type:N", title="Tax type"),
                alt.Tooltip("burden_pct:Q", title="Tax burden (%)", format=".2f"),
                alt.Tooltip(
                    "tax_type_rank:Q",
                    title="Tax-type rank (1 = highest)",
                    format=".0f",
                ),
                alt.Tooltip(
                    "rank_total:Q",
                    title="Overall rank (1 = highest)",
                    format=".0f",
                ),
                alt.Tooltip("total:Q", title="Total burden (%)", format=".2f"),
            ],
        )

        overall_rank_labels = data[
            ["state", "total", "rank_total"]
        ].drop_duplicates("state").copy()
        overall_rank_labels["overall_rank_label"] = (
            "#" + overall_rank_labels["rank_total"].astype(str)
        )
        labels = alt.Chart(overall_rank_labels).mark_text(
            align="left", baseline="middle", dx=5, fontSize=9, color="#666666"
        ).encode(
            x=alt.X("total:Q", scale=x_scale, axis=None),
            y=alt.Y("state:N", sort=state_sort),
            text="overall_rank_label:N",
        )

        return (
            alt.layer(bars, labels)
            .resolve_scale(x="shared", y="shared")
            .properties(
                width=760,
                height=760,
                title=alt.TitleParams(
                    text=title,
                    subtitle=[
                        "Muted # labels at bar ends show overall rank; hover on a segment for tax-type rank."
                    ],
                    anchor="start",
                ),
            )
        )

    return (tax_mix_chart,)


@app.cell
def _(LATEST_FY, mo, separate_sales_tax_mix, tax_mix_chart):
    separate_sales_chart = tax_mix_chart(
        separate_sales_tax_mix,
        f"State and local tax revenue by type — Census FY{LATEST_FY}",
    )
    mo.vstack(
        [
            mo.md("### General and selective sales shown separately"),
            separate_sales_chart,
        ]
    )
    return


@app.cell
def _(LATEST_FY, combined_sales_tax_mix, mo, tax_mix_chart):
    combined_sales_chart = tax_mix_chart(
        combined_sales_tax_mix,
        f"State and local tax revenue, sales/excise combined — Census FY{LATEST_FY}",
    )
    mo.vstack(
        [
            mo.md("### General and selective sales combined"),
            combined_sales_chart,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
