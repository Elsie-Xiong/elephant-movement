# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
# ]
# ///

import csv
import math
from pathlib import Path
from datetime import datetime, timedelta
from math import cos, radians, sin, asin, sqrt

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection


DATA = Path(
    "data/ThermochronTracking Elephants Kruger 2007.csv"
)

OUTPUT = Path(
    "out/living-rhythms-nested-test.png"
)

EARTH_KM_PER_DEGREE = 111.32


# ============================================================
# VISUAL LANGUAGE
# ============================================================

BACKGROUND = "#07090A"

HISTORICAL_LINE = "#9D9B96"
HISTORICAL_POINT = "#D4D1CA"

MOVEMENT_TEAL = "#32C7B5"
MOVEMENT_TEAL_BRIGHT = "#79E1D3"

TEXT_MAIN = "#E3E8E5"
TEXT_SECONDARY = "#89938F"
TEXT_FAINT = "#56615E"
GRID_FAINT = "#26302D"


MONTH_NAMES = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
]


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

        reader = csv.DictReader(
            f
        )

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

        tracks[
            elephant_id
        ].sort(
            key=lambda point: (
                point["time"]
            )
        )

    return tracks


# ============================================================
# GEOGRAPHIC PROJECTION
# ============================================================

def calculate_reference_point(
    tracks,
):
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
        sum(longitudes)
        / len(longitudes),

        sum(latitudes)
        / len(latitudes),
    )


def to_local_km(
    longitude,
    latitude,
    reference_lon,
    reference_lat,
):
    x = (
        (
            longitude
            - reference_lon
        )
        * EARTH_KM_PER_DEGREE
        * cos(
            radians(
                reference_lat
            )
        )
    )

    y = (
        (
            latitude
            - reference_lat
        )
        * EARTH_KM_PER_DEGREE
    )

    return x, y


# ============================================================
# MOVEMENT CALCULATION
# ============================================================

def distance_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    """
    Straight-line displacement
    between two GPS points.
    """

    earth_radius = 6371.0

    lat1 = radians(
        lat1
    )

    lon1 = radians(
        lon1
    )

    lat2 = radians(
        lat2
    )

    lon2 = radians(
        lon2
    )

    d_lat = (
        lat2
        - lat1
    )

    d_lon = (
        lon2
        - lon1
    )

    a = (
        sin(
            d_lat / 2
        ) ** 2

        + cos(lat1)
        * cos(lat2)
        * sin(
            d_lon / 2
        ) ** 2
    )

    return (
        2
        * earth_radius
        * asin(
            sqrt(a)
        )
    )


def median(
    values,
):
    if not values:
        return None

    values = sorted(
        values
    )

    middle = (
        len(values)
        // 2
    )

    if (
        len(values)
        % 2
        == 1
    ):
        return values[
            middle
        ]

    return (
        values[
            middle - 1
        ]
        + values[
            middle
        ]
    ) / 2


def percentile(
    values,
    fraction,
):
    """
    Simple percentile.

    Used only for visual scaling.
    No records are removed.
    """

    values = sorted(
        values
    )

    if not values:
        return 0

    position = (
        len(values) - 1
    ) * fraction

    lower = int(
        position
    )

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
        * (
            1
            - weight
        )

        + values[upper]
        * weight
    )


# ============================================================
# BUILD ANALYTICAL DATA
# ============================================================

