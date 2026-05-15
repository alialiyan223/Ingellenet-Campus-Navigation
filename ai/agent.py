import os
import json
import re
import sqlite3
import hashlib
from typing import Dict, List, Any, Optional

try:
    from cerebras.cloud.sdk import Cerebras
    CEREBRAS_AVAILABLE = True
except ImportError:
    CEREBRAS_AVAILABLE = False

from database.db_manager import get_all_rooms, get_room, search_rooms

class CampusAgent:
    """
    Agentic AI powered by Cerebras for ultra-fast campus navigation and RAG.
    """
    def __init__(self, graph_manager, db_path: str = "database/campus.db"):
        self.graph = graph_manager
        self.db_path = db_path
        # Use provided key or environment variable
        self.api_key = os.getenv("CEREBRAS_API_KEY") or "csk-c3wvvtwcc332kh8wnh92hekxjcj9j4d46mhp3ny3tnjn5vxk"
        self.client = None
        
        if CEREBRAS_AVAILABLE and self.api_key:
            try:
                self.client = Cerebras(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Cerebras: {e}")

    def _get_campus_context(self) -> str:
        """Retrieve full campus context for RAG."""
        try:
            rooms = get_all_rooms()
            context = "CAMPUS DIRECTORY & NAVIGATION NODES:\n"
            for r in rooms:
                context += f"- NAME: {r['name']} | CODE: {r['code']} | BLDG: {r['building']} | FLOOR: {r['floor']} | TYPE: {r['room_type']} | DESC: {r['description']}\n"
            return context
        except Exception as e:
            print(f"RAG Error: {e}")
            return "Campus directory unavailable."

    def process_query(self, query: str, current_loc: str = "MAIN_ENT") -> Dict[str, Any]:
        """Process user query using Cerebras and RAG."""
        if not self.client:
            return self._fallback_logic(query, current_loc)

        context = self._get_campus_context()
        
        prompt = f"""
You are the INTELLEGENT Campus Assistant. Use the provided context to help the user navigate.
Identify if the user wants to go to a specific location or just needs information.

CAMPUS CONTEXT (RAG):
{context}

USER STATE:
- Current Location: {current_loc}
- Query: {query}

TASK:
1. If navigation: Identify the exact 'CODE' of the destination.
2. If info: Provide details about the room or facility.

RESPONSE FORMAT (STRICT JSON):
{{
    "type": "navigation" | "info",
    "message": "Helpful response to the user",
    "destination_code": "CODE_OF_TARGET" (REQUIRED for navigation)
}}
"""
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3.1-70b",
                response_format={"type": "json_object"}
            )
            
            res_data = json.loads(response.choices[0].message.content)
            
            if res_data.get("type") == "navigation" and res_data.get("destination_code"):
                dest = res_data["destination_code"]
                path_data = self.graph.shortest_path(current_loc, dest)
                if path_data:
                    target_info = get_room(dest)
                    return {
                        "type": "navigation",
                        "message": res_data["message"],
                        "path_data": path_data,
                        "target": target_info
                    }
            
            return {
                "type": "info",
                "message": res_data["message"]
            }
            
        except Exception as e:
            print(f"Cerebras Error: {e}")
            return self._fallback_logic(query, current_loc)

    def _fallback_logic(self, query: str, current_loc: str) -> Dict[str, Any]:
        """Regex-based fallback for offline mode."""
        query_low = query.lower()
        rooms = get_all_rooms()
        
        for r in rooms:
            if r['name'].lower() in query_low or r['code'].lower() in query_low:
                path_data = self.graph.shortest_path(current_loc, r['code'])
                if path_data:
                    return {
                        "type": "navigation",
                        "message": f"Offline Mode: Found {r['name']}. Navigating now.",
                        "path_data": path_data,
                        "target": r
                    }
        
        return {
            "type": "info",
            "message": "I'm currently in offline mode and couldn't process that request. Please use the map or check your internet."
        }
