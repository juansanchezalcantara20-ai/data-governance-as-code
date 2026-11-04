"""Seeded synthetic data generator for a fictional field-services company.

Everything produced here is invented: sites, manufacturers, customers and people.
Names are deliberately implausible and emails use the reserved ``example.org`` domain.

Output: one CSV per source system in ``data/sources/`` plus ``_manifest.json`` with the
seed and the as-of date. With the same seed and as-of date the output is byte-identical.

The data contains **known, deliberately injected defects** so that the governance
controls have something to catch. They are listed in ``INJECTED_DEFECTS`` and in the
README; quality findings are an illustration of the method, not real results.
"""

from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

from .paths import sources_dir

DEFAULT_SEED = 42
DEFAULT_AS_OF = date(2026, 10, 31)

FIRST = ["Avery", "Blake", "Cameron", "Dakota", "Emery", "Finley", "Harper", "Jules", "Kendall", "Logan",
         "Marlowe", "Noel", "Oakley", "Parker", "Reese", "Sawyer", "Tatum", "Vesper", "Wren", "Zion"]
LAST = ["Fictus", "Sampleton", "Mockridge", "Placeholt", "Dummington", "Testwell", "Notreal", "Exemplar",
        "Fakenham", "Stubbs", "Proxima", "Lorem", "Ipsumson", "Synthwood", "Madeupova", "Invento"]
SITES = ["Site North", "Site South", "Site East", "Site West", "Site Central"]
ASSET_TYPES = ["Haul truck", "Wheel loader", "Drill rig", "Pump station", "Generator set"]
MANUFACTURERS = ["OEM Alpha", "OEM Bravo", "OEM Charlie", "OEM Delta"]
SERVICE_TYPES = ["Preventive maintenance", "Corrective maintenance", "Installation", "Inspection"]
TRADES = ["Mechanic", "Electrician", "Instrument technician", "Welder", "Supervisor"]
SEGMENTS = ["Mining", "Energy", "Construction", "Agriculture"]
COUNTRIES = ["Peru", "Chile", "Colombia", "Mexico"]
MATERIALS = [
    ("Oil filter", "Filters", 85.0), ("Air filter", "Filters", 64.0), ("Hydraulic hose", "Hydraulics", 420.0),
    ("Seal kit", "Hydraulics", 150.0), ("Proximity sensor", "Electrical", 610.0), ("Signal cable 10 m", "Electrical", 35.0),
    ("Battery 12 V", "Electrical", 540.0), ("Bearing", "Mechanical", 290.0), ("V-belt", "Mechanical", 48.0),
    ("Grease EP2 (kg)", "Lubricants", 22.0), ("Engine oil 15W40 (l)", "Lubricants", 18.0), ("Brake pad set", "Mechanical", 380.0),
]

INJECTED_DEFECTS = [
    ("service_orders", "6 orders without asset", "completeness"),
    ("service_orders", "4 orders closed before they were opened", "consistency"),
    ("service_orders", "1 impossible date (31/02)", "validity"),
    ("service_orders", "1 negative price", "validity"),
    ("service_orders", "5 exact duplicate rows", "uniqueness"),
    ("service_orders", "~10% of dates in dd/mm/yyyy, ~8% of statuses with stray case/spaces", "validity"),
    ("labor_entries", "5 entries with negative or > 24 hours", "validity"),
    ("labor_entries", "4 entries pointing to non-existent orders", "consistency"),
    ("labor_entries", "approver_email column holds personal data and is not declared as PII", "privacy"),
    ("material_issues", "3 negative unit costs", "validity"),
    ("material_issues", "4 unit costs off by a decimal shift (x10) versus the material master", "accuracy"),
    ("technicians", "1 national id with 7 digits, 1 malformed email", "validity"),
    ("customers", "8 malformed contact emails", "validity"),
    ("materials", "2 materials below reorder point", "business signal"),
]


