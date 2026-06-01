"""Link each USGS event to its nearest GEM fault within MAX_DIST_KM."""

import logging

import geopandas as gpd
import pandas as pd

from transform import _storage as processed_storage
from utils import dtypes

OUTPUT_BLOB = processed_storage.processed_path("event_fault_edges.csv")

MAX_DIST_KM = 50

log = logging.getLogger(__name__)


def link_events_to_faults() -> pd.DataFrame:
    events = dtypes.read_events()
    faults = dtypes.read_faults_geom()

    gdf_events = gpd.GeoDataFrame(
        events,
        geometry=gpd.points_from_xy(events["longitude"], events["latitude"]),
        crs="EPSG:4326",
    )

    # EPSG:3857 (Web Mercator) gives metric distances; good enough at this scale.
    gdf_events = gdf_events.to_crs("EPSG:3857")
    faults = faults.to_crs("EPSG:3857")

    joined = gpd.sjoin_nearest(
        gdf_events[["event_id", "geometry"]],
        faults[["fault_id", "geometry"]],
        how="left",
        max_distance=MAX_DIST_KM * 1000,
        distance_col="dist_to_fault_m",
    )

    joined = joined.dropna(subset=["fault_id"])
    joined["dist_to_fault_km"] = joined["dist_to_fault_m"] / 1000

    edges = pd.DataFrame(joined[["event_id", "fault_id", "dist_to_fault_km"]])
    uri = processed_storage.write_csv(edges, OUTPUT_BLOB)

    total = len(events)
    linked = len(edges)
    pct = (linked / total * 100) if total else 0.0
    log.info(
        "link_events_to_faults: %s/%s events linked (%.1f%%) → %s",
        f"{linked:,}", f"{total:,}", pct, uri,
    )
    return edges


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    link_events_to_faults()
