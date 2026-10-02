# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
#   "numpy",
#   "scipy",
# ]
# ///

import csv
from pathlib import Path
from datetime import datetime
from math import cos, radians

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np

from scipy.ndimage import gaussian_filter
from scipy.interpolate import RegularGridInterpolator


DATA = Path("data/ThermochronTracking Elephants Kruger 2007.csv")
OUTPUT = Path("out/tracking-landscape-v6.png")

EARTH_KM_PER_DEGREE = 111.32


# ------------------------------------------------------------
# DATA
# ------------------------------------------------------------

def parse_time(timestamp):
    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )


def read_tracks():
    tracks = {}

    with DATA.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if not row["location-long"] or not row["location-lat"]:
                continue

            elephant_id = row["individual-local-identifier"]

            tracks.setdefault(elephant_id, []).append(
                {
                    "time": parse_time(row["timestamp"]),
                    "longitude": float(row["location-long"]),
                    "latitude": float(row["location-lat"]),
                }
            )

    for elephant_id in tracks:
        tracks[elephant_id].sort(
            key=lambda point: point["time"]
        )

    return tracks


def calculate_reference_point(tracks):
    longitudes = []
    latitudes = []

    for points in tracks.values():
        for point in points:
            longitudes.append(point["longitude"])
            latitudes.append(point["latitude"])

    return (
        sum(longitudes) / len(longitudes),
        sum(latitudes) / len(latitudes),
    )


def to_local_km(
    longitude,
    latitude,
    reference_lon,
    reference_lat,
):
    x = (
        (longitude - reference_lon)
        * EARTH_KM_PER_DEGREE
        * cos(radians(reference_lat))
    )

    y = (
        (latitude - reference_lat)
        * EARTH_KM_PER_DEGREE
    )

    return x, y


def build_visual_data(
    tracks,
    reference_lon,
    reference_lat,
):
    all_x = []
    all_y = []
    valid_segments = []

    start_time = None
    end_time = None

    for elephant_id in sorted(tracks):
        projected = []

        for point in tracks[elephant_id]:
            x, y = to_local_km(
                point["longitude"],
                point["latitude"],
                reference_lon,
                reference_lat,
            )

            projected.append(
                {
                    "time": point["time"],
                    "x": x,
                    "y": y,
                }
            )

            all_x.append(x)
            all_y.append(y)

            if start_time is None or point["time"] < start_time:
                start_time = point["time"]

            if end_time is None or point["time"] > end_time:
                end_time = point["time"]

        for i in range(1, len(projected)):
            previous = projected[i - 1]
            current = projected[i]

            gap_minutes = (
                current["time"] - previous["time"]
            ).total_seconds() / 60

            if 29 <= gap_minutes <= 31:
                valid_segments.append(
                    [
                        (
                            previous["x"],
                            previous["y"],
                        ),
                        (
                            current["x"],
                            current["y"],
                        ),
                    ]
                )

    return (
        np.array(all_x),
        np.array(all_y),
        valid_segments,
        start_time,
        end_time,
    )


# ------------------------------------------------------------
# GPS DENSITY → DATA TERRAIN
# ------------------------------------------------------------

def build_density_terrain(
    x,
    y,
    bins=300,
):
    margin_x = (x.max() - x.min()) * 0.04
    margin_y = (y.max() - y.min()) * 0.04

    x_min = x.min() - margin_x
    x_max = x.max() + margin_x

    y_min = y.min() - margin_y
    y_max = y.max() + margin_y

    density, x_edges, y_edges = np.histogram2d(
        x,
        y,
        bins=bins,
        range=[
            [x_min, x_max],
            [y_min, y_max],
        ],
    )

    density = density.T

    # Broad smoothing creates continuous spatial structure,
    # but the result will be rendered as POINTS, not a surface.
    terrain = gaussian_filter(
        density,
        sigma=5.0,
    )

    terrain = np.log1p(terrain)

    if terrain.max() > 0:
        terrain /= terrain.max()

    # Reveal middle-density areas as part of the terrain.
    terrain = terrain ** 0.58

    x_centres = (
        x_edges[:-1] + x_edges[1:]
    ) / 2

    y_centres = (
        y_edges[:-1] + y_edges[1:]
    ) / 2

    X, Y = np.meshgrid(
        x_centres,
        y_centres,
    )

    return (
        terrain,
        X,
        Y,
        x_centres,
        y_centres,
    )


