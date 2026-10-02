# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "requests",
# ]
# ///

"""
Fetch the published source data once and save the raw files unchanged in data/.

Run:

    uv run fetch.py

Sources:
1. Movebank Data Repository
   ThermochronTracking Elephants Kruger 2007

2. Copernicus DEM GLO-30
   Digital Surface Model tiles covering the elephant GPS records
"""

from pathlib import Path

import requests


HERE = Path(__file__).parent
DATA = HERE / "data"


# ------------------------------------------------------------
# ELEPHANT TRACKING DATA
# ------------------------------------------------------------

ELEPHANT_URL = (
    "https://datarepository.movebank.org/server/api/core/"
    "bitstreams/10240da1-0a99-42bf-a34f-eff15883bbfb/content"
)

ELEPHANT_FILE = (
    "ThermochronTracking Elephants Kruger 2007.csv"
)


# ------------------------------------------------------------
# COPERNICUS DEM GLO-30
#
# These four 1° × 1° tiles are the tiles actually occupied
# by GPS observations in the tracking dataset.
# ------------------------------------------------------------

DEM_TILES = [
    "Copernicus_DSM_COG_10_S26_00_E031_00_DEM",
    "Copernicus_DSM_COG_10_S25_00_E031_00_DEM",
    "Copernicus_DSM_COG_10_S25_00_E032_00_DEM",
    "Copernicus_DSM_COG_10_S24_00_E031_00_DEM",
]


def copernicus_url(tile):
    """Build the public AWS URL for one Copernicus GLO-30 tile."""
    return (
        "https://copernicus-dem-30m.s3.amazonaws.com/"
        f"{tile}/{tile}.tif"
    )


def fetch(url, path):
    """
    Fetch a published raw file once.

    If the file already exists in data/, leave it unchanged.
    """
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)

        print(
            f"already here: {path.name} "
            f"({size_mb:.1f} MB)"
        )

        return path

    DATA.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".part"
    )

    print()
    print("asking:")
    print(url)

    try:
        with requests.get(
            url,
            timeout=120,
            stream=True,
            headers={
                "User-Agent": "SD5913 elephant movement project"
            },
        ) as reply:

            reply.raise_for_status()

            with temporary_path.open("wb") as f:
                for chunk in reply.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if chunk:
                        f.write(chunk)

        # Only rename after the whole download succeeds.
        temporary_path.replace(path)

    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()

        raise

    size_mb = path.stat().st_size / (1024 * 1024)

    print(
        f"saved: {path.name} "
        f"({size_mb:.1f} MB)"
    )

    return path


def main():
    print("FETCH SOURCE DATA")
    print("=================")

    # Elephant tracking CSV
    fetch(
        ELEPHANT_URL,
        DATA / ELEPHANT_FILE,
    )

    # Copernicus GLO-30 terrain tiles
    for tile in DEM_TILES:
        fetch(
            copernicus_url(tile),
            DATA / f"{tile}.tif",
        )

    print()
    print("DONE")
    print("----")
    print("All required raw source files are in data/.")


if __name__ == "__main__":
    main()