# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
#   "pillow",
# ]
# ///

import csv
import math
from pathlib import Path
from datetime import datetime, timedelta
from math import cos, radians, sin, asin, sqrt

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import LineCollection


# ============================================================
# FILES
# ============================================================

DATA = Path(
    "data/ThermochronTracking Elephants Kruger 2007.csv"
)

OUTPUT = Path(
    "out/living-rhythms-continuous-flow-test.gif"
)


# ============================================================
# VISUAL LANGUAGE
# ============================================================

BACKGROUND = "#07090A"

HISTORICAL_LINE = "#918F8A"
HISTORICAL_POINT = "#CBC8C1"

MOVEMENT_TEAL = "#32C7B5"
MOVEMENT_TEAL_BRIGHT = "#79E1D3"

TEXT_MAIN = "#E3E8E5"
TEXT_SECONDARY = "#89938F"
TEXT_FAINT = "#56615E"
GRID_FAINT = "#26302D"

EARTH_KM_PER_DEGREE = 111.32


# ============================================================
# BASIC DATA
# ============================================================

def parse_time(timestamp):
    return datetime.fromisoformat(
        timestamp.replace(
            "Z",
            "+00:00",
        )
    )


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
                [],
            ).append(
                {
                    "time": parse_time(
                        row["timestamp"]
                    ),
                    "longitude": float(
                        row["location-long"]
                    ),
                    "latitude": float(
                        row["location-lat"]
                    ),
                }
            )

    for elephant_id in tracks:
        tracks[elephant_id].sort(
            key=lambda point: point["time"]
        )

    return tracks


# ============================================================
# GEOGRAPHY
# ============================================================

def calculate_reference_point(tracks):
    longitudes = []
    latitudes = []

    for points in tracks.values():

        for point in points:

            longitudes.append(
                point["longitude"]
            )

            latitudes.append(
                point["latitude"]
            )

    return (
        sum(longitudes) / len(longitudes),
        sum(latitudes) / len(latitudes),
    )


def to_local_km(
    longitude,
    latitude,
    reference_lon,
    reference_lat,
):
    x = (
        (longitude - reference_lon)
        * EARTH_KM_PER_DEGREE
        * cos(radians(reference_lat))
    )

    y = (
        (latitude - reference_lat)
        * EARTH_KM_PER_DEGREE
    )

    return x, y


# ============================================================
# MOVEMENT
# ============================================================

