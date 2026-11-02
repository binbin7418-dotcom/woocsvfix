#!/usr/bin/env python3
"""WooCsvFix acceptance test: seeded WooCommerce product CSV.

Planted defects:
  format fixes expected: (1) price with $ and comma, (2) Type in mixed case,
  (3) Published 'yes', (4) In stock? 'yes', (5) whitespace-padded name
  blocking expected: (6) duplicate SKU, (7) orphan variation (Parent SKU
  missing), (8) Sale price above Regular price, (9) local-path image,
  (10) empty Name
Asserts exact fix/blocking counts, conservation and the re-check verdict.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from woo_csv_fix import fix_csv

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

HEADER = ["ID", "Type", "SKU", "Name", "Published", "Regular price", "Sale price",
          "Categories", "Images", "In stock?", "Stock", "Parent"]
ROWS = [
    ["1", "simple", "MUG-001", "  Stoneware Mug  ", "1", "19.99", "", "Kitchen",
     "https://example.com/mug.jpg", "1", "40", ""],
    ["2", "Simple", "TEE-001", "Logo Tee", "yes", "$1,299.00", "", "Apparel",
     "https://example.com/tee.jpg", "yes", "15", ""],
    ["3", "simple", "TEE-001", "Logo Tee (relisted)", "1", "25.00", "", "Apparel",
     "https://example.com/tee2.jpg", "1", "5", ""],
    ["4", "variable", "HOOD-001", "Hoodie", "1", "", "", "Apparel",
     "https://example.com/hood.jpg", "1", "", ""],
    ["5", "variation", "HOOD-001-M", "Hoodie - M", "1", "49.99", "", "Apparel",
     "", "1", "8", "HOOD-001"],
    ["6", "variation", "GHOST-001-M", "Ghost - M", "1", "39.99", "", "Apparel",
     "", "1", "3", "GHOST-001"],
    ["7", "simple", "SALE-001", "Backwards Sale", "1", "30.00", "45.00", "Misc",
     "https://example.com/sale.jpg", "1", "2", ""],
    ["8", "simple", "IMG-001", "Local Image Product", "1", "12.00", "", "Misc",
     "C:\\photos\\product.jpg", "1", "9", ""],
    ["9", "simple", "NONAME-001", "", "1", "12.00", "", "Misc",
     "https://example.com/x.jpg", "1", "1", ""],
]

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


def main():
    src = os.path.join(HERE, "seed_products.csv")
    with open(src, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(ROWS)

    s = fix_csv(src, OUT)
    check("rows conserved (9)", s["rows"] == 9, f"got {s['rows']}")
    fix_msgs = " | ".join(m for _, m in s["fixes"])
    blk_msgs = " | ".join(m for _, m in s["blocking"])
    check("price currency/comma cleaned", "1299.00" in fix_msgs, fix_msgs)
    check("Type case normalized", "normalized to 'simple'" in fix_msgs)
    check("Published 'yes' normalized", "Published 'yes' normalized to '1'" in fix_msgs)
    check("In stock? 'yes' normalized", "In stock? 'yes' normalized to '1'" in fix_msgs)
    check("whitespace trimmed", "trimmed whitespace in Name" in fix_msgs)
    check("exactly 5 fixes", len(s["fixes"]) == 5, f"got {len(s['fixes'])}: {fix_msgs}")
    check("duplicate SKU blocking", "duplicates line" in blk_msgs)
    check("orphan variation blocking", "does not exist in this file" in blk_msgs)
    check("sale>regular blocking", "higher than Regular price" in blk_msgs)
    check("local image blocking", "not a URL" in blk_msgs)
    check("empty Name blocking", "Name is empty" in blk_msgs)
    check("exactly 5 blocking issues", len(s["blocking"]) == 5, f"got {len(s['blocking'])}: {blk_msgs}")
    check("re-check PASS", s["recheck_ok"] and s["recheck_fixable_left"] == 0)
    with open(s["fixed_path"]) as f:
        fixed = f.read()
    check("fixed CSV keeps all rows + fixed values",
          "1299.00" in fixed and "Stoneware Mug" in fixed and "GHOST-001" in fixed)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
