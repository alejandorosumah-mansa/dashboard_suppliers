import json
import os
import pandas as pd
import openai
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Get OpenAI API key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logging.error(
        "OpenAI API key not found. Make sure OPENAI_API_KEY is set in your .env file."
    )
    raise ValueError("OpenAI API key is required to run this script")


class ProducerDataProcessor:
    def __init__(self, input_json_path, output_dir="processed_data"):
        """Initialize the processor with paths for input and output."""
        self.input_json_path = input_json_path
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Load the producer data from JSON
        with open(input_json_path, "r") as f:
            self.producer_data = json.load(f)

        logging.info(f"Loaded producer data from {input_json_path}")

    def extract_and_process_data(self):
        """Extract data from producer_data.json and process it into DataFrames."""
        # Extract producer summary data
        producer_summary = []
        for producer_id, data in self.producer_data.items():
            producer_summary.append(
                {
                    "producer_id": producer_id,
                    "total_images": data.get("total_images", 0),
                    "total_messages": data.get("total_chat_messages", 0),
                    "last_active": self._get_last_activity_date(data),
                }
            )

        producer_summary_df = pd.DataFrame(producer_summary)
        logging.info("Created producer summary DataFrame")

        # Extract images data
        images = []
        for producer_id, data in self.producer_data.items():
            for image_path, image_data in data.get("tree_images", {}).items():
                image_info = {
                    "producer_id": producer_id,
                    "filename": image_data.get("filename", ""),
                    "created_date": image_data.get("created_date", ""),
                    "s3_path": image_data.get("s3_path", ""),
                }

                # Add metadata if available
                if "metadata" in image_data:
                    for key, value in image_data["metadata"].items():
                        image_info[f"meta_{key}"] = value

                images.append(image_info)

        images_df = pd.DataFrame(images)
        logging.info("Created images DataFrame")

        # Extract messages data
        messages = []
        for producer_id, data in self.producer_data.items():
            for msg in data.get("chat_history", []):
                msg_data = {
                    "producer_id": producer_id,
                    "query_time": msg.get("query_time", ""),
                    "query": msg.get("query", ""),
                    "response": msg.get("response", ""),
                    "user_id": msg.get("user_id", ""),
                }
                messages.append(msg_data)

        messages_df = pd.DataFrame(messages)
        logging.info("Created messages DataFrame")

        return {
            "producer_summary": producer_summary_df,
            "images": images_df,
            "messages": messages_df,
        }

    def _get_last_activity_date(self, data):
        """Extract the most recent activity date from a producer's data."""
        dates = []

        # Check images for dates
        for image_data in data.get("tree_images", {}).values():
            if "created_date" in image_data:
                dates.append(image_data["created_date"])

        # Check messages for dates
        for msg in data.get("chat_history", []):
            if "query_time" in msg:
                dates.append(msg["query_time"])

        if dates:
            # Convert to datetime objects and find the most recent
            datetime_objects = []
            for date_str in dates:
                try:
                    # Convert to timezone-aware datetime
                    if date_str and isinstance(date_str, str):
                        # Make sure all datetime objects are timezone-aware
                        if "Z" in date_str:
                            # Handle 'Z' notation (UTC)
                            date_str = date_str.replace("Z", "+00:00")
                        elif "+" not in date_str and "-" not in date_str[10:]:
                            # If no timezone info, assume UTC
                            date_str = date_str + "+00:00"

                        dt = datetime.fromisoformat(date_str)
                        datetime_objects.append(dt)
                except (ValueError, AttributeError) as e:
                    logging.debug(f"Could not parse date '{date_str}': {e}")
                    pass

            if datetime_objects:
                return max(datetime_objects).strftime("%Y-%m-%d")

        return None

    def generate_insights_with_openai(self, dataframes):
        """Use OpenAI to generate insights from the data."""
        producer_summary = dataframes["producer_summary"]
        images_df = dataframes["images"]
        messages_df = dataframes["messages"]

        # Prepare data summaries for OpenAI
        total_producers = len(producer_summary)
        total_images = producer_summary["total_images"].sum()
        total_messages = producer_summary["total_messages"].sum()

        # Get most common image issues if any metadata is available
        image_health_data = ""
        if "meta_leaf_condition" in images_df.columns:
            leaf_conditions = images_df["meta_leaf_condition"].value_counts().to_dict()
            image_health_data = f"Leaf conditions from images: {leaf_conditions}"

        # Extract common message topics
        message_sample = ""
        if not messages_df.empty and "query" in messages_df.columns:
            message_sample = (
                messages_df["query"].sample(min(5, len(messages_df))).tolist()
            )

        # Create a prompt for OpenAI
        prompt = f"""
        Analyze the following cocoa farmer data and provide insights:
        
        Total Producers: {total_producers}
        Total Images Uploaded: {total_images}
        Total Messages: {total_messages}
        
        {image_health_data}
        
        Sample of farmer messages:
        {message_sample}
        
        Based on this data, provide:
        1. A summary of the current state of the cocoa farms
        2. Key health issues that might be present
        3. Recommendations for improving farm productivity
        4. Estimated yield potential based on activity levels
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",  # or whatever model you prefer
                messages=[
                    {
                        "role": "system",
                        "content": "You are an agricultural expert specializing in cocoa farming.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
            )

            insights = response.choices[0].message.content
            logging.info("Generated insights using OpenAI API")
            return insights

        except Exception as e:
            logging.error(f"Error generating insights with OpenAI: {e}")
            return "Could not generate insights due to an error."

    def generate_monthly_yields_with_openai(self, dataframes):
        """Generate realistic monthly yield data using OpenAI."""
        producer_summary = dataframes["producer_summary"]

        # Calculate total trees and average activity
        total_producers = len(producer_summary)
        total_trees = producer_summary["total_images"].sum() * 100  # Rough estimate
        avg_messages = producer_summary["total_messages"].mean()

        prompt = f"""
        Generate realistic monthly cocoa yield data for a cooperative with:
        - {total_producers} farmers
        - Approximately {total_trees} trees total
        - Average of {avg_messages} messages per farmer
        
        Create monthly yield data (in kg) for the years 2021, 2022, and 2023 (up to the current month).
        Format the data as a JSON object with this structure:
        {{
            "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            "2021": [value1, value2, ...],
            "2022": [value1, value2, ...],
            "2023": [value1, value2, ...]
        }}
        
        For 2023, include actual values only for months that have already occurred (the rest should be 0).
        
        The data should reflect seasonal patterns typical for cocoa farming in West Africa,
        with reasonable year-over-year growth based on improved farming practices.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data scientist specializing in agricultural yield forecasting.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
            )

            yield_data_str = response.choices[0].message.content

            # Extract the JSON object from the response
            import re

            json_match = re.search(r"({[\s\S]*})", yield_data_str)
            if json_match:
                yield_data_json = json_match.group(1)
                try:
                    yield_data = json.loads(yield_data_json)
                    logging.info("Generated monthly yield data using OpenAI API")
                    return yield_data
                except json.JSONDecodeError:
                    logging.error(
                        "Failed to parse monthly yield JSON from OpenAI response"
                    )

            # Fallback to default data
            return {
                "months": [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ],
                "2021": [850, 720, 640, 590, 480, 420, 380, 450, 720, 980, 1050, 920],
                "2022": [880, 750, 670, 610, 500, 440, 400, 480, 750, 1020, 1080, 950],
                "2023": [910, 780, 700, 630, 520, 460, 0, 0, 0, 0, 0, 0],
            }

        except Exception as e:
            logging.error(f"Error generating monthly yield data with OpenAI: {e}")
            # Return default data
            return {
                "months": [
                    "Jan",
                    "Feb",
                    "Mar",
                    "Apr",
                    "May",
                    "Jun",
                    "Jul",
                    "Aug",
                    "Sep",
                    "Oct",
                    "Nov",
                    "Dec",
                ],
                "2021": [850, 720, 640, 590, 480, 420, 380, 450, 720, 980, 1050, 920],
                "2022": [880, 750, 670, 610, 500, 440, 400, 480, 750, 1020, 1080, 950],
                "2023": [910, 780, 700, 630, 520, 460, 0, 0, 0, 0, 0, 0],
            }

    def generate_disease_reports_with_openai(self, dataframes):
        """Generate disease report data using OpenAI."""
        images_df = dataframes["images"]

        # Extract any disease-related metadata if available
        disease_info = ""

        for col in images_df.columns:
            if "meta_" in col and any(
                term in col for term in ["disease", "health", "condition", "leaf"]
            ):
                values = images_df[col].value_counts().to_dict()
                disease_info += f"{col.replace('meta_', '')}: {values}\n"

        if not disease_info:
            disease_info = "No specific disease metadata available in the images."

        prompt = f"""
        Based on the following image metadata from cocoa farms:
        
        {disease_info}
        
        Generate realistic disease report data for common cocoa diseases in West Africa.
        Format your response as a JSON object with disease names as keys and the number of reported cases as values:
        
        {{
            "black_pod": X,
            "swollen_shoot": Y,
            "capsid_damage": Z,
            "stem_borer": W,
            "other": V
        }}
        
        The total number of reports should be between 80-120, distributed realistically based on 
        prevalence patterns typical for West African cocoa farms.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a plant pathologist specializing in cocoa diseases.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=400,
            )

            disease_data_str = response.choices[0].message.content

            # Extract the JSON object from the response
            import re

            json_match = re.search(r"({[\s\S]*})", disease_data_str)
            if json_match:
                disease_data_json = json_match.group(1)
                try:
                    disease_data = json.loads(disease_data_json)
                    logging.info("Generated disease report data using OpenAI API")
                    return disease_data
                except json.JSONDecodeError:
                    logging.error(
                        "Failed to parse disease report JSON from OpenAI response"
                    )

            # Fallback
            return {
                "black_pod": 32,
                "swollen_shoot": 18,
                "capsid_damage": 26,
                "stem_borer": 14,
                "other": 11,
            }

        except Exception as e:
            logging.error(f"Error generating disease report data with OpenAI: {e}")
            return {
                "black_pod": 32,
                "swollen_shoot": 18,
                "capsid_damage": 26,
                "stem_borer": 14,
                "other": 11,
            }

    def generate_producer_details_with_openai(self, producer_id, producer_data):
        """Generate realistic producer details using OpenAI."""
        total_images = producer_data.get("total_images", 0)
        total_messages = producer_data.get("total_chat_messages", 0)

        # Extract some messages if available
        messages = []
        if "chat_history" in producer_data:
            for msg in producer_data["chat_history"][:3]:  # Just grab a few
                if "query" in msg:
                    messages.append(msg["query"])

        message_context = (
            f"Sample messages from the producer:\n" + "\n".join(messages)
            if messages
            else "No message samples available."
        )

        prompt = f"""
        Generate realistic profile data for a cocoa farmer in West Africa with the following activity:
        - Producer ID: {producer_id}
        - Total images uploaded: {total_images}
        - Total messages sent: {total_messages}
        
        {message_context}
        
        Return a JSON object with the following fields:
        - name: A realistic name for a farmer in West Africa
        - village: A realistic village name in a cocoa growing region
        - age: A reasonable age (between 30-65)
        - join_date: When they joined the cooperative (between 2018-2022)
        - farm_size_hectares: Farm size (between 2-15 hectares)
        - num_trees: Number of cocoa trees (between 200-1200)
        - phone: A realistic West African phone number
        - yield_history: Yield history for 2020, 2021, and 2022 in kg
        - estimated_yield: Estimated yield for current year
        - tree_health: Percentage breakdown of tree health (healthy, minor_issues, needs_attention)
        - soil_quality: Soil quality information (pH, nitrogen, phosphorus, potassium)
        
        Make the data realistic and consistent with cocoa farming in West Africa.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data specialist for an agricultural cooperative.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
            )

            producer_data_str = response.choices[0].message.content

            # Extract the JSON object from the response
            import re

            json_match = re.search(r"({[\s\S]*})", producer_data_str)
            if json_match:
                producer_data_json = json_match.group(1)
                try:
                    producer_details = json.loads(producer_data_json)
                    logging.info(
                        f"Generated details for producer {producer_id} using OpenAI API"
                    )
                    return producer_details
                except json.JSONDecodeError:
                    logging.error(
                        f"Failed to parse producer details JSON for {producer_id}"
                    )

            # Fallback data
            return {
                "name": f"Producer {producer_id}",
                "village": "Unknown",
                "age": 40,
                "join_date": "2020-01-01",
                "farm_size_hectares": 5.0,
                "num_trees": total_images * 100,
                "phone": "+225 00000000",
                "yield_history": {"2020": 3000, "2021": 3200, "2022": 3400},
                "estimated_yield": 3600,
                "tree_health": {
                    "healthy": 75,
                    "minor_issues": 20,
                    "needs_attention": 5,
                },
                "soil_quality": {
                    "pH": 6.5,
                    "nitrogen": "Medium",
                    "phosphorus": "Medium",
                    "potassium": "Medium",
                },
            }

        except Exception as e:
            logging.error(
                f"Error generating producer details with OpenAI for {producer_id}: {e}"
            )
            return {
                "name": f"Producer {producer_id}",
                "village": "Unknown",
                "age": 40,
                "join_date": "2020-01-01",
                "farm_size_hectares": 5.0,
                "num_trees": total_images * 100,
                "phone": "+225 00000000",
                "yield_history": {"2020": 3000, "2021": 3200, "2022": 3400},
                "estimated_yield": 3600,
                "tree_health": {
                    "healthy": 75,
                    "minor_issues": 20,
                    "needs_attention": 5,
                },
                "soil_quality": {
                    "pH": 6.5,
                    "nitrogen": "Medium",
                    "phosphorus": "Medium",
                    "potassium": "Medium",
                },
            }

    def create_dashboard_csvs(self, dataframes, insights):
        """Transform the extracted data into the format needed by the dashboard."""
        # Create a cooperative info using OpenAI
        try:
            coop_prompt = f"""
            Generate realistic cooperative information for a cocoa producers' cooperative in West Africa with {len(dataframes["producer_summary"])} members.
            Return a JSON object with:
            - name: A descriptive name for the cooperative
            - location: A specific region/country in West Africa known for cocoa
            - established: Year established (between 2000-2015)
            - total_members: {len(dataframes["producer_summary"])}
            - active_members: A realistic number of active members (slightly less than total)
            - total_hectares: Total hectares under cultivation
            - certification: A list of certifications the cooperative might have (2-4 certifications)
            """

            coop_response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data specialist for agricultural cooperatives.",
                    },
                    {"role": "user", "content": coop_prompt},
                ],
                max_tokens=400,
            )

            coop_data_str = coop_response.choices[0].message.content
            import re

            json_match = re.search(r"({[\s\S]*})", coop_data_str)
            if json_match:
                coop_info = json.loads(json_match.group(1))
                logging.info("Generated cooperative info using OpenAI API")
            else:
                # Fallback cooperative info
                coop_info = {
                    "name": "Cocoa Producers Cooperative",
                    "location": "Ivory Coast",
                    "established": 2010,
                    "total_members": len(dataframes["producer_summary"]),
                    "active_members": len(dataframes["producer_summary"]),
                    "total_hectares": 500,
                    "certification": ["Organic", "Fairtrade"],
                }
        except Exception as e:
            logging.error(f"Error generating cooperative info with OpenAI: {e}")
            # Fallback cooperative info
            coop_info = {
                "name": "Cocoa Producers Cooperative",
                "location": "Ivory Coast",
                "established": 2010,
                "total_members": len(dataframes["producer_summary"]),
                "active_members": len(dataframes["producer_summary"]),
                "total_hectares": 500,
                "certification": ["Organic", "Fairtrade"],
            }

        # Convert certifications to JSON string
        coop_info["certification"] = json.dumps(coop_info["certification"])

        coop_df = pd.DataFrame([coop_info])
        coop_df.to_csv(f"{self.output_dir}/cooperative_info.csv", index=False)
        logging.info(
            f"Saved cooperative info to {self.output_dir}/cooperative_info.csv"
        )

        # Generate monthly yield data
        monthly_yields = self.generate_monthly_yields_with_openai(dataframes)

        # Generate disease reports
        disease_reports = self.generate_disease_reports_with_openai(dataframes)

        # Create producers data with AI-generated details
        producers = []
        for _, row in dataframes["producer_summary"].iterrows():
            producer_id = row["producer_id"]

            # Get original producer data
            producer_orig_data = self.producer_data.get(producer_id, {})

            # Generate detailed producer info using OpenAI
            producer_details = self.generate_producer_details_with_openai(
                producer_id, producer_orig_data
            )

            # Get the messages for this producer
            producer_messages = dataframes["messages"][
                dataframes["messages"]["producer_id"] == producer_id
            ]

            # Create a producer record with AI-generated data
            producer = {
                "id": int(producers.__len__() + 1),  # Sequential ID
                "producer_id": producer_id,  # Original ID
                "name": producer_details["name"],
                "village": producer_details["village"],
                "age": producer_details["age"],
                "join_date": producer_details["join_date"],
                "farm_size_hectares": producer_details["farm_size_hectares"],
                "num_trees": producer_details["num_trees"],
                "phone": producer_details["phone"],
                "farm_images": json.dumps([]),  # Empty list as requested
                "yield_history": json.dumps(producer_details["yield_history"]),
                "estimated_yield": producer_details["estimated_yield"],
                "recent_activities": json.dumps(
                    [
                        {
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "activity": "Data imported from producer records",
                        }
                    ]
                ),
                "tree_health": json.dumps(producer_details["tree_health"]),
                "soil_quality": json.dumps(producer_details["soil_quality"]),
                "last_active": row["last_active"]
                or datetime.now().strftime("%Y-%m-%d"),
            }

            producers.append(producer)

        producers_df = pd.DataFrame(producers)
        producers_df.to_csv(f"{self.output_dir}/producers.csv", index=False)
        logging.info(f"Saved producers data to {self.output_dir}/producers.csv")

        # Create training attendance data with OpenAI
        try:
            training_prompt = "Generate realistic training attendance percentages for 5 different training types offered to cocoa farmers. Return a JSON object where keys are training types and values are attendance percentages (0-100)."

            training_response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a training coordinator for agricultural cooperatives.",
                    },
                    {"role": "user", "content": training_prompt},
                ],
                max_tokens=200,
            )

            training_data_str = training_response.choices[0].message.content
            import re

            json_match = re.search(r"({[\s\S]*})", training_data_str)
            if json_match:
                training_attendance = json.loads(json_match.group(1))
                logging.info("Generated training attendance data using OpenAI API")
            else:
                # Fallback
                training_attendance = {
                    "pest_management": 88,
                    "harvesting_techniques": 72,
                    "fermentation_workshop": 65,
                    "sustainable_practices": 93,
                    "quality_control": 79,
                }
        except Exception as e:
            logging.error(f"Error generating training attendance with OpenAI: {e}")
            # Fallback
            training_attendance = {
                "pest_management": 88,
                "harvesting_techniques": 72,
                "fermentation_workshop": 65,
                "sustainable_practices": 93,
                "quality_control": 79,
            }

        # Create aggregate data with insights from OpenAI
        aggregate_data = {
            "monthly_yields": json.dumps(monthly_yields),
            "disease_reports": json.dumps(disease_reports),
            "training_attendance": json.dumps(training_attendance),
            "ai_insights": insights,
        }

        aggregate_df = pd.DataFrame([aggregate_data])
        aggregate_df.to_csv(f"{self.output_dir}/aggregate.csv", index=False)
        logging.info(f"Saved aggregate data to {self.output_dir}/aggregate.csv")

        # Create chat history data from real messages
        chat_messages = []
        for _, row in dataframes["messages"].iterrows():
            # Use a default date if query_time is empty
            date_str = row.get("query_time", "")
            try:
                date = (
                    datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if date_str
                    else datetime.now()
                )
                date_formatted = date.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                date_formatted = datetime.now().strftime("%Y-%m-%d")

            # Find the corresponding producer
            producer_id = row.get("producer_id", "")
            producer_seq_id = 1  # Default
            for p in producers:
                if p["producer_id"] == producer_id:
                    producer_seq_id = p["id"]
                    break

            chat_messages.append(
                {
                    "producer_id": int(producer_seq_id),
                    "date": date_formatted,
                    "from": "farmer",
                    "message": row.get("query", ""),
                }
            )

            if row.get("response", ""):
                chat_messages.append(
                    {
                        "producer_id": int(producer_seq_id),
                        "date": date_formatted,
                        "from": "advisor",
                        "message": row.get("response", ""),
                    }
                )

        if not chat_messages:
            # Generate some placeholder messages with OpenAI if none exist
            try:
                chat_prompt = """
                Generate 5 realistic conversation exchanges between a cocoa farmer and an agricultural advisor.
                Each exchange should include a question from the farmer and a response from the advisor.
                Focus on common issues in cocoa farming like disease management, harvest timing, etc.
                
                Format as a JSON array of objects, each with:
                - producer_id: 1
                - date: a date in 2023 (YYYY-MM-DD format)
                - from: either "farmer" or "advisor"
                - message: the content of the message
                
                Make sure to alternate between farmer and advisor messages.
                """

                chat_response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an agricultural messaging system designer.",
                        },
                        {"role": "user", "content": chat_prompt},
                    ],
                    max_tokens=800,
                )

                chat_data_str = chat_response.choices[0].message.content
                import re

                json_match = re.search(r"(\[[\s\S]*\])", chat_data_str)
                if json_match:
                    chat_messages = json.loads(json_match.group(1))
                    logging.info("Generated chat messages using OpenAI API")
                else:
                    # Fallback
                    chat_messages = [
                        {
                            "producer_id": 1,
                            "date": "2023-07-01",
                            "from": "farmer",
                            "message": "Hello, I have a question about my cocoa trees.",
                        },
                        {
                            "producer_id": 1,
                            "date": "2023-07-01",
                            "from": "advisor",
                            "message": "Hello! What would you like to know?",
                        },
                        {
                            "producer_id": 1,
                            "date": "2023-07-01",
                            "from": "farmer",
                            "message": "Some leaves are turning yellow. What should I do?",
                        },
                        {
                            "producer_id": 1,
                            "date": "2023-07-01",
                            "from": "advisor",
                            "message": "That could be a sign of nutrient deficiency. Try adding some nitrogen-rich fertilizer.",
                        },
                    ]
            except Exception as e:
                logging.error(f"Error generating chat messages with OpenAI: {e}")
                # Fallback
                chat_messages = [
                    {
                        "producer_id": 1,
                        "date": "2023-07-01",
                        "from": "farmer",
                        "message": "Hello, I have a question about my cocoa trees.",
                    },
                    {
                        "producer_id": 1,
                        "date": "2023-07-01",
                        "from": "advisor",
                        "message": "Hello! What would you like to know?",
                    },
                    {
                        "producer_id": 1,
                        "date": "2023-07-01",
                        "from": "farmer",
                        "message": "Some leaves are turning yellow. What should I do?",
                    },
                    {
                        "producer_id": 1,
                        "date": "2023-07-01",
                        "from": "advisor",
                        "message": "That could be a sign of nutrient deficiency. Try adding some nitrogen-rich fertilizer.",
                    },
                ]

        chat_df = pd.DataFrame(chat_messages)
        chat_df.to_csv(f"{self.output_dir}/chat_history.csv", index=False)
        logging.info(f"Saved chat history to {self.output_dir}/chat_history.csv")


def main():
    # Set paths
    input_json_path = "producer_data/producer_data.json"
    output_dir = "processed_data"

    # Process the data
    processor = ProducerDataProcessor(input_json_path, output_dir)

    # Extract and process data
    dataframes = processor.extract_and_process_data()

    # Generate insights with OpenAI
    insights = processor.generate_insights_with_openai(dataframes)

    # Create dashboard CSVs with AI-generated data
    processor.create_dashboard_csvs(dataframes, insights)

    # Save the intermediate DataFrames as CSVs for reference
    dataframes["producer_summary"].to_csv(
        f"{output_dir}/producer_summary.csv", index=False
    )
    dataframes["images"].to_csv(f"{output_dir}/images.csv", index=False)
    dataframes["messages"].to_csv(f"{output_dir}/messages.csv", index=False)

    logging.info("Data processing complete!")


if __name__ == "__main__":
    main()
