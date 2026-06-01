"""Tectonic plate ingestion from local GeoJSON under ``datasets/``."""

from pathlib import Path

import geopandas as gpd
from shapely import force_2d

from ingestion import _storage

DATASETS_DIR = Path(__file__).resolve().parents[1] / "datasets"
SUBDIR = "tectonic_plates"

PLATES_FILE = "Tectonic_Plates.geojson"
BOUNDARIES_FILE = "Tectonic_Plate_Boundaries.geojson"

PLATES_CSV = "tectonic_plates.csv"
BOUNDARIES_CSV = "tectonic_plate_boundaries.csv"

PLATE_RENAMES = {
    "OBJECTID": "object_id",
    "Code": "plate_code",
    "PlateName": "plate_name",
    "Shape__Area": "shape_area",
    "Shape__Length": "shape_length",
}
BOUNDARY_RENAMES = {
    "OBJECTID": "object_id",
    "LAYER": "layer",
    "Name": "name",
    "Source": "source",
    "PlateA": "plate_a",
    "PlateB": "plate_b",
    "Type": "boundary_type",
    "Shape__Length": "shape_length",
}


def _read_geojson(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    gdf["geometry"] = gdf.geometry.apply(force_2d)
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    return gdf


def load_plates(source: Path) -> gpd.GeoDataFrame:
    return _read_geojson(source).rename(columns=PLATE_RENAMES)


def load_plate_boundaries(source: Path) -> gpd.GeoDataFrame:
    return _read_geojson(source).rename(columns=BOUNDARY_RENAMES)


def write_plates(gdf: gpd.GeoDataFrame) -> str:
    return _storage.write_csv(
        gdf, f"{_storage.dataset_prefix(SUBDIR)}/{PLATES_CSV}"
    )


def write_plate_boundaries(gdf: gpd.GeoDataFrame) -> str:
    return _storage.write_csv(
        gdf, f"{_storage.dataset_prefix(SUBDIR)}/{BOUNDARIES_CSV}"
    )
