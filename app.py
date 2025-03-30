# streamlit_app.py - RalphBot Analytics Dashboard
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import requests
import json

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

# API base URL - replace with your deployed API URL
API_BASE_URL = "https://ralphbot-api-ef7a0f4b6655.herokuapp.com/"

# Function to fetch data from API with error handling
def fetch_api_data(endpoint, params=None):
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"API Error: {str(e)}")
        return None

# Create mock data function for fallback
def get_mock_data():
    class MockDB:
        def __init__(self):
            # Mock bot status data
            self.bot_status = {
                "streamlit": {"bot_type": "streamlit", "last_heartbeat": datetime.now()},
                "slack": {"bot_type": "slack", "last_heartbeat": datetime.now() - timedelta(minutes=15)}
            }
            
            # Mock interaction data
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

# Authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def authenticate():
    # Password input
    password_input = st.sidebar.text_input(
        "Enter dashboard password", 
        type="password", 
        key="dashboard_password"
    )
    
    # Get password from environment or secrets
    dashboard_pwd = os.environ.get('DASHBOARD_PASSWORD', 
                    st.secrets.get("dashboard", {}).get("password", "ralphbot123"))
    
    # Authentication logic
    if password_input == dashboard_pwd:
        st.session_state.authenticated = True
    elif password_input:
        st.sidebar.error("Invalid password")

# Main authentication flow
if not st.session_state.authenticated:
    st.title("RalphBot Analytics Dashboard")
    st.write("Please authenticate to view the dashboard")
    authenticate()
else:
    # Main dashboard content starts here
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
    
    # Date parameters for API calls
    date_params = {
        'start_date': start_datetime.isoformat(),
        'end_date': end_datetime.isoformat()
    }
    
    # Bot Status
    st.header("Bot Status")
    
    # Fetch status data from API
    status_data = fetch_api_data('status')
    
    # Use mock data if API call fails
    if not status_data:
        mock_db = get_mock_data()
        streamlit_status = mock_db.bot_status["streamlit"]
        slack_status = mock_db.bot_status["slack"]
        st.warning("Using mock data (API connection failed)")
    else:
        streamlit_status = status_data.get("streamlit", {})
        slack_status = status_data.get("slack", {})
        
        # Convert ISO datetime strings to datetime objects
        if streamlit_status and 'last_heartbeat' in streamlit_status:
            streamlit_status['last_heartbeat'] = datetime.fromisoformat(streamlit_status['last_heartbeat'].replace('Z', '+00:00'))
        
        if slack_status and 'last_heartbeat' in slack_status:
            slack_status['last_heartbeat'] = datetime.fromisoformat(slack_status['last_heartbeat'].replace('Z', '+00:00'))
    
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
        
        # Fetch metrics from API
        metrics_data = fetch_api_data('metrics', date_params)
        
        # Use mock data if API call fails
        if not metrics_data:
            mock_db = get_mock_data()
            
            # Count metrics from mock data
            filtered = [i for i in mock_db.interactions 
                       if start_datetime <= i["timestamp"] <= end_datetime]
            
            total_streamlit = len([i for i in filtered if i["bot_type"] == "streamlit"])
            total_slack = len([i for i in filtered if i["bot_type"] == "slack"])
            
            unique_streamlit = len(set(i["user_id"] for i in filtered if i["bot_type"] == "streamlit"))
            unique_slack = len(set(i["user_id"] for i in filtered if i["bot_type"] == "slack"))
            
            streamlit_times = [i["response_time_ms"] for i in filtered if i["bot_type"] == "streamlit"]
            slack_times = [i["response_time_ms"] for i in filtered if i["bot_type"] == "slack"]
            
            avg_streamlit_time = sum(streamlit_times) / max(1, len(streamlit_times))
            avg_slack_time = sum(slack_times) / max(1, len(slack_times))
        else:
            total_streamlit = metrics_data.get("total_streamlit", 0)
            total_slack = metrics_data.get("total_slack", 0)
            unique_streamlit = metrics_data.get("unique_streamlit", 0)
            unique_slack = metrics_data.get("unique_slack", 0)
            avg_streamlit_time = metrics_data.get("avg_streamlit_time", 0)
            avg_slack_time = metrics_data.get("avg_slack_time", 0)
        
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
        
        # Fetch daily activity data from API
        daily_data = fetch_api_data('daily_activity', date_params)
        
        # Use mock data if API call fails
        if not daily_data:
            mock_db = get_mock_data()
            filtered = [i for i in mock_db.interactions 
                       if start_datetime <= i["timestamp"] <= end_datetime]
            
            # Group by date and bot_type
            daily_dict = {}
            for interaction in filtered:
                date_str = interaction["timestamp"].strftime("%Y-%m-%d")
                bot_type = interaction["bot_type"]
                key = (date_str, bot_type)
                
                if key not in daily_dict:
                    daily_dict[key] = 0
                daily_dict[key] += 1
            
            # Convert to list format
            daily_data = [
                {"date": date, "bot_type": bot_type, "count": count}
                for (date, bot_type), count in daily_dict.items()
            ]
        
        # Convert to DataFrame for plotting
        if daily_data:
            daily_df = pd.DataFrame(daily_data)
            
            fig = px.line(
                daily_df, 
                x="date", 
                y="count", 
                color="bot_type",
                title="Daily Interactions",
                labels={"count": "Number of Interactions", "date": "Date", "bot_type": "Bot Type"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No daily activity data available for the selected period")
    
    with tab2:
        st.header("Recent Conversations")
        
        bot_type = st.selectbox("Select Bot", ["Both", "Streamlit", "Slack"])
        
        # Fetch conversations from API
        interactions_params = date_params.copy()
        interactions_params['bot_type'] = bot_type
        conversations = fetch_api_data('interactions', interactions_params)
        
        # Use mock data if API call fails
        if not conversations:
            mock_db = get_mock_data()
            filtered = [i for i in mock_db.interactions 
                       if start_datetime <= i["timestamp"] <= end_datetime]
            
            if bot_type != "Both":
                filtered = [i for i in filtered if i["bot_type"] == bot_type.lower()]
            
            conversations = sorted(filtered, key=lambda x: x["timestamp"], reverse=True)[:50]
        else:
            # Convert ISO datetime strings to datetime objects
            for conv in conversations:
                if 'timestamp' in conv:
                    conv['timestamp'] = datetime.fromisoformat(conv['timestamp'].replace('Z', '+00:00'))
        
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
        
        # Fetch top queries from API
        top_queries = fetch_api_data('top_queries', date_params)
        
        # Use mock data if API call fails
        if not top_queries:
            mock_db = get_mock_data()
            filtered = [i for i in mock_db.interactions 
                       if start_datetime <= i["timestamp"] <= end_datetime]
            
            # Count queries
            query_counts = {}
            for interaction in filtered:
                query = interaction["query"]
                if query not in query_counts:
                    query_counts[query] = 0
                query_counts[query] += 1
            
            # Convert to list format
