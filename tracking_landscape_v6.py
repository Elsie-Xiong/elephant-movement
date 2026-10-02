# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
#   "numpy",
#   "pillow",
# ]
# ///

import csv
from pathlib import Path
from datetime import datetime
from math import cos, radians

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
from PIL import Image


DATA = Path("data")
TRACKING_FILE = DATA / "ThermochronTracking Elephants Kruger 2007.csv"
OUTPUT = Path("out/real-terrain-tracking-test.png")

EARTH_KM_PER_DEGREE = 111.32


# ------------------------------------------------------------
# STUDY AREA
# ------------------------------------------------------------

GPS_LAT_MIN = -25.37676
GPS_LAT_MAX = -23.97868
GPS_LON_MIN = 31.06269
GPS_LON_MAX = 32.00439

MARGIN = 0.04

PIXELS_PER_DEGREE = 500


TILES = [
    {
        "name": "Copernicus_DSM_COG_10_S26_00_E031_00_DEM.tif",
        "south": -26,
        "north": -25,
        "west": 31,
    },
    {
        "name": "Copernicus_DSM_COG_10_S25_00_E031_00_DEM.tif",
        "south": -25,
        "north": -24,
        "west": 31,
    },
    {
        "name": "Copernicus_DSM_COG_10_S25_00_E032_00_DEM.tif",
        "south": -25,
        "north": -24,
        "west": 32,
    },
    {
        "name": "Copernicus_DSM_COG_10_S24_00_E031_00_DEM.tif",
        "south": -24,
        "north": -23,
        "west": 31,
    },
]


# ------------------------------------------------------------
# TRACKING DATA
# ------------------------------------------------------------

def parse_time(timestamp):
    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )


def read_tracks():
    tracks = {}

    with TRACKING_FILE.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if not row["location-long"] or not row["location-lat"]:
                continue

            elephant_id = row["individual-local-identifier"]

            tracks.setdefault(elephant_id, []).append(
                {
                    "time": parse_time(row["timestamp"]),
                    "lon": float(row["location-long"]),
                    "lat": float(row["location-lat"]),
                }
            )

    for elephant_id in tracks:
        tracks[elephant_id].sort(
            key=lambda point: point["time"]
        )

    return tracks


# ------------------------------------------------------------
# REAL COPERNICUS TERRAIN
# ------------------------------------------------------------

def load_tile(path):
    with Image.open(path) as image:
        reduced = image.resize(
            (PIXELS_PER_DEGREE, PIXELS_PER_DEGREE),
            resample=Image.Resampling.BILINEAR,
        )

        return np.array(
            reduced,
            dtype=np.float32,
        )


def build_mosaic():
    width = 2 * PIXELS_PER_DEGREE
    height = 3 * PIXELS_PER_DEGREE

    mosaic = np.full(
        (height, width),
        np.nan,
        dtype=np.float32,
    )

    for tile in TILES:
        terrain = load_tile(
            DATA / tile["name"]
        )

        row = int(
            -23 - tile["north"]
        )

        col = int(
            tile["west"] - 31
        )

        y0 = row * PIXELS_PER_DEGREE
        y1 = y0 + PIXELS_PER_DEGREE

        x0 = col * PIXELS_PER_DEGREE
        x1 = x0 + PIXELS_PER_DEGREE

        mosaic[y0:y1, x0:x1] = terrain

    return mosaic


def crop_terrain(mosaic):
    lon_min = GPS_LON_MIN - MARGIN
    lon_max = GPS_LON_MAX + MARGIN

    lat_min = GPS_LAT_MIN - MARGIN
    lat_max = GPS_LAT_MAX + MARGIN

    x0 = int(
        (lon_min - 31)
        * PIXELS_PER_DEGREE
    )

    x1 = int(
        (lon_max - 31)
        * PIXELS_PER_DEGREE
    )

    y0 = int(
        (-23 - lat_max)
        * PIXELS_PER_DEGREE
    )

    y1 = int(
        (-23 - lat_min)
        * PIXELS_PER_DEGREE
    )

    elevation = mosaic[
        y0:y1,
        x0:x1,
    ]

    longitudes = np.linspace(
        lon_min,
        lon_max,
        elevation.shape[1],
    )

    latitudes = np.linspace(
        lat_max,
        lat_min,
        elevation.shape[0],
    )

    # Mask the tiny number of suspicious negative pixels.
    elevation[elevation < 0] = np.nan

    return (
        elevation,
        longitudes,
        latitudes,
        lon_min,
        lon_max,
        lat_min,
        lat_max,
    )


# ------------------------------------------------------------
# COORDINATES
# ------------------------------------------------------------

