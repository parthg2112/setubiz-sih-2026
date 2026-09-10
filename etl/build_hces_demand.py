"""Consumption demand from the published HCES 2023-24 Fact Sheet (MoSPI).

Everything transcribed here is **real published data**, cited to its statement number:

* Statement 7  — average rural MPCE for each of the 36 States/UTs.
* Statement 4  — rural MPCE percentage share for each item group, all-India.
* Figure 1R    — average rural MPCE across the twelve fractile classes.

Two things remain modelled rather than observed, and both are labelled as such in the output:

* `addressable_share` — what fraction of a category's household spend a single village
  micro-enterprise could realistically capture. No survey measures this.
* the category -> item-group mapping, which is a judgement about which published item groups a
  given business actually sells into. Each mapping ships its component list so it can be audited.

`cv` is **not** guessed: it is the coefficient of variation of the real rural MPCE distribution,
computed from the Figure 1R fractiles.

Household size comes from Mission Antyodaya (total_population / total_hhd per state) rather than
being assumed — the microdata needed for a survey-based figure is still behind registration.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from common import (
    DATASETS,
    DEFAULT_OUT,
    meta,
    num,
    progress,
    read_csv,
    state_id_of,
    state_name,
    write_json,
)

ANTYODAYA = DATASETS / "shrug-antyodaya-csv" / "antyodaya_shrid.csv"
SOURCE_URL = (
    "https://www.mospi.gov.in/sites/default/files/publication_reports/"
    "HCES%20FactSheet%202023-24.pdf"
)

#: Statement 7 — average MPCE (Rs.) for each State/UT in 2023-24. Keyed by the state names the
#: village records use, so `demand_profile(village.state, ...)` resolves directly.
STATE_MPCE_RURAL: dict[str, int] = {
    "Andhra Pradesh": 5327, "Arunachal Pradesh": 5995, "Assam": 3793, "Bihar": 3670,
    "Chhattisgarh": 2739, "NCT of Delhi": 7400, "Goa": 8048, "Gujarat": 4116,
    "Haryana": 5377, "Himachal Pradesh": 5825, "Jharkhand": 2946, "Karnataka": 4903,
    "Kerala": 6611, "Madhya Pradesh": 3441, "Maharashtra": 4145, "Manipur": 4531,
    "Meghalaya": 3852, "Mizoram": 5963, "Nagaland": 5155, "Odisha": 3357,
    "Punjab": 5817, "Rajasthan": 4510, "Sikkim": 9377, "Tamil Nadu": 5701,
    "Telangana": 5435, "Tripura": 6259, "Uttar Pradesh": 3481, "Uttarakhand": 5003,
    "West Bengal": 3620, "Andaman & Nicobar Islands": 7771, "Chandigarh": 8857,
    "Daman & Diu": 4311, "Dadra & Nagar Haveli": 4311, "Jammu & Kashmir": 4774,
    "Lakshadweep": 6350, "Puducherry": 7598,
}
ALL_INDIA_RURAL_MPCE = 4122  # Statement 7 / Statement 2

#: Statement 4 — rural % share of total MPCE, by item group.
ITEM_GROUP_SHARE_RURAL: dict[str, float] = {
    "cereals & cereal substitutes": 4.99,
    "pulses & their products": 2.04,
    "sugar & salt": 0.89,
    "milk & milk products": 8.44,
    "vegetables": 6.03,
    "fruits": 3.85,
    "egg, fish & meat": 4.92,
    "edible oil": 2.77,
    "spices": 3.27,
    "beverages, refreshments, processed food": 9.84,
    "pan, tobacco & intoxicants": 3.84,
    "fuel and light": 6.11,
    "education": 3.24,
    "medical": 6.83,
    "conveyance": 7.59,
    "consumer services excluding conveyance": 5.25,
    "misc. goods, entertainment": 6.22,
    "rent": 0.56,
    "taxes and cesses": 0.21,
    "clothing, bedding & footwear": 6.63,
    "durable goods": 6.48,
}

#: Figure 1R — (share of rural population, average MPCE) per fractile class, 2023-24.
FRACTILES_RURAL: list[tuple[float, int]] = [
    (0.05, 1677), (0.05, 2126), (0.10, 2473), (0.10, 2833), (0.10, 3162), (0.10, 3498),
    (0.10, 3866), (0.10, 4304), (0.10, 4885), (0.10, 5763), (0.05, 6929), (0.05, 10137),
]

#: category -> (item groups it sells into, addressable share, why that share).
#: The item groups are real; the addressable share is an explicit assumption.
CATEGORIES: dict[str, tuple[list[str], float, str]] = {
    "dairy": (
        ["milk & milk products"], 0.45,
        "Rural milk demand is largely met by own livestock and informal neighbour sales; a new "
        "unit competes for the purchased fraction only.",
    ),
    "kirana": (
        ["cereals & cereal substitutes", "pulses & their products", "sugar & salt",
         "edible oil", "spices", "beverages, refreshments, processed food"], 0.62,
        "Staples bought through shops rather than PDS, own production or weekly haat. Excludes "
        "vegetables, fruits and meat, which rural households mostly buy from vendors, "
        "not a kirana.",
    ),
    "tailoring": (
        ["consumer services excluding conveyance"], 0.30,
        "HCES puts tailoring charges inside 'consumer services excluding conveyance' (Statement 5 "
        "footnote) and explicitly outside 'clothing & bedding'. Tailoring is one service among "
        "several in that group, so only a minority of it is addressable.",
    ),
    "poultry": (
        ["egg, fish & meat"], 0.40,
        "The published group covers egg, fish and meat together; poultry is a subset, and part of "
        "rural consumption is backyard-reared rather than purchased.",
    ),
    "flour_mill": (
        ["cereals & cereal substitutes"], 0.18,
        "A chakki sells milling as a service on the cereal basket, not the cereal itself, so only "
        "the milling margin on that spend is addressable.",
    ),
}


def fractile_cv() -> float:
    """Coefficient of variation of the real rural MPCE distribution (Figure 1R)."""
    mean = sum(share * mpce for share, mpce in FRACTILES_RURAL)
    var = sum(share * (mpce - mean) ** 2 for share, mpce in FRACTILES_RURAL)
    return var**0.5 / mean


def income_segments(state_mpce: int) -> list[dict]:
    """Real fractile shares, with levels scaled from the all-India rural mean to the state mean."""
    scale = state_mpce / ALL_INDIA_RURAL_MPCE
    bands = [("Bottom 30%", FRACTILES_RURAL[:4]), ("Lower middle 40%", FRACTILES_RURAL[4:8]),
             ("Upper middle 20%", FRACTILES_RURAL[8:10]), ("Top 10%", FRACTILES_RURAL[10:])]
    out = []
    for label, rows in bands:
        share = sum(s for s, _ in rows)
        mean_mpce = sum(s * m for s, m in rows) / share
        out.append({
            "label": label,
            "share": round(share, 2),
            "mpce": round(mean_mpce * scale),
        })
    return out


def household_sizes(states: set[str]) -> dict[str, float]:
    """population / households per state, straight from Mission Antyodaya. Real, not assumed."""
    pop: dict[str, float] = defaultdict(float)
    hh: dict[str, float] = defaultdict(float)
    for n, row in enumerate(read_csv(ANTYODAYA, ["shrid2", "total_population", "total_hhd"]), 1):
        progress("antyodaya", n)
        sid = state_id_of(row["shrid2"].strip())
        if sid is None:
            continue
        name = state_name(sid)
        if name in states:
            pop[name] += num(row["total_population"], 0.0) or 0.0
            hh[name] += num(row["total_hhd"], 0.0) or 0.0
    return {s: round(pop[s] / hh[s], 2) for s in states if hh.get(s, 0) > 0}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    cv = round(fractile_cv(), 3)
    print(f"rural MPCE coefficient of variation (Figure 1R): {cv}")

    sizes = household_sizes(set(STATE_MPCE_RURAL))
    print(f"household size computed for {len(sizes)} states")

    states: dict[str, dict] = {}
    for name, mpce in STATE_MPCE_RURAL.items():
        size = sizes.get(name)
        if size is None:
            continue  # no rural Antyodaya coverage (small UTs) — omit rather than invent a size
        cats = {}
        for cat, (groups, addressable, rationale) in CATEGORIES.items():
            share = sum(ITEM_GROUP_SHARE_RURAL[g] for g in groups) / 100
            cats[cat] = {
                "share_of_mpce": round(share, 4),
                "cv": cv,
                "addressable_share": addressable,
                "item_groups": groups,
                "addressable_rationale": rationale,
            }
        states[name] = {
            "rural_mpce": mpce,
            "avg_household_size": size,
            "categories": cats,
        }

    payload = {
        "_meta": meta(
            "HCES 2023-24 Fact Sheet (MoSPI), Statements 4 & 7 and Figure 1R",
            "Real published data. See method_note for what remains modelled.",
            url=SOURCE_URL,
            year="2023-24",
            method_note=(
                "rural_mpce (Statement 7) and share_of_mpce (Statement 4) are published figures. "
                "cv is the coefficient of variation of the published rural MPCE distribution "
                "(Figure 1R), not an assumption. avg_household_size is population/households from "
                "Mission Antyodaya. addressable_share IS an assumption — each category carries its "
                "rationale — as is the mapping from published item groups to business category, "
                "which is why every category ships its item_groups list. Category shares are "
                "all-India rural; state variation in the composition of spend needs the HCES "
                "microdata (microdata.gov.in catalogue 237)."
            ),
        ),
        "all_india_rural_mpce": ALL_INDIA_RURAL_MPCE,
        "states": states,
        "income_segments": {
            "note": (
                "Real rural fractile shares from HCES 2023-24 Figure 1R; MPCE levels scaled from "
                "the all-India rural mean to each state's published mean."
            ),
            **{name: income_segments(row["rural_mpce"]) for name, row in states.items()},
        },
    }
    write_json(args.out / "hces_demand.json", payload)
    print(f"  {len(states)} states")


if __name__ == "__main__":
    main()
