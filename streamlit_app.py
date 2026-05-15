import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import os
import sys

# Add current dir to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from navigation.pathfinder import CampusGraph
from navigation.wifi_positioning import WifiLocaliser
from ai.agent import CampusAgent
from database.db_manager import initialize_database, get_all_rooms

# Page Config
st.set_page_config(
    page_title="Ingellenet Campus Navigation",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Look
st.markdown("""
<style>
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stApp {
        background: radial-gradient(circle at top right, #1e293b, #0f172a);
    }
    .stSidebar {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border-right: 1px solid #1e293b;
    }
    h1, h2, h3 {
        color: #38bdf8 !important;
        font-family: 'Inter', sans-serif;
    }
    .stButton>button {
        background-color: #38bdf8;
        color: #0f172a;
        border-radius: 8px;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #0ea5e9;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.3);
    }
    .chat-bubble {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border: 1px solid #1e293b;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "initialized" not in st.session_state:
    initialize_database()
    st.session_state.graph = CampusGraph()
    st.session_state.localiser = WifiLocaliser()
    st.session_state.agent = CampusAgent(st.session_state.graph)
    st.session_state.chat_history = []
    st.session_state.current_loc = "MAIN_ENT"
    st.session_state.initialized = True

# Sidebar
with st.sidebar:
    st.title("📍 Ingellenet")
    st.subheader("Campus Navigation")
    
    # Status Card
    with st.container():
        st.info(f"**Current Location:** {st.session_state.current_loc}")
        if st.button("🔄 Scan Wi-Fi Location"):
            res = st.session_state.localiser.locate()
            if res["room"]:
                st.session_state.current_loc = res["room"]
                st.success(f"Located at {res['room']} (Conf: {res['confidence']*100}%)")
            else:
                st.warning("Could not determine location. Using default.")

    st.divider()
    
    # Destination Selector
    all_rooms = get_all_rooms()
    room_options = {r['code']: f"{r['name']} ({r['building']})" for r in all_rooms}
    
    start_room = st.selectbox("Start Point", options=list(room_options.keys()), 
                               format_func=lambda x: room_options[x], index=list(room_options.keys()).index(st.session_state.current_loc))
    end_room = st.selectbox("Destination", options=list(room_options.keys()), 
                             format_func=lambda x: room_options[x], index=1)
    
    if st.button("🚀 Find Route"):
        path_data = st.session_state.graph.shortest_path(start_room, end_room)
        if path_data:
            st.session_state.path_data = path_data
            st.session_state.agent_response = {
                "type": "navigation",
                "message": f"Found the shortest path from {start_room} to {end_room}.",
                "path_data": path_data
            }
        else:
            st.error("No path found!")

# Main Content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ Interactive Campus Map")
    
    # Build Map Data
    rooms = st.session_state.graph.all_rooms()
    df_rooms = pd.DataFrame.from_dict(rooms, orient='index')
    
    # Create Plotly Figure
    fig = go.Figure()
    
    # Add Edges (background)
    for u, v, d in st.session_state.graph.G.edges(data=True):
        r1, r2 = rooms[u], rooms[v]
        fig.add_trace(go.Scatter(
            x=[r1['x'], r2['x']], y=[r1['y'], r2['y']],
            mode='lines',
            line=dict(color='#1e293b', width=1),
            hoverinfo='none',
            showlegend=False
        ))

    # Add Path (if exists)
    if "path_data" in st.session_state:
        path = st.session_state.path_data['path']
        for i in range(len(path)-1):
            r1, r2 = rooms[path[i]], rooms[path[i+1]]
            fig.add_trace(go.Scatter(
                x=[r1['x'], r2['x']], y=[r1['y'], r2['y']],
                mode='lines',
                line=dict(color='#34d399', width=4),
                hoverinfo='none',
                showlegend=False
            ))

    # Add Nodes
    fig.add_trace(go.Scatter(
        x=df_rooms['x'], y=df_rooms['y'],
        mode='markers+text',
        marker=dict(
            size=12,
            color='#38bdf8',
            line=dict(color='#0f172a', width=2)
        ),
        text=df_rooms['name'],
        textposition="bottom center",
        hovertext=df_rooms.apply(lambda r: f"{r['name']}<br>{r['building']} Floor {r['floor']}", axis=1),
        hoverinfo='text',
        showlegend=False
    ))

    # Update Layout
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=0, r=0, t=0, b=0),
        height=600,
        dragmode='pan'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

with col2:
    st.subheader("🤖 Agentic AI Assistant")
    
    # Chat History
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # Query Input
    if query := st.chat_input("Where is the nearest washroom?"):
        st.session_state.chat_history.append({"role": "user", "content": query})
        with chat_container:
            with st.chat_message("user"):
                st.write(query)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = st.session_state.agent.process_query(query, st.session_state.current_loc)
                st.write(response["message"])
                
                if response["type"] == "navigation":
                    st.session_state.path_data = response["path_data"]
                    with st.expander("Step-by-step Directions"):
                        for step in response["path_data"]["steps"]:
                            st.write(step)
                    st.rerun()
                
                st.session_state.chat_history.append({"role": "assistant", "content": response["message"]})

# Directions Expanders (if path exists)
if "path_data" in st.session_state:
    with st.expander("📋 Current Navigation Steps", expanded=True):
        cols = st.columns(len(st.session_state.path_data['steps']) // 4 + 1)
        for i, step in enumerate(st.session_state.path_data['steps']):
            cols[i % len(cols)].write(f"{i+1}. {step}")

st.divider()
st.caption("Ingellenet Offline Campus Navigation System © 2026")
