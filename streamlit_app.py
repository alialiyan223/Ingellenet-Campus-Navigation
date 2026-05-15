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
    page_title="Intellegent | AI Navigator",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- One UI Dash Styling ---
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">

<style>
    /* Base Reset */
    .stApp {
        background: radial-gradient(circle at 0% 0%, #0f172a 0%, #020617 100%);
        color: #f8fafc;
        font-family: 'Outfit', sans-serif;
    }

    /* Pulse Animation */
    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(56, 189, 248, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }
    }

    .pulse-badge {
        background: #38bdf8;
        border-radius: 50%;
        display: inline-block;
        height: 10px;
        width: 10px;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }

    /* High Contrast Text */
    h1, h2, h3, b, strong {
        color: #ffffff !important;
        letter-spacing: -0.5px;
    }
    
    .stMarkdown p, .stCaption {
        color: #94a3b8 !important;
    }

    /* Sidebar Enhancement */
    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(56, 189, 248, 0.2);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1 {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #38bdf8);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        animation: shine 3s linear infinite;
    }

    @keyframes shine {
        to { background-position: 200% center; }
    }

    /* Premium Dash Cards */
    .dash-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 28px;
        padding: 24px;
        height: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 20px 40px -15px rgba(0,0,0,0.5);
    }
    
    .dash-card:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-5px);
        box-shadow: 0 0 30px rgba(56, 189, 248, 0.1);
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #38bdf8 0%, #1d4ed8 100%) !important;
        color: white !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 16px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 25px rgba(56, 189, 248, 0.5);
    }

    /* Chat Styling */
    [data-testid="stChatMessage"] {
        background: rgba(30, 41, 59, 0.3) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 24px !important;
        margin-bottom: 15px !important;
    }

    /* Dropdown / Selectbox Menu */
    div[data-baseweb="popover"] {
        background-color: #020617 !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        border-radius: 16px !important;
    }
    div[data-baseweb="popover"] li {
        background-color: transparent !important;
        color: #f8fafc !important;
        margin: 4px 8px;
        border-radius: 10px;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: rgba(56, 189, 248, 0.2) !important;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# State Init
if "initialized" not in st.session_state:
    initialize_database()
    st.session_state.graph = CampusGraph()
    st.session_state.localiser = WifiLocaliser()
    st.session_state.agent = CampusAgent(st.session_state.graph)
    st.session_state.chat_history = []
    st.session_state.current_loc = "MAIN_ENT"
    st.session_state.initialized = True

# --- Sidebar ---
with st.sidebar:
    st.title("INTELLEGENT")
    st.caption("NEXT-GEN CAMPUS ASSISTANT")
    
    st.divider()
    st.markdown("### <div class='pulse-badge'></div> Live Status", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color:#38bdf8; margin:0;'>{st.session_state.current_loc}</h2>", unsafe_allow_html=True)
    if st.button("SYNC LOCATION", use_container_width=True):
        res = st.session_state.localiser.locate()
        if res["room"]: 
            st.session_state.current_loc = res["room"]
            st.rerun()

    st.subheader("Fast Navigation")
    all_rooms = get_all_rooms()
    room_opts = {r['code']: f"{r['name']} ({r['building']})" for r in all_rooms}
    
    src = st.selectbox("From", options=list(room_opts.keys()), format_func=lambda x: room_opts[x], index=list(room_opts.keys()).index(st.session_state.current_loc))
    dst = st.selectbox("To", options=list(room_opts.keys()), format_func=lambda x: room_opts[x], index=1)
    
    if st.button("FIND ROUTE", use_container_width=True):
        path = st.session_state.graph.shortest_path(src, dst)
        if path: st.session_state.path_data = path
        else: st.error("No Route Found")

    st.divider()
    with st.expander("🛠 ADVANCED SETTINGS"):
        if st.button("CLEAR APP CACHE", use_container_width=True):
            from database.db_manager import clear_ai_cache
            clear_ai_cache()
            st.session_state.clear()
            st.toast("Cache Cleared!", icon="🗑️")
            time.sleep(1)
            st.rerun()

# --- Dashboard Layout ---
main_col, side_col = st.columns([5, 3], gap="medium")

with main_col:
    # Map Section
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown("### 💠 Interactive Graph")
    
    rooms = st.session_state.graph.all_rooms()
    df_rooms = pd.DataFrame.from_dict(rooms, orient='index')
    
    fig = go.Figure()
    
    # Edges
    for u, v, d in st.session_state.graph.G.edges(data=True):
        r1, r2 = rooms[u], rooms[v]
        fig.add_trace(go.Scatter(
            x=[r1['x'], r2['x']], y=[r1['y'], r2['y']],
            mode='lines', line=dict(color='rgba(255,255,255,0.05)', width=1),
            hoverinfo='none', showlegend=False
        ))

    # Path
    if "path_data" in st.session_state:
        p = st.session_state.path_data['path']
        pxs = [rooms[i]['x'] for i in p]
        pys = [rooms[i]['y'] for i in p]
        fig.add_trace(go.Scatter(
            x=pxs, y=pys, mode='lines+markers',
            line=dict(color='#38bdf8', width=6),
            marker=dict(size=12, color='#38bdf8', line=dict(color='#fff', width=2)),
            hoverinfo='none', showlegend=False
        ))
        # Highlight current position
        fig.add_trace(go.Scatter(
            x=[rooms[st.session_state.current_loc]['x']], 
            y=[rooms[st.session_state.current_loc]['y']],
            mode='markers', marker=dict(size=20, color='#34d399', symbol='star'),
            name="You are here", showlegend=False
        ))

    # Nodes with Permanent Labels
    fig.add_trace(go.Scatter(
        x=df_rooms['x'], y=df_rooms['y'], 
        mode='markers+text',
        marker=dict(size=14, color='#1e293b', line=dict(color='#38bdf8', width=1.5)),
        text=df_rooms['name'],
        textposition="bottom center",
        textfont=dict(family="Outfit", size=10, color="rgba(255,255,255,0.8)"),
        hovertext=df_rooms['name'], 
        hoverinfo='text', 
        showlegend=False,
        customdata=df_rooms.index
    ))

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=0, r=0, t=10, b=0),
        height=680,
        dragmode='pan',
        clickmode='event+select'
    )
    
    # Handle Selection
    selection = st.plotly_chart(
        fig, 
        use_container_width=True, 
        config={'displayModeBar': False},
        on_select="rerun",
        key="map_selection"
    )

    if selection and "selection" in selection and selection["selection"]["points"]:
        clicked_room = selection["selection"]["points"][0]["customdata"]
        if clicked_room != st.session_state.current_loc:
            path = st.session_state.graph.shortest_path(st.session_state.current_loc, clicked_room)
            if path: 
                st.session_state.path_data = path
                st.toast(f"📍 Route to {clicked_room} calculated!", icon="🚀")
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with side_col:
    # Chat Container
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown("### 🤖 Campus AI")
    
    # Directions integrated into sidebar or compact list
    if "path_data" in st.session_state:
        with st.expander("📍 NAVIGATION STEPS", expanded=True):
            for i, step in enumerate(st.session_state.path_data['steps']):
                st.markdown(f"**{i+1}.** {step}")

    chat_h = 420 if "path_data" not in st.session_state else 250
    chat_box = st.container(height=chat_h, border=False)
    with chat_box:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if q := st.chat_input("Ask about campus..."):
        st.session_state.chat_history.append({"role": "user", "content": q})
        with chat_box:
            with st.chat_message("user"): st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    res = st.session_state.agent.process_query(q, st.session_state.current_loc)
                    st.markdown(res["message"])
                    if res["type"] == "navigation":
                        st.session_state.path_data = res["path_data"]
                        st.rerun()
                st.session_state.chat_history.append({"role": "assistant", "content": res["message"]})
    st.markdown('</div>', unsafe_allow_html=True)
