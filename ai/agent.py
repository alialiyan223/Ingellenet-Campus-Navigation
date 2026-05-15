"""
Agentic AI Module - Natural Language Processing for Campus Navigation.
Handles user queries like "Where is the nearest washroom?" or "How do I get to CS Lab 2?"
"""

import hashlib
import json
import logging
import os
import re
from typing import Optional, List, Dict, Any

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from database.db_manager import (
    search_rooms,
    get_cached_ai_response,
    cache_ai_response,
    get_all_rooms,
    get_room
)
from navigation.pathfinder import CampusGraph

logger = logging.getLogger(__name__)

class CampusAgent:
    """
    An 'Agentic' AI that interprets natural language and interacts with 
    the CampusGraph and Database to provide intelligent answers.
    """

    def __init__(self, graph: CampusGraph):
        self.graph = graph
        self.rooms_cache = get_all_rooms()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key) if (Anthropic and self.api_key) else None

    def process_query(self, query: str, current_location: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point for user queries.
        Uses Agentic AI if API is available, otherwise falls back to rule-based logic.
        """
        query_clean = query.strip().lower()
        query_hash = hashlib.md5(f"{query_clean}_{current_location}".encode()).hexdigest()

        # Check local offline cache first
        cached = get_cached_ai_response(query_hash)
        if cached:
            try:
                return json.loads(cached)
            except:
                pass

        # Try Agentic AI first if available
        if self.client:
            try:
                response = self._handle_agentic_query(query, current_location)
                cache_ai_response(query_hash, query, json.dumps(response))
                return response
            except Exception as e:
                logger.error(f"Agentic AI failed: {e}. Falling back to rule-based.")

        # Fallback to rule-based logic
        response = self._handle_intent(query_clean, current_location)
        cache_ai_response(query_hash, query, json.dumps(response))
        
        return response

    def _handle_agentic_query(self, query: str, current_loc: Optional[str]) -> Dict[str, Any]:
        """Use Claude with tool calling to handle the query."""
        
        tools = [
            {
                "name": "search_rooms",
                "description": "Search for rooms, labs, offices or buildings on campus.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The name or type of room to find (e.g., 'CS Lab', 'Washroom')"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_path",
                "description": "Calculate directions between two locations.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "target_code": {"type": "string", "description": "The code of the destination room."}
                    },
                    "required": ["target_code"]
                }
            }
        ]

        system_prompt = f"""You are the Intellegent Campus Assistant.
Your goal is to help users navigate the campus.
Current user location: {current_loc or 'Unknown'}.
If the user wants to go somewhere, search for the room first, then get the path.
Always provide a friendly response."""

        message = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=[{"role": "user", "content": query}]
        )

        if message.stop_reason == "tool_use":
            tool_use = message.content[-1]
            tool_name = tool_use.name
            tool_input = tool_use.input

            if tool_name == "search_rooms":
                results = search_rooms(tool_input["query"])
                if not results:
                    return {"type": "error", "message": f"I couldn't find any results for '{tool_input['query']}'."}
                
                if len(results) == 1:
                    r = results[0]
                    # If we have current location, auto-provide path
                    if current_loc:
                        path_data = self.graph.shortest_path(current_loc, r['code'])
                        return {
                            "type": "navigation",
                            "target": r,
                            "path_data": path_data,
                            "message": f"I found {r['name']}. Here are the directions from your current location."
                        }
                    return {
                        "type": "location_info",
                        "room": r,
                        "message": f"{r['name']} is in the {r['building']} building, Floor {r['floor']}."
                    }
                return {
                    "type": "search_results",
                    "results": results[:5],
                    "message": f"I found {len(results)} matches. Which one are you looking for?"
                }

            elif tool_name == "get_path":
                if not current_loc:
                    return {"type": "error", "message": "I need to know your current location to give directions."}
                
                target = get_room(tool_input["target_code"])
                path_data = self.graph.shortest_path(current_loc, tool_input["target_code"])
                if not path_data:
                    return {"type": "error", "message": "I couldn't find a path to that location."}
                
                return {
                    "type": "navigation",
                    "target": target,
                    "path_data": path_data,
                    "message": f"Calculating route to {target['name']}."
                }

        return {"type": "text", "message": message.content[0].text}

    def _handle_intent(self, query: str, current_loc: Optional[str]) -> Dict[str, Any]:
        """Simple rule-based 'Agentic' logic to handle intents offline."""
        
        # 1. Navigation Intent
        nav_match = re.search(r"(?:how to get to|go to|directions to|way to|navigate to)\s+(.+)", query)
        if nav_match:
            target_name = nav_match.group(1).strip()
            target_name = re.sub(r'^(the|a|an)\s+', '', target_name, flags=re.I)
            return self._execute_navigation(target_name, current_loc)

        # 2. Search/Location Intent
        search_match = re.search(r"(?:where is|find|locate|search for)\s+(.+)", query)
        if search_match:
            target_name = search_match.group(1).strip()
            target_name = re.sub(r'^(the|a|an)\s+', '', target_name, flags=re.I)
            return self._execute_search(target_name)

        # 3. Proximity Intent
        near_match = re.search(r"(?:nearest|closest|next to me)\s+(.+)", query)
        if near_match and current_loc:
            category = near_match.group(1).strip()
            category = re.sub(r'^(the|a|an)\s+', '', category, flags=re.I)
            return self._execute_proximity_search(category, current_loc)

        # 4. General Info Intent
        if "list" in query and ("rooms" in query or "labs" in query):
            return {
                "type": "list",
                "content": self.rooms_cache[:10],
                "message": "Here are some rooms on campus."
            }

        # Fallback: Generic Search
        query_cleaned = re.sub(r'^(the|a|an)\s+', '', query, flags=re.I)
        return self._execute_search(query_cleaned)

    def _execute_navigation(self, target_query: str, current_loc: Optional[str]) -> Dict[str, Any]:
        if not current_loc:
            return {
                "type": "error",
                "message": "I need to know your current location first. Try scanning Wi-Fi or selecting a start point."
            }
        
        potential_rooms = search_rooms(target_query)
        if not potential_rooms:
            return {"type": "error", "message": f"I couldn't find '{target_query}' on campus."}
        
        target_room = potential_rooms[0]
        path_data = self.graph.shortest_path(current_loc, target_room['code'])
        
        if not path_data:
            return {"type": "error", "message": f"I found {target_room['name']}, but there is no path from your location."}
        
        return {
            "type": "navigation",
            "target": target_room,
            "path_data": path_data,
            "message": f"Calculating route to {target_room['name']} in {target_room['building']}."
        }

    def _execute_search(self, query: str) -> Dict[str, Any]:
        results = search_rooms(query)
        if not results:
            return {"type": "error", "message": f"No results found for '{query}'."}
        
        if len(results) == 1:
            r = results[0]
            return {
                "type": "location_info",
                "room": r,
                "message": f"Found {r['name']} in the {r['building']} building (Floor {r['floor']})."
            }
        
        return {
            "type": "search_results",
            "results": results[:5],
            "message": f"I found {len(results)} matches for '{query}'."
        }

    def _execute_proximity_search(self, category: str, current_loc: Optional[str]) -> Dict[str, Any]:
        all_matches = [r for r in self.rooms_cache if category in r['room_type'].lower() or category in r['name'].lower()]
        
        if not all_matches:
            return {"type": "error", "message": f"No {category} found nearby."}
        
        ranked = []
        for r in all_matches:
            path = self.graph.shortest_path(current_loc, r['code'])
            if path:
                ranked.append((path['distance'], r, path))
        
        ranked.sort(key=lambda x: x[0])
        
        if not ranked:
            return {"type": "error", "message": f"Found {category}s, but they are inaccessible from your location."}
        
        best_dist, best_room, best_path = ranked[0]
        return {
            "type": "navigation",
            "target": best_room,
            "path_data": best_path,
            "message": f"The nearest {category} is {best_room['name']}, {best_dist} units away."
        }
