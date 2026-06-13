"""Build AFTERSHOCK_OF edges between USGS events.

Events below the catalog completeness floor (MC_GLOBAL) are dropped first,
so chain depth reflects seismicity rather than detection gaps. For each
M >= MAINSHOCK_MIN_MAG event, emit edges to every event within a
magnitude-scaled forward time window and a rupture-length-scaled distance
threshold, at least MAG_DIFF_MIN smaller (Båth's law). When an event
qualifies as an aftershock of multiple mainshocks, keep the edge to the
largest mag_diff.
"""

import logging

import pandas as pd

from transform import _storage as processed_storage
from transform._geo import haversine_km
from utils import dtypes

OUTPUT_BLOB = processed_storage.processed_path("aftershock_edges.csv")

# Catalog magnitude of completeness. USGS ComCat is complete to ~M4.5
# globally but far lower in well-instrumented regions; 4.0 is a pragmatic
# single floor until a per-region Mc is computed.
MC_GLOBAL = 4.0

MAG_DIFF_MIN      = 1.2
MAINSHOCK_MIN_MAG = 4.5

# Time window grows with mainshock magnitude: TIME_WINDOW_BASE_DAYS at
# REF_MAG, one decade per 2 magnitude units (alpha = 0.5), clipped so small
# events keep a sane minimum and great earthquakes don't absorb the catalog.
TIME_WINDOW_BASE_DAYS = 30.0
TIME_WINDOW_ALPHA     = 0.5
TIME_WINDOW_REF_MAG   = 5.0
TIME_WINDOW_MIN_DAYS  = 7.0
TIME_WINDOW_MAX_DAYS  = 1000.0

# Distance threshold scales with rupture length via Wells & Coppersmith
# (1994): log10(L_km) = 0.59 * M - 2.44. Aftershock zones extend beyond the
# rupture itself, hence the multiple.
RUPTURE_LENGTH_MULTIPLE = 2.0
DIST_THRESHOLD_MIN_KM   = 10.0
DIST_THRESHOLD_MAX_KM   = 500.0

log = logging.getLogger(__name__)


def time_window_days(mag: float) -> float:
    """Forward aftershock window in days for a mainshock of magnitude ``mag``."""
    scaled = TIME_WINDOW_BASE_DAYS * 10 ** (
        TIME_WINDOW_ALPHA * (mag - TIME_WINDOW_REF_MAG)
    )
    return min(TIME_WINDOW_MAX_DAYS, max(TIME_WINDOW_MIN_DAYS, scaled))


def dist_threshold_km(mag: float) -> float:
    """Spatial aftershock window in km for a mainshock of magnitude ``mag``."""
    rupture_len_km = 10 ** (0.59 * mag - 2.44)
    return min(
        DIST_THRESHOLD_MAX_KM,
        max(DIST_THRESHOLD_MIN_KM, RUPTURE_LENGTH_MULTIPLE * rupture_len_km),
    )


def build_aftershock_edges() -> pd.DataFrame:
    df = dtypes.read_events().sort_values("occurred_at").reset_index(drop=True)

    pre_cut = len(df)
    df = df[df["magnitude"] >= MC_GLOBAL].reset_index(drop=True)
    log.info(
        "build_aftershock_edges: completeness cut M >= %s kept %s/%s events",
        MC_GLOBAL, f"{len(df):,}", f"{pre_cut:,}",
    )

    mainshocks = df[df["magnitude"] >= MAINSHOCK_MIN_MAG]

    rows: list[dict] = []
    for _, ms in mainshocks.iterrows():
        window = pd.Timedelta(days=time_window_days(ms["magnitude"]))
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
        nearby = candidates[candidates["dist_km"] <= dist_threshold_km(ms["magnitude"])]

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