def geographic_to_local_km(lon, lat):
    centre_lon = (
        GPS_LON_MIN + GPS_LON_MAX
    ) / 2

    centre_lat = (
        GPS_LAT_MIN + GPS_LAT_MAX
    ) / 2

    x = (
        (lon - centre_lon)
        * EARTH_KM_PER_DEGREE
        * cos(radians(centre_lat))
    )

    y = (
        (lat - centre_lat)
        * EARTH_KM_PER_DEGREE
    )

    return x, y


def elevation_at(
    lon,
    lat,
    elevation,
    lon_min,
    lon_max,
    lat_min,
    lat_max,
):
    """Nearest-pixel DSM elevation at one GPS location."""

    col = int(
        (lon - lon_min)
        / (lon_max - lon_min)
        * (elevation.shape[1] - 1)
    )

    row = int(
        (lat_max - lat)
        / (lat_max - lat_min)
        * (elevation.shape[0] - 1)
    )

    col = np.clip(
        col,
        0,
        elevation.shape[1] - 1,
    )

    row = np.clip(
        row,
        0,
        elevation.shape[0] - 1,
    )

    value = elevation[row, col]

    if not np.isfinite(value):
        return np.nanmedian(elevation)

    return float(value)


# ------------------------------------------------------------
# 2.5D PROJECTION
# ------------------------------------------------------------

def project_25d(x, y, elevation, minimum_elevation):
    """
    x/y = real geographic position in local kilometres
    elevation = real Copernicus DSM surface elevation

    Vertical exaggeration is visual only.
    """

    angle = radians(-8)

    rotated_x = (
        x * np.cos(angle)
        - y * np.sin(angle)
    )

    rotated_y = (
        x * np.sin(angle)
        + y * np.cos(angle)
    )

    relative_height_km = (
        elevation - minimum_elevation
    ) / 1000

    VERTICAL_EXAGGERATION = 5.0

    screen_x = rotated_x

    screen_y = (
        rotated_y * 0.72
        + relative_height_km
        * VERTICAL_EXAGGERATION
    )

    return screen_x, screen_y


# ------------------------------------------------------------
# DRAW
# ------------------------------------------------------------

