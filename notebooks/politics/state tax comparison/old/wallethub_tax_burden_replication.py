# /// script
# requires-python = ">=3.10"
# dependencies = ["marimo", "pandas", "requests", "openpyxl", "xlrd", "matplotlib"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import io, json, os, re, zipfile, pathlib
    import marimo as mo
    import pandas as pd
    import requests

    return io, json, mo, os, pathlib, pd, re, requests, zipfile


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Reproducing WalletHub's "Tax Burden by State" from primary data

    See the companion [methodology and year-mapping notes](README.md).

    **Method (per [WalletHub](https://wallethub.com/edu/states-with-highest-lowest-tax-burden/20494)):** burden = (property tax, individual income tax, or
    sales and excise tax) / total state personal income. Total = sum of the three.
    Rank 1 = highest burden.

    **Primary sources downloaded by this notebook:**
    - [U.S. Census Bureau, state and local government finances](https://www.census.gov/data/developers/data-sets/govslocalfin.html)
      (tax collections; source years 2021–2024)
    - [U.S. BEA, SAINC1 state annual personal income](https://apps.bea.gov/regional/zip/SAINC.zip)

    The Census numerator is the combined state-and-local total for each state area:
    property taxes, individual income taxes, and general sales plus selective sales
    taxes. The BEA denominator is SAINC1 LineCode 1 (personal income). Census amounts
    are in thousands of dollars and BEA amounts in millions; the loaders convert both
    to dollars before calculating percentages. The [Tax Policy Center series definitions](https://state-local-finance-data.taxpolicycenter.org/help/revenue.html)
    describe the matching categories: property tax, individual income tax (not corporate
    income tax), and total sales/gross receipts (general plus selective sales).

    ### Source fit and limits

    WalletHub cites the [Tax Policy Center (TPC)](https://state-local-finance-data.taxpolicycenter.org/),
    whose state/local finance system republishes Census finance data and reports revenue
    as a fraction of personal income. Using Census and BEA directly is therefore a good
    primary-source match to the *same concepts and underlying programs* WalletHub describes.
    WalletHub does not name its input fiscal year or publish a frozen calculation extract,
    so we cannot verify that it used these exact files, revisions, or aggregations.

    The calculations themselves use downloaded Census and BEA data. To assess the
    source-year match, we compare those calculations with five WalletHub-published state
    figures per edition, manually transcribed in `FIXTURES` as validation targets. These
    published figures are the only copied comparison values; they are never calculation
    inputs. The article-to-data mapping used here is:

    | WalletHub article edition | Census fiscal year used |
    | --- | --- |
    | 2024 | FY2021 |
    | 2025 | FY2022 |
    | 2026 | FY2023 |
    | Latest Census data | FY2024 |

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

    WalletHub's published values appear only in `FIXTURES`, as five-state validation
    examples per edition. They are never inputs to the calculations.
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

    # (total, property, income, sales_excise) in %, transcribed from the articles
    # solely as validation targets.
    FIXTURES = {
        "WalletHub 2024 article": {
            "New York": (12.02, 4.36, 4.63, 3.03), "Hawaii": (11.80, 2.64, 3.82, 5.34),
            "Washington": (8.04, 2.58, 0.00, 5.46), "Alabama": (7.52, 1.33, 2.01, 4.18),
            "Alaska": (4.93, 3.54, 0.00, 1.39),
        },
        "WalletHub 2025 article": {
            "Hawaii": (13.92, 2.57, 4.18, 7.17), "New York": (13.56, 4.28, 5.76, 3.52),
            "Washington": (8.61, 2.64, 0.00, 5.97), "Alabama": (7.99, 1.35, 2.37, 4.27),
            "Alaska": (4.93, 3.46, 0.00, 1.47),
        },
        "WalletHub 2026 article": {
            "Hawaii": (13.30, 2.62, 3.20, 7.48), "New York": (12.39, 4.22, 4.65, 3.53),
            "Washington": (8.47, 2.47, 0.13, 5.87), "Alabama": (7.93, 1.40, 2.17, 4.36),
            "Alaska": (4.92, 3.32, 0.00, 1.60),
        },
    }
    STATES = ["Alabama","Alaska","Arizona","Arkansas","California","Colorado","Connecticut",
        "Delaware","Florida","Georgia","Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas",
        "Kentucky","Louisiana","Maine","Maryland","Massachusetts","Michigan","Minnesota",
        "Mississippi","Missouri","Montana","Nebraska","Nevada","New Hampshire","New Jersey",
        "New Mexico","New York","North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
        "Pennsylvania","Rhode Island","South Carolina","South Dakota","Tennessee","Texas",
        "Utah","Vermont","Virginia","Washington","West Virginia","Wisconsin","Wyoming"]
    return CACHE, EDITIONS, FIXTURES, HEADERS, LATEST_FY, STATES


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

    return (load_personal_income,)


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
                    CENSUS_API_URL, params=params, headers=HEADERS, timeout=60
                )
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Census API request failed ({type(exc).__name__}); "
                    "check your connection and Census API key."
                ) from None
            if response.status_code != 200:
                raise RuntimeError(
                    f"Census API returned HTTP {response.status_code}: "
                    f"{response.text[:250]}"
                )
            try:
                payload = response.json()
            except ValueError:
                raise RuntimeError("Census API returned non-JSON data.") from None
            if isinstance(payload, dict) and "error" in payload:
                raise RuntimeError(f"Census API error: {payload['error']}")
            cache_path.write_text(
                json.dumps(payload), encoding="utf-8"
            )
            source_url = CENSUS_API_URL

        if not payload or isinstance(payload[0], dict):
            raise RuntimeError(f"Census API returned an invalid FY{fy} response.")
        frame = pd.DataFrame(payload[1:], columns=payload[0])
        required = {"NAME", "AGG_DESC_LABEL", "GOVTYPE_LABEL", "AMOUNT"}
        if not required.issubset(frame.columns):
            raise RuntimeError(
                f"Census FY{fy} response is missing columns: "
                f"{sorted(required - set(frame.columns))}"
            )

        local_level = frame["GOVTYPE_LABEL"].astype(str).str.contains(
            r"state\s*(?:and|&)\s*local", case=False, regex=True, na=False
        )
        frame = frame[local_level & frame["NAME"].isin(STATES)].copy()
        labels = frame["AGG_DESC_LABEL"].astype(str).str.casefold()
        categories = {
            "property": labels.str.contains(r"\bproperty\b", regex=True),
            "income": labels.str.contains(r"\bindividual income\b", regex=True),
            "general_sales": labels.str.contains(r"\bgeneral sales\b", regex=True),
            "selective_sales": labels.str.contains(r"\bselective sales\b", regex=True),
        }

        rows = {}
        for category, mask in categories.items():
            selected = frame.loc[mask, ["NAME", "AMOUNT"]].copy()
            if len(selected) != len(STATES):
                matches = frame.loc[mask, "AGG_DESC_LABEL"].drop_duplicates().tolist()
                raise RuntimeError(
                    f"FY{fy}: expected one Census '{category}' row per state "
                    f"({len(STATES)}); found {len(selected)}. Matching labels: {matches}"
                )
            values = pd.to_numeric(selected["AMOUNT"], errors="coerce") * 1_000.0
            rows[category] = pd.Series(values.to_numpy(), index=selected["NAME"])

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
        return out.sort_values("total", ascending=False), url

    def safe_burden(fy, pi):
        try:
            return burden_table(fy, pi), None
        except Exception as e:
            return None, str(e)

    return (safe_burden,)


@app.cell
def _(load_personal_income, mo):
    with mo.status.spinner("Downloading BEA personal income..."):
        PI = load_personal_income()
    mo.md(f"BEA personal income loaded: {PI.shape[0]} states, years {PI.columns.min()}–{PI.columns.max()}")
    return (PI,)


@app.cell
def _(EDITIONS, FIXTURES, LATEST_FY, PI, mo, pd, safe_burden):
    def _():
        results, errors, rows = {}, {}, []
        all_fy = sorted(set(EDITIONS.values()) | {LATEST_FY})
        with mo.status.spinner("Downloading Census state & local finance tables..."):
            for _fy in all_fy:
                if _fy not in PI.columns:
                    errors[_fy] = f"BEA personal income not yet available for {_fy}"
                    continue
                res, err = safe_burden(_fy, PI)
                if err:
                    errors[_fy] = err
                else:
                    results[_fy] = res[0]

        for ed, _fy in EDITIONS.items():
            if _fy not in results:
                continue
            t = results[_fy]
            diffs = []
            for st, (tot, prop, inc, sal) in FIXTURES[ed].items():
                diffs += [
                    abs(t.loc[st, "total"] - tot),
                    abs(t.loc[st, "property"] - prop),
                    abs(t.loc[st, "income"] - inc),
                    abs(t.loc[st, "sales_excise"] - sal),
                ]
            if diffs:
                rows.append({
                    "WalletHub edition": ed,
                    "Census fiscal year used": _fy,
                    "max abs. difference (pp)": max(diffs),
                    "mean abs. difference (pp)": sum(diffs) / len(diffs),
                    "states checked": len(FIXTURES[ed]),
                })
        match = pd.DataFrame(rows)
        return results, errors, match


    results, errors, match = _()
    return errors, match, results


@app.cell
def _(errors, match, mo):
    err_md = "\n".join(f"- FY{k}: `{v[:300]}`" for k, v in errors.items()) or "None"
    mo.vstack([
        mo.md(
            "## Article-year check\n"
            "The table compares downloaded-source calculations with five published "
            "state examples per edition. The article does not name its fiscal-year input; "
            "the inferred year is the one used for the full rankings below. Small residual "
            "differences can reflect source revisions and rounding."
        ),
        mo.ui.table(match.round(3), selection=None) if len(match) else mo.md("No benchmark results."),
        mo.md(f"**Download / parse errors:**\n\n{err_md}"),
    ])
    return


@app.cell
def _(EDITIONS, LATEST_FY, mo, results):
    ranking_sections = []
    output_years = list(EDITIONS.items()) + [("Latest downloaded Census data", LATEST_FY)]
    for edition, fy in output_years:
        if fy not in results:
            continue
        table = results[fy].copy()
        table.index.name = "State"
        table = table.reset_index()
        columns = [
            "State", "rank_total", "total", "rank_property", "property",
            "rank_income", "income", "rank_sales_excise", "sales_excise",
        ]
        table = table[columns].rename(columns={
            "rank_total": "Overall rank",
            "total": "Overall burden (%)",
            "rank_property": "Property rank",
            "property": "Property (%)",
            "rank_income": "Income rank",
            "income": "Individual income (%)",
            "rank_sales_excise": "Sales & excise rank",
            "sales_excise": "Sales & excise (%)",
        }).round(2)
        title = (
            f"### {edition} — computed from Census fiscal year {fy}"
            if edition.startswith("WalletHub")
            else f"### {edition} — fiscal year {fy} (latest downloaded Census data)"
        )
        ranking_sections.extend([
            mo.md(title),
            mo.ui.table(table, selection=None, page_size=50),
        ])
    mo.vstack([
        mo.md(
            "## Recomputed rankings\n"
            "Rank 1 is the highest burden. Each article-year table is shown separately; "
            "the latest official Census year is a third, updated calculation."
        ),
        *ranking_sections,
    ])
    return


@app.cell
def _(LATEST_FY, mo, results):
    import matplotlib.pyplot as plt
    mo.stop(LATEST_FY not in results)
    t = results[LATEST_FY].sort_values("total")
    fig, ax = plt.subplots(figsize=(7, 10))
    ax.barh(t.index, t["property"], label="Property")
    ax.barh(t.index, t["income"], left=t["property"], label="Income")
    ax.barh(t.index, t["sales_excise"], left=t["property"] + t["income"], label="Sales & excise")
    ax.set_xlabel("% of personal income")
    ax.set_title(f"Tax burden by state, latest Census FY{LATEST_FY}")
    ax.legend(); fig.tight_layout()
    fig
    return


if __name__ == "__main__":
    app.run()
