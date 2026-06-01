"""Schemas and typed readers for every CSV in the project.

Writers don't enforce types — ``to_csv`` strips them anyway. Every consumer
goes through one of the ``read_*`` helpers below, which is the single source
of truth for the column types that flow into Neo4j.
"""

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# --- Raw layer ---------------------------------------------------------------

USGS_RAW_DTYPES: dict[str, str] = {
    "id":              "string",
    "latitude":        "float64",
    "longitude":       "float64",
    "depth":           "float64",
    "mag":             "float64",
    "magType":         "string",
    "nst":             "Int64",
    "gap":             "float64",
    "dmin":            "float64",
    "rms":             "float64",
    "net":             "string",
    "place":           "string",
    "type":            "string",
    "horizontalError": "float64",
    "depthError":      "float64",
    "magError":        "float64",
    "magNst":          "Int64",
    "status":          "string",
    "locationSource":  "string",
    "magSource":       "string",
}
USGS_RAW_DATES: tuple[str, ...] = ("time", "updated")

GLOBAL_CMT_DTYPES: dict[str, str] = {
    "event_id":          "string",
    "hypo_lat":          "float64",
    "hypo_lon":          "float64",
    "hypo_depth_km":     "float64",
    "magnitude":         "float64",
    "region":            "string",
    "centroid_lat":      "float64",
    "centroid_lon":      "float64",
    "centroid_depth_km": "float64",
    "strike1":           "Int64",
    "dip1":              "Int64",
    "rake1":             "Int64",
    "strike2":           "Int64",
    "dip2":              "Int64",
    "moment_exponent":   "Int64",
}
GLOBAL_CMT_DATES: tuple[str, ...] = ("datetime",)

GEM_FAULTS_DTYPES: dict[str, str] = {
    "name":      "string",
    "slip_type": "string",
    "slip_rate": "float64",
    "dip":       "float64",
    "rake":      "float64",
    "country":   "string",
}

# --- Processed layer ---------------------------------------------------------

EVENT_DTYPES: dict[str, str] = {
    "event_id":  "string",
    "latitude":  "float64",
    "longitude": "float64",
    "depth_km":  "float64",
    "magnitude": "float64",
    "magType":   "string",
    "net":       "string",
    "place":     "string",
    "region":    "string",
}
EVENT_DATES: tuple[str, ...] = ("occurred_at", "updated")

FAULT_DTYPES: dict[str, str] = {
    "fault_id":        "string",
    "fault_name":      "string",
    "fault_type":      "string",
    "raw_type":        "string",
    "slip_rate_mm_yr": "float64",
    "dip_angle_deg":   "float64",
    "rake_deg":        "float64",
    "country":         "string",
    "source":          "string",
}

EVENT_FAULT_EDGE_DTYPES: dict[str, str] = {
    "event_id":         "string",
    "fault_id":         "string",
    "dist_to_fault_km": "float64",
}

EVENT_CMT_EDGE_DTYPES: dict[str, str] = {
    "event_id": "string",
    "cmt_id":   "string",
    "dist_km":  "float64",
    "dt_sec":   "float64",
}

AFTERSHOCK_EDGE_DTYPES: dict[str, str] = {
    "mainshock_id":    "string",
    "aftershock_id":   "string",
    "dist_km":         "float64",
    "time_delta_days": "float64",
    "mag_diff":        "float64",
}

# --- Helpers -----------------------------------------------------------------


def apply_schema(
    df: pd.DataFrame,
    schema: dict[str, str],
    dates: Iterable[str] = (),
) -> pd.DataFrame:
    """Cast known columns; ignore any that aren't present in ``df``."""
    for col, dtype in schema.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)
    for col in dates:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


def _read_typed(
    path: Path,
    schema: dict[str, str],
    dates: Iterable[str] = (),
) -> pd.DataFrame:
    return apply_schema(pd.read_csv(path), schema, dates)


def _read_geo_typed(
    path: Path,
    schema: dict[str, str],
    *,
    crs: str = "EPSG:4326",
) -> gpd.GeoDataFrame:
    """Read a CSV with a WKT ``geometry`` column into a typed GeoDataFrame."""
    df = apply_schema(pd.read_csv(path), schema)
    geometry = gpd.GeoSeries.from_wkt(df["geometry"])
    return gpd.GeoDataFrame(
        df.drop(columns=["geometry"]), geometry=geometry, crs=crs
    )


# --- Raw readers -------------------------------------------------------------


def read_raw_usgs_events(path: Path) -> pd.DataFrame:
    return _read_typed(path, USGS_RAW_DTYPES, USGS_RAW_DATES)


def read_raw_global_cmt(path: Path) -> pd.DataFrame:
    return _read_typed(path, GLOBAL_CMT_DTYPES, GLOBAL_CMT_DATES)


def read_raw_gem_faults(path: Path) -> gpd.GeoDataFrame:
    return _read_geo_typed(path, GEM_FAULTS_DTYPES)


# --- Processed readers -------------------------------------------------------


def read_events(path: Path = PROCESSED_DIR / "events.csv") -> pd.DataFrame:
    return _read_typed(path, EVENT_DTYPES, EVENT_DATES)


def read_faults(path: Path = PROCESSED_DIR / "faults.csv") -> pd.DataFrame:
    return _read_typed(path, FAULT_DTYPES)


def read_faults_geom(
    path: Path = PROCESSED_DIR / "faults_geom.csv",
) -> gpd.GeoDataFrame:
    return _read_geo_typed(path, FAULT_DTYPES)


def read_event_fault_edges(
    path: Path = PROCESSED_DIR / "event_fault_edges.csv",
) -> pd.DataFrame:
    return _read_typed(path, EVENT_FAULT_EDGE_DTYPES)


def read_event_cmt_edges(
    path: Path = PROCESSED_DIR / "event_cmt_edges.csv",
) -> pd.DataFrame:
    return _read_typed(path, EVENT_CMT_EDGE_DTYPES)


def read_aftershock_edges(
    path: Path = PROCESSED_DIR / "aftershock_edges.csv",
) -> pd.DataFrame:
    return _read_typed(path, AFTERSHOCK_EDGE_DTYPES)
