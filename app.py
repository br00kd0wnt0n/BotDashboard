import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
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
</style>
""", unsafe_allow_html=True)

# Database connection
@st.cache_resource
def get_database_connection():
    mongo_uri = os.getenv("mongodb+srv://br00kd0wnt0n:XHZo54P7bqrVUIzj@ralphbot.nsyijw5.mongodb.net/?retryWrites=true&w=majority&appName=RalphBot")
    client = MongoClient(mongo_uri)
    return client.ralphbot_analytics

db = get_database_connection()

# Authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def authenticate():
    password = st.sidebar.text_input("Enter dashboard password", type="password")
    if password == os.getenv("DASHBOARD_PASSWORD", "ralphbot123"):
        st.session_state.authenticated = True
    else:
        st.sidebar.error("Invalid password")

if not st.session_state.authenticated:
    st.title("RalphBot Analytics Dashboard")
    st.write("Please authenticate to view the dashboard")
    authenticate()
else:
    # Main dashboard
    st.title("RalphBot Analytics Dashboard")
    
    # Date range selector
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
    streamlit_status = db.bot_status.find_one({"bot_type": "streamlit"})
    slack_status = db.bot_status.find_one({"bot_type": "slack"})
    
    # Calculate status based on last heartbeat
    def get_status(heartbeat_doc):
        if not heartbeat_doc:
            return "Unknown", "gray"
            
        last_heartbeat = heartbeat_doc.get("last_heartbeat")
        if not last_heartbeat:
            return "Unknown", "gray"
            
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
            <div>
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
            <div>
                <strong>Slack Bot:</strong> {slack_status_text}<br>
                {slack_status.get("last_heartbeat").strftime("%Y-%m-%d %H:%M:%S") if slack_status and slack_status.get("last_heartbeat") else "No data"}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Auto-refresh
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
        
        # Fetch data
        total_streamlit = db.interactions.count_documents({
            "bot_type": "streamlit",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        })
        
        total_slack = db.interactions.count_documents({
            "bot_type": "slack",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        })
        
        unique_streamlit = db.interactions.distinct("user_id", {
            "bot_type": "streamlit",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        })
        
        unique_slack = db.interactions.distinct("user_id", {
            "bot_type": "slack",
            "timestamp": {"$gte": start_datetime, "$lte": end_datetime}
        })
        
        avg_response_time = db.interactions.aggregate([
            {"$match": {"timestamp": {"$gte": start_datetime, "$lte": end_datetime}}},
            {"$group": {"_id": "$bot_type", "avg_time": {"$avg": "$response_time_ms"}}}
        ])
        
        avg_times = {doc["_id"]: doc["avg_time"] for doc in avg_response_time}
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Streamlit Interactions", total_streamlit)
        with col2:
            st.metric("Slack Interactions", total_slack)
        with col3:
            st.metric("Unique Streamlit Users", len(unique_streamlit))
        with col4:
            st.metric("Unique Slack Users", len(unique_slack))
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Avg. Streamlit Response Time", f"{int(avg_times.get('streamlit', 0))}ms")
        with col2:
            st.metric("Avg. Slack Response Time", f"{int(avg_times.get('slack', 0))}ms")
        
        # Daily activity chart
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
        
        if daily_data:
            daily_df = pd.DataFrame([
                {"date": item["_id"]["date"], "bot_type": item["_id"]["bot_type"], "count": item["count"]}
                for item in daily_data
            ])
            
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
        
        # Query filter
        filter_query = {"timestamp": {"$gte": start_datetime, "$lte": end_datetime}}
        if bot_type != "Both":
            filter_query["bot_type"] = bot_type.lower()
        
        # Get conversations
        conversations = list(db.interactions.find(
            filter_query, 
            {"_id": 0, "timestamp": 1, "user_id": 1, "query": 1, "response": 1, "bot_type": 1}
        ).sort("timestamp", -1).limit(50))
        
        # Display conversations
        if conversations:
            for conv in conversations:
                with st.expander(f"{conv['timestamp'].strftime('%Y-%m-%d %H:%M')} - {conv['bot_type'].upper()} - User: {conv['user_id'][:8]}"):
                    st.write("**Query:**")
                    st.write(conv["query"])
                    st.write("**Response:**")
                    st.write(conv["response"])
        else:
            st.write("No conversations found for the selected period")
    
    with tab3:
        st.header("Advanced Analysis")
        
        # Top queries
        top_queries = list(db.interactions.aggregate([
            {"$match": {"timestamp": {"$gte": start_datetime, "$lte": end_datetime}}},
            {"$group": {"_id": "$query", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))
        
        if top_queries:
            st.subheader("Most Common Queries")
            query_df = pd.DataFrame([{"query": item["_id"], "count": item["count"]} for item in top_queries])
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
        
        response_times = list(db.interactions.find(
            {
                "bot_type": bot_selector.lower(),
                "timestamp": {"$gte": start_datetime, "$lte": end_datetime},
                "response_time_ms": {"$exists": True, "$ne": 0}
            },
            {"response_time_ms": 1}
        ))
        
        if response_times:
            times = [doc["response_time_ms"] for doc in response_times]
            fig = px.histogram(
                times, 
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
