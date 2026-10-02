# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
# ]
# ///

import csv
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


DATA = Path("data/ThermochronTracking Elephants Kruger 2007.csv")
OUTPUT = Path("out/tracking-landscape-v2.png")


def parse_time(timestamp):
    """Convert Movebank timestamp text into datetime."""
    return datetime.fromisoformat(
        timestamp.replace("Z", "+00:00")
    )


def read_tracks():
    """Read GPS locations and group them by elephant."""
    tracks = {}

    with DATA.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if not row["location-long"] or not row["location-lat"]:
                continue

            elephant_id = row["individual-local-identifier"]

            if elephant_id not in tracks:
                tracks[elephant_id] = []

            tracks[elephant_id].append(
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


def build_valid_segments(points):
    """
    Connect only consecutive observations approximately
    30 minutes apart.

    Longer gaps remain visible as GPS observations,
    but are not drawn as known movement paths.
    """
    segments = []

    for i in range(1, len(points)):
        previous = points[i - 1]
        current = points[i]

        gap_minutes = (
            current["time"] - previous["time"]
        ).total_seconds() / 60

        if 29 <= gap_minutes <= 31:
            segments.append(
                [
                    (
                        previous["longitude"],
                        previous["latitude"],
                    ),
                    (
                        current["longitude"],
                        current["latitude"],
                    ),
                ]
            )

    return segments


def draw_tracking_landscape(tracks):
    fig, ax = plt.subplots(
        figsize=(12, 12),
        facecolor="#07090b",
    )

    ax.set_facecolor("#07090b")

    total_points = 0
    total_segments = 0

    for elephant_id in sorted(tracks):
        points = tracks[elephant_id]

        longitudes = [
            point["longitude"]
            for point in points
        ]

        latitudes = [
            point["latitude"]
            for point in points
        ]

        total_points += len(points)

        # Only trustworthy ~30-minute connections.
        segments = build_valid_segments(points)
        total_segments += len(segments)

        # Layer 1:
        # faint movement structure
        line_collection = LineCollection(
            segments,
            colors="#b9c7c2",
            linewidths=0.22,
            alpha=0.075,
            zorder=1,
        )

        ax.add_collection(line_collection)

        # Layer 2:
        # every real GPS observation
        ax.scatter(
            longitudes,
            latitudes,
            s=0.32,
            color="#e2ebe7",
            alpha=0.09,
            linewidths=0,
            zorder=2,
        )

    # Preserve real geographic proportions.
    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    # Let Matplotlib calculate limits from all data.
    ax.autoscale()

    # The data itself forms the landscape.
    ax.axis("off")

    plt.tight_layout(
        pad=0.15
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        OUTPUT,
        dpi=300,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
        pad_inches=0.05,
    )

    print("TRACKING LANDSCAPE V2")
    print("---------------------")
    print("Elephants:", len(tracks))
    print("GPS observations:", total_points)
    print("Valid 29–31 min trajectory segments:", total_segments)
    print("Saved:", OUTPUT)

    plt.show()


def main():
    tracks = read_tracks()
    draw_tracking_landscape(tracks)


if __name__ == "__main__":
    main()