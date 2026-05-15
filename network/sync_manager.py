"""
Network Sync Manager - Handles offline map updates via Campus LAN.
Implements LAN discovery and background synchronization to save mobile data.
"""

import socket
import json
import logging
import threading
import time
import requests
from typing import Optional
from database.db_manager import log_sync

logger = logging.getLogger(__name__)

CAMPUS_SERVER_PORT = 5005  # Hypothetical campus sync server port
SYNC_INTERVAL = 300        # Check every 5 minutes

class NetworkSyncManager:
    """
    Manages LAN connectivity and data synchronization.
    Works entirely on the local campus network.
    """

    def __init__(self):
        self._server_ip: Optional[str] = None
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None
        self.last_sync_status = "Not Started"

    def start_background_sync(self):
        """Start the background thread for LAN discovery and sync."""
        if self._running:
            return
        
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info("Background LAN sync service started.")

    def stop_background_sync(self):
        self._running = False

    def _sync_loop(self):
        while self._running:
            try:
                # 1. Discover Campus Server via UDP Broadcast (Simulated)
                self._discover_server()
                
                if self._server_ip:
                    # 2. Attempt Sync
                    self._perform_sync()
                else:
                    self.last_sync_status = "Searching for Campus LAN..."
                    
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                self.last_sync_status = "Sync Error"
            
            time.sleep(SYNC_INTERVAL)

    def _discover_server(self):
        """
        Attempts to find the campus update server on the local network.
        In a real scenario, this uses UDP broadcast or mDNS.
        """
        # Simulation of discovery logic
        try:
            # We assume if we are on a specific subnet or can reach a known gateway,
            # we consider the server 'discovered'.
            # For this demo, we simulate finding a server at 192.168.1.100 if on LAN.
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()

            if local_ip.startswith("192.168.") or local_ip.startswith("10."):
                self._server_ip = "192.168.1.100" # Dummy campus server IP
            else:
                self._server_ip = None
        except:
            self._server_ip = None

    def _perform_sync(self):
        """
        Connects to the campus server and pulls latest map data.
        """
        logger.info(f"Attempting sync with campus server at {self._server_ip}")
        
        # In a real app, this would be:
        # response = requests.get(f"http://{self._server_ip}:{CAMPUS_SERVER_PORT}/updates")
        # For now, we simulate a successful 'No Updates' or 'Success' message.
        
        time.sleep(2) # Simulate network delay
        
        success = True # Simulation
        if success:
            log_sync(self._server_ip, "Success", records=0)
            self.last_sync_status = f"Synced with {self._server_ip} at {time.strftime('%H:%M:%S')}"
        else:
            log_sync(self._server_ip, "Failed")
            self.last_sync_status = "Connection Failed"

    def get_status(self) -> str:
        return self.last_sync_status
