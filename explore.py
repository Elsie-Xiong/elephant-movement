# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import csv
from pathlib import Path
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from collections import Counter

DATA = Path("data/ThermochronTracking Elephants Kruger 2007.csv")


def distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in kilometres."""
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


def get_time_gap_minutes(rows):
    """Return time gaps in minutes between consecutive records."""
    sorted_rows = sorted(rows, key=lambda row: row["timestamp"])
    gaps = []

    for i in range(1, len(sorted_rows)):
        previous_time = datetime.fromisoformat(
            sorted_rows[i - 1]["timestamp"].replace("Z", "+00:00")
        )
        current_time = datetime.fromisoformat(
            sorted_rows[i]["timestamp"].replace("Z", "+00:00")
        )

        gap_minutes = (
            current_time - previous_time
        ).total_seconds() / 60

        gaps.append(gap_minutes)

    return gaps


def get_spatial_range(rows):
    """Return the latitude and longitude range of one elephant."""
    latitudes = []
    longitudes = []

    for row in rows:
        latitudes.append(float(row["location-lat"]))
        longitudes.append(float(row["location-long"]))

    return (
        min(latitudes),
        max(latitudes),
        min(longitudes),
        max(longitudes),
    )


def group_by_elephant(rows):
    """Group all records by elephant ID."""
    elephant_rows = {}

    for row in rows:
        elephant_id = row["individual-local-identifier"]

        if elephant_id not in elephant_rows:
            elephant_rows[elephant_id] = []

        elephant_rows[elephant_id].append(row)

    return elephant_rows


def main():
    rows = read_data()
    elephant_rows = group_by_elephant(rows)

    print("Total records:", len(rows))
    print("Elephants:", len(elephant_rows))

    # Basic dataset information
    temperatures = []
    timestamps = []

    for row in rows:
        if row["external-temperature"]:
            temperatures.append(float(row["external-temperature"]))

        if row["timestamp"]:
            timestamps.append(
                datetime.fromisoformat(
                    row["timestamp"].replace("Z", "+00:00")
                )
            )

    print("Start:", min(timestamps))
    print("End:", max(timestamps))
    print("Temperature min:", min(temperatures))
    print("Temperature max:", max(temperatures))

    # Compare record counts
    print("\nRecords per elephant:")

    for elephant_id in sorted(elephant_rows):
        print(
            elephant_id,
            len(elephant_rows[elephant_id]),
        )

    # Compare spatial ranges
    print("\nSpatial range per elephant:")

    for elephant_id in sorted(elephant_rows):
        spatial_range = get_spatial_range(
            elephant_rows[elephant_id]
        )

        lat_span = spatial_range[1] - spatial_range[0]
        lon_span = spatial_range[3] - spatial_range[2]

        print(
            elephant_id,
            "latitude span:",
            round(lat_span, 4),
            "longitude span:",
            round(lon_span, 4),
        )

    # Check how many intervals are approximately 30 minutes
    print("\n29-31 minute sampling per elephant:")

    for elephant_id in sorted(elephant_rows):
        gaps = get_time_gap_minutes(
            elephant_rows[elephant_id]
        )

        valid_count = 0

        for gap in gaps:
            if 29 <= gap <= 31:
                valid_count += 1

        total_count = len(gaps)

        if total_count > 0:
            percentage = valid_count / total_count * 100
        else:
            percentage = 0

        print(
            elephant_id,
            "valid:",
            valid_count,
            "/",
            total_count,
            "=",
            round(percentage, 2),
            "%",
        )

    # Find the most common sampling intervals for each elephant
    print("\nMost common sampling intervals per elephant:")

    for elephant_id in sorted(elephant_rows):
        gaps = get_time_gap_minutes(
            elephant_rows[elephant_id]
        )

        rounded_gaps = []

        for gap in gaps:
            rounded_gaps.append(round(gap))

        gap_counts = Counter(rounded_gaps)

        most_common = gap_counts.most_common(6)

        print("\n" + elephant_id)

        for gap_minutes, count in most_common:
            percentage = count / len(gaps) * 100

            print(
                gap_minutes,
                "minutes:",
                count,
                "(" + str(round(percentage, 2)) + "%)",
            )


if __name__ == "__main__":
    main()