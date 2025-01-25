valid_encounters = [
    88,
    89,
    90,
    91,
    92,
    93,
    94,
    95,
    96,
    1069,
    1070,
    1072,
    # 1077,
    1078,
    1079,
    3009,  # Byakko
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
    1069: 90,
    1070: 90,
    # 1077: 90,
    1071: 100,
    1072: 100,
    1078: 100,
    1079: 100,
    3009: 100,  # Byakko
}

encounter_phases = {
    1079: {
        1: "P1: Fatebreaker",
        2: "P2: Usurper of Frost",
        3: "P3: Oracle of Darkness",
        4: "P4: Enter the Dragon",
        5: "P5: Pandora",
    }
}

# These phases have downtime between them, so a new t_clip needs to be found
custom_t_clip_encounter_phases = {1079: [1, 2, 3, 4]}
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

# FFlogs periodically excludes damage to certain
excluded_enemy_game_ids = {1079: [17828]}

patch_times = {
    6.4: {"start": 1684836000000, "end": 1696327199999},
    6.5: {"start": 1696327200000, "end": 1719565299999},
    7.0: {"start": 1719565200000, "end": 1721109699999},
    7.01: {"start": 1721109600000, "end": 1722322899999},
    7.05: {"start": 1722322800000, "end": 1731427199999},
    7.1: {"start": 1731427200000, "end": 1741791600000},
}

stat_ranges = {
    "main_stat": {"lower": 3400, "upper": 6000},
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
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 89,
        "encounter_name": "Pandaemonium",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 90,
        "encounter_name": "Themis",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 91,
        "encounter_name": "Athena",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 92,
        "encounter_name": "Pallas Athena",
        "content_type": "Raid",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 93,
        "encounter_name": "Black Cat",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 94,
        "encounter_name": "Honey B. Lovely",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 95,
        "encounter_name": "Brute Bomber",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 96,
        "encounter_name": "Wicked Thunder",
        "content_type": "Raid",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 1069,
        "encounter_name": "Golbez",
        "content_type": "Extreme",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 1070,
        "encounter_name": "Zeromus",
        "content_type": "Extreme",
        "relevant_patch": "6.4 - 6.5",
    },
    {
        "encounter_id": 1072,
        "encounter_name": "Zoraal Ja",
        "content_type": "Extreme",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 1078,
        "encounter_name": "Queen Eternal",
        "content_type": "Extreme",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 1079,
        "encounter_name": "Futures Rewritten",
        "content_type": "Ultimate",
        "relevant_patch": "7.0 - 7.2",
    },
    {
        "encounter_id": 3009,
        "encounter_name": "Byakko",
        "content_type": "Unreal",
        "relevant_patch": "7.0 - 7.2",
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
