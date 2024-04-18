"""
Information specific to each role.
"""

from dash import html
import dash_bootstrap_components as dbc

# Main, secondary, and speed stat dictionary for each role.
# Allows for tool tips to be stored too.
role_stat_dict = {
    "Healer": {
        "main_stat": {"label": "MND:", "placeholder": "Mind"},
        "secondary_stat": {
            "label": [
                html.Span(
                    "STR:",
                    id="str-tooltip",
                    style={
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                        "cursor": "pointer",
                    },
                ),
                dbc.Tooltip(
                    "Strength, used for auto-attacks",
                    target="str-tooltip",
                ),
            ],
            "placeholder": "Strength",
        },
        "speed_stat": {"label": "SPS:", "placeholder": "Spell Speed"},
    },
    "Tank": {
        "main_stat": {"label": "STR:", "placeholder": "Strength"},
        "secondary_stat": {"label": "TEN:", "placeholder": "Tenacity"},
        "speed_stat": {"label": "SKS:", "placeholder": "Skill Speed"},
    },
    "Magical Ranged": {
        "main_stat": {"label": "INT:", "placeholder": "Intelligence"},
        "secondary_stat": {
            "label": [
                html.Span(
                    "STR:",
                    id="str-tooltip",
                    style={
                        "textDecoration": "underline",
                        "textDecorationStyle": "dotted",
                        "cursor": "pointer",
                    },
                ),
                dbc.Tooltip(
                    "Strength, used for auto-attacks",
                    target="str-tooltip",
                ),
            ],
            "placeholder": "Strength",
        },
        "speed_stat": {"label": "SPS:", "placeholder": "Spell Speed"},
    },
    "Melee": {
        "main_stat": {"label": "STR/DEX:", "placeholder": "Strength"},
        "secondary_stat": {"label": "N/A:", "placeholder": None},
        "speed_stat": {"label": "SKS:", "placeholder": "Skill Speed"},        
    },
    "Physical Ranged": {
        "main_stat": {"label": "DEX:", "placeholder": "Dexterity"},
        "secondary_stat": {"label": "N/A:", "placeholder": None},
        "speed_stat": {"label": "SKS:", "placeholder": "Skill Speed"},        
    }
}

# How jobs map to roles
role_mapping = {
    "WhiteMage": "Healer",
    "Scholar": "Healer",
    "Astrologian": "Healer",
    "Sage": "Healer",
    "Paladin": "Tank",
    "Warrior": "Tank",
    "DarkKnight": "Tank",
    "Gunbreaker": "Tank",
    "Bard": "Physical Ranged",
    "Dancer": "Physical Ranged",
    "Machinist": "Physical Ranged",
    "Dragoon": "Melee",
    "Monk": "Melee",
    "Ninja": "Melee",
    "Samurai": "Melee",
    "Reaper": "Melee",
    "BlackMage": "Magical Ranged",
    "Summoner": "Magical Ranged",
    "RedMage": "Magical Ranged"
}