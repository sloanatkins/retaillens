"""
Kaggle Download
===============

Downloads the Olist Brazilian E-Commerce dataset from Kaggle and checks
whether anything actually changed since the last run.

For each run there are two outcomes:
- files changed (or first run)  -> pipeline proceeds normally
- files unchanged               -> checksums match, safe to skip upstream

Integrity check uses MD5 because we just want to detect changes, not
cryptographic security. The checksum file lives next to the raw data so
it's easy to delete and force a fresh run.

Run with:
    python ingestion/download.py

Dependencies:
- loguru
- python-dotenv
- kaggle CLI (must be configured with ~/.kaggle/kaggle.json)
"""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────
DATASET = "olistbr/brazilian-ecommerce"
RAW_DATA_PATH = Path(__file__).parent.parent / "data" / "raw"
CHECKSUM_PATH = Path(__file__).parent.parent / "data" / ".checksums"

EXPECTED_FILES = [
    "olist_customers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


# ── Helpers ───────────────────────────────────────────────────────────
def compute_checksum(filepath: Path) -> str:
    """MD5 the file in chunks so large CSVs don't blow up memory."""
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def load_checksums() -> dict:
    """Read the checksum file from the last run. Returns empty dict if it doesn't exist yet."""
    checksums = {}
    if CHECKSUM_PATH.exists():
        with open(CHECKSUM_PATH, "r") as f:
            for line in f:
                parts = line.strip().split("  ")
                if len(parts) == 2:
                    checksums[parts[1]] = parts[0]
    return checksums


def save_checksums(checksums: dict):
    """Write checksums to disk so the next run can compare."""
    CHECKSUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKSUM_PATH, "w") as f:
        for filename, checksum in checksums.items():
            f.write(f"{checksum}  {filename}\n")


def verify_files() -> bool:
    """Make sure all 9 expected CSVs landed after the download."""
    missing = [f for f in EXPECTED_FILES if not (RAW_DATA_PATH / f).exists()]
    if missing:
        logger.error(f"Missing files after download: {missing}")
        return False
    logger.info(f"All {len(EXPECTED_FILES)} files verified present")
    return True


def files_changed(current: dict, previous: dict) -> bool:
    """Return True if any file has a different checksum than last time."""
    return any(previous.get(f) != cs for f, cs in current.items())


# ── Main ──────────────────────────────────────────────────────────────
def download():
    """Download the dataset and return a summary of what changed."""
    logger.info(f"Starting download — dataset: {DATASET}")
    logger.info(f"Target path: {RAW_DATA_PATH}")

    RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)

    # Path has a space ("Project 3") so it needs to be quoted in the shell call
    exit_code = os.system(
        f'kaggle datasets download -d {DATASET} --unzip -p "{RAW_DATA_PATH}" -q'
    )
    if exit_code != 0:
        logger.error(f"Kaggle download failed with exit code {exit_code}")
        raise RuntimeError("Kaggle download failed")

    logger.info("Download complete")

    if not verify_files():
        raise RuntimeError("File verification failed — not all expected CSVs present")

    # Compare against last run to decide if anything actually changed
    previous = load_checksums()
    current = {f: compute_checksum(RAW_DATA_PATH / f) for f in EXPECTED_FILES}

    if previous and not files_changed(current, previous):
        logger.info("Checksums match previous run — source data unchanged")
    else:
        logger.info("New or changed files detected — pipeline will proceed")

    save_checksums(current)
    logger.info(f"Checksums saved to {CHECKSUM_PATH}")

    return {
        "status": "success",
        "files": EXPECTED_FILES,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changed": files_changed(current, previous),
    }


if __name__ == "__main__":
    result = download()
    logger.info(f"Result: {result}")