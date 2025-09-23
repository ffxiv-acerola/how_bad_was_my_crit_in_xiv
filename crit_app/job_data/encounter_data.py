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
    100,
    1069,
    1070,
    1072,
    # 1077,
    1078,
    1079,
    1080,
    3009,  # Byakko
    3010,
    3011,
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
    1069: 90,
    1070: 90,
    # 1077: 90,
    1071: 100,
    1072: 100,
    1078: 100,
    1079: 100,
    1080: 100,
    3009: 100,  # Byakko
    3010: 100,
    3011: 100,
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
excluded_enemy_game_ids = {1079: [17828], 99: [18308]}

patch_times = {
    6.4: {"start": 1684836000000, "end": 1696327199999},
    6.5: {"start": 1696327200000, "end": 1719565299999},
    7.0: {"start": 1719565200000, "end": 1721109699999},
    7.01: {"start": 1721109600000, "end": 1722322899999},
    7.05: {"start": 1722322800000, "end": 1731427199999},
    7.1: {"start": 1731427200000, "end": 1742882399999},
    7.2: {"start": 1742882400000, "end": 1748321999999},
    7.25: {"start": 1748322000000, "end": 1754348399999},
    7.3: {"start": 1754348400000, "end": 1848322000000},
}

# IMPORTANT: Korean and Chinese servers roll all global minor patch potency changes with the main patch
# Example: 7.2 (KO / CN) = 7.2 + 7.25 for global
# In practice, this will just mean there's no X.Y patch and to have a X.Y5 patch start in its place
# https://ff14.huijiwiki.com/wiki/%E7%89%88%E6%9C%AC%E6%97%B6%E9%97%B4%E8%A1%A8
patch_times_cn = {
    6.4: {"start": 1695081600000, "end": 1709596799999},
    6.5: {"start": 1709596800000, "end": 1727395199999},
    7.0: {"start": 1727395200000, "end": 1729555199999},
    7.01: {"start": 1729555200000, "end": 1731369599999},
    7.05: {"start": 1731369600000, "end": 1731369599999},
    7.1: {"start": 1739836800000, "end": 1750748399999},
    7.25: {"start": 1750748400000, "end": 2754981999999},
}

# https://namu.wiki/w/%ED%8C%8C%EC%9D%B4%EB%84%90%20%ED%8C%90%ED%83%80%EC%A7%80%20XIV:%20%ED%9A%A8%EC%9B%94%EC%9D%98%20%EC%A2%85%EC%96%B8
# https://namu.wiki/w/%ED%8C%8C%EC%9D%B4%EB%84%90%20%ED%8C%90%ED%83%80%EC%A7%80%20XIV:%20%ED%99%A9%EA%B8%88%EC%9D%98%20%EC%9C%A0%EC%82%B0#s-5
# Important: see above note about rolled up patch potencies
patch_times_ko = {
    6.4: {"start": 1698728400000, "end": 1712033999999},
    6.5: {"start": 1712034000000, "end": 1733205599999},
    7.0: {"start": 1733205600000, "end": 1735019999999},
    7.01: {"start": 1735020000000, "end": 1736834399999},
    7.05: {"start": 1736834400000, "end": 1742273999999},
    7.1: {"start": 1742274000000, "end": 1752566399999},  # No 7.15 changes
    7.25: {"start": 1752566400000, "end": 1761638399999},
    7.3: {"start": 1761638400000, "end": 2742274000000},
}

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
]

world_to_region = {
    # North America
    "Adamantoise": "NA",
    "Cactuar": "NA",
    "Faerie": "NA",
    "Gilgamesh": "NA",
    "Jenova": "NA",
    "Midgardsormr": "NA",
    "Sargatanas": "NA",
    "Siren": "NA",
    "Balmung": "NA",
    "Brynhildr": "NA",
    "Coeurl": "NA",
    "Diabolos": "NA",
    "Goblin": "NA",
    "Malboro": "NA",
    "Mateus": "NA",
    "Zalera": "NA",
    "Cuchulainn": "NA",
    "Golem": "NA",
    "Halicarnassus": "NA",
    "Kraken": "NA",
    "Maduin": "NA",
    "Marilith": "NA",
    "Rafflesia": "NA",
    "Seraph": "NA",
    "Behemoth": "NA",
    "Excalibur": "NA",
    "Exodus": "NA",
    "Famfrit": "NA",
    "Hyperion": "NA",
    "Lamia": "NA",
    "Leviathan": "NA",
    "Ultros": "NA",
    # Europe
    "Cerberus": "EU",
    "Louisoix": "EU",
    "Moogle": "EU",
    "Omega": "EU",
    "Phantom": "EU",
    "Ragnarok": "EU",
    "Sagittarius": "EU",
    "Spriggan": "EU",
    "Alpha": "EU",
    "Lich": "EU",
    "Odin": "EU",
    "Phoenix": "EU",
    "Raiden": "EU",
    "Shiva": "EU",
    "Twintania": "EU",
    "Zodiark": "EU",
    # Oceania
    "Bismarck": "OC",
    "Ravana": "OC",
    "Sephirot": "OC",
    "Sophia": "OC",
    "Zurvan": "OC",
    # Japan
    "Aegis": "JP",
    "Atomos": "JP",
    "Carbuncle": "JP",
    "Garuda": "JP",
    "Gungnir": "JP",
    "Kujata": "JP",
    "Ramuh": "JP",
    "Tonberry": "JP",
    "Typhon": "JP",
    "Unicorn": "JP",
    "Alexander": "JP",
    "Bahamut": "JP",
    "Durandal": "JP",
    "Fenrir": "JP",
    "Ifrit": "JP",
    "Ridill": "JP",
    "Tiamat": "JP",
    "Ultima": "JP",
    "Valefor": "JP",
    "Yojimbo": "JP",
    "Zeromus": "JP",
    "Anima": "JP",
    "Asura": "JP",
    "Chocobo": "JP",
    "Hades": "JP",
    "Ixion": "JP",
    "Masamune": "JP",
    "Pandaemonium": "JP",
    "Shinryu": "JP",
    "Titan": "JP",
    "Belias": "JP",
    "Kaguya": "JP",
}

# Create a dictionary for quickly mapping encounter IDs to their short names
encounter_id_to_short_name = {
    encounter["encounter_id"]: encounter["encounter_short_name"]
    for encounter in encounter_information
}
