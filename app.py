# api.py - RalphBot API Middleware
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# MongoDB connection
def get_mongodb_connection():
    try:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            logger.error("MONGO_URI environment variable is not set")
            return None
        
        client = MongoClient(mongo_uri)
        return client.ralphbot_analytics
    except Exception as e:
        logger.error(f"MongoDB connection error: {str(e)}")
        return None

# Root route
@app.route('/')
def index():
    return jsonify({
        "message": "RalphBot API is running",
        "available_endpoints": [
            "/status", 
            "/heartbeat",
            "/interactions", 
            "/metrics", 
            "/daily_activity", 
            "/top_queries", 
            "/response_times"
        ]
    })

# Heartbeat endpoint
@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    try:
        bot_type = request.json.get('bot_type', 'streamlit')
        
        # Update or create heartbeat record
        db = get_mongodb_connection()
        if db is None:
            return jsonify({"error": "Database connection failed"}), 500
        
        db.bot_status.update_one(
            {"bot_type": bot_type},
            {"$set": {
                "last_heartbeat": datetime.now(),
                "status": "online"
            }},
            upsert=True
        )
        
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Heartbeat error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Status endpoint
@app.route('/status', methods=['GET'])
def get_status():
    try:
        db = get_mongodb_connection()
        if db is None:
            return jsonify({
                "error": "Database connection failed",
                "details": "Unable to establish MongoDB connection"
            }), 500
        
        # Use find_one with a default empty dict to prevent truth value testing
        streamlit_status = db.bot_status.find_one({"bot_type": "streamlit"}) or {}
        slack_status = db.bot_status.find_one({"bot_type": "slack"}) or {}
        
        # Convert MongoDB documents to JSON-serializable format
        if streamlit_status:
            streamlit_status['_id'] = str(streamlit_status.get('_id', ''))
            if 'last_heartbeat' in streamlit_status:
                streamlit_status['last_heartbeat'] = streamlit_status['last_heartbeat'].isoformat()
        
        if slack_status:
            slack_status['_id'] = str(slack_status.get('_id', ''))
            if 'last_heartbeat' in slack_status:
                slack_status['last_heartbeat'] = slack_status['last_heartbeat'].isoformat()
        
        return jsonify({
            "streamlit": streamlit_status,
            "slack": slack_status
        })
    except Exception as e:
        logger.error(f"Unexpected error in get_status: {str(e)}")
        return jsonify({
            "error": "Unexpected server error", 
            "details": str(e)
        }), 500

# Existing route methods (interactions, metrics, daily_activity, etc.) remain the same as in the previous implementation

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