def build_data(
    tracks,
    reference_lon,
    reference_lat,
):
    all_x = []
    all_y = []

    historical_segments = []

    peak_segments = []

    hourly_movements = {
        hour: []
        for hour in range(
            24
        )
    }

    monthly_hour_movements = {
        month: {
            hour: []
            for hour in range(
                24
            )
        }

        for month in range(
            1,
            13,
        )
    }

    valid_step_count = 0

    start_time = None
    end_time = None

    for elephant_id in sorted(
        tracks
    ):

        points = tracks[
            elephant_id
        ]

        projected = []

        for point in points:

            x, y = (
                to_local_km(
                    point[
                        "longitude"
                    ],
                    point[
                        "latitude"
                    ],
                    reference_lon,
                    reference_lat,
                )
            )

            projected.append(
                {
                    **point,
                    "x": x,
                    "y": y,
                }
            )

            all_x.append(
                x
            )

            all_y.append(
                y
            )

            if (
                start_time is None
                or point["time"]
                < start_time
            ):
                start_time = (
                    point["time"]
                )

            if (
                end_time is None
                or point["time"]
                > end_time
            ):
                end_time = (
                    point["time"]
                )

        for i in range(
            1,
            len(projected),
        ):

            previous = (
                projected[
                    i - 1
                ]
            )

            current = (
                projected[
                    i
                ]
            )

            gap_minutes = (
                (
                    current["time"]
                    - previous["time"]
                ).total_seconds()
                / 60
            )

            if not (
                29
                <= gap_minutes
                <= 31
            ):
                continue

            valid_step_count += 1

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

            historical_segments.append(
                segment
            )

            movement = (
                distance_km(
                    previous[
                        "latitude"
                    ],
                    previous[
                        "longitude"
                    ],
                    current[
                        "latitude"
                    ],
                    current[
                        "longitude"
                    ],
                )
            )

            midpoint_utc = (
                previous[
                    "time"
                ]

                + (
                    current[
                        "time"
                    ]
                    - previous[
                        "time"
                    ]
                )
                / 2
            )

            # South Africa local time
            # = UTC + 2.
            midpoint_local = (
                midpoint_utc
                + timedelta(
                    hours=2
                )
            )

            hour = (
                midpoint_local.hour
            )

            month = (
                midpoint_local.month
            )

            hourly_movements[
                hour
            ].append(
                movement
            )

            monthly_hour_movements[
                month
            ][
                hour
            ].append(
                movement
            )

            # Late-afternoon analytical window.
            if hour in (
                16,
                17,
            ):
                peak_segments.append(
                    {
                        "segment": segment,
                        "movement": movement,
                    }
                )

    # --------------------------------------------------------
    # OVERALL 24-HOUR RHYTHM
    # --------------------------------------------------------

    overall_hourly_medians = []

    for hour in range(
        24
    ):

        overall_hourly_medians.append(
            median(
                hourly_movements[
                    hour
                ]
            )
        )

    # --------------------------------------------------------
    # 12 MONTH × 24 HOUR RHYTHMS
    # --------------------------------------------------------

    monthly_medians = {}

    monthly_peak_hours = {}

    monthly_peak_values = {}

    for month in range(
        1,
        13,
    ):

        month_values = []

        for hour in range(
            24
        ):

            value = median(
                monthly_hour_movements[
                    month
                ][
                    hour
                ]
            )

            month_values.append(
                value
            )

        monthly_medians[
            month
        ] = month_values

        peak_hour = max(
            range(24),
            key=lambda hour: (
                month_values[
                    hour
                ]
            ),
        )

        monthly_peak_hours[
            month
        ] = peak_hour

        monthly_peak_values[
            month
        ] = (
            month_values[
                peak_hour
            ]
        )

    peak_month_count = sum(
        1

        for hour
        in monthly_peak_hours.values()

        if hour
        in (
            16,
            17,
        )
    )

    return {
        "all_x": all_x,
        "all_y": all_y,

        "historical_segments":
            historical_segments,

        "peak_segments":
            peak_segments,

        "overall_hourly_medians":
            overall_hourly_medians,

        "monthly_medians":
            monthly_medians,

        "monthly_peak_hours":
            monthly_peak_hours,

        "monthly_peak_values":
            monthly_peak_values,

        "peak_month_count":
            peak_month_count,

        "valid_step_count":
            valid_step_count,

        "start_time":
            start_time,

        "end_time":
            end_time,
    }


# ============================================================
# LEFT — SPATIAL MEMORY
# ============================================================

