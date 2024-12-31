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
    3009, # Byakko
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
    3009: 100, # Byakko
}

encounter_phases = {
    1079: {
        1: "P1: Fatebreaker",
        2: "P2: Usurper of Frost",
        3: "P3: Oracle of Darkness",
        4: "P4: Enter the Dragon",
        5: "P5: Pandora",
    }
    # 1077: {
    #     1: "P1: Omega",
    #     2: "P2: Omega-M/F",
    #     3: "P3: Omega Reconfigured",
    #     4: "P4: Blue Screen",
    #     5: "P5: Run: Dynamis",
    #     6: "P6: Alpha Omega",
    # }
}

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
