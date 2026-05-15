# Ingellenet Offline Campus Navigation System

An intelligent campus navigation system with Wi-Fi positioning and Agentic AI.

## 🚀 Live Deployment (Streamlit)
This app is optimized for deployment on **Streamlit Cloud**.

1. **Push to GitHub**: Upload this folder to a GitHub repository.
2. **Deploy to Streamlit**:
   - Log in to [Streamlit Cloud](https://share.streamlit.io/).
   - Click "New app" and select your repository.
   - Main file path: `streamlit_app.py`.
3. **Configure AI (Optional)**:
   - In Streamlit Cloud settings, go to **Secrets**.
   - Add: `ANTHROPIC_API_KEY = "your_key_here"` for Agentic features.

## ✨ Features
- **Agentic AI**: Natural language queries handled by Claude 3 Haiku (with rule-based fallback).
- **Interactive Map**: Plotly-based campus layout with path highlighting.
- **Pathfinding**: Dijkstra's algorithm for optimal route calculation.
- **Wi-Fi Positioning**: Simulated fingerprinting for location estimation.
- **Modern UI**: Dark mode with premium aesthetics.

## 🛠️ Local Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the Streamlit app:
   ```bash
   streamlit run streamlit_app.py
   ```
3. (Optional) Run the Flask backend for the classic web app:
   ```bash
   python server.py
   ```

## 🐛 Bug Fixes
- Fixed the location selection lag in the web frontend.
- Added hover feedback and increased selection hitboxes for better UX.
