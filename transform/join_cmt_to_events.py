"""Match Global CMT entries to USGS events (nearest-in-time + spatial gate)."""

import logging

import pandas as pd

from ingestion import global_cmt
from transform import _storage as processed_storage
from transform._geo import haversine_km
from utils import dtypes

OUTPUT_BLOB = processed_storage.processed_path("event_cmt_edges.csv")

# Two catalogs reference the same physical event when within both windows.
MAX_DIST_KM = 50
MAX_TIME_SEC = 60

log = logging.getLogger(__name__)


def join_cmt_to_events() -> pd.DataFrame:
    usgs = dtypes.read_events()
    cmt  = global_cmt.read_combined().rename(columns={"datetime": "occurred_at"})

    usgs = (
        usgs.dropna(subset=["occurred_at", "latitude", "longitude"])
            .sort_values("occurred_at")
    )
    cmt = (
        cmt.dropna(subset=["occurred_at", "centroid_lat", "centroid_lon"])
           .rename(columns={"event_id": "cmt_id"})
           .sort_values("occurred_at")
    )

    # Pair each CMT row with the nearest USGS event in time. Rename time
    # keys so both survive the merge for the dt_sec calc.
    matched = pd.merge_asof(
        cmt.rename(columns={"occurred_at": "cmt_time"})[
            ["cmt_id", "cmt_time", "centroid_lat", "centroid_lon"]
        ],
        usgs.rename(columns={"occurred_at": "usgs_time"})[
            ["event_id", "usgs_time", "latitude", "longitude"]
        ],
        left_on="cmt_time",
        right_on="usgs_time",
        direction="nearest",
        tolerance=pd.Timedelta(seconds=MAX_TIME_SEC),
    ).dropna(subset=["event_id"])

    matched["dist_km"] = haversine_km(
        matched["centroid_lat"].to_numpy(),
        matched["centroid_lon"].to_numpy(),
        matched["latitude"].to_numpy(),
        matched["longitude"].to_numpy(),
    )
    matched["dt_sec"] = (
        matched["usgs_time"] - matched["cmt_time"]
    ).dt.total_seconds()
    matched = matched[matched["dist_km"] <= MAX_DIST_KM]

    edges = matched[["event_id", "cmt_id", "dist_km", "dt_sec"]].reset_index(drop=True)
    uri = processed_storage.write_csv(edges, OUTPUT_BLOB)

    pct = (len(edges) / len(cmt) * 100) if len(cmt) else 0.0
    log.info(
        "join_cmt_to_events: %s/%s CMT entries linked (%.1f%%) → %s",
        f"{len(edges):,}", f"{len(cmt):,}", pct, uri,
    )
    return edges


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    join_cmt_to_events()
