# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///

"""
Read the raw elephant tracking data and make a first exploratory picture.

Run:
    uv run plot.py
"""

import csv
from pathlib import Path

import matplotlib.pyplot as plt


FILE = "ThermochronTracking Elephants Kruger 2007.csv"
PICTURE = "first-elephant-movement.png"

HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"


def read_elephants(path):
    """Read GPS locations and group them by elephant ID."""
    elephants = {}

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            elephant_id = row["individual-local-identifier"]
            longitude = float(row["location-long"])
            latitude = float(row["location-lat"])

            if elephant_id not in elephants:
                elephants[elephant_id] = []

            elephants[elephant_id].append((longitude, latitude))

    return elephants


def draw_path(ax, elephant_id, points):
    """Draw the movement path of one elephant."""
    longitudes = [point[0] for point in points]
    latitudes = [point[1] for point in points]

    ax.plot(
        longitudes,
        latitudes,
        linewidth=0.5,
        alpha=0.65,
        label=elephant_id,
    )


def main():
    elephants = read_elephants(DATA)

    print(f"{len(elephants)} elephants found")

    for elephant_id, points in elephants.items():
        print(f"{elephant_id}: {len(points)} locations")

    fig, ax = plt.subplots(figsize=(9, 11))

    for elephant_id, points in elephants.items():
        draw_path(ax, elephant_id, points)

    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_title("Elephant movement — Kruger National Park, 2007–2009")
    ax.legend(fontsize=7)
    ax.set_aspect("equal", adjustable="box")

    OUT.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / PICTURE, dpi=150)

    print(f"saved {OUT / PICTURE}")

    plt.show()


if __name__ == "__main__":
    main()