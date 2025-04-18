"""Constants and mappings for tincture (potion) related calculations."""

role_tincture_map = {
    "Tank": "Strength",
    "Healer": "Mind",
    "Melee": "Strength",
    "Physical Ranged": "Dexterity",
    "Magical Ranged": "Intelligence",
}

# Jobs that use a different tincture than their role would suggest
ad_hoc_job_tincture_map = {
    "Ninja": "Dexterity",
    "Viper": "Dexterity",
}

tincture_strengths = {
    "Grade 3 Tincture": 106,
    "Grade 3 Tincture [HQ]": 133,
    "Grade 4 Tincture": 115,
    "Grade 4 Tincture [HQ]": 144,
    "Grade 5 Tincture": 137,
    "Grade 5 Tincture [HQ]": 172,
    "Grade 6 Tincture": 151,
    "Grade 6 Tincture [HQ]": 189,
    "Grade 7 Tincture": 178,
    "Grade 7 Tincture [HQ]": 223,
    "Grade 8 Tincture": 209,
    "Grade 8 Tincture [HQ]": 262,
    "Grade 1 Gemdraught": 280,
    "Grade 1 Gemdraught [HQ]": 351,
    "Grade 2 Gemdraught": 313,
    "Grade 2 Gemdraught [HQ]": 392,
    "Grade 3 Gemdraught": 368,
    "Grade 3 Gemdraught [HQ]": 461,
}
