"""GEM Global Active Faults ingestion.

Source: https://github.com/GEMScienceTools/gem-global-active-faults
"""

import logging
import tempfile
from pathlib import Path

import geopandas as gpd
import requests
from shapely import force_2d

from ingestion import _storage
from utils import dtypes

REPO = "GEMScienceTools/gem-global-active-faults"
GEOJSON_PATH = "geojson/gem_active_faults.geojson"
DEFAULT_REF = "master"

SUBDIR = "gem_faults"
CSV_FILE = "gem_active_faults.csv"
TIMEOUT = 120

log = logging.getLogger(__name__)


def _rel_path() -> str:
    return f"{_storage.dataset_prefix(SUBDIR)}/{CSV_FILE}"


def _bytes_to_gdf(payload: bytes) -> gpd.GeoDataFrame:
    # geopandas needs a file path, so round-trip through a temp file.
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        tmp.write(payload)
        tmp_path = Path(tmp.name)
    try:
        gdf = gpd.read_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    gdf["geometry"] = gdf.geometry.apply(force_2d)
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    return gdf


def fetch(ref: str = DEFAULT_REF) -> gpd.GeoDataFrame:
    url = f"https://raw.githubusercontent.com/{REPO}/{ref}/{GEOJSON_PATH}"
    log.info("Downloading %s", url)
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return _bytes_to_gdf(r.content)


def write(gdf: gpd.GeoDataFrame) -> str:
    return _storage.write_csv(gdf, _rel_path())


def read() -> gpd.GeoDataFrame:
    return dtypes.read_raw_gem_faults(_storage.DATA_DIR / _rel_path())
