# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import csv
from pathlib import Path
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

DATA = Path("data/ThermochronTracking Elephants Kruger 2007.csv")


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
    Keep consecutive GPS records approximately 30 minutes apart.
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


def percentile(values, percentage):
    """Calculate a percentile without extra libraries."""

    values = sorted(values)

    position = (len(values) - 1) * percentage

    lower_index = int(position)
    upper_index = min(lower_index + 1, len(values) - 1)

    fraction = position - lower_index

    lower_value = values[lower_index]
    upper_value = values[upper_index]

    return lower_value + (
        upper_value - lower_value
    ) * fraction


def main():
    rows = read_data()
    elephant_rows = group_by_elephant(rows)
    valid_steps = build_valid_steps(elephant_rows)

    displacements = []

    for step in valid_steps:
        displacements.append(step["displacement_km"])

    print("MOVEMENT DISTRIBUTION")
    print("---------------------")

    print("Total records:", len(rows))
    print("Elephants:", len(elephant_rows))
    print("Valid ~30-minute steps:", len(valid_steps))

    print(
        "\nMean:",
        round(sum(displacements) / len(displacements), 4),
        "km",
    )

    print(
        "Median:",
        round(percentile(displacements, 0.50), 4),
        "km",
    )

    print(
        "90th percentile:",
        round(percentile(displacements, 0.90), 4),
        "km",
    )

    print(
        "95th percentile:",
        round(percentile(displacements, 0.95), 4),
        "km",
    )

    print(
        "99th percentile:",
        round(percentile(displacements, 0.99), 4),
        "km",
    )

    print(
        "99.9th percentile:",
        round(percentile(displacements, 0.999), 4),
        "km",
    )

    print(
        "Maximum:",
        round(max(displacements), 4),
        "km",
    )

def print_gps_bounds():
    """Print geographic extent and occupied 1-degree tiles."""
    latitudes = []
    longitudes = []
    tile_counts = {}

    with open(
        "data/ThermochronTracking Elephants Kruger 2007.csv",
        encoding="utf-8",
    ) as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["location-long"] and row["location-lat"]:
                lon = float(row["location-long"])
                lat = float(row["location-lat"])

                longitudes.append(lon)
                latitudes.append(lat)

                # Copernicus tiles are named by their
                # south-west 1-degree corner.
                south = int(lat // 1)
                west = int(lon // 1)

                tile = (south, west)

                tile_counts[tile] = (
                    tile_counts.get(tile, 0) + 1
                )

    print()
    print("GPS BOUNDING BOX")
    print("----------------")
    print("Latitude min:", min(latitudes))
    print("Latitude max:", max(latitudes))
    print("Longitude min:", min(longitudes))
    print("Longitude max:", max(longitudes))

    print()
    print("OCCUPIED 1-DEGREE TILES")
    print("-----------------------")

    for tile, count in sorted(tile_counts.items()):
        south, west = tile

        lat_name = (
            f"N{south:02d}"
            if south >= 0
            else f"S{abs(south):02d}"
        )

        lon_name = (
            f"E{west:03d}"
            if west >= 0
            else f"W{abs(west):03d}"
        )

        print(
            f"{lat_name}_{lon_name}:",
            count,
            "GPS records",
        )

print_gps_bounds()


if __name__ == "__main__":
    main()