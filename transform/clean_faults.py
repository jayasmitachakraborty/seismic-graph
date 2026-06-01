"""Clean GEM faults into flat and geometry CSVs for Neo4j and spatial joins.

Outputs:
    data/processed/faults.csv       — geometry-free, for the load step
    data/processed/faults_geom.csv  — WKT geometry, for link_events_to_faults
"""

import logging

import geopandas as gpd
import pandas as pd

from ingestion import gem_faults
from transform import _storage as processed_storage

FLAT_BLOB = processed_storage.processed_path("faults.csv")
GEOM_BLOB = processed_storage.processed_path("faults_geom.csv")

log = logging.getLogger(__name__)

# Collapse GEM's raw slip_type vocabulary to a small canonical set.
FAULT_TYPE_MAP = {
    "normal":                    "normal",
    "normal - oblique":          "oblique",
    "reverse":                   "reverse",
    "reverse - oblique":         "oblique",
    "thrust":                    "reverse",
    "strike slip":               "strike-slip",
    "strike-slip":               "strike-slip",
    "right lateral strike-slip": "strike-slip",
    "left lateral strike-slip":  "strike-slip",
    "oblique":                   "oblique",
    "oblique-slip":              "oblique",
    "unknown":                   "unknown",
}


def clean_faults() -> gpd.GeoDataFrame:
    gdf = gem_faults.read()

    gdf = gdf.rename(columns={
        "name":      "fault_name",
        "slip_type": "raw_type",
        "slip_rate": "slip_rate_mm_yr",
        "dip":       "dip_angle_deg",
        "rake":      "rake_deg",
    })

    gdf["fault_type"] = (
        gdf["raw_type"]
        .str.lower()
        .str.strip()
        .map(FAULT_TYPE_MAP)
        .fillna("unknown")
    )

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
