# /// script
# requires-python = ">=3.10"
# ///

import csv
import json
from pathlib import Path


DATA = Path(
    "data/ThermochronTracking Elephants Kruger 2007.csv"
)

OUTPUT = Path(
    "out/interactive_tracks.json"
)

# Keep 1 point every 4 records for the MVP.
# This is only for interactive display performance.
SAMPLE_EVERY = 4


def read_tracks():
    tracks = {}

    with DATA.open(
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            if (
                not row["location-long"]
                or not row["location-lat"]
            ):
                continue

            elephant_id = (
                row["individual-local-identifier"]
            )

            tracks.setdefault(
                elephant_id,
                []
            ).append(
                {
                    "time": row["timestamp"],
                    "lon": float(
                        row["location-long"]
                    ),
                    "lat": float(
                        row["location-lat"]
                    ),
                }
            )

    return tracks


def sample_tracks(tracks):
    sampled = {}

    for elephant_id, points in tracks.items():

        sampled_points = (
            points[::SAMPLE_EVERY]
        )

        sampled[
            elephant_id
        ] = sampled_points

    return sampled


def calculate_bounds(tracks):
    longitudes = []
    latitudes = []

    for points in tracks.values():

        for point in points:

            longitudes.append(
                point["lon"]
            )

            latitudes.append(
                point["lat"]
            )

    return {
        "min_lon": min(longitudes),
        "max_lon": max(longitudes),
        "min_lat": min(latitudes),
        "max_lat": max(latitudes),
    }


def main():
    print(
        "Reading original tracking data..."
    )

    tracks = read_tracks()

    print(
        "Tracked individuals:",
        len(tracks),
    )

    original_count = sum(
        len(points)
        for points in tracks.values()
    )

    print(
        "Original GPS points:",
        original_count,
    )

    sampled_tracks = sample_tracks(
        tracks
    )

    sampled_count = sum(
        len(points)
        for points
        in sampled_tracks.values()
    )

    print(
        "Interactive GPS points:",
        sampled_count,
    )

    output_data = {
        "metadata": {
            "study":
                "ThermochronTracking Elephants Kruger 2007",

            "sample_every":
                SAMPLE_EVERY,

            "original_point_count":
                original_count,

            "interactive_point_count":
                sampled_count,

            "individual_count":
                len(sampled_tracks),

            "note":
                (
                    "Interactive display uses systematic "
                    "downsampling for browser performance. "
                    "The original dataset remains unchanged."
                ),
        },

        "bounds":
            calculate_bounds(
                sampled_tracks
            ),

        "individuals": [
            {
                "id":
                    elephant_id,

                "points":
                    points,
            }

            for elephant_id, points
            in sorted(
                sampled_tracks.items()
            )
        ],
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output_data,
            f,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    print()
    print(
        "Saved:",
        OUTPUT,
    )


if __name__ == "__main__":
    main()