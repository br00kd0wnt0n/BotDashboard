# api.py - Your Flask middleware
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# MongoDB connection
def get_mongodb_connection():
    try:
        mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://br00kd0wnt0wn:XHZo54P7bqrVUIzj@ralphbot.nsyijw5.mongodb.net/?retryWrites=true&w=majority&appName=RalphBot")
        client = MongoClient(mongo_uri)
        return client.ralphbot_analytics
    except Exception as e:
        print(f"MongoDB connection error: {str(e)}")
        return None

# Convert MongoDB documents to JSON-serializable format
def convert_to_serializable(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

# API Routes
@app.route('/api/status', methods=['GET'])
def get_status():
    db = get_mongodb_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        streamlit_status = db.bot_status.find_one({"bot_type": "streamlit"})
        slack_status = db.bot_status.find_one({"bot_type": "slack"})
        
        # Convert MongoDB documents to JSON-serializable format
        if streamlit_status:
            streamlit_status['_id'] = str(streamlit_status['_id'])
            if 'last_heartbeat' in streamlit_status:
                streamlit_status['last_heartbeat'] = streamlit_status['last_heartbeat'].isoformat()
        
        if slack_status:
            slack_status['_id'] = str(slack_status['_id'])
            if 'last_heartbeat' in slack_status:
                slack_status['last_heartbeat'] = slack_status['last_heartbeat'].isoformat()
        
        return jsonify({
            "streamlit": streamlit_status,
            "slack": slack_status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/interactions', methods=['GET'])
def get_interactions():
    db = get_mongodb_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # Get query parameters
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        bot_type = request.args.get('bot_type', None)
        
        # Convert date strings to datetime objects
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_datetime = datetime.now() - timedelta(days=7)
            
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_datetime = datetime.now()
        
        # Build query
        query = {"timestamp": {"$gte": start_datetime, "$lte": end_datetime}}
        if bot_type and bot_type != "Both":
            query["bot_type"] = bot_type.lower()
        
        # Get interactions
        interactions = list(db.interactions.find(query).sort("timestamp", -1).limit(50))
        
        # Convert to JSON-serializable format
        for interaction in interactions:
            interaction['_id'] = str(interaction['_id'])
            if 'timestamp' in interaction:
                interaction['timestamp'] = interaction['timestamp'].isoformat()
        
        return jsonify(interactions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    db = get_mongodb_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # Get query parameters
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Convert date strings to datetime objects
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_datetime = datetime.now() - timedelta(days=7)
            
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_datetime = datetime.now()
        
        # Calculate metrics
        total_streamlit = db.interactions.count_documents({
            "bot_type": "streamlit",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        })
        
        total_slack = db.interactions.count_documents({
            "bot_type": "slack",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        })
        
        unique_streamlit = len(db.interactions.distinct("user_id", {
            "bot_type": "streamlit",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        }))
        
        unique_slack = len(db.interactions.distinct("user_id", {
            "bot_type": "slack",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        }))
        
        avg_times = list(db.interactions.aggregate([
            {"$match": {"timestamp": {"$gte": start_datetime, "$lte": end_datetime}}},
            {"$group": {"_id": "$bot_type", "avg_time": {"$avg": "$response_time_ms"}}}
        ]))
        
        avg_times_dict = {doc["_id"]: doc["avg_time"] for doc in avg_times}
        
        return jsonify({
            "total_streamlit": total_streamlit,
            "total_slack": total_slack,
            "unique_streamlit": unique_streamlit,
            "unique_slack": unique_slack,
            "avg_streamlit_time": avg_times_dict.get("streamlit", 0),
            "avg_slack_time": avg_times_dict.get("slack", 0)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/daily_activity', methods=['GET'])
def get_daily_activity():
    db = get_mongodb_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # Get query parameters
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Convert date strings to datetime objects
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_datetime = datetime.now() - timedelta(days=7)
            
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_datetime = datetime.now()
        
        # Get daily activity
        daily_data = list(db.interactions.aggregate([
            {"$match": {"timestamp": {"$gte": start_datetime, "$lte": end_datetime}}},
            {"$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                    "bot_type": "$bot_type"
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.date": 1}}
        ]))
        
        # Convert to JSON-serializable format
        result = [
            {"date": item["_id"]["date"], "bot_type": item["_id"]["bot_type"], "count": item["count"]}
            for item in daily_data
        ]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/top_queries', methods=['GET'])
def get_top_queries():
    db = get_mongodb_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # Get query parameters
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        limit = int(request.args.get('limit', '10'))
        
        # Convert date strings to datetime objects
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_datetime = datetime.now() - timedelta(days=7)
            
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_datetime = datetime.now()
        
        # Get top queries
        top_queries = list(db.interactions.aggregate([
            {"$match": {"timestamp": {"$gte": start_datetime, "$lte": end_datetime}}},
            {"$group": {"_id": "$query", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]))
        
        # Convert to JSON-serializable format
        result = [
            {"query": item["_id"], "count": item["count"]}
            for item in top_queries
        ]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/response_times', methods=['GET'])
def get_response_times():
    db = get_mongodb_connection()
    if not db:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        # Get query parameters
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        bot_type = request.args.get('bot_type', 'streamlit')
        
        # Convert date strings to datetime objects
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        else:
            start_datetime = datetime.now() - timedelta(days=7)
            
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        else:
            end_datetime = datetime.now()
        
        # Query for response times
        query = {
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime},
            "bot_type": bot_type.lower(),
            "response_time_ms": {"$exists": True, "$ne": 0}
        }
        
        response_times = list(db.interactions.find(query, {"response_time_ms": 1}))
        
        # Extract response times
        result = [doc["response_time_ms"] for doc in response_times]
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
