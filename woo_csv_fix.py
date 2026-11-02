#!/usr/bin/env python3
"""WooCsvFix engine: pre-flight check + fix + re-check for WooCommerce
product CSV files (the native WooCommerce importer format).

WooCommerce's built-in importer silently skips or mangles bad rows. This
tool catches the problems BEFORE import: formatting errors are auto-fixed,
decisions a human must make are listed as blocking issues, and the fixed
file is re-parsed to prove zero auto-fixable problems remain.

Deterministic, 100% local, pure standard library.

Usage:
    python woo_csv_fix.py products.csv out/
Outputs (in out/):
    products_fixed.csv  - the same rows, format-fixed, order preserved
    woocsvfix_report.md - fixes applied, blocking issues, re-check verdict
"""
import csv
import os
import re
import sys
from decimal import Decimal, InvalidOperation

VALID_TYPES = {"simple", "variable", "variation", "grouped", "external"}
PRICE_COLS = ["Regular price", "Sale price"]


def _dec(s):
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def fix_csv(src_path, outdir):
    with open(src_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)

    fixes = []      # (row_no, message) automatic format fixes applied
    blocking = []   # (row_no, message) human decisions required

    def col(name):
        return name if name in fields else None

    sku_col = col("SKU")
    type_col = col("Type")
    name_col = col("Name")
    parent_col = col("Parent")
    stock_col = col("Stock")
    instock_col = col("In stock?")
    published_col = col("Published")
    images_col = col("Images")

    skus = {}
    for i, row in enumerate(rows):
        rn = i + 2  # 1-based line number incl. header
        # whitespace trim everywhere
        for k in list(row.keys()):
            if row[k] is not None and row[k] != row[k].strip():
                row[k] = row[k].strip()
                fixes.append((rn, f"trimmed whitespace in {k}"))

        if type_col and row.get(type_col):
            raw = row[type_col]
            if raw.lower() in VALID_TYPES and raw != raw.lower():
                row[type_col] = raw.lower()
                fixes.append((rn, f"Type {raw!r} normalized to {raw.lower()!r}"))
            elif raw.lower() not in VALID_TYPES:
                blocking.append((rn, f"unknown Type {raw!r} — importer will treat "
                                      "this row unpredictably"))
        if published_col and row.get(published_col):
            raw = row[published_col]
            low = raw.lower()
            mapped = {"1": "1", "0": "0", "-1": "-1", "yes": "1", "true": "1",
                      "no": "0", "false": "0", "draft": "-1"}.get(low)
            if mapped is None:
                blocking.append((rn, f"Published value {raw!r} not understood "
                                      "(use 1, 0 or -1)"))
            elif mapped != raw:
                row[published_col] = mapped
                fixes.append((rn, f"Published {raw!r} normalized to {mapped!r}"))
        if instock_col and row.get(instock_col):
            raw = row[instock_col]
            low = raw.lower()
            mapped = {"1": "1", "0": "0", "yes": "1", "true": "1",
                      "instock": "1", "outofstock": "0", "no": "0", "false": "0"}.get(low)
            if mapped is None:
                blocking.append((rn, f"In stock? value {raw!r} not understood"))
            elif mapped != raw:
                row[instock_col] = mapped
                fixes.append((rn, f"In stock? {raw!r} normalized to {mapped!r}"))

        for pc in PRICE_COLS:
            if col(pc) and row.get(pc):
                raw = row[pc]
                cleaned = raw.replace("$", "").replace("€", "").replace("£", "") \
                             .replace(",", "").strip()
                if cleaned != raw and _dec(cleaned) is not None:
                    row[pc] = cleaned
                    fixes.append((rn, f"{pc} {raw!r} cleaned to {cleaned!r}"))
                elif _dec(cleaned) is None:
                    blocking.append((rn, f"{pc} {raw!r} is not a number — the "
                                          "importer will import it as no price"))
        reg = _dec(row.get("Regular price", "") or "")
        sale = _dec(row.get("Sale price", "") or "")
        if reg is not None and sale is not None and sale > reg:
            blocking.append((rn, f"Sale price {sale} is higher than Regular price "
                                  f"{reg} — the product will not show as on sale"))

        if stock_col and row.get(stock_col):
            raw = row[stock_col]
            if not re.fullmatch(r"-?\d+", raw):
                blocking.append((rn, f"Stock {raw!r} is not a whole number"))
        if name_col is not None and not row.get(name_col):
            blocking.append((rn, "Name is empty — the importer creates a nameless "
                                  "product or skips the row"))
        if sku_col is not None:
            sku = row.get(sku_col, "")
            if sku:
                if sku in skus:
                    blocking.append((rn, f"SKU {sku!r} duplicates line {skus[sku]} — "
                                          "the importer UPDATES the earlier product "
                                          "instead of creating a new one"))
                else:
                    skus[sku] = rn
        if images_col and row.get(images_col):
            for url in row[images_col].split(","):
                u = url.strip()
                if u and not (u.startswith("http://") or u.startswith("https://")):
                    blocking.append((rn, f"image {u!r} is not a URL — local paths "
                                          "cannot be imported"))
                    break

    # orphan variations: Parent must reference an existing SKU
    if parent_col and type_col:
        for i, row in enumerate(rows):
            rn = i + 2
            if (row.get(type_col) == "variation") and row.get(parent_col):
                p = row[parent_col]
                if p not in skus:
                    blocking.append((rn, f"variation's Parent SKU {p!r} does not "
                                          "exist in this file — it will be orphaned"))

    os.makedirs(outdir, exist_ok=True)
    fixed_path = os.path.join(outdir, "products_fixed.csv")
    with open(fixed_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)

    recheck = recheck_csv(fixed_path, len(rows))

    report_path = os.path.join(outdir, "woocsvfix_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# WooCsvFix report — {os.path.basename(src_path)}\n\n")
        f.write(f"- Product rows: {len(rows)} (all preserved, order unchanged)\n")
        f.write(f"- Automatic format fixes applied: {len(fixes)}\n")
        f.write(f"- Blocking issues needing your decision: {len(blocking)}\n")
        f.write("\n## Fixes applied\n")
        for rn, msg in fixes:
            f.write(f"- line {rn}: {msg}\n")
        f.write("\n## Blocking issues\n")
        for rn, msg in blocking:
            f.write(f"- line {rn}: {msg}\n")
        f.write("\n## Re-check of the fixed file\n")
        f.write(f"- Rows re-parsed: {recheck['rows']}\n")
        f.write(f"- Auto-fixable problems remaining: {recheck['fixable_left']}\n")
        f.write(f"- Verdict: {'PASS' if recheck['ok'] else 'FAIL'}\n")

    return {
        "rows": len(rows), "fixes": fixes, "blocking": blocking,
        "fixed_path": fixed_path, "report_path": report_path,
        "recheck_ok": recheck["ok"], "recheck_fixable_left": recheck["fixable_left"],
    }


