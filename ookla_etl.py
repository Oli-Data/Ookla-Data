"""Normalize Ookla coordinates and recover the missing 2021 Q3 extracts."""

import numpy as np
import pandas as pd
from shapely import bounds, box, equals, from_wkt, get_type_id, is_valid


def normalize_tile_coordinates(frame):
    """Fill missing tile centers from rectangular WKT tiles; keep existing values."""
    result = frame.copy()
    for column in ("tile_x", "tile_y"):
        if column not in result:
            result[column] = np.nan

    missing_x = result["tile_x"].isna()
    missing_y = result["tile_y"].isna()
    needs_center = missing_x | missing_y

    if needs_center.any():
        if "tile" not in result:
            raise ValueError("Missing coordinates cannot be repaired without tile polygons.")
        polygons = from_wkt(result.loc[needs_center, "tile"].to_numpy())
        tile_bounds = bounds(polygons)
        if not (
            np.isfinite(tile_bounds).all()
            and is_valid(polygons).all()
            and (get_type_id(polygons) == 3).all()
            and (tile_bounds[:, 2] > tile_bounds[:, 0]).all()
            and (tile_bounds[:, 3] > tile_bounds[:, 1]).all()
        ):
            raise ValueError("Invalid tile polygons: stop before geographic filtering.")
        rectangles = box(*tile_bounds.T)
        if not equals(polygons, rectangles).all():
            raise ValueError("Expected rectangular Ookla tiles; inspect this source geometry.")

        # Ookla's existing center columns use four decimal places.
        centers = pd.DataFrame(
            {
                "tile_x": ((tile_bounds[:, 0] + tile_bounds[:, 2]) / 2).round(4),
                "tile_y": ((tile_bounds[:, 1] + tile_bounds[:, 3]) / 2).round(4),
            },
            index=result.index[needs_center],
        )
        result.loc[missing_x, "tile_x"] = centers.loc[missing_x[needs_center], "tile_x"]
        result.loc[missing_y, "tile_y"] = centers.loc[missing_y[needs_center], "tile_y"]

    coordinates = result[["tile_x", "tile_y"]].to_numpy(dtype=float)
    if not (
        np.isfinite(coordinates).all()
        and result["tile_x"].between(-180, 180).all()
        and result["tile_y"].between(-90, 90).all()
    ):
        raise ValueError("Missing or invalid coordinates remain; do not filter these rows.")
    return result


from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


