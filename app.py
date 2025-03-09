from flask import Flask, render_template, request, jsonify
import json
import random
from datetime import datetime, timedelta
import os
import pandas as pd
import boto3
import re
from urllib.parse import urlparse

app = Flask(__name__)


# Load data from CSV files
def load_data_from_csv():
    # Load cooperative info
    coop_df = pd.read_csv("processed_data/cooperative_info.csv")
    coop_info = coop_df.iloc[0].to_dict()
    # Convert certification string back to list
    coop_info["certification"] = json.loads(coop_info["certification"])

    # Load producers
    producers_df = pd.read_csv("processed_data/producers.csv")
    producers = []
    for _, row in producers_df.iterrows():
        producer = row.to_dict()
        # Convert JSON strings back to original structures
        producer["yield_history"] = json.loads(producer["yield_history"])
        producer["tree_health"] = json.loads(producer["tree_health"])
        producer["soil_quality"] = json.loads(producer["soil_quality"])
        producer["recent_activities"] = json.loads(producer["recent_activities"])

        # Remove profile_image entirely - don't even include the field
        if "profile_image" in producer:
            del producer["profile_image"]

        # Remove farm_images to prevent any image processing
        producer["farm_images"] = []

        producers.append(producer)

    # Load aggregate data
    aggregate_df = pd.read_csv("processed_data/aggregate.csv")
    aggregate = aggregate_df.iloc[0].to_dict()
    # Convert JSON strings back to original structures
    for key, value in aggregate.items():
        if isinstance(value, str) and value.startswith("{"):
            aggregate[key] = json.loads(value)

    # Load chat history
    chat_df = pd.read_csv("processed_data/chat_history.csv")
    chat_history = []

    # Group by producer_id
    for producer_id, group in chat_df.groupby("producer_id"):
        messages = []
        for _, row in group.iterrows():
            messages.append(
                {"date": row["date"], "from": row["from"], "message": row["message"]}
            )

        chat_history.append({"producer_id": producer_id, "messages": messages})

    # Recreate the producers_data structure
    producers_data = {
        "cooperative_info": coop_info,
        "producers": producers,
        "aggregate": aggregate,
        "chat_history": chat_history,
    }

    return producers_data


# Generate some diagnostic data
def generate_diagnostics_data():
    diagnostics_data = []
    for i in range(100):
        random_date = datetime.now() - timedelta(days=random.randint(1, 180))
        diagnostics_data.append(
            {
                "producer_id": random.randint(1, 5),
                "date": random_date.strftime("%Y-%m-%d"),
                "tree_id": f"TR-{random.randint(100, 999)}",
                "health_score": random.randint(60, 100),
                "leaf_condition": random.choice(
                    ["Healthy", "Yellowing", "Spots", "Wilting"]
                ),
                "pest_detected": random.choice([True, False, False, False]),
                "disease_risk": random.choice(["Low", "Medium", "High", "Low", "Low"]),
                "recommended_action": random.choice(
                    ["None", "Fertilize", "Treat for Pests", "Pruning", "Water", "None"]
                ),
            }
        )
    return diagnostics_data


@app.route("/")
def dashboard():
    # Load data from CSV
    producers_data = load_data_from_csv()

    # Generate diagnostic data
    diagnostics_data = generate_diagnostics_data()

    # Get aggregated data
    coop_info = producers_data["cooperative_info"]
    producers = producers_data["producers"]
    aggregate = producers_data["aggregate"]

    # Calculate summary statistics
    total_trees = sum(p["num_trees"] for p in producers)
    avg_health = (
        sum(
            (
                int(p["tree_health"]["healthy"].replace("%", ""))
                if isinstance(p["tree_health"]["healthy"], str)
                else p["tree_health"]["healthy"]
            )
            for p in producers
        )
        / len(producers)
        if producers
        else 0
    )
    estimated_yield_current = sum(p["estimated_yield"] for p in producers)

    # Convert data to JSON for JavaScript
    producers_json = json.dumps(producers)
    chat_json = json.dumps(producers_data["chat_history"])
    aggregate_json = json.dumps(aggregate)
    diagnostics_json = json.dumps(diagnostics_data)

    return render_template(
        "dashboard.html",
        coop_info=coop_info,
        producers=producers,
        total_trees=total_trees,
        avg_health=avg_health,
        estimated_yield=estimated_yield_current,
        producers_json=producers_json,
        chat_json=chat_json,
        aggregate_json=aggregate_json,
        diagnostics_json=diagnostics_json,
        aggregate=aggregate,
    )


@app.route("/producer/<int:producer_id>")
def producer_detail(producer_id):
    # Load data from CSV
    producers_data = load_data_from_csv()

    # Generate diagnostic data
    diagnostics_data = generate_diagnostics_data()

    producer = next(
        (p for p in producers_data["producers"] if p["id"] == producer_id), None
    )
    if not producer:
        return "Producer not found", 404

    # Get chat history for this producer
    chat_history = next(
        (c for c in producers_data["chat_history"] if c["producer_id"] == producer_id),
        {"messages": []},
    )

    # Get diagnostics for this producer
    producer_diagnostics = [
        d for d in diagnostics_data if d["producer_id"] == producer_id
    ]

    return render_template(
        "producer_detail.html",
        producer=producer,
        chat_history=chat_history,
        diagnostics=producer_diagnostics,
    )


@app.route("/activity/<int:producer_id>/<path:activity_date>")
def activity_detail(producer_id, activity_date):
    """View details for a specific activity."""
    # Load data from CSV
    producers_data = load_data_from_csv()

    producer = next(
        (p for p in producers_data["producers"] if p["id"] == producer_id), None
    )
    if not producer:
        return "Producer not found", 404

    # Find the activity by date
    activity = next(
        (a for a in producer["recent_activities"] if a["date"] == activity_date), None
    )

    if not activity:
        return "Activity not found", 404

    # No more image loading - completely removed

    return render_template("activity_detail.html", producer=producer, activity=activity)


if __name__ == "__main__":
    # Create a static directory for images if it doesn't exist
    if not os.path.exists("static/img"):
        os.makedirs("static/img")

    app.run(debug=True, port=5011)
