# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
# ]
# ///

import csv
from pathlib import Path
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from statistics import median

import matplotlib.pyplot as plt

DATA = Path("data/ThermochronTracking Elephants Kruger 2007.csv")
OUTPUT = Path("out/monthly-daily-heatmap.png")


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
    Build comparable ~30-minute movement steps.

    Movebank timestamps are stored in UTC.
    Kruger local time is UTC+2.
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

            midpoint_utc = previous_time + (
                current_time - previous_time
            ) / 2

            midpoint_local = midpoint_utc + timedelta(hours=2)

            valid_steps.append(
                {
                    "elephant": elephant_id,
                    "month": midpoint_local.month,
                    "hour": midpoint_local.hour,
                    "displacement_km": displacement,
                }
            )

    return valid_steps


def build_heatmap(valid_steps):
    """
    Create 12 × 24 bins:
    month × local hour.
    """
    bins = {}

    for month in range(1, 13):
        bins[month] = {}

        for hour in range(24):
            bins[month][hour] = []

    for step in valid_steps:
        bins[step["month"]][step["hour"]].append(
            step["displacement_km"]
        )

    heatmap = []
    counts = []

    for month in range(1, 13):
        movement_row = []
        count_row = []

        for hour in range(24):
            values = bins[month][hour]

            if values:
                movement_row.append(median(values))
                count_row.append(len(values))
            else:
                movement_row.append(float("nan"))
                count_row.append(0)

        heatmap.append(movement_row)
        counts.append(count_row)

    return heatmap, counts


def plot_heatmap(heatmap):
    month_labels = [
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec",
    ]

    fig, ax = plt.subplots(
        figsize=(13, 7)
    )

    image = ax.imshow(
        heatmap,
        aspect="auto",
        origin="upper",
        interpolation="nearest",
    )

    ax.set_xticks(range(24))
    ax.set_xticklabels(range(24))

    ax.set_yticks(range(12))
    ax.set_yticklabels(month_labels)

    ax.set_xlabel(
        "Local time in Kruger National Park (hour)"
    )

    ax.set_ylabel(
        "Calendar month"
    )

    ax.set_title(
        "Elephant Movement Rhythm Across Month and Time of Day"
    )

    colorbar = fig.colorbar(
        image,
        ax=ax,
    )

    colorbar.set_label(
        "Median ~30-min displacement (km)"
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

    heatmap, counts = build_heatmap(valid_steps)

    print("MONTH × HOUR MOVEMENT HEATMAP")
    print("-----------------------------")
    print("Valid ~30-minute steps:", len(valid_steps))

    print("\nMonthly daily movement peaks")
    print("Month | Peak hour | Median displacement | Steps")

    for month in range(1, 13):
        row = heatmap[month - 1]

        peak_hour = max(
            range(24),
            key=lambda hour: row[hour],
        )

        print(
            f"{month:02d}",
            "|",
            f"{peak_hour:02d}:00",
            "|",
            round(row[peak_hour], 4),
            "km |",
            counts[month - 1][peak_hour],
        )

    print("\nSmallest bin size:", min(
        count
        for row in counts
        for count in row
        if count > 0
    ))

    print("Largest bin size:", max(
        count
        for row in counts
        for count in row
    ))

    plot_heatmap(heatmap)


if __name__ == "__main__":
    main()