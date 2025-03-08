import os
import boto3
import json
import pandas as pd
from datetime import datetime
from collections import defaultdict
from PIL import Image
import io
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
# Try looking in different directories if needed
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("../.env"):
    load_dotenv("../.env")
elif os.path.exists("dashboard_suppliers/.env"):
    load_dotenv("dashboard_suppliers/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Print environment variables for debugging
logger.info(f"S3_BUCKET_NAME: {os.environ.get('S3_BUCKET_NAME')}")
logger.info(f"AWS_REGION: {os.environ.get('AWS_REGION')}")


class S3DataExtractor:
    """Class to extract and organize producer data from S3 bucket."""

    def __init__(
        self, bucket_name, aws_region="us-east-1", local_output_dir="./extracted_data"
    ):
        """
        Initialize the extractor with bucket details and output location.

        Args:
            bucket_name (str): Name of the S3 bucket
            aws_region (str): AWS region of the bucket
            local_output_dir (str): Directory to save data locally (if needed)
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3", region_name=aws_region)
        self.s3_resource = boto3.resource("s3", region_name=aws_region)
        self.bucket = self.s3_resource.Bucket(bucket_name)
        self.local_output_dir = local_output_dir

        # Create output directory if it doesn't exist
        if not os.path.exists(local_output_dir):
            os.makedirs(local_output_dir)

    def list_producers(self):
        """
        List all producer folders in the bucket.

        Returns:
            list: List of producer folder names
        """
        producers = set()
        try:
            # List all objects in the bucket
            objects = self.bucket.objects.all()

            # Extract unique producer folder names
            for obj in objects:
                path_parts = obj.key.split("/")
                if len(path_parts) > 1:  # Ensure it's inside a folder
                    producers.add(path_parts[0])

            logger.info(f"Found {len(producers)} producer directories")
            return sorted(list(producers))

        except Exception as e:
            logger.error(f"Error listing producers: {str(e)}")
            return []

    def extract_chat_history(self, producer_folder):
        """
        Extract chat history for a specific producer.

        Args:
            producer_folder (str): Producer folder name

        Returns:
            list: List of chat messages with metadata
        """
        chat_history = []

        try:
            # Look for JSON files in the chat_history subfolder of the producer folder
            chat_prefix = f"{producer_folder}/chat_history/"
            for obj in self.bucket.objects.filter(Prefix=chat_prefix):
                if obj.key.endswith(".json"):
                    logger.info(f"Found chat history file: {obj.key}")
                    content = (
                        self.s3_client.get_object(Bucket=self.bucket_name, Key=obj.key)[
                            "Body"
                        ]
                        .read()
                        .decode("utf-8")
                    )
                    try:
                        chat_data = json.loads(content)
                        if isinstance(chat_data, list):
                            chat_history.extend(chat_data)
                        elif isinstance(chat_data, dict):
                            chat_history.append(chat_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON from {obj.key}: {str(e)}")

            # Sort by timestamp if available
            if (
                chat_history
                and isinstance(chat_history[0], dict)
                and "timestamp" in chat_history[0]
            ):
                chat_history.sort(key=lambda x: x.get("timestamp", ""))

            return chat_history

        except Exception as e:
            logger.error(
                f"Error extracting chat history for {producer_folder}: {str(e)}"
            )
            return []

    def extract_tree_images(self, producer_folder):
        """
        Extract tree images for a specific producer.

        Args:
            producer_folder (str): Producer folder name

        Returns:
            dict: Dictionary mapping image paths to metadata
        """
        image_data = {}

        try:
            # Look for images directly in the producer's folder
            image_extensions = (".jpg", ".jpeg", ".png", ".gif")

            # Look in the main producer folder
            for obj in self.bucket.objects.filter(Prefix=f"{producer_folder}/"):
                if obj.key.lower().endswith(image_extensions):
                    # Extract metadata
                    metadata = self.s3_client.head_object(
                        Bucket=self.bucket_name, Key=obj.key
                    ).get("Metadata", {})

                    # Extract creation date and filename
                    filename = os.path.basename(obj.key)
                    created_date = obj.last_modified

                    # Store path and metadata
                    image_data[obj.key] = {
                        "filename": filename,
                        "created_date": created_date,
                        "metadata": metadata,
                        "s3_path": f"s3://{self.bucket_name}/{obj.key}",
                    }
                    logger.info(f"Found image: {filename} in {producer_folder}")

            return image_data

        except Exception as e:
            logger.error(
                f"Error extracting tree images for {producer_folder}: {str(e)}"
            )
            return {}

    def download_image(self, s3_key, local_path=None):
        """
        Download an image from S3.

        Args:
            s3_key (str): S3 object key
            local_path (str, optional): Path to save the image locally

        Returns:
            PIL.Image or None: Image object if successful, None if failed
        """
        try:
            # Get the image data
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            image_data = response["Body"].read()

            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))

            # Save locally if path provided
            if local_path:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                image.save(local_path)

            return image

        except Exception as e:
            logger.error(f"Error downloading image {s3_key}: {str(e)}")
            return None

    def extract_all_producer_data(self):
        """
        Extract data for all producers.

        Returns:
            dict: Dictionary mapping producer names to their data (chat history and images)
        """
        all_data = {}
        producers = self.list_producers()

        for producer in producers:
            logger.info(f"Processing producer: {producer}")

            # Extract data for this producer
            chat_history = self.extract_chat_history(producer)
            tree_images = self.extract_tree_images(producer)

            # Store in the result dictionary
            all_data[producer] = {
                "producer_id": producer,
                "chat_history": chat_history,
                "tree_images": tree_images,
                "total_images": len(tree_images),
                "total_chat_messages": len(chat_history),
            }

        logger.info(f"Completed extraction for {len(producers)} producers")
        return all_data

    def save_as_json(self, data, filename="producer_data.json"):
        """
        Save the extracted data as JSON.

        Args:
            data (dict): Data to save
            filename (str): Filename to save as

        Returns:
            str: Path to the saved file
        """
        file_path = os.path.join(self.local_output_dir, filename)

        # Convert datetime objects to strings for JSON serialization
        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(file_path, "w") as f:
            json.dump(data, f, default=json_serial, indent=2)

        logger.info(f"Data saved to {file_path}")
        return file_path

    def create_analysis_dataframes(self, producer_data):
        """
        Create pandas DataFrames for analysis.

        Args:
            producer_data (dict): Extracted producer data

        Returns:
            dict: Dictionary containing various DataFrames
        """
        # Producer summary DataFrame
        producer_summary = []
        for producer_id, data in producer_data.items():
            producer_summary.append(
                {
                    "producer_id": producer_id,
                    "total_images": data["total_images"],
                    "total_messages": data["total_chat_messages"],
                }
            )

        producer_df = pd.DataFrame(producer_summary)

        # Chat messages DataFrame
        messages = []
        for producer_id, data in producer_data.items():
            for msg in data["chat_history"]:
                msg_data = {
                    "producer_id": producer_id,
                }

                # Map query and response fields
                if isinstance(msg, dict):
                    msg_data["query"] = msg.get("query", "")
                    msg_data["response"] = msg.get("response", "")
                    msg_data["sender"] = msg.get("username", "Unknown")

                    # Try to parse timestamp if available
                    if "query_time" in msg and msg["query_time"]:
                        try:
                            msg_data["timestamp"] = pd.to_datetime(msg["query_time"])
                        except:
                            msg_data["timestamp"] = None
                else:
                    # If msg is a string, use it directly as the message
                    msg_data["query"] = str(msg)
                    msg_data["response"] = ""
                    msg_data["sender"] = "Unknown"

                messages.append(msg_data)

        messages_df = pd.DataFrame(messages)

        # Images DataFrame
        images = []
        for producer_id, data in producer_data.items():
            for image_path, image_data in data["tree_images"].items():
                image_info = {
                    "producer_id": producer_id,
                    "filename": image_data["filename"],
                    "s3_path": image_data["s3_path"],
                }

                # Add created date if available
                if "created_date" in image_data:
                    image_info["created_date"] = image_data["created_date"]

                # Add any custom metadata
                for key, value in image_data.get("metadata", {}).items():
                    image_info[f"meta_{key}"] = value

                images.append(image_info)

        images_df = pd.DataFrame(images)

        return {
            "producer_summary": producer_df,
            "messages": messages_df,
            "images": images_df,
        }


def main():
    """Main function to execute the extraction process."""
    # Read configuration from environment variables
    BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
    OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./producer_data")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

    # Validate required environment variables
    if not BUCKET_NAME:
        logger.error("S3_BUCKET_NAME environment variable is not set")
        return

    logger.info(f"Using bucket: {BUCKET_NAME} in region: {AWS_REGION}")

    # Create extractor
    extractor = S3DataExtractor(
        BUCKET_NAME, aws_region=AWS_REGION, local_output_dir=OUTPUT_DIR
    )

    # Extract all data
    producer_data = extractor.extract_all_producer_data()

    # Save as JSON
    extractor.save_as_json(producer_data)

    # Create analysis DataFrames
    dataframes = extractor.create_analysis_dataframes(producer_data)

    # Example: Save DataFrames as CSV
    for name, df in dataframes.items():
        df.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False)
        print(f"Saved {name}.csv with {len(df)} rows")

    print(f"Data extraction complete. Found {len(producer_data)} producers.")
    return producer_data


if __name__ == "__main__":
    main()
