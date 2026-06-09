"""Clean GEM faults into flat and geometry CSVs for Neo4j and spatial joins.

Outputs:
    data/processed/faults.csv       — geometry-free, for the load step
    data/processed/faults_geom.csv  — WKT geometry, for link_events_to_faults
"""

import logging
import re

import geopandas as gpd
import pandas as pd

from ingestion import gem_faults
from transform import _storage as processed_storage

FLAT_BLOB = processed_storage.processed_path("faults.csv")
GEOM_BLOB = processed_storage.processed_path("faults_geom.csv")

log = logging.getLogger(__name__)

# Canonical fault-type buckets the loader and quality suite rely on.
CANONICAL_FAULT_TYPES: tuple[str, ...] = (
    "normal", "reverse", "strike-slip", "oblique", "unknown",
)

# GEM's slip_type is a compound vocabulary (e.g. "Reverse-Dextral",
# "Sinistral_Transform"). Map each individual slip sense to a family; a
# segment combining two distinct families is classified as "oblique".
_SENSE_TO_FAMILY = {
    "normal":     "normal",
    "reverse":    "reverse",
    "thrust":     "reverse",
    "dextral":    "strike-slip",
    "sinistral":  "strike-slip",
    "strikeslip": "strike-slip",
    "transform":  "strike-slip",
    "oblique":    "oblique",
    "spreading":  "normal",  # spreading ridges are extensional
    "ridge":      "normal",
}


def _canonical_fault_type(raw_type: object) -> str:
    """Collapse a GEM ``slip_type`` string into one of CANONICAL_FAULT_TYPES."""
    if raw_type is None or pd.isna(raw_type):
        return "unknown"
    text = str(raw_type).strip().lower().replace("strike-slip", "strikeslip")
    text = text.replace("strike slip", "strikeslip")
    families = {
        fam
        for token in re.split(r"[-_ ]+", text)
        if (fam := _SENSE_TO_FAMILY.get(token))
    }
    if not families:
        return "unknown"
    if "oblique" in families or len(families) > 1:
        return "oblique"
    return families.pop()


def _preferred_value(triple: object) -> float | None:
    """GEM encodes numerics as ``"(preferred, min, max)"``; take preferred."""
    if triple is None or pd.isna(triple):
        return None
    match = re.match(r"\s*\(\s*([^,]*)", str(triple))
    if not match:
        return None
    try:
        return float(match.group(1).strip())
    except ValueError:
        return None


def clean_faults() -> gpd.GeoDataFrame:
    gdf = gem_faults.read()

    gdf = gdf.rename(columns={
        "name":          "fault_name",
        "slip_type":     "raw_type",
        "net_slip_rate": "slip_rate_mm_yr",
        "average_dip":   "dip_angle_deg",
        "average_rake":  "rake_deg",
    })

    # GEM ships dip/rake/slip-rate as "(preferred, min, max)" triple strings.
    for col in ("slip_rate_mm_yr", "dip_angle_deg", "rake_deg"):
        if col in gdf.columns:
            gdf[col] = gdf[col].map(_preferred_value)

    gdf["fault_type"] = gdf["raw_type"].map(_canonical_fault_type)

    gdf["fault_id"] = "gem_" + gdf.index.astype(str).str.zfill(5)
    gdf["source"]   = "gem"

    gdf = gdf[gdf.geometry.notnull()].copy()
    gdf = gdf.to_crs("EPSG:4326")

    geom_uri = processed_storage.write_csv(gdf, GEOM_BLOB)
    log.info("Wrote %s", geom_uri)

    flat_cols = [
        "fault_id", "fault_name", "fault_type", "raw_type",
        "slip_rate_mm_yr", "dip_angle_deg", "rake_deg",
        "country", "source",
    ]
    flat_cols = [c for c in flat_cols if c in gdf.columns]
    flat = pd.DataFrame(gdf[flat_cols])
    flat_uri = processed_storage.write_csv(flat, FLAT_BLOB)

    log.info("clean_faults: %s GEM fault segments → %s", f"{len(gdf):,}", flat_uri)
    log.info("fault_type distribution:\n%s", gdf["fault_type"].value_counts())
    return gdf


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    clean_faults()
