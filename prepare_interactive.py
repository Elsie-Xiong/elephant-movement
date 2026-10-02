# /// script
# requires-python = ">=3.10"
# ///

import csv
import json
import math
from datetime import datetime, timedelta
from pathlib import Path


DATA = Path(
    "data/ThermochronTracking Elephants Kruger 2007.csv"
)

OUTPUT = Path(
    "out/interactive_tracks.json"
)


# ============================================================
# SAMPLING SETTINGS
# ============================================================

# Individual trajectory layer:
# keep 1 point every 4 original GPS records
TRACK_SAMPLE_EVERY = 4

# Macro animation layer:
# keep 1 valid movement step every 3 valid steps
MOVEMENT_SAMPLE_EVERY = 3


# ============================================================
# BASIC HELPERS
# ============================================================

def parse_time(timestamp):
    return datetime.fromisoformat(
        timestamp.replace(
            "Z",
            "+00:00",
        )
    )


def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    earth_radius = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)

    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    d_lat = lat2 - lat1
    d_lon = lon2 - lon1

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(d_lon / 2) ** 2
    )

    return (
        2
        * earth_radius
        * math.asin(
            math.sqrt(a)
        )
    )


def median(values):
    if not values:
        return 0.0

    values = sorted(values)

    middle = len(values) // 2

    if len(values) % 2 == 1:
        return values[middle]

    return (
        values[middle - 1]
        + values[middle]
    ) / 2


def percentile(
    values,
    fraction,
):
    values = sorted(values)

    if not values:
        return 0.0

    position = (
        len(values) - 1
    ) * fraction

    lower = int(position)

    upper = min(
        lower + 1,
        len(values) - 1,
    )

    weight = (
        position
        - lower
    )

    return (
        values[lower]
        * (1 - weight)
        + values[upper]
        * weight
    )


# ============================================================
# READ ORIGINAL DATA
# ============================================================

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
                row[
                    "individual-local-identifier"
                ]
            )

            tracks.setdefault(
                elephant_id,
                [],
            ).append(
                {
                    "time":
                        row["timestamp"],

                    "datetime":
                        parse_time(
                            row["timestamp"]
                        ),

                    "lon":
                        float(
                            row["location-long"]
                        ),

                    "lat":
                        float(
                            row["location-lat"]
                        ),
                }
            )

    for elephant_id in tracks:

        tracks[
            elephant_id
        ].sort(
            key=lambda point:
                point["datetime"]
        )

    return tracks


# ============================================================
# INDIVIDUAL TRAJECTORY DATA
# ============================================================

def build_sampled_tracks(
    tracks,
):
    sampled = {}

    for (
        elephant_id,
        points,
    ) in tracks.items():

        sampled_points = []

        for point in points[
            ::TRACK_SAMPLE_EVERY
        ]:

            sampled_points.append(
                {
                    "time":
                        point["time"],

                    "lon":
                        point["lon"],

                    "lat":
                        point["lat"],
                }
            )

        sampled[
            elephant_id
        ] = sampled_points

    return sampled


# ============================================================
# 24-HOUR MOVEMENT DATA
# ============================================================

def build_hourly_movements(
    tracks,
):
    hourly_segments = {
        str(hour): []
        for hour in range(24)
    }

    hourly_values = {
        hour: []
        for hour in range(24)
    }

    valid_step_count = 0
    stored_step_count = 0
    movement_index = 0

    all_movements = []

    for elephant_id in sorted(
        tracks
    ):

        points = tracks[
            elephant_id
        ]

        for i in range(
            1,
            len(points),
        ):

            previous = points[
                i - 1
            ]

            current = points[i]

            gap_minutes = (
                (
                    current["datetime"]
                    - previous["datetime"]
                ).total_seconds()
                / 60
            )

            # Only comparable ~30 minute movement steps
            if not (
                29 <= gap_minutes <= 31
            ):
                continue

            valid_step_count += 1

            movement = haversine_km(
                previous["lat"],
                previous["lon"],
                current["lat"],
                current["lon"],
            )

            midpoint_utc = (
                previous["datetime"]
                + (
                    current["datetime"]
                    - previous["datetime"]
                )
                / 2
            )

            # South Africa local time = UTC + 2
            midpoint_local = (
                midpoint_utc
                + timedelta(
                    hours=2
                )
            )

            hour = midpoint_local.hour

            hourly_values[
                hour
            ].append(
                movement
            )

            all_movements.append(
                movement
            )

            # Systematic sampling only for
            # browser animation performance
            if (
                movement_index
                % MOVEMENT_SAMPLE_EVERY
                == 0
            ):

                hourly_segments[
                    str(hour)
                ].append(
                    {
                        "id":
                            elephant_id,

                        "x1":
                            previous["lon"],

                        "y1":
                            previous["lat"],

                        "x2":
                            current["lon"],

                        "y2":
                            current["lat"],

                        "movement":
                            round(
                                movement,
                                5,
                            ),
                    }
                )

                stored_step_count += 1

            movement_index += 1

    hourly_medians = {
        str(hour):
            round(
                median(
                    hourly_values[
                        hour
                    ]
                ),
                5,
            )

        for hour in range(24)
    }

    visual_p95 = percentile(
        all_movements,
        0.95,
    )

    return {
        "hourly_segments":
            hourly_segments,

        "hourly_medians":
            hourly_medians,

        "valid_step_count":
            valid_step_count,

        "display_step_count":
            stored_step_count,

        "visual_p95":
            round(
                visual_p95,
                5,
            ),
    }


