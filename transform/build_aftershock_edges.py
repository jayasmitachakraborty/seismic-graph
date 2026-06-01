"""Build AFTERSHOCK_OF edges between USGS events.

For each M >= MAINSHOCK_MIN_MAG event, emit edges to every event within
TIME_WINDOW_DAYS forward, DIST_THRESHOLD_KM and at least MAG_DIFF_MIN
smaller (Båth's law + Kagan spatial window heuristic). When an event
qualifies as an aftershock of multiple mainshocks, keep the edge to the
largest mag_diff.
"""

import logging

import pandas as pd

from transform import _storage as processed_storage
from transform._geo import haversine_km
from utils import dtypes

OUTPUT_BLOB = processed_storage.processed_path("aftershock_edges.csv")

TIME_WINDOW_DAYS  = 30
DIST_THRESHOLD_KM = 50
MAG_DIFF_MIN      = 1.2
MAINSHOCK_MIN_MAG = 4.5

log = logging.getLogger(__name__)


def build_aftershock_edges() -> pd.DataFrame:
    df = dtypes.read_events().sort_values("occurred_at").reset_index(drop=True)

    mainshocks = df[df["magnitude"] >= MAINSHOCK_MIN_MAG]
    window = pd.Timedelta(days=TIME_WINDOW_DAYS)

    rows: list[dict] = []
    for _, ms in mainshocks.iterrows():
        candidates = df[
            (df["occurred_at"] >  ms["occurred_at"]) &
            (df["occurred_at"] <= ms["occurred_at"] + window) &
            (df["magnitude"]   <= ms["magnitude"] - MAG_DIFF_MIN)
        ]
        if candidates.empty:
            continue

        candidates = candidates.assign(
            dist_km=haversine_km(
                ms["latitude"], ms["longitude"],
                candidates["latitude"].to_numpy(),
                candidates["longitude"].to_numpy(),
            )
        )
        nearby = candidates[candidates["dist_km"] <= DIST_THRESHOLD_KM]

        for _, after in nearby.iterrows():
            rows.append({
                "mainshock_id":   ms["event_id"],
                "aftershock_id":  after["event_id"],
                "dist_km":        float(after["dist_km"]),
                "time_delta_days": (after["occurred_at"]
                                    - ms["occurred_at"]).total_seconds() / 86400,
                "mag_diff":       float(ms["magnitude"] - after["magnitude"]),
            })

    edges = pd.DataFrame(rows, columns=list(dtypes.AFTERSHOCK_EDGE_DTYPES.keys()))

    if not edges.empty:
        edges = (
            edges.sort_values("mag_diff", ascending=False)
                 .drop_duplicates(subset=["aftershock_id"], keep="first")
                 .reset_index(drop=True)
        )

    uri = processed_storage.write_csv(edges, OUTPUT_BLOB)
    log.info(
        "build_aftershock_edges: %s AFTERSHOCK_OF edges → %s",
        f"{len(edges):,}", uri,
    )
    return edges


def read() -> pd.DataFrame:
    return dtypes.read_aftershock_edges()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    build_aftershock_edges()
