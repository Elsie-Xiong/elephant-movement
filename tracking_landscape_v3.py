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
OUTPUT = Path("out/tracking-landscape-v3.png")

EARTH_KM_PER_DEGREE = 111.32


def parse_time(timestamp):
    """Convert Movebank timestamp text into datetime."""
    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )


def read_tracks():
    """Read GPS observations and group them by elephant."""
    tracks = {}

    with DATA.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if not row["location-long"] or not row["location-lat"]:
                continue

            elephant_id = row["individual-local-identifier"]

            point = {
                "time": parse_time(row["timestamp"]),
                "longitude": float(row["location-long"]),
                "latitude": float(row["location-lat"]),
            }

            tracks.setdefault(elephant_id, []).append(point)

    for elephant_id in tracks:
        tracks[elephant_id].sort(
            key=lambda point: point["time"]
        )

    return tracks


def calculate_reference_point(tracks):
    """
    Calculate one central geographic reference point.
    It is used only to convert longitude/latitude into local kilometres.
    """
    all_longitudes = []
    all_latitudes = []

    for points in tracks.values():
        for point in points:
            all_longitudes.append(point["longitude"])
            all_latitudes.append(point["latitude"])

    reference_lon = sum(all_longitudes) / len(all_longitudes)
    reference_lat = sum(all_latitudes) / len(all_latitudes)

    return reference_lon, reference_lat


def to_local_km(longitude, latitude, reference_lon, reference_lat):
    """
    Convert longitude/latitude to approximate local x/y distances in km.

    This keeps east-west and north-south distances visually comparable
    at the latitude of the study area.
    """
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
    Keep every real GPS observation as a point.

    Draw trajectory segments only when consecutive observations
    are approximately 30 minutes apart.
    """
    all_x = []
    all_y = []
    valid_segments = []

    start_time = None
    end_time = None

    for elephant_id in sorted(tracks):
        points = tracks[elephant_id]

        projected = []

        for point in points:
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


def add_monitoring_interface(
    fig,
    elephant_count,
    observation_count,
    segment_count,
    start_time,
    end_time,
):
    """Add restrained scientific-monitoring information."""

    fig.text(
        0.055,
        0.925,
        "LIVING RHYTHMS",
        color="#e6efec",
        fontsize=17,
        fontweight="medium",
        ha="left",
        va="top",
    )

    fig.text(
        0.055,
        0.892,
        "ELEPHANT MOVEMENT / KRUGER / 2007—2009",
        color="#6f817d",
        fontsize=7.5,
        ha="left",
        va="top",
    )

    info = (
        f"TRACKED INDIVIDUALS    {elephant_count:02d}\n"
        f"GPS OBSERVATIONS       {observation_count:,}\n"
        f"30 MIN SEGMENTS        {segment_count:,}\n"
        f"START                  {start_time:%Y.%m.%d}\n"
        f"END                    {end_time:%Y.%m.%d}"
    )

    fig.text(
        0.785,
        0.915,
        info,
        color="#82928e",
        fontsize=7,
        family="monospace",
        linespacing=1.65,
        ha="left",
        va="top",
    )

    fig.text(
        0.055,
        0.075,
        "MOVEMENT DENSITY BECOMES LANDSCAPE",
        color="#60716d",
        fontsize=6.5,
        ha="left",
        va="bottom",
    )

    fig.text(
        0.945,
        0.075,
        "ALL LOCATIONS SHOWN  /  PATHS CONNECTED ONLY AT 29–31 MIN INTERVALS",
        color="#52615e",
        fontsize=5.8,
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

    # 16:9 composition for the later animated version.
    fig = plt.figure(
        figsize=(16, 9),
        facecolor="#070a0b",
    )

    # Leave breathing space for monitoring information.
    ax = fig.add_axes(
        [0.12, 0.10, 0.70, 0.80]
    )

    ax.set_facecolor("#070a0b")

    # ---------------------------------------------------------
    # LAYER 1 — ecological memory
    #
    # Every GPS observation remains visible.
    # Dense areas naturally become brighter through overlap.
    # ---------------------------------------------------------
    ax.scatter(
        all_x,
        all_y,
        s=0.45,
        color="#9eaaa6",
        alpha=0.035,
        linewidths=0,
        zorder=1,
    )

    # ---------------------------------------------------------
    # LAYER 2 — tracking structure
    #
    # Only ~30 minute consecutive observations are connected.
    # ---------------------------------------------------------
    historical_tracks = LineCollection(
        valid_segments,
        colors="#b6c4bf",
        linewidths=0.18,
        alpha=0.055,
        zorder=2,
    )

    ax.add_collection(historical_tracks)

    # ---------------------------------------------------------
    # LAYER 3 — micro observations
    #
    # A second, sharper point layer means that when the viewer
    # looks closely, the "landscape" resolves into tracking data.
    # ---------------------------------------------------------
    ax.scatter(
        all_x,
        all_y,
        s=0.16,
        color="#e3eeea",
        alpha=0.16,
        linewidths=0,
        zorder=3,
    )

    # Real local-kilometre coordinates now share one scale.
    ax.set_aspect("equal", adjustable="box")

    ax.autoscale()

    # Small spatial breathing room.
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    x_padding = (x_max - x_min) * 0.04
    y_padding = (y_max - y_min) * 0.04

    ax.set_xlim(
        x_min - x_padding,
        x_max + x_padding,
    )

    ax.set_ylim(
        y_min - y_padding,
        y_max + y_padding,
    )

    ax.axis("off")

    add_monitoring_interface(
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
        pad_inches=0.08,
    )

    print("TRACKING LANDSCAPE V3")
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