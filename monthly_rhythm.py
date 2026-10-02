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
OUTPUT = Path("out/monthly-rhythm.png")


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

            previous_temperature = float(
                previous["external-temperature"]
            )

            current_temperature = float(
                current["external-temperature"]
            )

            average_temperature = (
                previous_temperature + current_temperature
            ) / 2

            midpoint_utc = previous_time + (
                current_time - previous_time
            ) / 2

            midpoint_local = midpoint_utc + timedelta(hours=2)

            valid_steps.append(
                {
                    "elephant": elephant_id,
                    "year": midpoint_local.year,
                    "month": midpoint_local.month,
                    "temperature": average_temperature,
                    "displacement_km": displacement,
                }
            )

    return valid_steps


def build_monthly_bins(valid_steps):
    """Group temperature and movement values by calendar month."""
    monthly = {}

    for month in range(1, 13):
        monthly[month] = {
            "temperature": [],
            "displacement": [],
            "years": set(),
        }

    for step in valid_steps:
        month = step["month"]

        monthly[month]["temperature"].append(
            step["temperature"]
        )

        monthly[month]["displacement"].append(
            step["displacement_km"]
        )

        monthly[month]["years"].add(
            step["year"]
        )

    return monthly


def plot_monthly_rhythm(monthly):
    months = list(range(1, 13))

    temperatures = []
    movements = []

    for month in months:
        temperatures.append(
            median(monthly[month]["temperature"])
        )

        movements.append(
            median(monthly[month]["displacement"])
        )

    month_labels = [
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec",
    ]

    fig, (ax1, ax2) = plt.subplots(
        2,
        1,
        figsize=(11, 8),
        sharex=True,
    )

    ax1.plot(
        months,
        temperatures,
        marker="o",
    )

    ax1.set_ylabel(
        "Median external temperature (°C)"
    )

    ax1.set_title(
        "Annual Thermal Rhythm"
    )

    ax1.grid(alpha=0.25)

    ax2.plot(
        months,
        movements,
        marker="o",
    )

    ax2.set_ylabel(
        "Median ~30-min displacement (km)"
    )

    ax2.set_xlabel(
        "Calendar month"
    )

    ax2.set_title(
        "Annual Movement Rhythm"
    )

    ax2.grid(alpha=0.25)

    ax2.set_xticks(months)
    ax2.set_xticklabels(month_labels)

    fig.suptitle(
        "Elephant Annual Rhythm: Temperature and Movement",
        fontsize=15,
    )

    plt.tight_layout(
        rect=[0, 0, 1, 0.95]
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
    monthly = build_monthly_bins(valid_steps)

    print("MONTHLY RHYTHM")
    print("--------------")
    print("Valid ~30-minute steps:", len(valid_steps))

    print(
        "\nMonth | Median temp | "
        "Median displacement | Steps | Years represented"
    )

    for month in range(1, 13):
        temperatures = monthly[month]["temperature"]
        movements = monthly[month]["displacement"]
        years = sorted(monthly[month]["years"])

        print(
            f"{month:02d}",
            "|",
            round(median(temperatures), 2),
            "C |",
            round(median(movements), 4),
            "km |",
            len(movements),
            "|",
            years,
        )

    plot_monthly_rhythm(monthly)


if __name__ == "__main__":
    main()