import pandas as pd
import json
import os

# Create a data directory if it doesn't exist
if not os.path.exists("data"):
    os.makedirs("data")

# Sample data from producers_data (as in your app.py)
# Mock data for a cocoa cooperative in Ivory Coast
producers_data = {
    "cooperative_info": {
        "name": "Coopérative Agricole de Côte d'Ivoire",
        "location": "Aboisso, Ivory Coast",
        "established": 2008,
        "total_members": 150,
        "active_members": 132,
        "total_hectares": 860,
        "certification": ["Rainforest Alliance", "UTZ", "Fairtrade"],
    },
    "producers": [
        {
            "id": 1,
            "name": "Kouadio Konan",
            "village": "Abengourou",
            "age": 45,
            "join_date": "2010-03-15",
            "farm_size_hectares": 5.2,
            "num_trees": 4200,
            "phone": "+225 0701234567",
            "profile_image": "farmer1.jpg",
            "farm_images": ["farm1_1.jpg", "farm1_2.jpg", "farm1_3.jpg"],
            "yield_history": {"2020": 4800, "2021": 5100, "2022": 5300},
            "estimated_yield": 5500,
            "recent_activities": [
                {"date": "2023-06-15", "activity": "Applied fungicide treatment"},
                {
                    "date": "2023-05-28",
                    "activity": "Reported black pod disease in section 3",
                },
                {"date": "2023-05-10", "activity": "Completed pruning"},
            ],
            "tree_health": {"healthy": 80, "minor_issues": 15, "needs_attention": 5},
            "soil_quality": {
                "pH": 6.2,
                "nitrogen": "Medium",
                "phosphorus": "High",
                "potassium": "Medium",
            },
            "last_active": "2023-06-28",
        },
        {
            "id": 2,
            "name": "Amara Bamba",
            "village": "Divo",
            "age": 38,
            "join_date": "2012-07-22",
            "farm_size_hectares": 3.8,
            "num_trees": 3100,
            "phone": "+225 0702345678",
            "profile_image": "farmer2.jpg",
            "farm_images": ["farm2_1.jpg", "farm2_2.jpg"],
            "yield_history": {"2020": 3200, "2021": 3400, "2022": 3600},
            "estimated_yield": 3800,
            "recent_activities": [
                {"date": "2023-06-20", "activity": "Harvested central section"},
                {"date": "2023-06-05", "activity": "Applied organic fertilizer"},
                {"date": "2023-05-15", "activity": "Reported water shortage issues"},
            ],
            "tree_health": {"healthy": 75, "minor_issues": 20, "needs_attention": 5},
            "soil_quality": {
                "pH": 6.5,
                "nitrogen": "Low",
                "phosphorus": "Medium",
                "potassium": "High",
            },
            "last_active": "2023-06-25",
        },
        {
            "id": 3,
            "name": "Fatou Diallo",
            "village": "Daloa",
            "age": 41,
            "join_date": "2009-04-10",
            "farm_size_hectares": 6.5,
            "num_trees": 5200,
            "phone": "+225 0703456789",
            "profile_image": "farmer3.jpg",
            "farm_images": ["farm3_1.jpg", "farm3_2.jpg", "farm3_3.jpg", "farm3_4.jpg"],
            "yield_history": {"2020": 6100, "2021": 6400, "2022": 6200},
            "estimated_yield": 6700,
            "recent_activities": [
                {"date": "2023-06-18", "activity": "Installed new irrigation system"},
                {"date": "2023-06-02", "activity": "Completed soil testing"},
                {"date": "2023-05-20", "activity": "Added shade trees in section 2"},
            ],
            "tree_health": {"healthy": 85, "minor_issues": 12, "needs_attention": 3},
            "soil_quality": {
                "pH": 6.8,
                "nitrogen": "High",
                "phosphorus": "High",
                "potassium": "Medium",
            },
            "last_active": "2023-06-27",
        },
        {
            "id": 4,
            "name": "Ibrahim Kone",
            "village": "Aboisso",
            "age": 52,
            "join_date": "2008-09-05",
            "farm_size_hectares": 7.2,
            "num_trees": 5900,
            "phone": "+225 0704567890",
            "profile_image": "farmer4.jpg",
            "farm_images": ["farm4_1.jpg", "farm4_2.jpg"],
            "yield_history": {"2020": 6800, "2021": 6500, "2022": 7000},
            "estimated_yield": 7200,
            "recent_activities": [
                {
                    "date": "2023-06-12",
                    "activity": "Reported swollen shoot virus in eastern plot",
                },
                {"date": "2023-05-30", "activity": "Attended pest management workshop"},
                {"date": "2023-05-08", "activity": "Completed harvest of main section"},
            ],
            "tree_health": {"healthy": 70, "minor_issues": 20, "needs_attention": 10},
            "soil_quality": {
                "pH": 6.0,
                "nitrogen": "Medium",
                "phosphorus": "Low",
                "potassium": "Medium",
            },
            "last_active": "2023-06-22",
        },
        {
            "id": 5,
            "name": "Aya Koné",
            "village": "Agboville",
            "age": 35,
            "join_date": "2015-02-18",
            "farm_size_hectares": 4.3,
            "num_trees": 3500,
            "phone": "+225 0705678901",
            "profile_image": "farmer5.jpg",
            "farm_images": ["farm5_1.jpg", "farm5_2.jpg", "farm5_3.jpg"],
            "yield_history": {"2020": 3600, "2021": 3900, "2022": 4200},
            "estimated_yield": 4500,
            "recent_activities": [
                {"date": "2023-06-25", "activity": "Applied eco-friendly pest control"},
                {
                    "date": "2023-06-10",
                    "activity": "Planted new seedlings in section 1",
                },
                {
                    "date": "2023-05-22",
                    "activity": "Reported good flowering on new trees",
                },
            ],
            "tree_health": {"healthy": 88, "minor_issues": 10, "needs_attention": 2},
            "soil_quality": {
                "pH": 6.7,
                "nitrogen": "High",
                "phosphorus": "Medium",
                "potassium": "High",
            },
            "last_active": "2023-06-29",
        },
    ],
    "chat_history": [
        {
            "producer_id": 1,
            "messages": [
                {
                    "date": "2023-06-28",
                    "from": "farmer",
                    "message": "I've noticed some yellowing leaves on the east section.",
                },
                {
                    "date": "2023-06-28",
                    "from": "advisor",
                    "message": "Can you send a photo of the affected trees?",
                },
                {
                    "date": "2023-06-28",
                    "from": "farmer",
                    "message": "Yes, I've uploaded 3 images through the app.",
                },
                {
                    "date": "2023-06-29",
                    "from": "advisor",
                    "message": "I've reviewed your images. This appears to be a minor nutrient deficiency. Please apply the recommended fertilizer we discussed last month.",
                },
            ],
        },
        {
            "producer_id": 2,
            "messages": [
                {
                    "date": "2023-06-25",
                    "from": "farmer",
                    "message": "When is the next pickup scheduled?",
                },
                {
                    "date": "2023-06-25",
                    "from": "advisor",
                    "message": "The next pickup is scheduled for July 5th. Please have your harvest ready by then.",
                },
                {
                    "date": "2023-06-25",
                    "from": "farmer",
                    "message": "Great, thank you for the information.",
                },
            ],
        },
        {
            "producer_id": 3,
            "messages": [
                {
                    "date": "2023-06-27",
                    "from": "farmer",
                    "message": "The new irrigation system is working well.",
                },
                {
                    "date": "2023-06-27",
                    "from": "advisor",
                    "message": "Excellent news! Have you noticed any improvements in the trees?",
                },
                {
                    "date": "2023-06-27",
                    "from": "farmer",
                    "message": "Yes, the younger trees are showing more growth.",
                },
                {
                    "date": "2023-06-27",
                    "from": "advisor",
                    "message": "That's great. Please monitor water usage and log it in the app.",
                },
            ],
        },
    ],
    "aggregate_data": {
        "monthly_yields": {
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
        },
        "disease_reports": {
            "black_pod": 32,
            "swollen_shoot": 18,
            "capsid_damage": 26,
            "stem_borer": 14,
            "other": 11,
        },
        "training_attendance": {
            "pest_management": 88,
            "harvesting_techniques": 72,
            "fermentation_workshop": 65,
            "sustainable_practices": 93,
            "quality_control": 79,
        },
    },
}
# 1. Save cooperative info to CSV
coop_df = pd.DataFrame([producers_data["cooperative_info"]])
# Convert certification list to a string
coop_df["certification"] = coop_df["certification"].apply(lambda x: json.dumps(x))
coop_df.to_csv("data/cooperative_info.csv", index=False)

