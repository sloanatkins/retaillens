import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

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


def compute_checksum(filepath: Path) -> str:
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def load_checksums() -> dict:
    checksums = {}
    if CHECKSUM_PATH.exists():
        with open(CHECKSUM_PATH, "r") as f:
            for line in f:
                parts = line.strip().split("  ")
                if len(parts) == 2:
                    checksums[parts[1]] = parts[0]
    return checksums


def save_checksums(checksums: dict):
    CHECKSUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKSUM_PATH, "w") as f:
        for filename, checksum in checksums.items():
            f.write(f"{checksum}  {filename}\n")


def verify_files() -> bool:
    missing = []
    for filename in EXPECTED_FILES:
        if not (RAW_DATA_PATH / filename).exists():
            missing.append(filename)
    if missing:
        logger.error(f"Missing files after download: {missing}")
        return False
    logger.info(f"All {len(EXPECTED_FILES)} files verified present")
    return True


def files_changed(current_checksums: dict, previous_checksums: dict) -> bool:
    for filename, checksum in current_checksums.items():
        if previous_checksums.get(filename) != checksum:
            return True
    return False


def download():
    logger.info(f"Starting download — dataset: {DATASET}")
    logger.info(f"Target path: {RAW_DATA_PATH}")

    RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)

    exit_code = os.system(
        f'kaggle datasets download -d {DATASET} --unzip -p "{RAW_DATA_PATH}" -q'
    )
    if exit_code != 0:
        logger.error(f"Kaggle download failed with exit code {exit_code}")
        raise RuntimeError("Kaggle download failed")

    logger.info("Download complete")

    if not verify_files():
        raise RuntimeError("File verification failed — not all expected CSVs present")

    previous_checksums = load_checksums()
    current_checksums = {
        f: compute_checksum(RAW_DATA_PATH / f) for f in EXPECTED_FILES
    }

    if previous_checksums and not files_changed(current_checksums, previous_checksums):
        logger.info("Checksums match previous run — source data unchanged, skipping upstream")
    else:
        logger.info("New or changed files detected — pipeline will proceed")

    save_checksums(current_checksums)
    logger.info(f"Checksums saved to {CHECKSUM_PATH}")

    return {
        "status": "success",
        "files": EXPECTED_FILES,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "changed": files_changed(current_checksums, previous_checksums),
    }


if __name__ == "__main__":
    result = download()
    logger.info(f"Result: {result}")