def draw():
    tracks = read_tracks()

    mosaic = build_mosaic()

    (
        elevation,
        longitudes,
        latitudes,
        lon_min,
        lon_max,
        lat_min,
        lat_max,
    ) = crop_terrain(
        mosaic
    )

    minimum_elevation = float(
        np.nanmin(elevation)
    )

    maximum_elevation = float(
        np.nanmax(elevation)
    )

    # --------------------------------------------------------
    # TERRAIN POINT GRID
    #
    # Sparse enough to read as digital points,
    # not as one solid rectangular surface.
    # --------------------------------------------------------

    terrain_step = 5

    lon_grid, lat_grid = np.meshgrid(
        longitudes[::terrain_step],
        latitudes[::terrain_step],
    )

    terrain_elevation = elevation[
        ::terrain_step,
        ::terrain_step,
    ]

    valid_terrain = np.isfinite(
        terrain_elevation
    )

    terrain_x, terrain_y = geographic_to_local_km(
        lon_grid,
        lat_grid,
    )

    (
        terrain_screen_x,
        terrain_screen_y,
    ) = project_25d(
        terrain_x,
        terrain_y,
        terrain_elevation,
        minimum_elevation,
    )

    # --------------------------------------------------------
    # REAL ELEPHANT TRACKING POINTS + SEGMENTS
    # --------------------------------------------------------

    gps_x = []
    gps_y = []
    gps_screen_x = []
    gps_screen_y = []

    projected_segments = []

    for elephant_id in sorted(tracks):
        points = tracks[elephant_id]

        projected_points = []

        for point in points:
            x, y = geographic_to_local_km(
                point["lon"],
                point["lat"],
            )

            z = elevation_at(
                point["lon"],
                point["lat"],
                elevation,
                lon_min,
                lon_max,
                lat_min,
                lat_max,
            )

            sx, sy = project_25d(
                x,
                y,
                z,
                minimum_elevation,
            )

            gps_x.append(x)
            gps_y.append(y)
            gps_screen_x.append(sx)
            gps_screen_y.append(sy)

            projected_points.append(
                {
                    "time": point["time"],
                    "sx": sx,
                    "sy": sy,
                }
            )

        for i in range(1, len(projected_points)):
            previous = projected_points[i - 1]
            current = projected_points[i]

            gap_minutes = (
                current["time"] - previous["time"]
            ).total_seconds() / 60

            if 29 <= gap_minutes <= 31:
                projected_segments.append(
                    [
                        (
                            previous["sx"],
                            previous["sy"],
                        ),
                        (
                            current["sx"],
                            current["sy"],
                        ),
                    ]
                )

    gps_screen_x = np.array(
        gps_screen_x
    )

    gps_screen_y = np.array(
        gps_screen_y
    )

    # --------------------------------------------------------
    # FIGURE
    # --------------------------------------------------------

    fig = plt.figure(
        figsize=(16, 9),
        facecolor="#06090a",
    )

    ax = fig.add_axes(
        [0.08, 0.035, 0.84, 0.92]
    )

    ax.set_facecolor(
        "#06090a"
    )

    # --------------------------------------------------------
    # 1. REAL TERRAIN — DIGITAL POINT FIELD
    # --------------------------------------------------------

    normalized_elevation = (
        terrain_elevation
        - minimum_elevation
    ) / (
        maximum_elevation
        - minimum_elevation
    )

    ax.scatter(
        terrain_screen_x[valid_terrain],
        terrain_screen_y[valid_terrain],
        s=0.34,
        c=normalized_elevation[valid_terrain],
        cmap="Greys",
        vmin=0,
        vmax=1,
        alpha=0.28,
        linewidths=0,
        zorder=1,
    )

    # --------------------------------------------------------
    # 2. REAL ELEPHANT TRAJECTORIES
    # --------------------------------------------------------

    tracks_layer = LineCollection(
        projected_segments,
        colors="#d7e3df",
        linewidths=0.16,
        alpha=0.10,
        zorder=3,
    )

    ax.add_collection(
        tracks_layer
    )

    # --------------------------------------------------------
    # 3. REAL GPS OBSERVATIONS
    # --------------------------------------------------------

    ax.scatter(
        gps_screen_x,
        gps_screen_y,
        s=0.13,
        color="#edf4f1",
        alpha=0.18,
        linewidths=0,
        zorder=4,
    )

    # --------------------------------------------------------
    # FRAME
    # --------------------------------------------------------

    all_x = np.concatenate(
        [
            terrain_screen_x[valid_terrain],
            gps_screen_x,
        ]
    )

    all_y = np.concatenate(
        [
            terrain_screen_y[valid_terrain],
            gps_screen_y,
        ]
    )

    x_min = np.nanmin(all_x)
    x_max = np.nanmax(all_x)

    y_min = np.nanmin(all_y)
    y_max = np.nanmax(all_y)

    ax.set_xlim(
        x_min - (x_max - x_min) * 0.03,
        x_max + (x_max - x_min) * 0.03,
    )

    ax.set_ylim(
        y_min - (y_max - y_min) * 0.03,
        y_max + (y_max - y_min) * 0.03,
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    ax.axis("off")

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    fig.text(
        0.045,
        0.936,
        "LIVING RHYTHMS",
        color="#dde6e2",
        fontsize=15,
        fontweight="medium",
        ha="left",
        va="top",
    )

    fig.text(
        0.045,
        0.903,
        "ELEPHANT TRACKING / REAL COPERNICUS TERRAIN",
        color="#61716d",
        fontsize=6.8,
        ha="left",
        va="top",
    )

    info = (
        f"TRACKED INDIVIDUALS   {len(tracks):02d}\n"
        f"GPS OBSERVATIONS      {len(gps_screen_x):,}\n"
        f"TRACK SEGMENTS        {len(projected_segments):,}\n"
        f"DSM RANGE             {minimum_elevation:.0f}–{maximum_elevation:.0f} M"
    )

    fig.text(
        0.805,
        0.924,
        info,
        color="#687873",
        fontsize=6.2,
        family="monospace",
        linespacing=1.65,
        ha="left",
        va="top",
    )

    fig.text(
        0.045,
        0.050,
        "REAL TERRAIN + REAL TRACKING RECORDS",
        color="#667671",
        fontsize=5.8,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.955,
        0.050,
        "TERRAIN HEIGHT = COPERNICUS DSM  /  TRACKS = CONSECUTIVE 29–31 MIN GPS RECORDS",
        color="#495753",
        fontsize=5.0,
        family="monospace",
        ha="right",
        va="bottom",
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        OUTPUT,
        dpi=220,
        facecolor=fig.get_facecolor(),
    )

    print("REAL TERRAIN + ELEPHANT TRACKING TEST")
    print("-------------------------------------")
    print("Tracked individuals:", len(tracks))
    print("GPS observations:", len(gps_screen_x))
    print("Valid trajectory segments:", len(projected_segments))
    print(
        "DSM range:",
        round(minimum_elevation, 2),
        "to",
        round(maximum_elevation, 2),
        "m",
    )
    print("Saved:", OUTPUT)

    plt.show()


if __name__ == "__main__":
    draw()