# ============================================================
# BOUNDS
# ============================================================

def calculate_bounds(
    tracks,
):
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
        "min_lon":
            min(longitudes),

        "max_lon":
            max(longitudes),

        "min_lat":
            min(latitudes),

        "max_lat":
            max(latitudes),
    }


# ============================================================
# MAIN
# ============================================================

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

    # --------------------------------------------------------
    # Individual trajectory layer
    # --------------------------------------------------------

    sampled_tracks = (
        build_sampled_tracks(
            tracks
        )
    )

    sampled_count = sum(
        len(points)
        for points
        in sampled_tracks.values()
    )

    print(
        "Interactive trajectory points:",
        sampled_count,
    )

    # --------------------------------------------------------
    # 24-hour macro animation layer
    # --------------------------------------------------------

    print()

    print(
        "Preparing 24-hour movement animation..."
    )

    movement_data = (
        build_hourly_movements(
            tracks
        )
    )

    print(
        "Valid ~30 min movement steps:",
        movement_data[
            "valid_step_count"
        ],
    )

    print(
        "Movement steps stored for browser:",
        movement_data[
            "display_step_count"
        ],
    )

    print()

    print(
        "Hourly median displacement:"
    )

    for hour in range(24):

        print(
            f"{hour:02d}:00",
            movement_data[
                "hourly_medians"
            ][
                str(hour)
            ],
            "km",
        )

    # --------------------------------------------------------
    # Build JSON
    # --------------------------------------------------------

    output_data = {
        "metadata": {
            "study":
                "ThermochronTracking Elephants Kruger 2007",

            "track_sample_every":
                TRACK_SAMPLE_EVERY,

            "movement_sample_every":
                MOVEMENT_SAMPLE_EVERY,

            "original_point_count":
                original_count,

            "interactive_point_count":
                sampled_count,

            "valid_movement_step_count":
                movement_data[
                    "valid_step_count"
                ],

            "display_movement_step_count":
                movement_data[
                    "display_step_count"
                ],

            "individual_count":
                len(
                    sampled_tracks
                ),

            "movement_definition":
                (
                    "Straight-line displacement "
                    "between consecutive GPS records "
                    "29–31 minutes apart."
                ),

            "time_definition":
                (
                    "Movement is aggregated by "
                    "South Africa local hour (UTC+2) "
                    "across the full study period."
                ),

            "note":
                (
                    "Interactive trajectory and "
                    "movement layers use systematic "
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

            for (
                elephant_id,
                points,
            )
            in sorted(
                sampled_tracks.items()
            )
        ],

        "rhythm": {
            "hourly_medians":
                movement_data[
                    "hourly_medians"
                ],

            "visual_p95":
                movement_data[
                    "visual_p95"
                ],

            "hourly_segments":
                movement_data[
                    "hourly_segments"
                ],
        },
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
            separators=(
                ",",
                ":",
            ),
        )

    file_size_mb = (
        OUTPUT.stat().st_size
        / 1024
        / 1024
    )

    print()

    print(
        "Saved:",
        OUTPUT,
    )

    print(
        "JSON size:",
        f"{file_size_mb:.2f} MB",
    )


if __name__ == "__main__":
    main()