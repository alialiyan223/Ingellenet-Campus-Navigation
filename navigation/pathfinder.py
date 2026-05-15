"""
Pathfinding Engine – Dijkstra's Algorithm on the campus graph.
Builds a NetworkX graph from SQLite and exposes shortest-path utilities.
"""

import heapq
import networkx as nx
import logging
from typing import Optional
from database.db_manager import get_all_rooms, get_all_edges, log_navigation

logger = logging.getLogger(__name__)


class CampusGraph:
    """Weighted, undirected campus graph backed by NetworkX."""

    def __init__(self):
        self.G = nx.Graph()
        self._rooms: dict[str, dict] = {}
        self.reload()

    # ── Graph Construction ─────────────────────────────────────────────────────

    def reload(self):
        """Reload nodes and edges from the database."""
        self.G.clear()
        self._rooms.clear()

        for room in get_all_rooms():
            code = room["code"]
            self._rooms[code] = room
            self.G.add_node(
                code,
                name=room["name"],
                building=room["building"],
                floor=room["floor"],
                room_type=room["room_type"],
                x=room["x"],
                y=room["y"],
                capacity=room["capacity"],
                is_accessible=room["is_accessible"],
            )

        for edge in get_all_edges():
            self.G.add_edge(
                edge["from_room"],
                edge["to_room"],
                weight=edge["weight"],
                path_type=edge["path_type"],
                is_accessible=edge["is_accessible"],
            )

        logger.info(
            "Graph loaded: %d nodes, %d edges", self.G.number_of_nodes(), self.G.number_of_edges()
        )

    # ── Pathfinding ────────────────────────────────────────────────────────────

    def shortest_path(
        self,
        source: str,
        target: str,
        accessible_only: bool = False,
    ) -> Optional[dict]:
        """
        Return shortest path between source and target using Dijkstra.

        Returns:
            dict with keys: path (list of room codes), distance (float),
                            steps (list of human-readable directions), or None if no path.
        """
        if source not in self.G or target not in self.G:
            logger.warning("Unknown node: %s or %s", source, target)
            return None

        subgraph = self.G
        if accessible_only:
            accessible_edges = [
                (u, v) for u, v, d in self.G.edges(data=True) if d.get("is_accessible", 1)
            ]
            subgraph = self.G.edge_subgraph(accessible_edges)

        try:
            path = nx.dijkstra_path(subgraph, source, target, weight="weight")
            distance = nx.dijkstra_path_length(subgraph, source, target, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

        steps = self._generate_directions(path)
        log_navigation(source, target, path, distance)

        return {
            "path": path,
            "distance": round(distance, 1),
            "steps": steps,
            "rooms": [self._rooms[c] for c in path if c in self._rooms],
        }

    def _generate_directions(self, path: list[str]) -> list[str]:
        """Convert a path of room codes into plain-English turn-by-turn steps."""
        if not path:
            return []
        if len(path) == 1:
            return [f"You are already at {self._rooms[path[0]]['name']}."]

        directions = [f"🚩 Start at {self._rooms[path[0]]['name']} ({path[0]})"]
        for i in range(1, len(path)):
            prev = path[i - 1]
            curr = path[i]
            edge_data = self.G.get_edge_data(prev, curr, default={})
            path_type = edge_data.get("path_type", "corridor")
            weight = edge_data.get("weight", 1)

            prev_room = self._rooms.get(prev, {})
            curr_room = self._rooms.get(curr, {})

            if path_type == "stairs":
                floor_diff = curr_room.get("floor", 1) - prev_room.get("floor", 1)
                direction = "up" if floor_diff > 0 else "down"
                directions.append(
                    f"🪜 Take stairs {direction} to Floor {curr_room.get('floor')} → {curr_room['name']} ({curr})"
                )
            elif path_type == "outdoor" or path_type == "path":
                directions.append(
                    f"🌳 Walk outside (~{int(weight * 10)}m) → {curr_room['name']} ({curr})"
                )
            else:
                directions.append(
                    f"➡️  Walk along corridor (~{int(weight * 10)}m) → {curr_room['name']} ({curr})"
                )

        directions.append(f"🏁 Arrived at {self._rooms[path[-1]]['name']} ({path[-1]})")
        return directions

    # ── Graph Queries ──────────────────────────────────────────────────────────

    def get_room_info(self, code: str) -> Optional[dict]:
        return self._rooms.get(code)

    def get_neighbors(self, code: str) -> list[dict]:
        neighbors = []
        for n in self.G.neighbors(code):
            edge = self.G.get_edge_data(code, n, default={})
            info = dict(self._rooms.get(n, {}))
            info["edge_weight"] = edge.get("weight", 1)
            info["path_type"] = edge.get("path_type", "corridor")
            neighbors.append(info)
        return neighbors

    def all_rooms(self) -> dict[str, dict]:
        return dict(self._rooms)

    def rooms_by_type(self, room_type: str) -> list[dict]:
        return [r for r in self._rooms.values() if r["room_type"] == room_type]

    def rooms_by_building(self, building: str) -> list[dict]:
        return [r for r in self._rooms.values() if r["building"].lower() == building.lower()]

    def graph_summary(self) -> dict:
        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "is_connected": nx.is_connected(self.G),
            "buildings": list({r["building"] for r in self._rooms.values()}),
            "room_types": list({r["room_type"] for r in self._rooms.values()}),
        }