def draw_landscape(
    fig,
    visual_data,
):
    ax = fig.add_axes(
        [
            0.045,
            0.12,
            0.49,
            0.75,
        ]
    )

    ax.set_facecolor(
        BACKGROUND
    )

    # --------------------------------------------------------
    # HISTORICAL MOVEMENT MEMORY
    # --------------------------------------------------------

    historical = LineCollection(
        visual_data[
            "historical_segments"
        ],
        colors=HISTORICAL_LINE,
        linewidths=0.14,
        alpha=0.043,
        zorder=1,
    )

    ax.add_collection(
        historical
    )

    ax.scatter(
        visual_data[
            "all_x"
        ],
        visual_data[
            "all_y"
        ],
        s=0.14,
        color=HISTORICAL_POINT,
        alpha=0.11,
        linewidths=0,
        zorder=2,
    )

    # --------------------------------------------------------
    # 16–17H MOVEMENT
    #
    # Brighter / thicker =
    # longer ~30 min displacement.
    #
    # P95 is only used to cap visual scaling.
    # No GPS record is removed.
    # --------------------------------------------------------

    peak_movements = [
        item[
            "movement"
        ]

        for item
        in visual_data[
            "peak_segments"
        ]
    ]

    p95 = percentile(
        peak_movements,
        0.95,
    )

    segments = []
    colors = []
    widths = []

    for item in visual_data[
        "peak_segments"
    ]:

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

        alpha = (
            0.055
            + strength
            * 0.33
        )

        linewidth = (
            0.15
            + strength
            * 0.38
        )

        segments.append(
            item[
                "segment"
            ]
        )

        colors.append(
            (
                0.196,
                0.780,
                0.710,
                alpha,
            )
        )

        widths.append(
            linewidth
        )

    peak_layer = (
        LineCollection(
            segments,
            colors=colors,
            linewidths=widths,
            zorder=3,
        )
    )

    ax.add_collection(
        peak_layer
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    ax.autoscale()

    x_min, x_max = (
        ax.get_xlim()
    )

    y_min, y_max = (
        ax.get_ylim()
    )

    x_padding = (
        x_max
        - x_min
    ) * 0.01

    y_padding = (
        y_max
        - y_min
    ) * 0.01

    ax.set_xlim(
        x_min
        - x_padding,

        x_max
        + x_padding,
    )

    ax.set_ylim(
        y_min
        - y_padding,

        y_max
        + y_padding,
    )

    ax.axis(
        "off"
    )

    fig.text(
        0.055,
        0.842,
        "01  SPATIAL MEMORY",
        color=TEXT_MAIN,
        fontsize=6.2,
        family="monospace",
        ha="left",
        va="top",
    )

    fig.text(
        0.055,
        0.819,
        (
            "LONG-TERM GPS MOVEMENT "
            "+ LATE-AFTERNOON ACTIVITY"
        ),
        color=TEXT_SECONDARY,
        fontsize=5.3,
        family="monospace",
        ha="left",
        va="top",
    )


# ============================================================
# RIGHT TOP — 24H RHYTHM DIAL
# ============================================================

def draw_overall_rhythm(
    fig,
    visual_data,
):
    """
    24-hour circular rhythm.

    Angle =
    local hour.

    Distance from inner ring =
    median ~30 min displacement.
    """

    values = visual_data[
        "overall_hourly_medians"
    ]

    hours = list(
        range(24)
    )

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

    closed_values = (
        values
        + [
            values[0]
        ]
    )

    closed_hours = (
        hours
        + [24]
    )

    theta = [
        2
        * math.pi
        * hour
        / 24

        for hour
        in closed_hours
    ]

    base_radius = 1.0

    radii = []

    for value in closed_values:

        normalized = (
            (
                value
                - minimum_value
            )
            / value_range
        )

        radii.append(
            base_radius
            + normalized
            * 0.55
        )

    ax = fig.add_axes(
        [
            0.665,
            0.675,
            0.19,
            0.19,
        ],
        projection="polar",
    )

    ax.set_facecolor(
        BACKGROUND
    )

    # Midnight at top.
    ax.set_theta_zero_location(
        "N"
    )

    # Clockwise.
    ax.set_theta_direction(
        -1
    )

    # --------------------------------------------------------
    # REFERENCE RING
    # --------------------------------------------------------

    reference_theta = [
        2
        * math.pi
        * i
        / 120

        for i
        in range(
            121
        )
    ]

    ax.plot(
        reference_theta,
        [
            base_radius
        ]
        * len(
            reference_theta
        ),
        color=GRID_FAINT,
        linewidth=0.55,
        alpha=0.85,
        zorder=1,
    )

    # --------------------------------------------------------
    # RHYTHM BODY
    # --------------------------------------------------------

    ax.fill_between(
        theta,
        [
            base_radius
        ]
        * len(theta),
        radii,
        color=MOVEMENT_TEAL,
        alpha=0.10,
        zorder=2,
    )

    ax.plot(
        theta,
        radii,
        color=MOVEMENT_TEAL,
        linewidth=1.35,
        alpha=0.95,
        zorder=3,
    )

    # --------------------------------------------------------
    # MINIMUM / MAXIMUM
    # --------------------------------------------------------

    minimum_hour = min(
        range(24),
        key=lambda hour: (
            values[
                hour
            ]
        ),
    )

    maximum_hour = max(
        range(24),
        key=lambda hour: (
            values[
                hour
            ]
        ),
    )

    def radius_for_hour(
        hour,
    ):
        normalized = (
            (
                values[
                    hour
                ]
                - minimum_value
            )
            / value_range
        )

        return (
            base_radius
            + normalized
            * 0.55
        )

    minimum_theta = (
        2
        * math.pi
        * minimum_hour
        / 24
    )

    maximum_theta = (
        2
        * math.pi
        * maximum_hour
        / 24
    )

    ax.scatter(
        [
            minimum_theta
        ],
        [
            radius_for_hour(
                minimum_hour
            )
        ],
        s=24,
        color=MOVEMENT_TEAL_BRIGHT,
        linewidths=0,
        zorder=5,
    )

    ax.scatter(
        [
            maximum_theta
        ],
        [
            radius_for_hour(
                maximum_hour
            )
        ],
        s=28,
        color=MOVEMENT_TEAL_BRIGHT,
        linewidths=0,
        zorder=5,
    )

    # --------------------------------------------------------
    # 16–17H ANALYTICAL REGION
    # --------------------------------------------------------

    peak_start = (
        2
        * math.pi
        * 15.5
        / 24
    )

    peak_end = (
        2
        * math.pi
        * 17.5
        / 24
    )

    peak_angles = [
        peak_start
        + (
            peak_end
            - peak_start
        )
        * i
        / 30

        for i
        in range(
            31
        )
    ]

    ax.fill_between(
        peak_angles,
        [
            0.92
        ]
        * len(
            peak_angles
        ),
        [
            1.64
        ]
        * len(
            peak_angles
        ),
        color=MOVEMENT_TEAL,
        alpha=0.055,
        zorder=0,
    )

    # --------------------------------------------------------
    # HOUR LABELS
    # --------------------------------------------------------

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

        ax.text(
            angle,
            1.72,
            f"{hour:02d}",
            color=TEXT_FAINT,
            fontsize=4.7,
            family="monospace",
            ha="center",
            va="center",
        )

    ax.set_ylim(
        0.90,
        1.78,
    )

    ax.grid(
        False
    )

    ax.set_xticks(
        []
    )

    ax.set_yticks(
        []
    )

    ax.spines[
        "polar"
    ].set_visible(
        False
    )

    # --------------------------------------------------------
    # PANEL LABELS
    # --------------------------------------------------------

    fig.text(
        0.585,
        0.855,
        "02  DAILY RHYTHM",
        color=TEXT_MAIN,
        fontsize=6.2,
        family="monospace",
        ha="left",
        va="top",
    )

    fig.text(
        0.585,
        0.832,
        "24H MOVEMENT CYCLE · LOCAL TIME",
        color=TEXT_SECONDARY,
        fontsize=5.2,
        family="monospace",
        ha="left",
        va="top",
    )

    fig.text(
        0.585,
        0.775,
        "LOW",
        color=TEXT_FAINT,
        fontsize=4.8,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.585,
        0.755,
        (
            f"{minimum_hour:02d}:00  "
            f"{values[minimum_hour]:.3f} km"
        ),
        color=MOVEMENT_TEAL_BRIGHT,
        fontsize=5.2,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.585,
        0.720,
        "PEAK",
        color=TEXT_FAINT,
        fontsize=4.8,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.585,
        0.700,
        (
            f"{maximum_hour:02d}:00  "
            f"{values[maximum_hour]:.3f} km"
        ),
        color=MOVEMENT_TEAL_BRIGHT,
        fontsize=5.2,
        family="monospace",
        ha="left",
    )


# ============================================================
# RIGHT BOTTOM — MONTHLY RHYTHM RIBBONS
# ============================================================

def draw_monthly_rhythms(
    fig,
    visual_data,
):
    """
    12 monthly rhythm ribbons.

    Horizontal position =
    local hour.

    Ribbon thickness =
    median ~30 min displacement.

    All months use the same
    movement scale.
    """

    ax = fig.add_axes(
        [
            0.585,
            0.125,
            0.355,
            0.49,
        ]
    )

    ax.set_facecolor(
        BACKGROUND
    )

    hours = list(
        range(24)
    )

    monthly_medians = (
        visual_data[
            "monthly_medians"
        ]
    )

    monthly_peaks = (
        visual_data[
            "monthly_peak_hours"
        ]
    )

    monthly_peak_values = (
        visual_data[
            "monthly_peak_values"
        ]
    )

    # --------------------------------------------------------
    # COMMON SCALE
    # --------------------------------------------------------

    global_peak = max(
        monthly_peak_values.values()
    )

    # --------------------------------------------------------
    # 16–17H RECURRING WINDOW
    # --------------------------------------------------------

    ax.axvspan(
        15.5,
        17.5,
        color=MOVEMENT_TEAL,
        alpha=0.045,
        linewidth=0,
        zorder=0,
    )

    ribbon_height = 0.52

    # --------------------------------------------------------
    # DRAW 12 RIBBONS
    # --------------------------------------------------------

    for index, month in enumerate(
        range(
            1,
            13,
        )
    ):

        baseline = (
            12
            - index
        )

        values = (
            monthly_medians[
                month
            ]
        )

        amplitudes = [
            (
                value
                / global_peak
            )
            * ribbon_height

            for value
            in values
        ]

        upper = [
            baseline
            + amplitude

            for amplitude
            in amplitudes
        ]

        lower = [
            baseline
            - amplitude

            for amplitude
            in amplitudes
        ]

        # Centre guide
        ax.plot(
            [
                0,
                23,
            ],
            [
                baseline,
                baseline,
            ],
            color=GRID_FAINT,
            linewidth=0.40,
            alpha=0.65,
            zorder=1,
        )

        # Filled ribbon
        ax.fill_between(
            hours,
            lower,
            upper,
            color=MOVEMENT_TEAL,
            alpha=0.10,
            linewidth=0,
            zorder=2,
        )

        # Upper contour
        ax.plot(
            hours,
            upper,
            color=MOVEMENT_TEAL,
            linewidth=0.75,
            alpha=0.70,
            zorder=3,
        )

        # Lower contour
        ax.plot(
            hours,
            lower,
            color=MOVEMENT_TEAL,
            linewidth=0.45,
            alpha=0.28,
            zorder=2,
        )

        # ----------------------------------------------------
        # PEAK
        # ----------------------------------------------------

        peak_hour = (
            monthly_peaks[
                month
            ]
        )

        peak_value = (
            monthly_peak_values[
                month
            ]
        )

        peak_amplitude = (
            peak_value
            / global_peak
        ) * ribbon_height

        peak_y = (
            baseline
            + peak_amplitude
        )

        ax.scatter(
            [
                peak_hour
            ],
            [
                peak_y
            ],
            s=14,
            color=MOVEMENT_TEAL_BRIGHT,
            linewidths=0,
            zorder=5,
        )

        # Month label
        ax.text(
            -1.0,
            baseline,
            MONTH_NAMES[
                month - 1
            ],
            color=TEXT_SECONDARY,
            fontsize=5.2,
            family="monospace",
            ha="right",
            va="center",
        )

        # Peak magnitude
        ax.text(
            24.0,
            baseline,
            f"{peak_value:.3f}",
            color=TEXT_SECONDARY,
            fontsize=4.9,
            family="monospace",
            ha="left",
            va="center",
        )

    # --------------------------------------------------------
    # RECURRING PEAK RIDGE
    # --------------------------------------------------------

    ridge_x = []
    ridge_y = []

    for index, month in enumerate(
        range(
            1,
            13,
        )
    ):

        baseline = (
            12
            - index
        )

        peak_hour = (
            monthly_peaks[
                month
            ]
        )

        peak_value = (
            monthly_peak_values[
                month
            ]
        )

        peak_amplitude = (
            peak_value
            / global_peak
        ) * ribbon_height

        ridge_x.append(
            peak_hour
        )

        ridge_y.append(
            baseline
            + peak_amplitude
        )

    ax.plot(
        ridge_x,
        ridge_y,
        color=MOVEMENT_TEAL_BRIGHT,
        linewidth=0.75,
        alpha=0.50,
        linestyle="--",
        zorder=4,
    )

    # --------------------------------------------------------
    # LABELS
    # --------------------------------------------------------

    ax.text(
        16.5,
        13.10,
        (
            "RECURRING PEAK RIDGE\n"
            "16–17H"
        ),
        color=MOVEMENT_TEAL_BRIGHT,
        fontsize=5.3,
        family="monospace",
        ha="center",
        va="bottom",
    )

    ax.text(
        24.0,
        13.10,
        (
            "PEAK KM\n"
            "/ ~30 MIN"
        ),
        color=TEXT_FAINT,
        fontsize=4.7,
        family="monospace",
        ha="left",
        va="bottom",
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
        23,
    ]:

        ax.text(
            hour,
            0.30,
            f"{hour:02d}",
            color=TEXT_FAINT,
            fontsize=4.6,
            family="monospace",
            ha="center",
            va="bottom",
        )

    ax.set_xlim(
        -1.8,
        26.2,
    )

    ax.set_ylim(
        0.15,
        13.75,
    )

    ax.axis(
        "off"
    )

    fig.text(
        0.585,
        0.650,
        "03  RHYTHMS WITHIN RHYTHMS",
        color=TEXT_MAIN,
        fontsize=6.2,
        family="monospace",
        ha="left",
        va="top",
    )

    fig.text(
        0.585,
        0.627,
        (
            "THE DAILY PULSE REPEATS, "
            "WHILE ITS AMPLITUDE CHANGES "
            "THROUGH THE YEAR."
        ),
        color=TEXT_SECONDARY,
        fontsize=5.2,
        family="monospace",
        ha="left",
        va="top",
    )


# ============================================================
# TITLE + EXPLANATION
# ============================================================

def add_interface(
    fig,
    tracks,
    visual_data,
):
    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    fig.text(
        0.045,
        0.955,
        "LIVING RHYTHMS",
        color=TEXT_MAIN,
        fontsize=17,
        fontweight="medium",
        ha="left",
        va="top",
    )

    fig.text(
        0.045,
        0.920,
        (
            "ELEPHANT MOVEMENT / "
            "KRUGER / 2007—2009"
        ),
        color=TEXT_SECONDARY,
        fontsize=6.8,
        ha="left",
        va="top",
    )

    # --------------------------------------------------------
    # MAIN FINDING
    # --------------------------------------------------------

    fig.text(
        0.045,
        0.888,
        "STABLE TIMING. CHANGING INTENSITY.",
        color=MOVEMENT_TEAL_BRIGHT,
        fontsize=7.0,
        fontweight="medium",
        ha="left",
        va="top",
    )

    fig.text(
        0.045,
        0.865,
        (
            "MOVEMENT FOLLOWS A RECURRING DAILY RHYTHM: "
            "THE LATE-AFTERNOON PEAK REPEATS ACROSS MONTHS, "
            "BUT ITS STRENGTH VARIES."
        ),
        color=TEXT_MAIN,
        fontsize=6.0,
        ha="left",
        va="top",
    )

    # --------------------------------------------------------
    # STUDY INFO
    # --------------------------------------------------------

    info = (
        f"TRACKED INDIVIDUALS   "
        f"{len(tracks):02d}\n"

        f"GPS OBSERVATIONS      "
        f"{len(visual_data['all_x']):,}\n"

        f"~30 MIN STEPS         "
        f"{visual_data['valid_step_count']:,}\n"

        f"STUDY START           "
        f"{visual_data['start_time']:%Y.%m.%d}\n"

        f"STUDY END             "
        f"{visual_data['end_time']:%Y.%m.%d}"
    )

    fig.text(
        0.815,
        0.945,
        info,
        color=TEXT_SECONDARY,
        fontsize=6.0,
        family="monospace",
        linespacing=1.65,
        ha="left",
        va="top",
    )

    # --------------------------------------------------------
    # MAP LEGEND
    # --------------------------------------------------------

    fig.text(
        0.055,
        0.095,
        "PALE",
        color=HISTORICAL_POINT,
        fontsize=5.2,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.092,
        0.095,
        "ALL HISTORICAL GPS MOVEMENT",
        color=TEXT_SECONDARY,
        fontsize=5.0,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.055,
        0.075,
        "TEAL",
        color=MOVEMENT_TEAL,
        fontsize=5.2,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.092,
        0.075,
        "LOCAL 16:00–17:59 MOVEMENT",
        color=TEXT_SECONDARY,
        fontsize=5.0,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.055,
        0.055,
        "BRIGHTER / THICKER",
        color=MOVEMENT_TEAL_BRIGHT,
        fontsize=5.2,
        family="monospace",
        ha="left",
    )

    fig.text(
        0.150,
        0.055,
        "LONGER ~30 MIN DISPLACEMENT",
        color=TEXT_SECONDARY,
        fontsize=5.0,
        family="monospace",
        ha="left",
    )

    # --------------------------------------------------------
    # METHOD NOTE
    # --------------------------------------------------------

    fig.text(
        0.955,
        0.025,
        (
            "CALENDAR MONTHS AGGREGATED ACROSS AVAILABLE STUDY YEARS  /  "
            "STRAIGHT-LINE DISPLACEMENT BETWEEN CONSECUTIVE "
            "29–31 MIN GPS RECORDS"
        ),
        color=TEXT_FAINT,
        fontsize=4.5,
        family="monospace",
        ha="right",
        va="top",
    )


# ============================================================
# MAIN
# ============================================================

def main():
    tracks = read_tracks()

    reference_lon, reference_lat = (
        calculate_reference_point(
            tracks
        )
    )

    visual_data = build_data(
        tracks,
        reference_lon,
        reference_lat,
    )

    fig = plt.figure(
        figsize=(
            16,
            9,
        ),
        facecolor=BACKGROUND,
    )

    draw_landscape(
        fig,
        visual_data,
    )

    draw_overall_rhythm(
        fig,
        visual_data,
    )

    draw_monthly_rhythms(
        fig,
        visual_data,
    )

    add_interface(
        fig,
        tracks,
        visual_data,
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        OUTPUT,
        dpi=220,
        facecolor=fig.get_facecolor(),
    )

    print(
        "LIVING RHYTHMS — RHYTHM VISUAL TEST"
    )

    print(
        "-----------------------------------"
    )

    print(
        "Tracked individuals:",
        len(tracks),
    )

    print(
        "GPS observations:",
        len(
            visual_data[
                "all_x"
            ]
        ),
    )

    print(
        "Valid ~30-minute steps:",
        visual_data[
            "valid_step_count"
        ],
    )

    print()

    print(
        "MONTHLY PEAK HOURS"
    )

    print(
        "------------------"
    )

    for month in range(
        1,
        13,
    ):

        print(
            MONTH_NAMES[
                month - 1
            ],
            "|",
            (
                f"{visual_data['monthly_peak_hours'][month]:02d}:00"
            ),
            "|",
            (
                f"{visual_data['monthly_peak_values'][month]:.4f} km"
            ),
        )

    print()

    print(
        "Months peaking at 16–17h:",
        visual_data[
            "peak_month_count"
        ],
        "/ 12",
    )

    print(
        "Saved:",
        OUTPUT,
    )

    plt.show()


if __name__ == "__main__":
    main()