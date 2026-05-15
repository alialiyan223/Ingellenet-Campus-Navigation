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
        """Retrieve full campus context for RAG, including connectivity."""
        try:
            rooms = get_all_rooms()
            context = "CAMPUS DIRECTORY:\n"
            for r in rooms:
                context += f"- {r['name']} ({r['code']}): {r['building']}, Floor {r['floor']}, Type: {r['room_type']}. {r['description']}\n"
            
            # Add basic connectivity context
            context += "\nCAMPUS CONNECTIVITY:\n"
            edges = self.graph.G.edges()
            for u, v in list(edges)[:30]: # Limit to avoid token overflow
                context += f"- {u} connects to {v}\n"
            
            return context
        except Exception as e:
            print(f"RAG Error: {e}")
            return "Campus directory unavailable."

    def process_query(self, query: str, current_loc: str = "MAIN_ENT") -> Dict[str, Any]:
        """Process user query using Cerebras and RAG with typo tolerance."""
        if not self.client:
            return self._fallback_logic(query, current_loc)

        context = self._get_campus_context()
        
        prompt = f"""
You are the INTELLEGENT Campus Assistant. Use the provided context to help the user navigate.
BE FLEXIBLE: Users may have typos (e.g., 'sport compl' means 'Sport Complex'). 
Match their query to the closest location in the context.

CAMPUS CONTEXT (RAG):
{context}

USER STATE:
- Current Location: {current_loc}
- Query: {query}

TASK:
1. Identify the destination 'CODE' from the context, even if the user misspelled it.
2. If they just want info, provide it.
3. If you can't find a match, say so politely.

RESPONSE FORMAT (STRICT JSON):
{{
    "type": "navigation" | "info",
    "message": "Helpful response here",
    "destination_code": "CODE_OF_TARGET" (only if navigation)
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
                    return {
                        "type": "navigation",
                        "message": res_data["message"],
                        "path_data": path_data,
                        "target": get_room(dest)
                    }
            
            return {
                "type": "info",
                "message": res_data["message"]
            }
            
        except Exception as e:
            print(f"Cerebras Error: {e}")
            return self._fallback_logic(query, current_loc)

    def _fallback_logic(self, query: str, current_loc: str) -> Dict[str, Any]:
        """Fuzzy matching fallback with basic conversational support."""
        import difflib
        query_low = query.lower().strip()
        
        # 1. Handle Greetings
        greetings = ["hi", "hello", "hey", "hola", "greetings", "yo"]
        if query_low in greetings:
            return {
                "type": "info",
                "message": "Hello! I'm your INTELLEGENT Campus Assistant. How can I help you navigate today?"
            }

        rooms = get_all_rooms()
        
        # 2. Try fuzzy matching room names
        room_names = [r['name'].lower() for r in rooms]
        matches = difflib.get_close_matches(query_low, room_names, n=1, cutoff=0.4)
        
        if not matches:
            # 2. Try simple keyword search (e.g. 'sport' in 'Sport Complex')
            for r in rooms:
                name_low = r['name'].lower()
                if any(word in name_low for word in query_low.split() if len(word) > 3):
                    matches = [name_low]
                    break

        if matches:
            match_name = matches[0]
            matched_room = next(r for r in rooms if r['name'].lower() == match_name)
            path_data = self.graph.shortest_path(current_loc, matched_room['code'])
            if path_data:
                return {
                    "type": "navigation",
                    "message": f"I think you're looking for {matched_room['name']}. Navigating there now!",
                    "path_data": path_data,
                    "target": matched_room
                }
        
        return {
            "type": "info",
            "message": "I'm having trouble finding that location. Could you try checking the spelling or use the map dropdown?"
        }
