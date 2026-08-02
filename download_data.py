#!/usr/bin/env python
"""
Download UCI Adult Census Dataset

Automatically downloads adult.data, adult.test, and adult.names
from the UCI Machine Learning Repository.
"""

import urllib.request
import os
import sys

# URLs for dataset files
BASE_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult"
FILES = {
    "adult.data": f"{BASE_URL}/adult.data",
    "adult.test": f"{BASE_URL}/adult.test",
    "adult.names": f"{BASE_URL}/adult.names",
}

# Target directory
DATA_DIR = "data/raw"


def create_data_directory():
    """Create data/raw directory if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"✓ Data directory ensured: {DATA_DIR}/")


def download_file(filename: str, url: str) -> bool:
    """
    Download a single file from URL.

    Parameters
    ----------
    filename : str
        Name of file to save

    url : str
        URL to download from

    Returns
    -------
    bool
        True if successful, False otherwise
    """
    filepath = os.path.join(DATA_DIR, filename)

    # Skip if already exists
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        print(f"  ✓ {filename} already exists ({file_size:,} bytes)")
        return True

    print(f"  ⬇️  Downloading {filename}...", end="", flush=True)

    try:
        urllib.request.urlretrieve(url, filepath)
        file_size = os.path.getsize(filepath)
        print(f" ✓ ({file_size:,} bytes)")
        return True

    except Exception as e:
        print(f" ✗ Failed!")
        print(f"     Error: {e}")
        return False


def verify_files() -> bool:
    """Verify all files were downloaded."""
    print("\n[VERIFICATION]")

    for filename in FILES.keys():
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  ✓ {filename}: {size:,} bytes")
        else:
            print(f"  ✗ {filename}: NOT FOUND")
            return False

    return True


def main():
    """Download Adult Census dataset."""
    print("=" * 60)
    print("UCI Adult Census Dataset Downloader")
    print("=" * 60)

    print("\n[SETUP]")
    create_data_directory()

    print("\n[DOWNLOAD]")
    success_count = 0
    for filename, url in FILES.items():
        if download_file(filename, url):
            success_count += 1

    print(f"\n[SUMMARY]")
    print(f"Downloaded: {success_count}/{len(FILES)} files")

    if verify_files():
        print("\n" + "=" * 60)
        print("✓ SUCCESS: All files downloaded and verified!")
        print("=" * 60)
        print("\nYou can now run:")
        print("  python pipeline.py")
        return 0
    else:
        print("\n" + "=" * 60)
        print("✗ ERROR: Some files missing")
        print("=" * 60)
        print("\nManual download:")
        for filename, url in FILES.items():
            print(f"  {filename}:")
            print(f"    {url}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
