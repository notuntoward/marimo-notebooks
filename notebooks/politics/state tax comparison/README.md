# WalletHub state tax burden replication

This note accompanies the [marimo notebook](wallethub_tax_burden_replication.py). It
explains the article-year notation, source choices, and how to run the Census API years.

## WalletHub edition and Census fiscal year

These are two different years. The WalletHub edition is the year named in its article;
the Census fiscal year identifies the source observations used in that calculation.

| WalletHub article edition | Census fiscal year used |
| --- | --- |
| 2024 | FY2021 |
| 2025 | FY2022 |
| 2026 | FY2023 |
| Latest available Census data | FY2024 |

The historical article years are informed mappings, not confirmed WalletHub input
vintages. WalletHub does not name the source fiscal year or publish an edition-frozen
calculation file. The assignments are supported by source-release timing and by
comparing the notebook's downloaded-data results with all 50 states in each published
article table.

## Requested Census FY2025 analysis

The WalletHub **2025 article edition** maps to Census FY2022; that article year is not
the same thing as **Census fiscal year 2025**. Census's [current State and Local
Government Finances data/API page](https://www.census.gov/data/developers/data-sets/govslocalfin.html)
documents coverage through FY2024, and the [FY2024 data release](https://www.census.gov/data/datasets/2024/econ/local/public-use-datasets.html)
was published in July 2026. Census has not published FY2025 government-finance
observations yet.

Because the Census tax-revenue numerator for FY2025 is not available, the notebook
cannot honestly compute 2025 tax-to-income percentages or rankings. It includes FY2025
in the requested-year output and explicitly reports it as unavailable; it does not
substitute a BEA-only denominator or relabel another Census year as 2025. FY2024 remains
the latest calculation until Census releases FY2025 data.

The release dates make FY2022 a reasonable match for the 2025 article: Census released
the 2022 finance data on [October 31, 2024](https://www.census.gov/newsroom/press-releases/2024/census-of-governments.html),
before WalletHub's April 1, 2025 report. Census published its FY2023 data in
[July 2025](https://www.census.gov/data/datasets/2023/econ/local/public-use-datasets.html),
after that article. The 2024 article predates the FY2022 release, and the 2026 article
predates FY2024 data, released in July 2026.

## Sources and calculation

- **Tax receipts:** U.S. Census Bureau state-and-local government finance data. The
  notebook downloads the official summary workbooks for FY2021 and FY2022 and uses
  the Census API for FY2023 and FY2024.
- **Personal income:** U.S. Bureau of Economic Analysis (BEA), Regional table SAINC1,
  LineCode 1 (“Personal income”), in current dollars.
- **Categories:** Census property tax; individual income tax (excluding corporate
  income tax); and general sales plus selective sales taxes. This follows the
  [Tax Policy Center's series definitions](https://state-local-finance-data.taxpolicycenter.org/help/revenue.html),
  which correspond to WalletHub's described tax categories. For FY2023–FY2024 the notebook
  selects Census aggregate codes LF0009 (property), LF0023 (individual income), LF0011
  (general sales), and LF0012 (total selective sales), avoiding ambiguous substring
  matches such as “Sale of Property.” The API omits some state/category rows with no
  reported receipts; those absent combinations are represented as $0. Duplicate rows
  and blank amounts are still treated as errors.
- **WalletHub article values:** the complete 50-state rankings are downloaded from the
  archived article reproductions for [2024](https://www.cpapracticeadvisor.com/2024/12/01/how-the-50-states-rank-by-tax-burden/103495/),
  [2025](https://www.cpapracticeadvisor.com/2025/04/01/how-the-50-states-rank-by-tax-burden-updated-for-2025/158094/),
  and [2026](https://www.cpapracticeadvisor.com/2026/03/31/2026-update-how-the-50-states-rank-by-tax-burden/180445/).
  They are comparison values only; they are never inputs to the Census/BEA calculation.

For each state, the calculation divides each of four combined state-and-local
tax-type revenues by state personal income, then sums the four shares. General-sales
and selective-sales shares are also added together to reproduce WalletHub's single
sales/excise category. The raw Census and BEA values are downloaded and used in the
calculations. The article values are downloaded separately so their complete
published rankings can be compared against the independent calculations.

### Official definitions

The Census Bureau defines taxes for its government-finance statistics as compulsory
contributions exacted by a government for public purposes, excluding special
assessments for capital improvements and contributions to retirement or social
insurance systems. The tax-type definitions below are concise summaries of Census
categories; the linked manual is the official source. `T` codes are Census tax
classification codes; the `LF` codes in the source table are separate Census API
aggregate IDs ([API variable definitions](https://api.census.gov/data/timeseries/govslocalfin/variables/AGG_DESC_LABEL.html)).

- **Property tax (T01):** tax on ownership of property, measured by its value. Census
  includes both real and personal property. [Census Tax Revenue Classification
  Manual, p. 4-9](https://www2.census.gov/programs-surveys/stc/technical-documentation/questionnaires/Tax-Revenue-Classification-Manual.pdf#page=1).
- **Individual income tax (T40):** tax on individuals measured by net income, plus
  taxes on certain types of individual income such as interest and dividends. This
  is distinct from corporate net-income tax. [Census Tax Revenue Classification
  Manual, p. 4-15](https://www2.census.gov/programs-surveys/stc/technical-documentation/questionnaires/Tax-Revenue-Classification-Manual.pdf#page=7).
- **General sales tax (T09):** tax applying broadly, subject to specified exceptions,
  to sales of goods and services or gross receipts; it includes sales/use taxes.
  [Census Tax Revenue Classification Manual, p. 4-10](https://www2.census.gov/programs-surveys/stc/technical-documentation/questionnaires/Tax-Revenue-Classification-Manual.pdf#page=2).
- **Selective sales tax (T10–T19):** tax on particular goods or services, or on the
  gross receipts of particular businesses, imposed separately from a general sales
  tax. Census's selective-sales total is the tax type plotted separately from general
  sales in the chart, but is combined with it for WalletHub's sales/excise result.
  [Census Tax Revenue Classification Manual, p. 4-11](https://www2.census.gov/programs-surveys/stc/technical-documentation/questionnaires/Tax-Revenue-Classification-Manual.pdf#page=3).
- **State personal income:** income received by, or on behalf of, people who live in
  the state. BEA calculates it as wage and salary disbursements and supplements,
  proprietors' and rental income, dividends, interest, and current transfer receipts,
  less contributions for government social insurance. It is assigned by recipient
  residence and reported in current dollars (not inflation-adjusted); it is not
  taxable income or a per-capita amount. [BEA glossary: State personal
  income](https://www.bea.gov/help/glossary/state-personal-income).

### Equation and source mapping

Each tax-type percentage is that tax revenue divided by the state's personal
income, multiplied by 100. In other words, the denominator is not total tax
revenue. WalletHub reports three categories: property tax, individual income
tax, and sales/excise tax. The chart at the end displays four Census tax types,
splitting sales/excise into general-sales and selective-sales revenue:

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
`GOVTYPE_LABEL=combined state and local`, and `time=Census FY`; the code checks
the returned `AGG_DESC_LABEL`. Census amounts are in thousands of dollars. The
common denominator for every tax type and year is BEA Regional `SAINC1`:
`GeoName=state`, `LineCode=1` (“Personal income”), and the year-named column,
in millions of dollars.

For FY2024 specifically, Census API `time=2024` supplies the numerator and BEA
`SAINC1` column `2024` supplies the denominator. Since Census amounts are
thousands and BEA values are millions, the tax-type equation in raw units is
`tax_type_pct = 0.1 * Census_AMOUNT_thousands / BEA_SAINC1_millions`;
for WalletHub's sales/excise category, add the general-sales and selective-sales
amounts first. The chart displays these two percentages separately; with
property and individual income, all four tax-type shares sum to the total burden.
Census FY2024 is a government fiscal year, while BEA column 2024 is a calendar
year. This is different from the **WalletHub 2024 article edition**, which the
notebook maps to Census FY2021. Tax-type and total ranks use descending values
and minimum rank for ties, so rank 1 is highest.

## Charts

The notebook first displays a state-by-year table of overall rank and total burden
(formatted `rank / burden (%)`), sorted by each state's average rank across the
available independent Census + BEA years. A second table shows the latest configured
year's rank, total burden, individual tax-type shares, and BEA personal income.

The rank-trend chart shows all calculated states as thin gray reference lines.
Choose states by name in its multiselect to highlight their tracks; the selected
states have larger points, hover tooltips, and labels at the last available year.
The initial selection is the three states with the lowest mean ranks and the three
with the highest mean ranks. Rank 1 (highest burden) is at the top. This chart uses
only the independent Census + BEA calculations, not WalletHub article ranks.

FY2024 is the latest Census fiscal year currently included in the notebook and is
calculated from Census FY2024 tax collections and BEA 2024 personal income when the
API data load succeeds. It is not a WalletHub article edition, so there is no
corresponding WalletHub article rank for FY2024. FY2023 and FY2024 require
`CENSUS_API_KEY`; if FY2024 cannot be loaded, the notebook displays the recorded
calculation error instead of implying the year is unavailable or silently dropping it.

The latest-year stacked bar chart shows property, individual income, general sales,
and selective sales separately. Every segment is the corresponding state-and-local
revenue divided by personal income, not a fraction of total taxes collected. The
four segments sum to the total burden; general and selective sales are combined only
when comparing with WalletHub's sales/excise category.

## Full state tables

The notebook displays the state-by-period comparison with WalletHub and downloaded
Census + BEA values side by side. Each row is one state and period, with overall and
tax-type percentages and ranks. The 2025 article does not publish tax-type subranks,
so those article cells remain missing rather than being inferred. The separate
rank/value tables and trend chart use one calculated state-year DataFrame; the tables
are derived from it with pivots and filters rather than separate calculations.

For programmatic use, `comparison_data` is the long-form MultiIndex DataFrame with one
row per period, state, and source. Its index is
`(period, census_fy, state, data_source)`; `data_source` distinguishes `WalletHub article`
from `Downloaded Census + BEA`. Burden percentages retain full precision in this
DataFrame; the visual table rounds them to two decimal places.

The separate `downloaded_inputs` DataFrame is indexed by `(period, census_fy, state)`
and contains the Census property, individual-income, general-sales, and selective-sales
receipts; total sales/excise receipts; and BEA personal income. Monetary columns are
numeric dollars in the DataFrame; the visual table formats them with dollar signs and
commas. Both DataFrames retain source URLs and can be exported from the notebook with
`comparison_data.reset_index().to_csv(...)` or
`downloaded_inputs.reset_index().to_csv(...)`.

This is a replication of a tax-revenue-to-personal-income ratio, not a household tax
incidence estimate. Census records revenue by the location of state and local
governments; it does not allocate business-paid taxes to households. Census data use
government fiscal years while BEA personal income is annual calendar-year data, so
the numerator and denominator periods are close but not perfectly aligned. Revisions,
aggregation choices, and the unavailable frozen WalletHub extract can also produce
small differences from published values.

## Running the notebook

FY2021 and FY2022 use downloadable Census workbooks and BEA data; they do not require
an API key. FY2023 and FY2024 use the Census API and require a free
[Census API key](https://api.census.gov/data/key_signup.html). Set the key in the same
shell that launches marimo:

```powershell
$env:CENSUS_API_KEY = "paste-your-key"
uvx marimo edit "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py"
```

```bash
export CENSUS_API_KEY="paste-your-key"
uvx marimo edit "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py"
```

If marimo is already running, restart it after setting the variable. The notebook
reads the key from the environment and does not save it; raw downloads are cached
locally in `data_cache/`.

The notebook currently uses the Census API for FY2023 and FY2024. FY2025 is shown as
unavailable until the Census source above publishes that year; adding an API key cannot
provide unpublished data.

## Readable report

The [HTML export](exports/wallethub_tax_burden_replication.html) is a browser-readable
snapshot of the notebook with its code and rendered outputs; it is not updated
automatically when the source notebook changes. Regenerate it after notebook edits
using the command below. Without `CENSUS_API_KEY`, API-key messages appear for
FY2023/FY2024; FY2025 is separately marked as not yet published.

After setting the key, regenerate the report with:

```bash
uvx marimo export html --sandbox --force \
  "notebooks/politics/state tax comparison/wallethub_tax_burden_replication.py" \
  -o "notebooks/politics/state tax comparison/exports/wallethub_tax_burden_replication.html"
```
