# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
# ]
# ///

import csv
from pathlib import Path
from datetime import datetime
from math import cos, radians

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


DATA = Path("data/ThermochronTracking Elephants Kruger 2007.csv")
OUTPUT = Path("out/tracking-landscape-v4.png")

EARTH_KM_PER_DEGREE = 111.32


def parse_time(timestamp):
    """Convert Movebank timestamp text into datetime."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def read_tracks():
    """Read GPS observations and group them by elephant."""
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
    """Calculate the geographic centre used for local projection."""
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


def to_local_km(longitude, latitude, reference_lon, reference_lat):
    """Convert longitude/latitude to approximate local kilometres."""
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


def build_visual_data(tracks, reference_lon, reference_lat):
    """
    Keep all GPS observations.

    Connect only consecutive observations approximately
    30 minutes apart.
    """
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
                        (previous["x"], previous["y"]),
                        (current["x"], current["y"]),
                    ]
                )

    return all_x, all_y, valid_segments, start_time, end_time


def add_interface(
    fig,
    elephant_count,
    observation_count,
    segment_count,
    start_time,
    end_time,
):
    """Add a quieter monitoring interface around the landscape."""

    # Main identity
    fig.text(
        0.045,
        0.935,
        "LIVING RHYTHMS",
        color="#dbe5e1",
        fontsize=15,
        fontweight="medium",
        ha="left",
        va="top",
    )

    fig.text(
        0.045,
        0.902,
        "ELEPHANT MOVEMENT / KRUGER / 2007—2009",
        color="#667773",
        fontsize=6.8,
        ha="left",
        va="top",
    )

    # Scientific metadata
    info = (
        f"TRACKED INDIVIDUALS   {elephant_count:02d}\n"
        f"GPS OBSERVATIONS      {observation_count:,}\n"
        f"30 MIN SEGMENTS       {segment_count:,}\n"
        f"STUDY START           {start_time:%Y.%m.%d}\n"
        f"STUDY END             {end_time:%Y.%m.%d}"
    )

    fig.text(
        0.825,
        0.925,
        info,
        color="#687975",
        fontsize=6.4,
        family="monospace",
        linespacing=1.65,
        ha="left",
        va="top",
    )

    # Small methodological markers
    fig.text(
        0.045,
        0.060,
        "MOVEMENT DENSITY BECOMES LANDSCAPE",
        color="#53635f",
        fontsize=6,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.955,
        0.060,
        "ALL GPS LOCATIONS SHOWN  /  TRAJECTORIES CONNECTED ONLY AT 29–31 MIN",
        color="#485652",
        fontsize=5.5,
        family="monospace",
        ha="right",
        va="bottom",
    )


def draw_landscape(tracks):
    reference_lon, reference_lat = calculate_reference_point(tracks)

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

    fig = plt.figure(
        figsize=(16, 9),
        facecolor="#070a0b",
    )

    # V4 CHANGE:
    # Landscape occupies much more of the frame.
    ax = fig.add_axes(
        [0.12, 0.055, 0.76, 0.89]
    )

    ax.set_facecolor("#070a0b")

    # Layer 1 — accumulated ecological memory
    ax.scatter(
        all_x,
        all_y,
        s=0.50,
        color="#9ca9a5",
        alpha=0.038,
        linewidths=0,
        zorder=1,
    )

    # Layer 2 — valid tracking structure
    historical_tracks = LineCollection(
        valid_segments,
        colors="#b8c5c1",
        linewidths=0.19,
        alpha=0.060,
        zorder=2,
    )

    ax.add_collection(historical_tracks)

    # Layer 3 — individual GPS observations
    ax.scatter(
        all_x,
        all_y,
        s=0.17,
        color="#e1ece8",
        alpha=0.17,
        linewidths=0,
        zorder=3,
    )

    ax.set_aspect("equal", adjustable="box")
    ax.autoscale()

    # Less padding than V3 = larger visual presence.
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    x_padding = (x_max - x_min) * 0.015
    y_padding = (y_max - y_min) * 0.015

    ax.set_xlim(
        x_min - x_padding,
        x_max + x_padding,
    )

    ax.set_ylim(
        y_min - y_padding,
        y_max + y_padding,
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
        bbox_inches="tight",
        pad_inches=0.05,
    )

    print("TRACKING LANDSCAPE V4")
    print("---------------------")
    print("Tracked individuals:", len(tracks))
    print("GPS observations:", len(all_x))
    print("Valid 29–31 min segments:", len(valid_segments))
    print(
        "Reference coordinate:",
        f"{reference_lat:.5f}, {reference_lon:.5f}",
    )
    print("Study start:", start_time)
    print("Study end:", end_time)
    print("Saved:", OUTPUT)

    plt.show()


def main():
    tracks = read_tracks()
    draw_landscape(tracks)


if __name__ == "__main__":
    main()