def build_height_interpolator(
    x_centres,
    y_centres,
    terrain,
):
    return RegularGridInterpolator(
        (
            y_centres,
            x_centres,
        ),
        terrain,
        bounds_error=False,
        fill_value=0,
    )


# ------------------------------------------------------------
# 2.5D PROJECTION
# ------------------------------------------------------------

def project_25d(
    x,
    y,
    z,
):
    """
    Convert data-space x/y/z into a 2D oblique projection.

    x/y = real relative GPS position.
    z   = relative tracking density, NOT elevation.
    """

    angle = np.radians(-8)

    rotated_x = (
        x * np.cos(angle)
        - y * np.sin(angle)
    )

    rotated_y = (
        x * np.sin(angle)
        + y * np.cos(angle)
    )

    # Keep strong map readability.
    screen_x = rotated_x

    # Compress north/south direction slightly,
    # then lift higher-density points upward.
    screen_y = (
        rotated_y * 0.72
        + z * 24.0
    )

    return screen_x, screen_y


def prepare_tracking_projection(
    all_x,
    all_y,
    valid_segments,
    height_interpolator,
):
    # --------------------------------------------------------
    # GPS points
    # --------------------------------------------------------

    point_coordinates = np.column_stack(
        [
            all_y,
            all_x,
        ]
    )

    point_z = height_interpolator(
        point_coordinates
    )

    point_screen_x, point_screen_y = project_25d(
        all_x,
        all_y,
        point_z,
    )

    # --------------------------------------------------------
    # Track segments
    # --------------------------------------------------------

    segment_array = np.array(
        valid_segments,
        dtype=float,
    )

    flat_xy = segment_array.reshape(
        -1,
        2,
    )

    segment_coordinates = np.column_stack(
        [
            flat_xy[:, 1],
            flat_xy[:, 0],
        ]
    )

    flat_z = height_interpolator(
        segment_coordinates
    )

    flat_screen_x, flat_screen_y = project_25d(
        flat_xy[:, 0],
        flat_xy[:, 1],
        flat_z,
    )

    projected_segments = np.column_stack(
        [
            flat_screen_x,
            flat_screen_y,
        ]
    ).reshape(
        -1,
        2,
        2,
    )

    return (
        point_screen_x,
        point_screen_y,
        point_z,
        projected_segments,
    )


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

def add_interface(
    fig,
    elephant_count,
    observation_count,
    segment_count,
    start_time,
    end_time,
):
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
        "ELEPHANT MOVEMENT / KRUGER / 2007—2009",
        color="#61716d",
        fontsize=6.8,
        ha="left",
        va="top",
    )

    info = (
        f"TRACKED INDIVIDUALS   {elephant_count:02d}\n"
        f"GPS OBSERVATIONS      {observation_count:,}\n"
        f"30 MIN SEGMENTS       {segment_count:,}\n"
        f"STUDY START           {start_time:%Y.%m.%d}\n"
        f"STUDY END             {end_time:%Y.%m.%d}"
    )

    fig.text(
        0.815,
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
        0.087,
        "XY POSITION      GPS LOCATION\n"
        "POINT HEIGHT     RELATIVE GPS OBSERVATION DENSITY\n"
        "TRACK LINES      CONSECUTIVE 29–31 MIN OBSERVATIONS",
        color="#52615d",
        fontsize=5.2,
        family="monospace",
        linespacing=1.55,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.045,
        0.048,
        "TRACKING RECORDS FORM THE LANDSCAPE",
        color="#667671",
        fontsize=6,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.955,
        0.048,
        "NO BASEMAP  /  POINT HEIGHT REPRESENTS TRACKING DENSITY, NOT ELEVATION",
        color="#495753",
        fontsize=5.2,
        family="monospace",
        ha="right",
        va="bottom",
    )


# ------------------------------------------------------------
# DRAW
# ------------------------------------------------------------

