import os
import csv
import requests
from pathlib import Path


def download_images_from_csv():
    """
    Download all images listed in images.csv and save them to static/img directory
    """
    print("Starting image download process...")

    # Ensure the static/img directory exists
    img_dir = Path("dashboard_suppliers/static/img")
    img_dir.mkdir(parents=True, exist_ok=True)

    # Path to the CSV file
    csv_path = Path("dashboard_suppliers/static/data/images.csv")

    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return

    # Count variables for reporting
    total_images = 0
    downloaded = 0
    skipped = 0
    failed = 0

    try:
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            csv_reader = csv.DictReader(csvfile)

            # Check required columns
            if (
                "url" not in csv_reader.fieldnames
                and "image_url" not in csv_reader.fieldnames
            ):
                print("Error: CSV must contain a 'url' or 'image_url' column")
                return

            # Determine column names
            url_col = "url" if "url" in csv_reader.fieldnames else "image_url"
            filename_col = next(
                (
                    col
                    for col in csv_reader.fieldnames
                    if col in ["filename", "name", "file", "image_name"]
                ),
                None,
            )

            # Process each row
            for row in csv_reader:
                total_images += 1
                image_url = row[url_col].strip()

                # Skip if URL is empty
                if not image_url:
                    print(f"Row {total_images}: Empty URL, skipping")
                    skipped += 1
                    continue

                # Determine filename
                if filename_col and row[filename_col].strip():
                    filename = row[filename_col].strip()
                else:
                    # Extract filename from URL
                    filename = os.path.basename(image_url.split("?")[0])
                    # If no extension, default to jpg
                    if "." not in filename:
                        filename += ".jpg"

                # Full path where image will be saved
                image_path = img_dir / filename

                # Download the image
                try:
                    print(f"Downloading: {image_url} -> {image_path}")
                    response = requests.get(image_url, stream=True, timeout=30)

                    if response.status_code == 200:
                        with open(image_path, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded += 1
                        print(f"✓ Downloaded: {filename}")
                    else:
                        print(
                            f"✗ Failed to download: {filename}. Status code: {response.status_code}"
                        )
                        failed += 1

                except Exception as e:
                    print(f"✗ Error downloading {filename}: {str(e)}")
                    failed += 1

    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
        return

    # Print summary
    print("\nDownload Summary:")
    print(f"Total images in CSV: {total_images}")
    print(f"Successfully downloaded: {downloaded}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Images saved to: {img_dir.absolute()}")


if __name__ == "__main__":
    download_images_from_csv()
