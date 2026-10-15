# /// script
# requires-python = ">=3.10"
# dependencies = ["marimo", "pandas", "numpy", "requests", "openpyxl", "xlrd", "matplotlib"]
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import io, re, zipfile, pathlib
    import marimo as mo
    import numpy as np
    import pandas as pd
    import requests

    return io, mo, pathlib, pd, re, requests, zipfile


@app.cell
def _(mo):
    mo.md(r"""
    # Reproducing WalletHub's "Tax Burden by State" from primary data

    **Method (per WalletHub):** burden = (property tax, individual income tax, or
    sales and excise tax) / total state personal income. Total = sum of the three.
    Rank 1 = highest burden.

    **Primary sources downloaded by this notebook (no WalletHub numbers are used as inputs):**
    - U.S. Census Bureau, Annual Survey of State and Local Government Finances (state + local combined taxes)
    - U.S. BEA, SAINC1 state annual personal income

    WalletHub's published values appear only in `FIXTURES`, used solely to *validate*
    which fiscal year reproduces each article.
    """)
    return


@app.cell
def _(pathlib):
    CACHE = pathlib.Path("data_cache")
    CACHE.mkdir(exist_ok=True)
    HEADERS = {"User-Agent": "Mozilla/5.0 (research notebook; contact: local user)"}

    # Fiscal years to test against each WalletHub article (the vintage is not
    # stated on WalletHub's page, so the notebook finds the best match).
    EDITIONS = {
        "WalletHub 2025 article (data collected 2024-03-12)": [2020, 2021, 2022],
        "WalletHub 2026 article": [2021, 2022, 2023, 2024],
    }
    LATEST_FY = 2024  # Census released FY2024 in July 2026; falls back automatically.

    # (total, property, income, sales_excise) in %, transcribed from the articles
    # solely as validation targets.
    FIXTURES = {
        "WalletHub 2025 article (data collected 2024-03-12)": {
            "New York": (12.02, 4.36, 4.63, 3.03), "Hawaii": (11.80, 2.64, 3.82, 5.34),
            "Washington": (8.04, 2.58, 0.00, 5.46), "Alabama": (7.52, 1.33, 2.01, 4.18),
            "Alaska": (4.93, 3.54, 0.00, 1.39),
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
def _(STATES, fetch_first, pd):
    def census_urls(fy):
        yy = str(fy)[-2:]
        base = f"https://www2.census.gov/programs-surveys/gov-finances/tables/{fy}/"
        return [base + f"{yy}slsstab1.xlsx", base + f"{yy}slsstab1.xls"]

    def load_census_taxes(fy):
        """State+local combined tax revenue ($) from ALFIN Table 1 for fiscal year fy."""
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
            out[f"rank_{c}"] = out[c].round(2).rank(ascending=False, method="min").astype(int)
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
def _():
    return


@app.cell
def _():
    return


@app.cell
def _(EDITIONS, FIXTURES, LATEST_FY, PI, mo, pd, safe_burden):
    def _():
        results, errors, rows = {}, {}, []
        all_fy = sorted({fy for v in EDITIONS.values() for fy in v} | {LATEST_FY})
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

        for ed, fys in EDITIONS.items():
            for _fy in fys:
                if _fy not in results:
                    continue
                t = results[_fy]
                diffs = []
                for st, (tot, prop, inc, sal) in FIXTURES[ed].items():
                    diffs += [abs(t.loc[st, "total"] - tot), abs(t.loc[st, "property"] - prop),
                              abs(t.loc[st, "income"] - inc), abs(t.loc[st, "sales_excise"] - sal)]
                if diffs:
                    rows.append({"edition": ed, "census_FY": _fy,
                                 "max_abs_diff_pp": max(diffs), "mean_abs_diff_pp": sum(diffs) / len(diffs)})
        match = pd.DataFrame(rows)
        best = (match.sort_values("mean_abs_diff_pp").groupby("edition").head(1)
                if len(match) else match)
        return results, errors, match, best


    results, errors, match, best = _()
    return best, errors, match, results


@app.cell
def _(best, errors, match, mo):
    err_md = "\n".join(f"- FY{k}: `{v[:300]}`" for k, v in errors.items()) or "None"
    mo.md("## Step 1 – Which fiscal year reproduces each WalletHub article?")
    mo.vstack([
        mo.md("## Step 1 – Which fiscal year reproduces each WalletHub article?\n"
              "Differences are in percentage points of personal income, vs. five spot-check states."),
        mo.ui.table(match.round(3), selection=None) if len(match) else mo.md("No results."),
        mo.md("**Best match per article:**"),
        mo.ui.table(best.round(3), selection=None) if len(best) else mo.md("n/a"),
        mo.md(f"**Download / parse errors:**\n\n{err_md}"),
    ])
    return


@app.cell
def _(EDITIONS, best, mo, results):
    chosen = {}
    for ed in EDITIONS:
        sub = best[best["edition"] == ed] if len(best) else []
        if len(sub):
            chosen[ed] = int(sub["census_FY"].iloc[0])
    latest_fy = max(results) if results else None
    options = {f"{ed} → Census FY{fy}": ed for ed, fy in chosen.items()}
    if latest_fy:
        options[f"Latest available → Census FY{latest_fy}"] = "latest"
    pick = mo.ui.dropdown(options=options, value=next(iter(options), None), label="View")
    return chosen, latest_fy, pick


@app.cell
def _(chosen, latest_fy, mo, pick, results):
    sel = pick.value
    fy_sel = latest_fy if sel == "latest" else chosen.get(sel)
    tbl = results[fy_sel].round(2) if fy_sel in results else None
    mo.vstack([
        mo.md("## Step 2 – Recomputed rankings"), pick,
        mo.ui.table(tbl, selection=None, page_size=50) if tbl is not None else mo.md("n/a"),
    ])
    return (sel,)


@app.cell
def _(chosen, latest_fy, mo, pd, results):
    mo.stop(not chosen or latest_fy is None)
    _ed = next((ed for ed, fy in chosen.items() if fy != latest_fy), list(chosen)[0])
    fy_start = chosen[_ed]
    old, new = results[fy_start], results[latest_fy]
    if fy_start == latest_fy:
        _output = mo.md("No multi-year comparison available.")
    else:
        cmp = pd.DataFrame({
            f"total FY{fy_start}": old["total"], f"total FY{latest_fy}": new["total"],
            f"rank FY{fy_start}": old["rank_total"], f"rank FY{latest_fy}": new["rank_total"],
        })
        cmp["rank_change"] = cmp.iloc[:, 2] - cmp.iloc[:, 3]
        cmp["pp_change"] = cmp.iloc[:, 1] - cmp.iloc[:, 0]
        wa = cmp.loc[["Washington"]].round(2)
        _output = mo.vstack([
            mo.md(f"## Step 3 – Washington and biggest movers (FY{fy_start} → FY{latest_fy})"),
            mo.ui.table(wa, selection=None),
            mo.ui.table(cmp.sort_values("rank_change", key=abs, ascending=False).head(10).round(2), selection=None),
        ])
    _output
    return


@app.cell
def _(chosen, latest_fy, mo, results, sel):
    import matplotlib.pyplot as plt
    _fy = latest_fy if sel == "latest" else chosen.get(sel)
    mo.stop(_fy not in results)
    t = results[_fy].sort_values("total")
    fig, ax = plt.subplots(figsize=(7, 10))
    ax.barh(t.index, t["property"], label="Property")
    ax.barh(t.index, t["income"], left=t["property"], label="Income")
    ax.barh(t.index, t["sales_excise"], left=t["property"] + t["income"], label="Sales & excise")
    ax.set_xlabel("% of personal income"); ax.set_title(f"Tax burden by state, Census FY{_fy}")
    ax.legend(); fig.tight_layout()
    fig
    return


if __name__ == "__main__":
    app.run()
