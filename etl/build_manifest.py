"""Write `manifest.json` — the index the loader reads at startup instead of parsing every shard.

Scanning the emitted files rather than being told about them means the manifest cannot drift out
of sync with what is actually on disk.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from common import DEFAULT_OUT, PC11_STATES, meta, write_json

CODE_TO_NAME = {code: name for name, code in PC11_STATES.values()}


def read_shard(path: Path) -> dict:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    states: dict[str, dict] = {}
    for shard in sorted((args.out / "villages").glob("*.json*")):
        code = shard.name.split(".")[0]
        payload = read_shard(shard)
        rows = payload["villages"]
        poi_path = next(iter((args.out / "pois").glob(f"{code}.json*")), None)
        states[code] = {
            "code": code,
            "name": CODE_TO_NAME.get(code, code),
            "villages": len(rows),
            "districts": sorted({r["district"] for r in rows if r.get("district")}),
            "village_shard": str(shard.relative_to(args.out)),
            "poi_shard": str(poi_path.relative_to(args.out)) if poi_path else None,
            "pois": len(read_shard(poi_path)["pois"]) if poi_path else 0,
        }
        print(f"  {code}: {len(rows):,} villages, {states[code]['pois']:,} POIs, "
              f"{len(states[code]['districts'])} districts")

    if not states:
        raise SystemExit(f"no village shards under {args.out / 'villages'}")

    write_json(args.out / "manifest.json", {
        "_meta": meta("SetuBiz dataset build", "Index of committed per-state shards."),
        "states": states,
    })


if __name__ == "__main__":
    main()
