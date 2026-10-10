# /// script
# requires-python = ">=3.10"
# dependencies = ["marimo", "pandas", "requests", "openpyxl", "xlrd", "matplotlib"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import io, json, os, re, zipfile, pathlib
    from html.parser import HTMLParser
    import marimo as mo
    import pandas as pd
    import requests

    return HTMLParser, io, json, mo, os, pathlib, pd, re, requests, zipfile


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
    revenue. The chart at the end stacks three percentages: property tax,
    individual income tax, and sales/excise tax. Sales/excise combines general-sales
    and selective-sales revenue:

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
    `tax_type_pct = 0.1 * Census_AMOUNT_thousands / BEA_SAINC1_millions`;
    for sales/excise, add the general-sales and selective-sales amounts first. The
    stacked bar chart shows these three resulting tax-type percentages for each
    state; the total bar length is their sum.
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
            "sales_excise": taxes["sales_excise"] / denom * 100,
        })
        out["total"] = out[["property", "income", "sales_excise"]].sum(axis=1)
        for c in ["total", "property", "income", "sales_excise"]:
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
def _(LATEST_FY, mo, results):
    import matplotlib.pyplot as plt
    mo.stop(LATEST_FY not in results)
    t = results[LATEST_FY].sort_values("total")
    fig, ax = plt.subplots(figsize=(7, 10))
    ax.barh(t.index, t["property"], label="Property tax")
    ax.barh(t.index, t["income"], left=t["property"], label="Individual income tax")
    ax.barh(
        t.index,
        t["sales_excise"],
        left=t["property"] + t["income"],
        label="Sales & excise taxes",
    )
    ax.set_xlabel("Tax revenue as % of state personal income")
    ax.set_title(f"State and local tax revenue by type — Census FY{LATEST_FY}")
    ax.legend(); fig.tight_layout()
    mo.vstack([
        mo.md(
            "## Latest-year tax mix by state\n"
            "Each bar segment is the corresponding state-and-local tax revenue "
            "divided by that state's BEA personal income, multiplied by 100. "
            "It is **not** a share of total tax revenue. Sales & excise combines "
            "Census general-sales and selective-sales revenue; the full bar is "
            "the sum of property, individual-income, and sales/excise percentages."
        ),
        fig,
    ])
    return


if __name__ == "__main__":
    app.run()
