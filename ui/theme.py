"""
UI Theme Configuration - Defines the 'Wow' factor aesthetics.
"""

COLORS = {
    "bg_dark": "#0F172A",      # Slate 900
    "bg_card": "#1E293B",      # Slate 800
    "primary": "#38BDF8",      # Sky 400
    "secondary": "#818CF8",    # Indigo 400
    "accent": "#F472B6",       # Pink 400
    "text_main": "#F8FAFC",    # Slate 50
    "text_dim": "#94A3B8",     # Slate 400
    "success": "#34D399",      # Emerald 400
    "warning": "#FB7185",      # Rose 400
}

FONT_MAIN = ("Inter", 12)
FONT_BOLD = ("Inter", 14, "bold")
FONT_TITLE = ("Outfit", 24, "bold")

# Custom Styles for CustomTkinter
THEME_CONFIG = {
    "appearance_mode": "dark",
    "color_theme": "blue" # We will override most colors manually
}