def recheck_csv(path, expect_rows):
    """Re-run ONLY the auto-fixable rules on the fixed file: they must all
    be at zero, and the row count must be conserved."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    fixable = 0
    for row in rows:
        for k, v in row.items():
            if v is not None and v != v.strip():
                fixable += 1
        if "Type" in fields and row.get("Type") and \
                row["Type"].lower() in VALID_TYPES and row["Type"] != row["Type"].lower():
            fixable += 1
        for pc in PRICE_COLS:
            if pc in fields and row.get(pc):
                raw = row[pc]
                if any(c in raw for c in "$€£,") and _dec(raw.replace("$", "").replace("€", "")
                                                          .replace("£", "").replace(",", "")) is not None:
                    fixable += 1
        for c, allowed in (("Published", {"1", "0", "-1"}), ("In stock?", {"1", "0"})):
            if c in fields and row.get(c) and row[c] not in allowed and \
                    row[c].lower() in {"yes", "no", "true", "false", "draft", "instock", "outofstock"}:
                fixable += 1
    return {"rows": len(rows), "fixable_left": fixable,
            "ok": len(rows) == expect_rows and fixable == 0}


def run_woocsvfix(src_path, outdir):
    return fix_csv(src_path, outdir)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    s = fix_csv(sys.argv[1], sys.argv[2])
    print(f"{s['rows']} rows, {len(s['fixes'])} fixes applied, "
          f"{len(s['blocking'])} blocking issues, re-check "
          f"{'PASS' if s['recheck_ok'] else 'FAIL'}")
    print(f"Fixed CSV: {s['fixed_path']}\nReport: {s['report_path']}")
