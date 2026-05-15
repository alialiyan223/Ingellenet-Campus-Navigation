"""
Main UI Application - Using CustomTkinter for a premium, modern experience.
Combines Pathfinding, Wi-Fi Positioning, Agentic AI, and LAN Sync.
"""

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import logging
import threading
import time

from ui.theme import COLORS, FONT_MAIN, FONT_BOLD, FONT_TITLE
from navigation.pathfinder import CampusGraph
from navigation.wifi_positioning import WifiLocaliser
from ai.agent import CampusAgent
from network.sync_manager import NetworkSyncManager
from database.db_manager import initialize_database, search_rooms

logger = logging.getLogger(__name__)

class CampusNavApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Setup Backend ---
        initialize_database()
        self.graph = CampusGraph()
        self.localiser = WifiLocaliser()
        self.agent = CampusAgent(self.graph)
        self.sync_mgr = NetworkSyncManager()

        # --- Window Configuration ---
        self.title("Ingellenet | Intelligent Offline Campus Navigation")
        self.geometry("1100x700")
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Grid layout (Sidebar + Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_main_content()
        
        # --- Start Background Services ---
        self.localiser.start_background_scan()
        self.sync_mgr.start_background_sync()
        self._update_status_loop()

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COLORS["bg_card"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)

        # Logo / Title
        self.logo_label = ctk.CTkLabel(self.sidebar, text="🔵 INGELLENET", font=FONT_TITLE, text_color=COLORS["primary"])
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        self.sub_label = ctk.CTkLabel(self.sidebar, text="Campus Intelligence System", font=FONT_MAIN, text_color=COLORS["text_dim"])
        self.sub_label.grid(row=1, column=0, padx=20, pady=(0, 30))

        # Current Location Card
        self.loc_card = ctk.CTkFrame(self.sidebar, fg_color=COLORS["bg_dark"], corner_radius=12)
        self.loc_card.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.loc_title = ctk.CTkLabel(self.loc_card, text="CURRENT LOCATION", font=FONT_BOLD, text_color=COLORS["text_dim"])
        self.loc_title.pack(pady=(10, 0), padx=15, anchor="w")
        
        self.loc_val = ctk.CTkLabel(self.loc_card, text="Scanning Wi-Fi...", font=FONT_BOLD, text_color=COLORS["success"])
        self.loc_val.pack(pady=(0, 10), padx=15, anchor="w")

        # Network Status Card
        self.net_card = ctk.CTkFrame(self.sidebar, fg_color=COLORS["bg_dark"], corner_radius=12)
        self.net_card.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.net_title = ctk.CTkLabel(self.net_card, text="LAN CONNECTIVITY", font=FONT_BOLD, text_color=COLORS["text_dim"])
        self.net_title.pack(pady=(10, 0), padx=15, anchor="w")
        
        self.net_val = ctk.CTkLabel(self.net_card, text="Disconnected", font=FONT_MAIN, text_color=COLORS["text_dim"])
        self.net_val.pack(pady=(0, 10), padx=15, anchor="w")

        # Footer
        self.mode_switch = ctk.CTkSwitch(self.sidebar, text="Offline Mode", font=FONT_MAIN, progress_color=COLORS["primary"])
        self.mode_switch.select()
        self.mode_switch.grid(row=5, column=0, padx=20, pady=20)

    def _create_main_content(self):
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        # --- Top Bar (AI Search) ---
        self.search_frame = ctk.CTkFrame(self.content, fg_color=COLORS["bg_card"], height=60, corner_radius=15)
        self.search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.search_frame.grid_columnconfigure(0, weight=1)

        self.query_entry = ctk.CTkEntry(
            self.search_frame, 
            placeholder_text="Ask AI: 'Where is the nearest washroom?' or 'Directions to CS Lab 2'...",
            font=FONT_MAIN,
            fg_color="transparent",
            border_width=0,
            height=50
        )
        self.query_entry.grid(row=0, column=0, padx=20, sticky="ew")
        self.query_entry.bind("<Return>", lambda e: self._on_ai_query())

        self.ask_btn = ctk.CTkButton(
            self.search_frame, 
            text="Ask Agent", 
            width=100, 
            height=35,
            fg_color=COLORS["primary"],
            hover_color=COLORS["secondary"],
            font=FONT_BOLD,
            command=self._on_ai_query
        )
        self.ask_btn.grid(row=0, column=1, padx=10)

        # --- Main Split View ---
        self.split_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.split_frame.grid(row=1, column=0, sticky="nsew")
        self.split_frame.grid_columnconfigure(0, weight=2) # Map
        self.split_frame.grid_columnconfigure(1, weight=1) # Directions

        # Map Visualizer
        self.map_frame = ctk.CTkFrame(self.split_frame, fg_color=COLORS["bg_card"], corner_radius=20)
        self.map_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.map_canvas = tk.Canvas(
            self.map_frame, 
            bg=COLORS["bg_card"], 
            highlightthickness=0,
            cursor="cross"
        )
        self.map_canvas.pack(fill="both", expand=True, padx=20, pady=20)
        self._draw_campus_map()

        # Directions / Results Panel
        self.results_frame = ctk.CTkFrame(self.split_frame, fg_color=COLORS["bg_card"], corner_radius=20)
        self.results_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        self.results_title = ctk.CTkLabel(self.results_frame, text="NAVIGATOR", font=FONT_BOLD, text_color=COLORS["primary"])
        self.results_title.pack(pady=20, padx=20, anchor="w")

        self.directions_box = ctk.CTkTextbox(
            self.results_frame, 
            fg_color="transparent", 
            font=FONT_MAIN, 
            text_color=COLORS["text_main"],
            wrap="word"
        )
        self.directions_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.directions_box.insert("0.0", "Welcome to the Campus Navigation System.\n\nEnter a query above or click on the map to start.")

    def _draw_campus_map(self):
        """Simple node-link diagram for the campus."""
        self.map_canvas.delete("all")
        rooms = self.graph.all_rooms()
        
        # Draw Edges
        for u, v, d in self.graph.G.edges(data=True):
            r1 = rooms.get(u)
            r2 = rooms.get(v)
            if r1 and r2:
                self.map_canvas.create_line(
                    r1['x'], r1['y'], r2['x'], r2['y'],
                    fill="#334155", width=2, tags="edge"
                )

        # Draw Nodes
        for code, r in rooms.items():
            color = COLORS["primary"] if r['room_type'] == 'lab' else COLORS["text_dim"]
            if r['room_type'] == 'washroom': color = COLORS["accent"]
            
            radius = 6
            self.map_canvas.create_oval(
                r['x']-radius, r['y']-radius, r['x']+radius, r['y']+radius,
                fill=color, outline=COLORS["bg_card"], width=2, tags=("node", code)
            )
            # Labels for key rooms
            if r['room_type'] in ['lab', 'library', 'cafeteria', 'entrance']:
                self.map_canvas.create_text(
                    r['x'], r['y']+15, text=r['name'], fill=COLORS["text_dim"], 
                    font=("Inter", 8), tags="label"
                )

    def _on_ai_query(self):
        query = self.query_entry.get()
        if not query: return
        
        current_loc = self.localiser.current_room
        response = self.agent.process_query(query, current_loc)
        
        self.directions_box.delete("0.0", "end")
        self.directions_box.insert("0.0", f"🤖 AI: {response['message']}\n\n")
        
        if response['type'] == "navigation":
            path_data = response['path_data']
            for step in path_data['steps']:
                self.directions_box.insert("end", f"{step}\n")
            self._highlight_path(path_data['path'])
        
        elif response['type'] == "search_results":
            for r in response['results']:
                self.directions_box.insert("end", f"• {r['name']} ({r['building']})\n")

    def _highlight_path(self, path: list):
        self._draw_campus_map() # Reset
        rooms = self.graph.all_rooms()
        for i in range(len(path)-1):
            r1, r2 = rooms[path[i]], rooms[path[i+1]]
            self.map_canvas.create_line(
                r1['x'], r1['y'], r2['x'], r2['y'],
                fill=COLORS["success"], width=4, tags="path_highlight"
            )
        # Highlight start/end
        start, end = rooms[path[0]], rooms[path[-1]]
        self.map_canvas.create_oval(start['x']-8, start['y']-8, start['x']+8, start['y']+8, fill=COLORS["success"])
        self.map_canvas.create_oval(end['x']-8, end['y']-8, end['x']+8, end['y']+8, fill=COLORS["warning"])

    def _update_status_loop(self):
        """Periodically update UI with backend status."""
        room_code = self.localiser.current_room
        if room_code:
            room_info = self.graph.get_room_info(room_code)
            loc_text = f"{room_info['name']}\n({room_code})" if room_info else room_code
            self.loc_val.configure(text=loc_text, text_color=COLORS["success"])
        else:
            self.loc_val.configure(text="Unknown Location", text_color=COLORS["warning"])

        self.net_val.configure(text=self.sync_mgr.get_status())
        
        self.after(2000, self._update_status_loop)

if __name__ == "__main__":
    app = CampusNavApp()
    app.mainloop()
