valid_encounters = [
    88,
    89,
    90,
    91,
    92,
    93,
    94,
    95,
    96,  # Start cruiserweight
    97,
    98,
    99,
    100,  # Start Heavyweight
    101,
    102,
    103,
    104,
    105,  # Lindwurm II
    1069,
    1070,
    1072,
    # 1077,
    1078,
    1079,
    1080,
    1081,
    1082,
    1083,
    1084,
    1085,  # DMU
    3009,  # Byakko
    3010,
    3011,  # Seiryu
    3012,  # Tsukuyomi
    3013,  # Shinryu
]
valid_encounter_text = ""

encounter_level = {
    88: 90,
    89: 90,
    90: 90,
    91: 90,
    92: 90,
    93: 100,
    94: 100,
    95: 100,
    96: 100,
    97: 100,
    98: 100,
    99: 100,
    100: 100,
    101: 100,
    102: 100,
    103: 100,
    104: 100,
    105: 100,
    1069: 90,
    1070: 90,
    # 1077: 90,
    1071: 100,
    1072: 100,
    1078: 100,
    1079: 100,
    1080: 100,
    1081: 100,
    1082: 100,
    1083: 100,
    1084: 100,
    1085: 100,
    3009: 100,  # Byakko
    3010: 100,
    3011: 100,
    3012: 100,
    3013: 100,
}

encounter_phases = {
    1079: {
        1: "P1: Fatebreaker",
        2: "P2: Usurper of Frost",
        3: "P3: Oracle of Darkness",
        4: "P4: Enter the Dragon",
        5: "P5: Pandora",
    },
    98: {
        1: "Phase 1",
        2: "Phase 2",
        3: "Phase 3",
    },
    99: {
        1: "Phase 1",
        2: "Phase 2",
        3: "Phase 3",
    },
    100: {
        1: "Phase 1",
        2: "Phase 2",
    },
}

# These phases have downtime between them, so a new t_clip needs to be found
custom_t_clip_encounter_phases = {1079: [1, 2, 3, 4]}
custom_t_clip_encounter_phases = {100: [1]}
# Fixed length encounters
# TODO: Add 4?
skip_kill_time_analysis_phases = {1079: [2, 3]}

# Used for Party analysis
boss_hp = {
    88: 36660084,
    89: 43656896,
    90: 49884204,
    91: 32790420,
    92: 40192744,
    93: 75867953,
    94: 83966736,
    95: 96522580,
    96: 114525943,
    1069: 37255204,
    1070: 40478540,
    1072: 66146024,
}

# FFlogs periodically excludes damage to certain enemies
# Find them by their game ID
excluded_enemy_game_ids = {1079: [17828], 99: [18308], 1081: [18701]}

stat_ranges = {
    "main_stat": {"lower": 3200, "upper": 6700},
    "DET": {"lower": 380, "upper": 5000},
    "SPEED": {"lower": 380, "upper": 5000},
    "CRT": {"lower": 380, "upper": 5000},
    "DH": {"lower": 380, "upper": 5000},
    "WD": {"lower": 50, "upper": 250},
    "TEN": {"lower": 380, "upper": 5000},
}