def draw_landscape(tracks):
    reference_lon, reference_lat = calculate_reference_point(
        tracks
    )

    (
        all_x,
        all_y,
        valid_segments,
        start_time,
        end_time,
    ) = build_visual_data(
        tracks,
        reference_lon,
        reference_lat,
    )

    (
        terrain,
        X,
        Y,
        x_centres,
        y_centres,
    ) = build_density_terrain(
        all_x,
        all_y,
    )

    height_interpolator = build_height_interpolator(
        x_centres,
        y_centres,
        terrain,
    )

    (
        point_screen_x,
        point_screen_y,
        point_z,
        projected_segments,
    ) = prepare_tracking_projection(
        all_x,
        all_y,
        valid_segments,
        height_interpolator,
    )

    # --------------------------------------------------------
    # TERRAIN GRID POINTS
    # --------------------------------------------------------

    terrain_mask = terrain > 0.075

    terrain_x = X[terrain_mask]
    terrain_y = Y[terrain_mask]
    terrain_z = terrain[terrain_mask]

    (
        terrain_screen_x,
        terrain_screen_y,
    ) = project_25d(
        terrain_x,
        terrain_y,
        terrain_z,
    )

    fig = plt.figure(
        figsize=(16, 9),
        facecolor="#06090a",
    )

    ax = fig.add_axes(
        [0.08, 0.035, 0.84, 0.92]
    )

    ax.set_facecolor("#06090a")

    # --------------------------------------------------------
    # LAYER 1 — POINT-GRID DATA TERRAIN
    #
    # No surface.
    # No glow.
    # Every visible terrain mark is an individual grid point.
    # --------------------------------------------------------

    terrain_sizes = (
        0.4
        + terrain_z * 2.0
    )

    ax.scatter(
        terrain_screen_x,
        terrain_screen_y,
        s=terrain_sizes,
        c=terrain_z,
        cmap="Greys",
        vmin=0,
        vmax=1,
        alpha=0.52,
        linewidths=0,
        zorder=1,
    )

    # --------------------------------------------------------
    # LAYER 2 — REAL TRAJECTORY FRAGMENTS
    # --------------------------------------------------------

    track_collection = LineCollection(
        projected_segments,
        colors="#8fa29c",
        linewidths=0.13,
        alpha=0.055,
        zorder=2,
    )

    ax.add_collection(
        track_collection
    )

    # --------------------------------------------------------
    # LAYER 3 — ALL REAL GPS OBSERVATIONS
    # --------------------------------------------------------

    ax.scatter(
        point_screen_x,
        point_screen_y,
        s=0.10,
        color="#dfe8e4",
        alpha=0.12,
        linewidths=0,
        zorder=3,
    )

    # Slightly emphasise locations where density is higher.
    high_density = point_z > 0.55

    ax.scatter(
        point_screen_x[high_density],
        point_screen_y[high_density],
        s=0.18,
        color="#e8efec",
        alpha=0.15,
        linewidths=0,
        zorder=4,
    )

    # --------------------------------------------------------
    # FRAME
    # --------------------------------------------------------

    all_screen_x = np.concatenate(
        [
            terrain_screen_x,
            point_screen_x,
        ]
    )

    all_screen_y = np.concatenate(
        [
            terrain_screen_y,
            point_screen_y,
        ]
    )

    x_min = all_screen_x.min()
    x_max = all_screen_x.max()

    y_min = all_screen_y.min()
    y_max = all_screen_y.max()

    x_pad = (x_max - x_min) * 0.035
    y_pad = (y_max - y_min) * 0.035

    ax.set_xlim(
        x_min - x_pad,
        x_max + x_pad,
    )

    ax.set_ylim(
        y_min - y_pad,
        y_max + y_pad,
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    ax.axis("off")

    add_interface(
        fig,
        elephant_count=len(tracks),
        observation_count=len(all_x),
        segment_count=len(valid_segments),
        start_time=start_time,
        end_time=end_time,
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

    print("TRACKING LANDSCAPE — POINT GRID TERRAIN")
    print("---------------------------------------")
    print("Tracked individuals:", len(tracks))
    print("GPS observations:", len(all_x))
    print("Valid 29–31 min segments:", len(valid_segments))
    print("Terrain grid points:", len(terrain_x))
    print(
        "Terrain height meaning:",
        "relative GPS observation density",
    )
    print("Saved:", OUTPUT)

    plt.show()


def main():
    tracks = read_tracks()
    draw_landscape(tracks)


if __name__ == "__main__":
    main()