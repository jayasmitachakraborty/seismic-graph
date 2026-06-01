"""Local-filesystem storage for the transform layer (data/processed/...)."""

from pathlib import Path

import geopandas as gpd
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PREFIX = "processed"


def processed_path(filename: str) -> str:
    return f"{PREFIX}/{filename}"


def write_csv(df: pd.DataFrame, rel_path: str) -> str:
    """Write a (Geo)DataFrame to ``data/<rel_path>``; geometry → WKT."""
    out = DATA_DIR / rel_path
    out.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(df, gpd.GeoDataFrame):
        df = pd.DataFrame(df).assign(geometry=df.geometry.to_wkt())
    df.to_csv(out, index=False)
    return str(out)
