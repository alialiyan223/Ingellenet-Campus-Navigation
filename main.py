"""
Ingellenet Offline Campus Navigation System
──────────────────────────────────────────────────────────────────────────────
Entry point for the application.
"""

import sys
import logging
import os

# Ensure the project root is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.app import CampusNavApp

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("campus_nav.log"),
            logging.StreamHandler()
        ]
    )

def main():
    setup_logging()
    logger = logging.getLogger("Main")
    logger.info("Starting Ingellenet Offline Campus Navigation System...")
    
    try:
        app = CampusNavApp()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Application failed to start: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