def distance_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    earth_radius = 6371.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    d_lat = lat2 - lat1
    d_lon = lon2 - lon1

    a = (
        sin(d_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(d_lon / 2) ** 2
    )

    return (
        2
        * earth_radius
        * asin(sqrt(a))
    )


def median(values):
    if not values:
        return 0

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
        return 0

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
# PREPARE DATA
# ============================================================

def build_animation_data(
    tracks,
    reference_lon,
    reference_lat,
):
    all_x = []
    all_y = []

    historical_segments = []

    hourly_segments = {
        hour: []
        for hour in range(24)
    }

    hourly_movements = {
        hour: []
        for hour in range(24)
    }

    for elephant_id in sorted(tracks):

        points = tracks[
            elephant_id
        ]

        projected = []

        for point in points:

            x, y = to_local_km(
                point["longitude"],
                point["latitude"],
                reference_lon,
                reference_lat,
            )

            projected.append(
                {
                    **point,
                    "x": x,
                    "y": y,
                }
            )

            all_x.append(x)
            all_y.append(y)

        for i in range(
            1,
            len(projected),
        ):

            previous = projected[
                i - 1
            ]

            current = projected[i]

            gap_minutes = (
                (
                    current["time"]
                    - previous["time"]
                ).total_seconds()
                / 60
            )

            if not (
                29 <= gap_minutes <= 31
            ):
                continue

            segment = [
                (
                    previous["x"],
                    previous["y"],
                ),
                (
                    current["x"],
                    current["y"],
                ),
            ]

            movement = distance_km(
                previous["latitude"],
                previous["longitude"],
                current["latitude"],
                current["longitude"],
            )

            midpoint_utc = (
                previous["time"]
                + (
                    current["time"]
                    - previous["time"]
                )
                / 2
            )

            midpoint_local = (
                midpoint_utc
                + timedelta(
                    hours=2
                )
            )

            hour = (
                midpoint_local.hour
            )

            historical_segments.append(
                segment
            )

            hourly_segments[
                hour
            ].append(
                {
                    "segment": segment,
                    "movement": movement,
                }
            )

            hourly_movements[
                hour
            ].append(
                movement
            )

    hourly_medians = [
        median(
            hourly_movements[
                hour
            ]
        )
        for hour in range(24)
    ]

    all_movements = []

    for hour in range(24):

        all_movements.extend(
            hourly_movements[
                hour
            ]
        )

    visual_p95 = percentile(
        all_movements,
        0.95,
    )

    animated_segments = []

    golden_ratio = (
        0.61803398875
    )

    for hour in range(24):

        items = hourly_segments[
            hour
        ]

        for index, item in enumerate(
            items
        ):

            offset = (
                index
                * golden_ratio
            ) % 1.0

            display_start = (
                hour
                + offset
            )

            animated_segments.append(
                {
                    "segment":
                        item["segment"],

                    "movement":
                        item["movement"],

                    "display_start":
                        display_start,
                }
            )

    return {
        "all_x":
            all_x,

        "all_y":
            all_y,

        "historical_segments":
            historical_segments,

        "hourly_medians":
            hourly_medians,

        "visual_p95":
            visual_p95,

        "animated_segments":
            animated_segments,
    }


# ============================================================
# ANIMATION
# ============================================================

def create_animation(
    tracks,
    data,
):

    fig = plt.figure(
        figsize=(16, 9),
        facecolor=BACKGROUND,
    )


    # ========================================================
    # LEFT — MOVEMENT LANDSCAPE
    # ========================================================

    map_ax = fig.add_axes(
        [
            0.055,
            0.13,
            0.55,
            0.72,
        ]
    )

    map_ax.set_facecolor(
        BACKGROUND
    )

    historical_layer = LineCollection(
        data[
            "historical_segments"
        ],
        colors=HISTORICAL_LINE,
        linewidths=0.11,
        alpha=0.020,
        zorder=1,
    )

    map_ax.add_collection(
        historical_layer
    )

    map_ax.scatter(
        data["all_x"],
        data["all_y"],
        s=0.09,
        color=HISTORICAL_POINT,
        alpha=0.045,
        linewidths=0,
        zorder=2,
    )

    flowing_layer = LineCollection(
        [],
        zorder=5,
    )

    map_ax.add_collection(
        flowing_layer
    )

    map_ax.set_aspect(
        "equal",
        adjustable="box",
    )

    map_ax.autoscale()

    x_min, x_max = (
        map_ax.get_xlim()
    )

    y_min, y_max = (
        map_ax.get_ylim()
    )

    x_padding = (
        x_max
        - x_min
    ) * 0.015

    y_padding = (
        y_max
        - y_min
    ) * 0.015

    map_ax.set_xlim(
        x_min - x_padding,
        x_max + x_padding,
    )

    map_ax.set_ylim(
        y_min - y_padding,
        y_max + y_padding,
    )

    map_ax.axis(
        "off"
    )


    # ========================================================
    # RIGHT — RHYTHM DIAL
    # ========================================================

    dial_ax = fig.add_axes(
        [
            0.665,
            0.25,
            0.27,
            0.48,
        ],
        projection="polar",
    )

    dial_ax.set_facecolor(
        BACKGROUND
    )

    dial_ax.set_theta_zero_location(
        "N"
    )

    dial_ax.set_theta_direction(
        -1
    )

    values = data[
        "hourly_medians"
    ]

    minimum_value = min(
        values
    )

    maximum_value = max(
        values
    )

    value_range = (
        maximum_value
        - minimum_value
    )

    base_radius = 0.95

    rhythm_radii = []

    for value in values:

        normalized = (
            value
            - minimum_value
        ) / value_range

        rhythm_radii.append(
            base_radius
            + normalized
            * 0.58
        )

    closed_radii = (
        rhythm_radii
        + [
            rhythm_radii[0]
        ]
    )

    closed_theta = [
        2
        * math.pi
        * hour
        / 24

        for hour
        in range(
            25
        )
    ]

    dial_ax.plot(
        closed_theta,
        [
            base_radius
        ] * len(
            closed_theta
        ),
        color=GRID_FAINT,
        linewidth=0.7,
        alpha=0.8,
        zorder=1,
    )

    dial_ax.fill_between(
        closed_theta,
        [
            base_radius
        ] * len(
            closed_theta
        ),
        closed_radii,
        color=MOVEMENT_TEAL,
        alpha=0.055,
        zorder=1,
    )

    dial_ax.plot(
        closed_theta,
        closed_radii,
        color=MOVEMENT_TEAL,
        linewidth=1.0,
        alpha=0.30,
        zorder=2,
    )

    hour_angles = [
        2
        * math.pi
        * hour
        / 24

        for hour
        in range(
            24
        )
    ]

    dial_ax.scatter(
        hour_angles,
        [1.68] * 24,
        s=4,
        color=TEXT_FAINT,
        alpha=0.6,
        linewidths=0,
        zorder=1,
    )

    pointer_line, = (
        dial_ax.plot(
            [],
            [],
            color=MOVEMENT_TEAL_BRIGHT,
            linewidth=1.0,
            alpha=0.8,
            zorder=5,
        )
    )

    current_dot = (
        dial_ax.scatter(
            [],
            [],
            s=55,
            color=MOVEMENT_TEAL_BRIGHT,
            linewidths=0,
            zorder=6,
        )
    )

    progress_line, = (
        dial_ax.plot(
            [],
            [],
            color=MOVEMENT_TEAL_BRIGHT,
            linewidth=2.1,
            alpha=0.95,
            zorder=4,
        )
    )

    for hour in [
        0,
        3,
        6,
        9,
        12,
        15,
        18,
        21,
    ]:

        angle = (
            2
            * math.pi
            * hour
            / 24
        )

        dial_ax.text(
            angle,
            1.80,
            f"{hour:02d}",
            color=TEXT_FAINT,
            fontsize=6,
            family="monospace",
            ha="center",
            va="center",
        )

    dial_ax.text(
        0,
        0.42,
        (
            "MEDIAN\n"
            "~30 MIN\n"
            "DISPLACEMENT"
        ),
        color=TEXT_SECONDARY,
        fontsize=6,
        family="monospace",
        ha="center",
        va="center",
        linespacing=1.35,
    )

    dial_ax.set_ylim(
        0,
        1.88,
    )

    dial_ax.set_xticks([])
    dial_ax.set_yticks([])
    dial_ax.grid(False)

    dial_ax.spines[
        "polar"
    ].set_visible(
        False
    )


    # ========================================================
    # TEXT
    # ========================================================

    fig.text(
        0.055,
        0.945,
        "LIVING RHYTHMS",
        color=TEXT_MAIN,
        fontsize=18,
        fontweight="medium",
        ha="left",
        va="top",
    )

    fig.text(
        0.055,
        0.908,
        (
            "ELEPHANT MOVEMENT / "
            "KRUGER / 2007—2009"
        ),
        color=TEXT_SECONDARY,
        fontsize=7,
        ha="left",
        va="top",
    )

    fig.text(
        0.055,
        0.874,
        (
            "HOW THE MOVEMENT LANDSCAPE "
            "BREATHES THROUGH A 24-HOUR CYCLE"
        ),
        color=MOVEMENT_TEAL_BRIGHT,
        fontsize=7.3,
        fontweight="medium",
        ha="left",
        va="top",
    )

    fig.text(
        0.055,
        0.835,
        "01  MOVEMENT LANDSCAPE",
        color=TEXT_MAIN,
        fontsize=6.4,
        family="monospace",
        ha="left",
        va="top",
    )

    fig.text(
        0.055,
        0.811,
        (
            "EACH TEAL SEGMENT GROWS "
            "FROM ITS START POINT TOWARD ITS END POINT"
        ),
        color=TEXT_SECONDARY,
        fontsize=5.4,
        family="monospace",
        ha="left",
        va="top",
    )

    fig.text(
        0.660,
        0.835,
        "02  DAILY RHYTHM",
        color=TEXT_MAIN,
        fontsize=6.4,
        family="monospace",
        ha="left",
        va="top",
    )

    fig.text(
        0.660,
        0.811,
        (
            "AGGREGATED BY LOCAL HOUR "
            "ACROSS THE STUDY PERIOD"
        ),
        color=TEXT_SECONDARY,
        fontsize=5.4,
        family="monospace",
        ha="left",
        va="top",
    )

    time_text = fig.text(
        0.805,
        0.765,
        "00:00",
        color=TEXT_MAIN,
        fontsize=22,
        family="monospace",
        ha="center",
        va="center",
    )

    state_text = fig.text(
        0.805,
        0.720,
        "",
        color=MOVEMENT_TEAL_BRIGHT,
        fontsize=6.4,
        family="monospace",
        ha="center",
        va="center",
    )

    movement_text = fig.text(
        0.805,
        0.687,
        "",
        color=TEXT_SECONDARY,
        fontsize=5.8,
        family="monospace",
        ha="center",
        va="center",
    )

    fig.text(
        0.055,
        0.045,
        (
            "THIS IS AN AGGREGATED 24-HOUR RHYTHM, NOT ONE REAL DAY. "
            "DISPLAY TIMING WITHIN EACH HOUR IS STAGGERED ONLY "
            "TO REVEAL MOVEMENT DIRECTION."
        ),
        color=TEXT_FAINT,
        fontsize=4.7,
        family="monospace",
        ha="left",
        va="bottom",
    )


    # ========================================================
    # CONTINUOUS FLOW SETTINGS
    # ========================================================

    p95 = data[
        "visual_p95"
    ]

    # 4 visual frames per hour:
    # 00:00 -> 00:15 -> 00:30 -> 00:45 -> 01:00
    frames_per_hour = 4

    total_frames = (
        24
        * frames_per_hour
    )

    # Segment lifecycle:
    #
    # 0.00 -> 0.38 h : grows
    # 0.38 -> 0.55 h : remains visible
    # 0.55 -> 1.10 h : fades away

    grow_duration = 0.38
    hold_until = 0.55
    life_duration = 1.10


    # ========================================================
    # UPDATE
    # ========================================================

    def update(frame):

        current_time = (
            frame
            / frames_per_hour
        )

        current_hour = (
            int(current_time)
            % 24
        )

        minute = int(
            (
                current_time
                - int(current_time)
            )
            * 60
        )


        # ====================================================
        # CONTINUOUS MOVEMENT FLOW
        # ====================================================

        visible_segments = []
        colors = []
        widths = []

        for item in data[
            "animated_segments"
        ]:

            start_time = (
                item[
                    "display_start"
                ]
            )

            age = (
                current_time
                - start_time
            ) % 24

            if age > life_duration:
                continue

            movement = (
                item[
                    "movement"
                ]
            )

            strength = min(
                movement
                / p95,
                1.0,
            )

            original_segment = (
                item[
                    "segment"
                ]
            )

            x1, y1 = (
                original_segment[0]
            )

            x2, y2 = (
                original_segment[1]
            )

            # ------------------------------------------------
            # GROW
            # ------------------------------------------------

            if age < grow_duration:

                progress = (
                    age
                    / grow_duration
                )

                progress = (
                    1
                    - (
                        1 - progress
                    ) ** 2
                )

                end_x = (
                    x1
                    + (
                        x2 - x1
                    )
                    * progress
                )

                end_y = (
                    y1
                    + (
                        y2 - y1
                    )
                    * progress
                )

                alpha_phase = (
                    0.35
                    + 0.65
                    * progress
                )

            # ------------------------------------------------
            # HOLD
            # ------------------------------------------------

            elif age < hold_until:

                end_x = x2
                end_y = y2

                alpha_phase = 1.0

            # ------------------------------------------------
            # FADE
            # ------------------------------------------------

            else:

                end_x = x2
                end_y = y2

                fade_progress = (
                    (
                        age
                        - hold_until
                    )
                    / (
                        life_duration
                        - hold_until
                    )
                )

                alpha_phase = (
                    1.0
                    - fade_progress
                )

            visible_segments.append(
                [
                    (
                        x1,
                        y1,
                    ),
                    (
                        end_x,
                        end_y,
                    ),
                ]
            )

            base_alpha = (
                0.08
                + strength
                * 0.72
            )

            final_alpha = (
                base_alpha
                * alpha_phase
            )

            width = (
                0.18
                + strength
                * 0.78
            )

            colors.append(
                (
                    0.196,
                    0.780,
                    0.710,
                    final_alpha,
                )
            )

            widths.append(
                width
            )

        flowing_layer.set_segments(
            visible_segments
        )

        flowing_layer.set_color(
            colors
        )

        flowing_layer.set_linewidth(
            widths
        )


        # ====================================================
        # DIAL
        # ====================================================

        current_angle = (
            2
            * math.pi
            * current_time
            / 24
        )

        next_hour = (
            current_hour
            + 1
        ) % 24

        fraction = (
            current_time
            - int(
                current_time
            )
        )

        current_radius = (
            rhythm_radii[
                current_hour
            ]
            * (
                1 - fraction
            )
            + rhythm_radii[
                next_hour
            ]
            * fraction
        )

        pointer_line.set_data(
            [
                current_angle,
                current_angle,
            ],
            [
                0.82,
                current_radius,
            ],
        )

        current_dot.set_offsets(
            [
                [
                    current_angle,
                    current_radius,
                ]
            ]
        )

        completed_hours = (
            current_hour
            + 1
        )

        progress_theta = [
            2
            * math.pi
            * hour
            / 24

            for hour in range(
                completed_hours
            )
        ]

        progress_radius = (
            rhythm_radii[
                :completed_hours
            ]
        )

        progress_line.set_data(
            progress_theta,
            progress_radius,
        )


        # ====================================================
        # TEXT
        # ====================================================

        time_text.set_text(
            f"{current_hour:02d}:{minute:02d}"
        )

        current_movement = (
            values[
                current_hour
            ]
            * (
                1 - fraction
            )
            + values[
                next_hour
            ]
            * fraction
        )

        movement_text.set_text(
            (
                "MEDIAN ~30 MIN DISPLACEMENT  "
                f"{current_movement:.3f} KM"
            )
        )

        if (
            2 <= current_time < 5
        ):

            state = (
                "LOW ACTIVITY"
            )

        elif (
            16 <= current_time < 18
        ):

            state = (
                "LATE-AFTERNOON PEAK"
            )

        elif (
            5 <= current_time < 8
        ):

            state = (
                "MORNING RISE"
            )

        else:

            state = (
                "DAILY MOVEMENT"
            )

        state_text.set_text(
            state
        )

        return (
            flowing_layer,
            pointer_line,
            current_dot,
            progress_line,
            time_text,
            state_text,
            movement_text,
        )


    # ========================================================
    # SAVE
    # ========================================================

    animation = FuncAnimation(
        fig,
        update,
        frames=total_frames,
        interval=80,
        repeat=True,
        blit=False,
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Rendering continuous flow test..."
    )

    animation.save(
        OUTPUT,
        writer=PillowWriter(
            fps=12
        ),
        dpi=110,
    )

    print()

    print(
        "Saved:",
        OUTPUT,
    )

    plt.show()


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Reading elephant tracking data..."
    )

    tracks = read_tracks()

    reference_lon, reference_lat = (
        calculate_reference_point(
            tracks
        )
    )

    print(
        "Preparing continuous flow data..."
    )

    animation_data = (
        build_animation_data(
            tracks,
            reference_lon,
            reference_lat,
        )
    )

    print(
        "Tracked individuals:",
        len(tracks),
    )

    print(
        "Movement segments:",
        len(
            animation_data[
                "historical_segments"
            ]
        ),
    )

    create_animation(
        tracks,
        animation_data,
    )


if __name__ == "__main__":
    main()