def recover_q3_2021(regions, data_dir=Path("."), apply=False):
    """Recover only 2021 Q3. Validate all regions before backing up and replacing files."""
    data_dir = Path(data_dir)
    keys = ["quadkey", "year", "quarter"]
    source_url = (
        "https://ookla-open-data.s3.amazonaws.com/parquet/performance/"
        "type=mobile/year=2021/quarter=3/"
        "2021-07-01_performance_mobile_tiles.parquet"
    )
    cache = data_dir / ".ookla-cache"
    cache.mkdir(exist_ok=True)
    source = cache / "2021-07-01_performance_mobile_tiles.parquet"
    if not source.exists():
        print("Downloading only the 2021 Q3 source (about 204 MB)...", flush=True)
        partial = source.with_suffix(".partial")
        try:
            with urllib.request.urlopen(source_url, timeout=60) as response:
                with partial.open("wb") as output:
                    shutil.copyfileobj(response, output)
            pq.ParquetFile(partial)  # Reject incomplete/non-Parquet downloads.
            os.replace(partial, source)
        finally:
            partial.unlink(missing_ok=True)

    source_file = pq.ParquetFile(source)
    required = {"quadkey", "tile", "avg_d_kbps", "avg_u_kbps", "avg_lat_ms", "tests", "devices"}
    if not required.issubset(source_file.schema.names):
        raise ValueError("Q3 source is missing required measurement columns.")

    chunks = {name: [] for name in regions}
    source_rows = 0
    repaired_rows = 0
    for batch in source_file.iter_batches(batch_size=100_000):
        raw = batch.to_pandas()
        absent = pd.Series(False, index=raw.index)
        for column in ("tile_x", "tile_y"):
            absent |= raw[column].isna() if column in raw else True
        repaired_rows += int(absent.sum())
        data = normalize_tile_coordinates(raw)
        source_rows += len(data)
        for name, bbox in regions.items():
            selected = data.loc[
                data["tile_y"].between(bbox["min_lat"], bbox["max_lat"])
                & data["tile_x"].between(bbox["min_lon"], bbox["max_lon"])
            ].copy()
            chunks[name].append(selected)

    if source_rows != source_file.metadata.num_rows:
        raise ValueError("Source read did not account for every Q3 record.")
    print(f"Read {source_rows:,} source records; repaired coordinates for {repaired_rows:,}.")

    datasets, originals, reports, signatures, paths = {}, {}, [], {}, {}
    for name in regions:
        path = data_dir / f"{name.lower()}_mobile_historical_2020_2025.parquet"
        signature_before = (path.stat().st_size, path.stat().st_mtime_ns)
        old = pd.read_parquet(path)
        if signature_before != (path.stat().st_size, path.stat().st_mtime_ns):
            raise RuntimeError(f"{path.name} changed during validation; retry.")
        if old.duplicated(keys).any():
            raise ValueError(f"Existing duplicate tile-quarter keys in {name}.")

        recovered = pd.concat(chunks[name], ignore_index=True)
        recovered["year"] = 2021
        recovered["quarter"] = 3
        recovered["region"] = name
        recovered["avg_d_mbps"] = recovered["avg_d_kbps"] / 1000
        recovered["avg_u_mbps"] = recovered["avg_u_kbps"] / 1000
        # These two newer measurements were not supplied in the old Q3 schema.
        for column in ("avg_lat_down_ms", "avg_lat_up_ms"):
            if column in old and column not in recovered:
                recovered[column] = np.nan
        missing_columns = set(old.columns) - set(recovered.columns)
        if missing_columns:
            raise ValueError(f"Unaccounted-for columns in {name}: {missing_columns}")
        recovered = recovered.loc[:, old.columns].astype(old.dtypes.to_dict())
        if recovered.empty or recovered.duplicated(keys).any():
            raise ValueError(f"Empty or duplicate Q3 recovery for {name}.")

        old_q3 = old.loc[old["year"].eq(2021) & old["quarter"].eq(3)]
        expected = recovered.set_index(keys)
        actual = old_q3.set_index(keys)
        if not actual.index.isin(expected.index).all():
            raise ValueError(f"Existing Q3 records do not belong to this source: {name}")
        if not actual.empty:
            pd.testing.assert_frame_equal(
                actual.sort_index(), expected.loc[actual.index].sort_index(),
                check_exact=False, atol=1e-9, rtol=1e-12,
            )
        to_add = recovered.loc[
            ~pd.MultiIndex.from_frame(recovered[keys]).isin(actual.index)
        ]
        combined = pd.concat([old, to_add], ignore_index=True)
        pd.testing.assert_frame_equal(combined.iloc[:len(old)], old.reset_index(drop=True))
        if combined.duplicated(keys).any():
            raise ValueError(f"Duplicate records after recovery: {name}")
        q3_mask = combined["year"].eq(2021) & combined["quarter"].eq(3)
        if int(q3_mask.sum()) != len(recovered):
            raise ValueError(f"Q3 count mismatch after recovery: {name}")
        originals[name], datasets[name] = old, combined
        signatures[name], paths[name] = signature_before, path
        reports.append({
            "region": name, "previous_records": len(old), "added_q3": len(to_add),
            "q3_records": len(recovered), "q3_at_least_20_tests": int(recovered["tests"].ge(20).sum()),
            "total_records": len(combined),
        })

    summary = pd.DataFrame(reports)
    print(summary.to_string(index=False))
    changed = summary.loc[summary["added_q3"].gt(0), "region"].tolist()
    if not apply:
        print("Preview only: regional files have not changed.")
    elif not changed:
        print("Already complete: Q3 matches the source; no files rewritten.")
    else:
        # Stage and read back every replacement before changing any original file.
        with tempfile.TemporaryDirectory(prefix="q3-stage-", dir=cache) as stage_dir:
            staged = {}
            for name in changed:
                staged[name] = Path(stage_dir) / paths[name].name
                datasets[name].to_parquet(staged[name], index=False)
                pd.testing.assert_frame_equal(pd.read_parquet(staged[name]), datasets[name])
            for name in changed:
                if signatures[name] != (paths[name].stat().st_size, paths[name].stat().st_mtime_ns):
                    raise RuntimeError(f"{paths[name].name} changed since validation; retry.")

            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = data_dir / ".ookla-backups" / stamp
            backup.mkdir(parents=True, exist_ok=False)
            for name in changed:
                shutil.copy2(paths[name], backup / paths[name].name)
            with source.open("rb") as handle:
                source_sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
            (backup / "recovery.json").write_text(json.dumps({
                "source_url": source_url, "source_sha256": source_sha256,
                "source_records": source_rows, "coordinate_repaired_records": repaired_rows,
                "coordinate_method": "WKT bounding-box midpoint, rounded to 4 decimals",
                "summary": reports,
            }, indent=2) + "\n")
            replaced = []
            try:
                for name in changed:
                    os.replace(staged[name], paths[name])
                    replaced.append(name)
            except Exception:
                for name in replaced:
                    shutil.copy2(backup / paths[name].name, paths[name])
                raise
            print(f"Updated {len(changed)} files. Original files backed up to: {backup}")
    return summary, datasets
