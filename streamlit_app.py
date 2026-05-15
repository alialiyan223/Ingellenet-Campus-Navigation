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
    page_title="Ingellenet AI | Campus Navigation",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Premium UI/UX Styling ---
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">

<style>
    /* Base Theme */
    :root {
        --bg-primary: #0a0f1e;
        --accent: #38bdf8;
        --accent-glow: rgba(56, 189, 248, 0.3);
        --glass: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.08);
        --text-main: #f8fafc;
        --text-dim: #94a3b8;
    }

    .stApp {
        background: radial-gradient(circle at 0% 0%, #1e293b 0%, #0a0f1e 100%);
        color: var(--text-main);
        font-family: 'Outfit', sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(10, 15, 30, 0.95) !important;
        border-right: 1px solid var(--glass-border);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1 {
        font-size: 2rem;
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    /* Glass Cards */
    .glass-card {
        background: var(--glass);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }

    /* Custom Buttons */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #38bdf8, #0ea5e9);
        color: #0f172a;
        border-radius: 12px;
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: uppercase;
        font-size: 0.8rem;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 20px var(--accent-glow);
        background: linear-gradient(135deg, #7dd3fc, #38bdf8);
        color: #0f172a;
    }

    /* AI Chat bubbles */
    [data-testid="stChatMessage"] {
        background-color: var(--glass) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 16px !important;
        margin-bottom: 12px !important;
    }

    /* Inputs */
    .stSelectbox div[data-baseweb="select"] {
        background-color: var(--glass) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 12px !important;
    }

    /* Hide standard Streamlit header/footer */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
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

# --- Sidebar Content ---
with st.sidebar:
    st.title("Ingellenet")
    st.caption("AI-POWERED CAMPUS NAVIGATION")
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.write(f"📡 **Live Position**")
    st.code(st.session_state.current_loc, language="text")
    
    if st.button("SCAN NEARBY NETWORKS"):
        with st.spinner("Triangulating..."):
            res = st.session_state.localiser.locate()
            if res["room"]:
                st.session_state.current_loc = res["room"]
                st.toast(f"📍 Location Locked: {res['room']}", icon="✅")
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    
    # Selection Area
    st.subheader("Navigation")
    all_rooms = get_all_rooms()
    room_options = {r['code']: f"{r['name']} — {r['building']}" for r in all_rooms}
    
    start_room = st.selectbox("Current Location", options=list(room_options.keys()), 
                               format_func=lambda x: room_options[x], 
                               index=list(room_options.keys()).index(st.session_state.current_loc))
    
    end_room = st.selectbox("Target Destination", options=list(room_options.keys()), 
                             format_func=lambda x: room_options[x], index=6)
    
    if st.button("CALCULATE OPTIMAL ROUTE"):
        path_data = st.session_state.graph.shortest_path(start_room, end_room)
        if path_data:
            st.session_state.path_data = path_data
            st.success("Path Calculated!")
        else:
            st.error("Route Unavailable")

# --- Main Dashboard ---
col1, col2 = st.columns([3, 2], gap="large")

with col1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 💠 Dynamic Campus Map")
    
    rooms = st.session_state.graph.all_rooms()
    df_rooms = pd.DataFrame.from_dict(rooms, orient='index')
    
    fig = go.Figure()
    
    # Edges
    for u, v, d in st.session_state.graph.G.edges(data=True):
        r1, r2 = rooms[u], rooms[v]
        fig.add_trace(go.Scatter(
            x=[r1['x'], r2['x']], y=[r1['y'], r2['y']],
            mode='lines',
            line=dict(color='rgba(148, 163, 184, 0.1)', width=1),
            hoverinfo='none',
            showlegend=False
        ))

    # Path
    if "path_data" in st.session_state:
        path = st.session_state.path_data['path']
        path_x, path_y = [], []
        for p in path:
            path_x.append(rooms[p]['x'])
            path_y.append(rooms[p]['y'])
            
        fig.add_trace(go.Scatter(
            x=path_x, y=path_y,
            mode='lines+markers',
            line=dict(color='#38bdf8', width=5),
            marker=dict(size=10, color='#38bdf8', symbol="circle"),
            hoverinfo='none',
            showlegend=False
        ))
        
        # Start/End highlight
        fig.add_trace(go.Scatter(
            x=[path_x[0], path_x[-1]], y=[path_y[0], path_y[-1]],
            mode='markers',
            marker=dict(size=18, color=['#34d399', '#fb7185'], line=dict(color='#fff', width=2)),
            showlegend=False
        ))

    # Nodes
    fig.add_trace(go.Scatter(
        x=df_rooms['x'], y=df_rooms['y'],
        mode='markers',
        marker=dict(
            size=14,
            color='#1e293b',
            line=dict(color='rgba(56, 189, 248, 0.4)', width=1.5),
            opacity=0.8
        ),
        text=df_rooms['name'],
        hovertext=df_rooms.apply(lambda r: f"<b>{r['name']}</b><br>{r['building']} · Floor {r['floor']}", axis=1),
        hoverinfo='text',
        showlegend=False
    ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=0, r=0, t=0, b=0),
        height=650,
        hoverlabel=dict(bgcolor="#0f172a", bordercolor="#1e293b", font_family="Outfit"),
        dragmode='pan'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # --- AI Chat Section ---
    st.markdown('<div class="glass-card" style="height: 100%;">', unsafe_allow_html=True)
    st.markdown("### 🤖 Campus AI")
    
    chat_sub = st.container(height=450, border=False)
    with chat_sub:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    if query := st.chat_input("Ask me anything about the campus..."):
        st.session_state.chat_history.append({"role": "user", "content": query})
        with chat_sub:
            with st.chat_message("user"):
                st.write(query)
            with st.chat_message("assistant"):
                with st.spinner(" "):
                    response = st.session_state.agent.process_query(query, st.session_state.current_loc)
                    st.write(response["message"])
                    if response["type"] == "navigation":
                        st.session_state.path_data = response["path_data"]
                        st.rerun()
                st.session_state.chat_history.append({"role": "assistant", "content": response["message"]})
    st.markdown('</div>', unsafe_allow_html=True)

# Directions Footer
if "path_data" in st.session_state:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 📋 Navigation Guide")
    steps = st.session_state.path_data['steps']
    cols = st.columns(4)
    for i, step in enumerate(steps):
        with cols[i % 4]:
            st.markdown(f"**Step {i+1}**")
            st.caption(step)
    st.markdown('</div>', unsafe_allow_html=True)
