"""
Data pertaining to guaranteed critical/direct hits. Guaranteed hit types are granted either by:
(i) A buff acting upon a particular set of actions
(ii) An action inherently has a guaranteed hit type

Information is stored as a dictionary of dictionaries, where keys are the action name and the inner dictionary
is information pertaining to hit types (1 = auto crit, 2 = auto direct hit, 3 = auto cdh) and affected actions.
New keys might be added later to account for changes over time (e.g., Midare)
"""

guaranteed_hit_via_buff = {"Inner Release": {"affected_actions": [], "hit_type": 3}}

guaranteed_hit_via_action = {
    "Inner Chaos": {"hit_type": 3},
    "Primal Rend": {
        "hit_type": 3,
    },
    "Midare Setsugekka": {"hit_type": 1},
}
