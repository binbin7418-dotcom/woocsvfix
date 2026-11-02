# WooCsvFix

Pre-flight check, fix and re-check for **WooCommerce product CSV** files — before the built-in importer silently skips, mangles or mis-files your products.

## Why

WooCommerce's native importer is unforgiving and quiet about it: a duplicated SKU doesn't create a product, it *updates the earlier one*. A variation whose parent SKU is missing gets orphaned. A price written `$1,299.00` imports as no price. Import plugin suites charge $59–$229/yr for the privilege of finding out afterwards. WooCsvFix checks the file first: format errors are fixed automatically, decisions are listed as blocking issues with line numbers, and the fixed file is re-parsed to prove zero fixable problems remain.

## Use

**App (Windows):** launch `WooCsvFix.exe`, pick your product CSV, click **Check, fix & re-check**. Output lands in a `woocsvfix_out` folder next to the CSV:

- `products_fixed.csv` — every row preserved, in order, format-fixed
- `woocsvfix_report.md` — fixes applied, blocking issues by line number, re-check verdict

**Command line:** `python woo_csv_fix.py products.csv out/`

## Auto-fixed (format only)

Currency symbols and thousands commas in prices · mixed-case product Types · `Published` values (`yes`/`draft`/…) normalized to 1/0/-1 · `In stock?` values normalized to 1/0 · stray whitespace trimmed.

## Blocking issues (your decision, never silently "fixed")

Duplicate SKUs · variations whose Parent SKU doesn't exist in the file · sale price higher than regular price · images that aren't URLs (local paths can't import) · empty product names · non-numeric stock · unparseable prices.

## Verified

Seeded acceptance test (15/15 PASS, `test/acceptance_results.txt`): a 9-product CSV with 10 planted defects produced exactly 5 automatic fixes and exactly 5 blocking issues, all 9 rows conserved, re-check at zero fixable problems.

## Scope

WooCsvFix works on the CSV file only — it never connects to your store, never imports anything, and never drops or merges rows. 100% local: no upload, no account.

## Build from source

`pip install pyinstaller`, then `pyinstaller woocsvfix.spec` — pure standard library. Or push to GitHub and let the included Actions workflow build the Windows package.
