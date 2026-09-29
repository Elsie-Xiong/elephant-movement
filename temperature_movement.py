# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
# ]
# ///

import csv
from pathlib import Path
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from statistics import median

import matplotlib.pyplot as plt

DATA = Path("data/ThermochronTracking Elephants Kruger 2007.csv")
OUTPUT = Path("out/temperature-movement.png")


def distance_km(lat1, lon1, lat2, lon2):
    """Calculate straight-line displacement between two GPS points."""
    earth_radius = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius * c


def read_data():
    rows = []

    with DATA.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    return rows


def group_by_elephant(rows):
    """Group records by elephant ID."""
    elephant_rows = {}

    for row in rows:
        elephant_id = row["individual-local-identifier"]

        if elephant_id not in elephant_rows:
            elephant_rows[elephant_id] = []

        elephant_rows[elephant_id].append(row)

    return elephant_rows


def build_valid_steps(elephant_rows):
    """
    Build comparable movement steps using consecutive
    GPS records approximately 30 minutes apart.
    """
    valid_steps = []

    for elephant_id in sorted(elephant_rows):
        rows = sorted(
            elephant_rows[elephant_id],
            key=lambda row: row["timestamp"],
        )

        for i in range(1, len(rows)):
            previous = rows[i - 1]
            current = rows[i]

            previous_time = datetime.fromisoformat(
                previous["timestamp"].replace("Z", "+00:00")
            )

            current_time = datetime.fromisoformat(
                current["timestamp"].replace("Z", "+00:00")
            )

            gap_minutes = (
                current_time - previous_time
            ).total_seconds() / 60

            if not 29 <= gap_minutes <= 31:
                continue

            if (
                not previous["external-temperature"]
                or not current["external-temperature"]
            ):
                continue

            displacement = distance_km(
                float(previous["location-lat"]),
                float(previous["location-long"]),
                float(current["location-lat"]),
                float(current["location-long"]),
            )

            previous_temperature = float(
                previous["external-temperature"]
            )

            current_temperature = float(
                current["external-temperature"]
            )

            average_temperature = (
                previous_temperature + current_temperature
            ) / 2

            valid_steps.append(
                {
                    "elephant": elephant_id,
                    "temperature": average_temperature,
                    "displacement_km": displacement,
                }
            )

    return valid_steps


def make_temperature_bins(valid_steps):
    """
    Group movement steps into 1-degree temperature bins.
    """
    bins = {}

    for step in valid_steps:
        temperature_bin = round(step["temperature"])

        if temperature_bin not in bins:
            bins[temperature_bin] = []

        bins[temperature_bin].append(
            step["displacement_km"]
        )

    return bins


def plot_temperature_movement(bins):
    temperatures = sorted(bins.keys())

    median_displacements = []
    counts = []

    for temperature in temperatures:
        values = bins[temperature]

        median_displacements.append(
            median(values)
        )

        counts.append(
            len(values)
        )

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(11, 8),
        sharex=True,
        height_ratios=[3, 1],
    )

    # Top: median movement
    ax1.plot(
        temperatures,
        median_displacements,
        marker="o",
    )

    ax1.set_ylabel(
        "Median ~30-min displacement (km)"
    )

    ax1.set_title(
        "Elephant Movement Across External Temperature"
    )

    ax1.grid(
        alpha=0.25
    )

    # Bottom: number of observations
    ax2.bar(
        temperatures,
        counts,
    )

    ax2.set_xlabel(
        "External temperature (°C)"
    )

    ax2.set_ylabel(
        "Steps"
    )

    ax2.grid(
        axis="y",
        alpha=0.25,
    )

    fig.suptitle(
        "14 tracked elephants, Kruger National Park",
        fontsize=10,
        y=0.94,
    )

    plt.tight_layout()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        OUTPUT,
        dpi=200,
        bbox_inches="tight",
    )

    plt.show()


def main():
    rows = read_data()
    elephant_rows = group_by_elephant(rows)
    valid_steps = build_valid_steps(elephant_rows)
    bins = make_temperature_bins(valid_steps)

    print("TEMPERATURE × MOVEMENT")
    print("----------------------")
    print("Valid steps:", len(valid_steps))
    print("Temperature bins:", len(bins))

    print("\nTemperature | Median displacement | Steps")

    for temperature in sorted(bins):
        values = bins[temperature]

        print(
            temperature,
            "C |",
            round(median(values), 4),
            "km |",
            len(values),
        )

    plot_temperature_movement(bins)


if __name__ == "__main__":
    main()