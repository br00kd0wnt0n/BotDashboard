import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os

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

# Mock data function
def get_mock_data():
    # Create a class to simulate the database
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

# Get mock data
db = get_mock_data()

# Authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def authenticate():
    password = st.sidebar.text_input("Enter dashboard password", type="password")
    if password == "ralphbot123":  # Hardcoded for demonstration
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
    
    # Calculate status based on last heartbeat
    def get_status(heartbeat_time):
        if not heartbeat_time:
            return "Unknown", "gray"
            
        # Consider offline if no heartbeat in last 5 minutes
        time_diff = datetime.now() - heartbeat_time
        if time_diff.total_seconds() > 300:  # 5 minutes
            return "Offline", "red"
        else:
            return "Online", "green"
    
    # Get statuses and colors
    streamlit_status_text, streamlit_color = get_status(db.bot_status["streamlit"]["last_heartbeat"])
    slack_status_text, slack_color = get_status(db.bot_status["slack"]["last_heartbeat"])
    
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
                {db.bot_status["streamlit"]["last_heartbeat"].strftime("%Y-%m-%d %H:%M:%S")}
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
                {db.bot_status["slack"]["last_heartbeat"].strftime("%Y-%m-%d %H:%M:%S")}
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
        
        # Filter interactions based on date range
        filtered_interactions = [
            interaction for interaction in db.interactions
            if start_datetime <= interaction["timestamp"] <= end_datetime
        ]
        
        # Calculate metrics
        total_streamlit = sum(1 for i in filtered_interactions if i["bot_type"] == "streamlit")
        total_slack = sum(1 for i in filtered_interactions if i["bot_type"] == "slack")
        
        unique_streamlit = len(set(i["user_id"] for i in filtered_interactions if i["bot_type"] == "streamlit"))
        unique_slack = len(set(i["user_id"] for i in filtered_interactions if i["bot_type"] == "slack"))
        
        avg_streamlit_time = sum(i["response_time_ms"] for i in filtered_interactions if i["bot_type"] == "streamlit") / max(1, total_streamlit)
        avg_slack_time = sum(i["response_time_ms"] for i in filtered_interactions if i["bot_type"] == "slack") / max(1, total_slack)
        
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
        # Group interactions by date and bot type
        daily_data = {}
        for interaction in filtered_interactions:
            date_str = interaction["timestamp"].strftime("%Y-%m-%d")
            bot_type = interaction["bot_type"]
            key = (date_str, bot_type)
            
            if key not in daily_data:
                daily_data[key] = 0
            daily_data[key] += 1
        
        # Convert to DataFrame
        daily_df = pd.DataFrame([
            {"date": date, "bot_type": bot_type, "count": count}
            for (date, bot_type), count in daily_data.items()
        ])
        
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
        
        # Filter conversations
        conversations = []
        for interaction in db.interactions:
            if start_datetime <= interaction["timestamp"] <= end_datetime:
                if bot_type == "Both" or interaction["bot_type"] == bot_type.lower():
                    conversations.append(interaction)
        
        # Sort by timestamp (newest first)
        conversations.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit to 50
        conversations = conversations[:50]
        
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
        
        # Count queries
        query_counts = {}
        for interaction in filtered_interactions:
            query = interaction["query"]
            if query not in query_counts:
                query_counts[query] = 0
            query_counts[query] += 1
        
        # Convert to DataFrame and sort
        query_df = pd.DataFrame([
            {"query": query, "count": count}
            for query, count in query_counts.items()
        ]).sort_values("count", ascending=False).head(10)
        
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
        
        response_times = [
            interaction["response_time_ms"]
            for interaction in filtered_interactions
            if interaction["bot_type"] == bot_selector.lower()
        ]
        
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
