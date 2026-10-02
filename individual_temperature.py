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
OUTPUT = Path("out/individual-temperature.png")


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


def build_individual_bins(valid_steps):
    """
    Group displacement values by elephant
    and by 1-degree temperature bin.
    """
    individual_bins = {}

    for step in valid_steps:
        elephant_id = step["elephant"]
        temperature_bin = round(step["temperature"])

        if elephant_id not in individual_bins:
            individual_bins[elephant_id] = {}

        if temperature_bin not in individual_bins[elephant_id]:
            individual_bins[elephant_id][temperature_bin] = []

        individual_bins[elephant_id][temperature_bin].append(
            step["displacement_km"]
        )

    return individual_bins


def plot_individuals(individual_bins):
    elephant_ids = sorted(individual_bins.keys())

    # Same axes for every elephant so comparisons are fair.
    fig, axes = plt.subplots(
        4,
        4,
        figsize=(15, 12),
        sharex=True,
        sharey=True,
    )

    axes = axes.flatten()

    for index, elephant_id in enumerate(elephant_ids):
        ax = axes[index]
        bins = individual_bins[elephant_id]

        temperatures = []
        median_displacements = []

        for temperature in sorted(bins):
            values = bins[temperature]

            # Very small bins can create misleading spikes.
            # We only draw bins with at least 20 movement steps.
            if len(values) < 20:
                continue

            temperatures.append(temperature)
            median_displacements.append(
                median(values)
            )

        ax.plot(
            temperatures,
            median_displacements,
            marker="o",
            markersize=3,
            linewidth=1.3,
        )

        ax.set_title(elephant_id)
        ax.grid(alpha=0.2)

    # Hide the two unused panels.
    for index in range(len(elephant_ids), len(axes)):
        axes[index].set_visible(False)

    fig.supxlabel("External temperature (°C)")
    fig.supylabel("Median ~30-min displacement (km)")

    fig.suptitle(
        "Temperature × Movement by Individual Elephant",
        fontsize=16,
    )

    plt.tight_layout(
        rect=[0.03, 0.03, 1, 0.96]
    )

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
    individual_bins = build_individual_bins(valid_steps)

    print("INDIVIDUAL TEMPERATURE × MOVEMENT")
    print("---------------------------------")
    print("Valid ~30-minute steps:", len(valid_steps))
    print("Elephants:", len(individual_bins))

    print("\nTEMPERATURE COVERAGE")

    for elephant_id in sorted(individual_bins):
        bins = individual_bins[elephant_id]

        usable_temperatures = []

        for temperature in sorted(bins):
            if len(bins[temperature]) >= 20:
                usable_temperatures.append(temperature)

        if usable_temperatures:
            print(
                elephant_id,
                "|",
                min(usable_temperatures),
                "to",
                max(usable_temperatures),
                "C",
            )

    plot_individuals(individual_bins)


if __name__ == "__main__":
    main()