encounter_information = [
    {
        "encounter_id": 88,
        "encounter_name": "Kokytos",
        "encounter_short_name": "p9s",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 89,
        "encounter_name": "Pandaemonium",
        "encounter_short_name": "p10s",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 90,
        "encounter_name": "Themis",
        "encounter_short_name": "p11s",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 91,
        "encounter_name": "Athena",
        "encounter_short_name": "p12sp1",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 92,
        "encounter_name": "Pallas Athena",
        "encounter_short_name": "p12sp2",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 93,
        "encounter_name": "Black Cat",
        "encounter_short_name": "m1s",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 94,
        "encounter_name": "Honey B. Lovely",
        "encounter_short_name": "m2s",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 95,
        "encounter_name": "Brute Bomber",
        "encounter_short_name": "m3s",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 96,
        "encounter_name": "Wicked Thunder",
        "encounter_short_name": "m4s",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 97,
        "encounter_name": "Dancing Green",
        "encounter_short_name": "m5s",
        "content_type": "Raid",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 98,
        "encounter_name": "Sugar Riot",
        "encounter_short_name": "m6s",
        "content_type": "Raid",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 99,
        "encounter_name": "Brute Abominator",
        "encounter_short_name": "m7s",
        "content_type": "Raid",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 100,
        "encounter_name": "Howling Blade",
        "encounter_short_name": "m8s",
        "content_type": "Raid",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 101,
        "encounter_name": "Vamp Fatale",
        "encounter_short_name": "m9s",
        "content_type": "Raid",
        "relevant_patch": "7.4 - 7.5",
    },
    {
        "encounter_id": 102,
        "encounter_name": "Red Hot + Deep Blue",
        "encounter_short_name": "m10s",
        "content_type": "Raid",
        "relevant_patch": "7.4 - 7.5",
    },
    {
        "encounter_id": 103,
        "encounter_name": "The Tyrant",
        "encounter_short_name": "m11s",
        "content_type": "Raid",
        "relevant_patch": "7.4 - 7.5",
    },
    {
        "encounter_id": 104,
        "encounter_name": "Lindwurm",
        "encounter_short_name": "m12s",
        "content_type": "Raid",
        "relevant_patch": "7.4 - 7.5",
    },
    {
        "encounter_id": 105,
        "encounter_name": "Lindwurm II",
        "encounter_short_name": "m12sp2",
        "content_type": "Raid",
        "relevant_patch": "7.4 - 7.5",
    },
    {
        "encounter_id": 1069,
        "encounter_name": "Golbez",
        "encounter_short_name": "DT EX6",
        "content_type": "Extreme",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 1070,
        "encounter_name": "Zeromus",
        "encounter_short_name": "EW EX7",
        "content_type": "Extreme",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 1072,
        "encounter_name": "Zoraal Ja",
        "encounter_short_name": "DT EX2",
        "content_type": "Extreme",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 1078,
        "encounter_name": "Queen Eternal",
        "encounter_short_name": "DT EX3",
        "content_type": "Extreme",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 1079,
        "encounter_name": "Futures Rewritten",
        "encounter_short_name": "FRU",
        "content_type": "Ultimate",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 1080,
        "encounter_name": "Zelenia",
        "encounter_short_name": "DT EX4",
        "content_type": "Extreme",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 1081,
        "encounter_name": "????",
        "encounter_short_name": "DT EX5",
        "content_type": "Extreme",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 1083,
        "encounter_name": "The Doomtrain",
        "encounter_short_name": "DT EX6",
        "content_type": "Extreme",
        "relevant_patch": "7.4 - 7.5",
    },
    {
        "encounter_id": 1085,
        "encounter_name": "Dancing Mad",
        "encounter_short_name": "DMU",
        "content_type": "Ultimate",
        "relevant_patch": "7.4 - 7.5",
    },
    {
        "encounter_id": 3009,
        "encounter_name": "Byakko",
        "encounter_short_name": "Byakko",
        "content_type": "Unreal",
        "relevant_patch": "7.0 - 7.1",
    },
    {
        "encounter_id": 3010,
        "encounter_name": "Suzaku",
        "encounter_short_name": "Suzaku",
        "content_type": "Unreal",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 3011,
        "encounter_name": "Seiryu",
        "encounter_short_name": "Seiryu",
        "content_type": "Unreal",
        "relevant_patch": "7.2 - 7.3",
    },
    {
        "encounter_id": 3012,
        "encounter_name": "Tsukuyomi",
        "encounter_short_name": "Tsukuyomi",
        "content_type": "Unreal",
        "relevant_patch": "7.4 - 7.5",
    },
]

# Create a dictionary for quickly mapping encounter IDs to their short names
encounter_id_to_short_name = {
    encounter["encounter_id"]: encounter["encounter_short_name"]
    for encounter in encounter_information
}