def _write(path: Path, header: list[str], rows: list[list]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    return len(rows)


def _person(rnd: random.Random) -> tuple[str, str, str, str, str]:
    first, last = rnd.choice(FIRST), rnd.choice(LAST)
    national_id = f"{rnd.randint(10_000_000, 79_999_999)}"
    email = f"{first[0].lower()}.{last.lower()}{rnd.randint(1, 99)}@example.org"
    phone = f"9{rnd.randint(10_000_000, 99_999_999)}"
    return first, last, national_id, email, phone


def _fmt(d: date, rnd: random.Random, alt_share: float) -> str:
    return d.strftime("%d/%m/%Y") if rnd.random() < alt_share else d.isoformat()


def generate(seed: int = DEFAULT_SEED, as_of: date = DEFAULT_AS_OF, out: Path | None = None) -> dict[str, int]:
    out = out or sources_dir()
    rnd = random.Random(seed)
    counts: dict[str, int] = {}

    assets = [[f"AS-{i:04d}", rnd.choice(ASSET_TYPES), rnd.choice(MANUFACTURERS), rnd.choice(SITES),
               rnd.randint(500, 40_000), (as_of - timedelta(days=rnd.randint(200, 3000))).isoformat()]
              for i in range(1, 61)]
    counts["assets"] = _write(out / "assets.csv", ["asset_id", "asset_type", "manufacturer", "site",
                                                   "operating_hours", "commissioned_on"], assets)

    technicians = []
    for i in range(1, 46):
        first, last, nid, email, phone = _person(rnd)
        trade = rnd.choice(TRADES)
        cost = round(rnd.uniform(28, 45) * (1.4 if trade == "Supervisor" else 1), 2)
        technicians.append([f"TE-{i:03d}", nid, first, last, email, phone, trade, cost])
    technicians[7][1] = technicians[7][1][:7]
    technicians[12][4] = "not-an-email"
    counts["technicians"] = _write(out / "technicians.csv", ["technician_id", "national_id", "first_name",
                                                             "last_name", "email", "phone", "trade",
                                                             "hourly_cost"], technicians)

    customers = []
    for i in range(1, 121):
        first, last, _, email, phone = _person(rnd)
        company = f"{rnd.choice(LAST)} {rnd.choice(['Holdings', 'Works', 'Group', 'Industries', 'Partners'])} {i}"
        customers.append([f"CU-{i:04d}", company, rnd.choice(SEGMENTS), rnd.choice(COUNTRIES), f"{first} {last}",
                          email, phone, (as_of - timedelta(days=rnd.randint(60, 1500))).isoformat(),
                          rnd.choice(["Y", "N", "Y", "yes", "no"])])
    for i in rnd.sample(range(len(customers)), 8):
        customers[i][5] = customers[i][5].replace("@", "")
    counts["customers"] = _write(out / "customers.csv", ["customer_id", "company_name", "segment", "country",
                                                         "contact_name", "contact_email", "contact_phone",
                                                         "created_on", "marketing_consent"], customers)

    materials = []
    for i, (desc, category, cost) in enumerate(MATERIALS, 1):
        reorder = rnd.randint(10, 60)
        stock = rnd.randint(reorder, reorder * 4)
        materials.append([f"MA-{i:04d}", desc, category, cost, stock, reorder, rnd.randint(3, 45)])
    materials[2][4] = materials[2][5] - 4
    materials[6][4] = 0
    counts["materials"] = _write(out / "materials.csv", ["material_id", "description", "category", "unit_cost",
                                                         "stock_on_hand", "reorder_point", "lead_time_days"],
                                 materials)

    orders = []
    for i in range(1, 401):
        opened = as_of - timedelta(days=rnd.randint(0, 180))
        status = rnd.choices(["Closed", "Open", "Cancelled"], [70, 25, 5])[0]
        closed = min(opened + timedelta(days=rnd.randint(1, 20)), as_of) if status == "Closed" else None
        hours = rnd.randint(8, 160)
        labor = round(hours * rnd.uniform(30, 42), 2)
        material = round(rnd.uniform(200, 9000), 2)
        price = round((labor + material) * rnd.uniform(1.15, 1.45), 2)
        status_txt = status if rnd.random() > 0.08 else f" {status.lower()} "
        orders.append([f"SO-{i:06d}", rnd.choice(customers)[0], rnd.choice(assets)[0], rnd.choice(SERVICE_TYPES),
                       _fmt(opened, rnd, 0.1), _fmt(closed, rnd, 0.1) if closed else "", status_txt, hours,
                       labor, material, price])
    for i in rnd.sample(range(len(orders)), 6):
        orders[i][2] = ""
    iso_closed = [k for k, o in enumerate(orders) if o[5] and "-" in o[4] and "-" in o[5]]
    for i in rnd.sample(iso_closed, 4):
        orders[i][5] = (date.fromisoformat(orders[i][4]) - timedelta(days=3)).isoformat()
    orders[20][4] = "31/02/2026"
    orders[33][10] = "-1500"
    orders += [list(orders[k]) for k in rnd.sample(range(len(orders)), 5)]
    counts["service_orders"] = _write(out / "service_orders.csv", [
        "order_id", "customer_id", "asset_id", "service_type", "opened_on", "closed_on", "status",
        "planned_hours", "planned_labor_cost", "planned_material_cost", "price"], orders)

    labor_rows, k = [], 1
    for order in orders[:400]:
        if order[6].strip().lower() == "cancelled":
            continue
        try:
            start = date.fromisoformat(order[4])
        except ValueError:
            start = as_of - timedelta(days=30)
        approver = _person(rnd)[3]
        for _ in range(rnd.randint(1, 6)):
            tech = rnd.choice(technicians)
            work = min(start + timedelta(days=rnd.randint(0, 5)), as_of)
            labor_rows.append([f"LE-{k:06d}", order[0], tech[0], work.isoformat(),
                               round(rnd.choice([4, 6, 8, 8, 10, 12]) * rnd.uniform(0.9, 1.0), 1), approver])
            k += 1
    for i in rnd.sample(range(len(labor_rows)), 5):
        labor_rows[i][4] = rnd.choice([-8, 26, 30])
    for i in rnd.sample(range(len(labor_rows)), 4):
        labor_rows[i][1] = f"SO-{rnd.randint(900_000, 999_999)}"
    counts["labor_entries"] = _write(out / "labor_entries.csv", ["entry_id", "order_id", "technician_id",
                                                                 "work_date", "hours", "approver_email"],
                                     labor_rows)

    issues, k = [], 1
    for order in orders[:400]:
        try:
            start = date.fromisoformat(order[4])
        except ValueError:
            start = as_of - timedelta(days=30)
        for _ in range(rnd.randint(0, 4)):
            mat = rnd.choice(materials)
            issues.append([f"MI-{k:06d}", order[0], mat[0], rnd.randint(1, 12),
                           round(mat[3] * rnd.uniform(0.95, 1.08), 2),
                           min(start + timedelta(days=rnd.randint(0, 3)), as_of).isoformat()])
            k += 1
    for i in rnd.sample(range(len(issues)), 3):
        issues[i][4] = -abs(float(issues[i][4]))
    for i in rnd.sample(range(len(issues)), 4):
        issues[i][4] = round(float(issues[i][4]) * 10, 2)
    counts["material_issues"] = _write(out / "material_issues.csv", ["issue_id", "order_id", "material_id",
                                                                     "quantity", "unit_cost", "issued_on"], issues)

    manifest = {"seed": seed, "as_of": as_of.isoformat(), "files": counts,
                "injected_defects": [{"source": s, "defect": d, "dimension": m} for s, d, m in INJECTED_DEFECTS]}
    (out / "_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return counts


def as_of_date() -> date:
    manifest = sources_dir() / "_manifest.json"
    if manifest.exists():
        return date.fromisoformat(json.loads(manifest.read_text(encoding="utf-8"))["as_of"])
    return DEFAULT_AS_OF