# 2. Save producers to CSV
# First, flatten complex nested structures
producers_flat = []
for producer in producers_data["producers"]:
    producer_flat = producer.copy()
    # Convert complex nested structures to JSON strings
    producer_flat["yield_history"] = json.dumps(producer["yield_history"])
    producer_flat["tree_health"] = json.dumps(producer["tree_health"])
    producer_flat["soil_quality"] = json.dumps(producer["soil_quality"])
    producer_flat["farm_images"] = json.dumps(producer["farm_images"])
    producer_flat["recent_activities"] = json.dumps(producer["recent_activities"])
    producers_flat.append(producer_flat)

# Save to CSV
producers_df = pd.DataFrame(producers_flat)
producers_df.to_csv("data/producers.csv", index=False)

# 3. Save aggregate data to CSV
aggregate_flat = {}
for key, value in producers_data["aggregate_data"].items():
    if isinstance(value, dict):
        aggregate_flat[key] = json.dumps(value)
    else:
        aggregate_flat[key] = value

aggregate_df = pd.DataFrame([aggregate_flat])
aggregate_df.to_csv("data/aggregate.csv", index=False)

print("Data converted and saved to CSV files in the 'data' directory.")
# 4. Save chat history to CSV - Add this new section
chat_messages = []
for chat in producers_data["chat_history"]:
    producer_id = chat["producer_id"]
    for message in chat["messages"]:
        chat_messages.append(
            {
                "producer_id": producer_id,
                "date": message["date"],
                "from": message["from"],
                "message": message["message"],
            }
        )

chat_df = pd.DataFrame(chat_messages)
chat_df.to_csv("data/chat_history.csv", index=False)

print("Data converted and saved to CSV files in the 'data' directory.")
