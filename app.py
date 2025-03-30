import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import ssl
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set page config
st.set_page_config(
    page_title="RalphBot Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Apply custom styling
st.markdown("""
<style>
    .main {background-color: #f5f5f5;}
    div[data-testid="stHeader"] {background-color: #E90080;}
    p, div {color: #333333;} /* Dark gray text */
    h1, h2, h3 {color: #222222;} /* Even darker text for headings */
</style>
""", unsafe_allow_html=True)

# Create mock data function for fallback
def get_mock_data():
    class MockDB:
        def __init__(self):
            # Mock bot status data
            self.bot_status = {
                "streamlit": {"bot_type": "streamlit", "last_heartbeat": datetime.now()},
                "slack": {"bot_type": "slack", "last_heartbeat": datetime.now() - timedelta(minutes=15)}
            }
            
            # Mock interaction data (same as before)
            self.interactions = []
            for i in range(50):
                hours_ago = i % 24
                days_ago = i // 24
                self.interactions.append({
                    "timestamp": datetime.now() - timedelta(days=days_ago, hours=hours_ago),
                    "user_id": f"user{i%10}",
                    "query": f"Sample query {i}",
                    "response": f"Sample response {i}",
                    "bot_type": "streamlit" if i % 3 == 0 else "slack",
                    "response_time_ms": 500 + (i * 10)
                })
    
    return MockDB()

# Set up MongoDB connection with proper error handling and SSL configuration
def get_mongodb_connection():
    try:
        # MongoDB connection string - using st.secrets if available
        mongo_uri = st.secrets.get("mongodb", {}).get("uri", None)
        
        # Fallback to environment variable if not in secrets
        if not mongo_uri:
            mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://br00kd0wnt0wn:XHZo54P7bqrVUIzj@ralphbot.nsyijw5.mongodb.net/?retryWrites=true&w=majority&appName=RalphBot")
            st.sidebar.info("Using environment variable for MongoDB connection")
        
        # Connect with explicit SSL configuration
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_NONE,  # Less secure but helps bypass cert issues
            tlsAllowInvalidCertificates=True  # For older PyMongo versions
        )
        
        # Test the connection
        client.admin.command('ping')
        
        # Get database
        db = client.ralphbot_analytics
        
        # Create MongoDBWrapper to handle MongoDB methods safely
        class MongoDBWrapper:
            def __init__(self, db):
                self.db = db
                self.use_mock = False
                
            def get_bot_status(self, bot_type):
                try:
                    return self.db.bot_status.find_one({"bot_type": bot_type})
                except Exception as e:
                    st.sidebar.warning(f"Error getting bot status: {e}")
                    # Return mock data structure
                    if bot_type == "streamlit":
                        return {"bot_type": "streamlit", "last_heartbeat": datetime.now()}
                    else:
                        return {"bot_type": "slack", "last_heartbeat": datetime.now() - timedelta(minutes=15)}
            
            def get_interactions(self, start_time, end_time, bot_type=None):
                try:
                    query = {"timestamp": {"$gte": start_time, "$lte": end_time}}
                    if bot_type and bot_type != "Both":
                        query["bot_type"] = bot_type.lower()
                    
                    return list(self.db.interactions.find(query).sort("timestamp", -1).limit(50))
                except Exception as e:
                    st.sidebar.warning(f"Error getting interactions: {e}")
                    # Return mock data filtered by date
                    mock_db = get_mock_data()
                    filtered = [i for i in mock_db.interactions 
                               if start_time <= i["timestamp"] <= end_time]
                    
                    if bot_type and bot_type != "Both":
                        filtered = [i for i in filtered if i["bot_type"] == bot_type.lower()]
                    
                    return sorted(filtered, key=lambda x: x["timestamp"], reverse=True)[:50]
            
            def get_interaction_count(self, start_time, end_time, bot_type=None):
                try:
                    query = {"timestamp": {"$gte": start_time, "$lte": end_time}}
                    if bot_type:
                        query["bot_type"] = bot_type
                    
                    return self.db.interactions.count_documents(query)
                except Exception as e:
                    st.sidebar.warning(f"Error getting interaction count: {e}")
                    # Count from mock data
                    mock_db = get_mock_data()
                    filtered = [i for i in mock_db.interactions 
                               if start_time <= i["timestamp"] <= end_time]
                    
                    if bot_type:
                        filtered = [i for i in filtered if i["bot_type"] == bot_type]
                    
                    return len(filtered)
            
            def get_unique_users(self, start_time, end_time, bot_type=None):
                try:
                    query = {"timestamp": {"$gte": start_time, "$lte": end_time}}
                    if bot_type:
                        query["bot_type"] = bot_type
                    
                    return len(self.db.interactions.distinct("user_id", query))
                except Exception as e:
                    st.sidebar.warning(f"Error getting unique users: {e}")
                    # Count from mock data
                    mock_db = get_mock_data()
                    filtered = [i for i in mock_db.interactions 
                               if start_time <= i["timestamp"] <= end_time]
                    
                    if bot_type:
                        filtered = [i for i in filtered if i["bot_type"] == bot_type]
                    
                    return len(set(i["user_id"] for i in filtered))
            
            def get_average_response_time(self, start_time, end_time, bot_type=None):
                try:
                    query = {
                        "timestamp": {"$gte": start_time, "$lte": end_time},
                        "response_time_ms": {"$exists": True, "$ne": 0}
                    }
                    if bot_type:
                        query["bot_type"] = bot_type
                    
                    result = list(self.db.interactions.aggregate([
                        {"$match": query},
                        {"$group": {"_id": None, "avg_time": {"$avg": "$response_time_ms"}}}
                    ]))
                    
                    if result:
                        return result[0]["avg_time"]
                    return 0
                except Exception as e:
                    st.sidebar.warning(f"Error getting average response time: {e}")
                    # Calculate from mock data
                    mock_db = get_mock_data()
                    filtered = [i for i in mock_db.interactions 
                               if start_time <= i["timestamp"] <= end_time
                               and "response_time_ms" in i]
                    
                    if bot_type:
                        filtered = [i for i in filtered if i["bot_type"] == bot_type]
                    
                    if filtered:
                        return sum(i["response_time_ms"] for i in filtered) / len(filtered)
                    return 0
            
            def get_daily_activity(self, start_time, end_time):
                try:
                    result = list(self.db.interactions.aggregate([
                        {"$match": {"timestamp": {"$gte": start_time, "$lte": end_time}}},
                        {"$group": {
                            "_id": {
                                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                                "bot_type": "$bot_type"
                            },
                            "count": {"$sum": 1}
                        }},
                        {"$sort": {"_id.date": 1}}
                    ]))
                    
                    # Convert to DataFrame format
                    if result:
                        return pd.DataFrame([
                            {"date": item["_id"]["date"], 
                             "bot_type": item["_id"]["bot_type"], 
                             "count": item["count"]}
                            for item in result
                        ])
                    return pd.DataFrame()
                except Exception as e:
                    st.sidebar.warning(f"Error getting daily activity: {e}")
                    # Create from mock data
                    mock_db = get_mock_data()
                    filtered = [i for i in mock_db.interactions 
                               if start_time <= i["timestamp"] <= end_time]
                    
                    # Group by date and bot_type
                    daily_data = {}
                    for interaction in filtered:
                        date_str = interaction["timestamp"].strftime("%Y-%m-%d")
                        bot_type = interaction["bot_type"]
                        key = (date_str, bot_type)
                        
                        if key not in daily_data:
                            daily_data[key] = 0
                        daily_data[key] += 1
                    
                    # Convert to DataFrame
                    return pd.DataFrame([
                        {"date": date, "bot_type": bot_type, "count": count}
                        for (date, bot_type), count in daily_data.items()
                    ])
            
            def get_top_queries(self, start_time, end_time, limit=10):
                try:
                    result = list(self.db.interactions.aggregate([
                        {"$match": {"timestamp": {"$gte": start_time, "$lte": end_time}}},
                        {"$group": {"_id": "$query", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                        {"$limit": limit}
                    ]))
                    
                    # Convert to DataFrame format
                    if result:
                        return pd.DataFrame([
                            {"query": item["_id"], "count": item["count"]} 
                            for item in result
                        ])
                    return pd.DataFrame()
                except Exception as e:
                    st.sidebar.warning(f"Error getting top queries: {e}")
                    # Create from mock data
                    mock_db = get_mock_data()
                    filtered = [i for i in mock_db.interactions 
                               if start_time <= i["timestamp"] <= end_time]
                    
                    # Count queries
                    query_counts = {}
                    for interaction in filtered:
                        query = interaction["query"]
                        if query not in query_counts:
                            query_counts[query] = 0
                        query_counts[query] += 1
                    
                    # Convert to DataFrame and sort
                    return pd.DataFrame([
                        {"query": query, "count": count}
                        for query, count in query_counts.items()
                    ]).sort_values("count", ascending=False).head(limit)
            
            def get_response_times(self, start_time, end_time, bot_type):
                try:
                    query = {
                        "timestamp": {"$gte": start_time, "$lte": end_time},
                        "bot_type": bot_type.lower(),
                        "response_time_ms": {"$exists": True, "$ne": 0}
                    }
                    
                    result = list(self.db.interactions.find(query, {"response_time_ms": 1}))
                    
                    if result:
                        return [doc["response_time_ms"] for doc in result]
                    return []
                except Exception as e:
                    st.sidebar.warning(f"Error getting response times: {e}")
                    # Get from mock data
                    mock_db = get_mock_data()
                    filtered = [i["response_time_ms"] for i in mock_db.interactions 
                               if start_time <= i["timestamp"] <= end_time
                               and i["bot_type"] == bot_type.lower()
                               and "response_time_ms" in i]
                    
                    return filtered
        
        st.sidebar.success("MongoDB connected successfully")
        return MongoDBWrapper(db)
        
    except Exception as e:
        st.sidebar.error(f"MongoDB connection error: {str(e)}")
        st.sidebar.info("Using mock data instead")
        return None

# Try to connect to MongoDB
mongo_db = get_mongodb_connection()

# Use mock data if MongoDB connection failed
if not mongo_db:
    mock_db = get_mock_data()
    
    # Create a wrapper with the same methods as MongoDBWrapper
    class MockDBWrapper:
        def __init__(self, mock_db):
            self.mock_db = mock_db
        
        def get_bot_status(self, bot_type):
            return self.mock_db.bot_status.get(bot_type, 
                   {"bot_type": bot_type, "last_heartbeat": datetime.now()})
        
        # Implement other methods like in the MongoDBWrapper class
        # with mock data instead of MongoDB queries
        # ...
    
    # Use mock data instead
    db = MockDBWrapper(mock_db)
    st.sidebar.info("Using mock data for demonstration")
else:
    db = mongo_db

# Authentication (same as before)
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def authenticate():
    password = st.sidebar.text_input("Enter dashboard password", type="password")
    dashboard_pwd = st.secrets.get("dashboard", {}).get("password", "ralphbot123")
    if password == dashboard_pwd:
        st.session_state.authenticated = True
    else:
        st.sidebar.error("Invalid password")

if not st.session_state.authenticated:
    st.title("RalphBot Analytics Dashboard")
    st.write("Please authenticate to view the dashboard")
    authenticate()
else:
    # Main dashboard (modified to use db wrapper)
    st.title("RalphBot Analytics Dashboard")
    
    # Date range selector (same as before)
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start date", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End date", datetime.now())
    
    # Convert to datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Bot Status
    st.header("Bot Status")
    
    # Get current status
    streamlit_status = db.get_bot_status("streamlit")
    slack_status = db.get_bot_status("slack")
    
    # Calculate status based on last heartbeat
    def get_status(status_doc):
        if not status_doc or "last_heartbeat" not in status_doc:
            return "Unknown", "gray"
            
        last_heartbeat = status_doc["last_heartbeat"]
        
        # Consider offline if no heartbeat in last 5 minutes
        time_diff = datetime.now() - last_heartbeat
        if time_diff.total_seconds() > 300:  # 5 minutes
            return "Offline", "red"
        else:
            return "Online", "green"
    
    # Get statuses and colors
    streamlit_status_text, streamlit_color = get_status(streamlit_status)
    slack_status_text, slack_color = get_status(slack_status)
    
    # Display status indicators
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            padding: 10px;
            border-radius: 5px;
            background-color: #f0f0f0;
        ">
            <div style="
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background-color: {streamlit_color};
                margin-right: 10px;
            "></div>
            <div style="color: #333333;">
                <strong>Streamlit Bot:</strong> {streamlit_status_text}<br>
                {streamlit_status.get("last_heartbeat").strftime("%Y-%m-%d %H:%M:%S") if streamlit_status and streamlit_status.get("last_heartbeat") else "No data"}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            padding: 10px;
            border-radius: 5px;
            background-color: #f0f0f0;
        ">
            <div style="
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background-color: {slack_color};
                margin-right: 10px;
            "></div>
            <div style="color: #333333;">
                <strong>Slack Bot:</strong> {slack_status_text}<br>
                {slack_status.get("last_heartbeat").strftime("%Y-%m-%d %H:%M:%S") if slack_status and slack_status.get("last_heartbeat") else "No data"}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Auto-refresh (same as before)
    st.sidebar.title("Dashboard Controls")
    auto_refresh = st.sidebar.checkbox("Auto refresh", value=True)
    
    if auto_refresh:
        st.sidebar.write("Dashboard will refresh every 60 seconds")
        st.sidebar.write(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
        st.markdown("""
        <script>
            setTimeout(function() {
                window.location.reload();
            }, 60000);
        </script>
        """, unsafe_allow_html=True)
    
    if st.sidebar.button("Refresh Now"):
        st.rerun()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Overview", "Conversations", "Analysis"])
    
    with tab1:
        st.header("Overview Metrics")
        
        # Fetch metrics using the wrapper methods
        total_streamlit = db.get_interaction_count(start_datetime, end_datetime, "streamlit")
        total_slack = db.get_interaction_count(start_datetime, end_datetime, "slack")
        
        unique_streamlit = db.get_unique_users(start_datetime, end_datetime, "streamlit")
        unique_slack = db.get_unique_users(start_datetime, end_datetime, "slack")
        
        avg_streamlit_time = db.get_average_response_time(start_datetime, end_datetime, "streamlit")
        avg_slack_time = db.get_average_response_time(start_datetime, end_datetime, "slack")
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Streamlit Interactions", total_streamlit)
        with col2:
            st.metric("Slack Interactions", total_slack)
        with col3:
            st.metric("Unique Streamlit Users", unique_streamlit)
        with col4:
            st.metric("Unique Slack Users", unique_slack)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Avg. Streamlit Response Time", f"{int(avg_streamlit_time)}ms")
        with col2:
            st.metric("Avg. Slack Response Time", f"{int(avg_slack_time)}ms")
        
        # Daily activity chart
        daily_df = db.get_daily_activity(start_datetime, end_datetime)
        
        if not daily_df.empty:
            fig = px.line(
                daily_df, 
                x="date", 
                y="count", 
                color="bot_type",
                title="Daily Interactions",
                labels={"count": "Number of Interactions", "date": "Date", "bot_type": "Bot Type"}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("Recent Conversations")
        
        bot_type = st.selectbox("Select Bot", ["Both", "Streamlit", "Slack"])
        
        # Get conversations
        conversations = db.get_interactions(start_datetime, end_datetime, bot_type)
        
        # Display conversations
        if conversations:
            for conv in conversations:
                with st.expander(f"{conv['timestamp'].strftime('%Y-%m-%d %H:%M')} - {conv['bot_type'].upper()} - User: {conv['user_id']}"):
                    st.write("**Query:**")
                    st.write(conv["query"])
                    st.write("**Response:**")
                    st.write(conv["response"])
        else:
            st.write("No conversations found for the selected period")
    
    with tab3:
        st.header("Advanced Analysis")
        
        # Top queries
        query_df = db.get_top_queries(start_datetime, end_datetime)
        
        if not query_df.empty:
            st.subheader("Most Common Queries")
            fig = px.bar(
                query_df, 
                x="count", 
                y="query", 
                orientation='h',
                title="Top 10 Queries",
                labels={"count": "Number of Times Asked", "query": "Query"}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Response time distribution
        st.subheader("Response Time Distribution")
        bot_selector = st.radio("Select Bot Type", ["Streamlit", "Slack"], horizontal=True)
        
        response_times = db.get_response_times(start_datetime, end_datetime, bot_selector)
        
        if response_times:
            fig = px.histogram(
                response_times, 
                nbins=20,
                title=f"{bot_selector} Response Time Distribution (ms)",
                labels={"value": "Response Time (ms)", "count": "Number of Interactions"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No response time data available for the selected period")

# Add footer
st.markdown("---")
st.markdown("RalphBot Analytics Dashboard | Internal Use Only")
