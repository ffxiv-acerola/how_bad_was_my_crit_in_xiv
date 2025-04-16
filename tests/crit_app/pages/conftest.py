import pytest
from dash import html


# Define a fixture for parameterization that allows getting different build responses
@pytest.fixture
def build_response(request):
    """Fixture that returns the specified build response based on the parameter."""
    build_type = request.param
    if build_type == "etro.gg":
        return (
            True,  # job_build_call_successful
            [],  # feedback
            True,  # hide_xiv_gear_set_selector
            True,  # job_build_valid
            False,  # job_build_invalid
            [html.H4("Build name: 2.50")],  # build_name_html
            "Melee",  # selected_role
            3379,  # main_stat
            1870,  # determination
            400,  # speed
            2567,  # crit
            1396,  # dh
            132,  # wd
            "None",  # tenacity
            {"gear_index": -1, "data": []},  # gear_set_store
        )
    elif build_type == "xivgear.app":
        return (
            True,  # job_build_call_successful
            [],  # feedback
            False,  # hide_xiv_gear_set_selector
            True,  # job_build_valid
            False,  # job_build_invalid
            [html.H4("dsr nin tentative bis")],  # build_name_html
            "Melee",  # selected_role
            2588,  # main_stat
            1829,  # determination
            514,  # speed
            2208,  # crit
            1353,  # dh
            120,  # wd
            "None",  # tenacity
            {
                "gear_index": 0,
                "data": [
                    (
                        "NIN",
                        "dsr nin tentative bis",
                        "Melee",
                        2588,
                        1829,
                        514,
                        2208,
                        1353,
                        120,
                        "None",
                    )
                ],
            },  # gear_set_store
        )


@pytest.fixture
def mock_encounter_information(request):
    """Fixture that returns different encounter information based on the parameter."""
    encounter_type = request.param.get("type", "single_phase")
    fight_id = request.param.get("fight_id", 18)
    encounter_name = request.param.get("encounter_name", "Sugar Riot")
    encounter_id = request.param.get("encounter_id", 98)  # Default to valid encounter
    error_message = request.param.get("error_message", "")

    # Return error message if specified
    if error_message:
        return (error_message, None, None, None, None, None, None, None, None, None, None)

    if encounter_type == "single_phase":
        return (
            "",
            fight_id,
            encounter_id,
            1744157984802,
            [
                {
                    "job": "RedMage",
                    "player_name": "Lisa Manoban",
                    "player_server": "Excalibur",
                    "player_id": 91,
                    "pet_ids": None,
                    "role": "Magical Ranged",
                },
                {
                    "job": "Sage",
                    "player_name": "Zazla Hrezlovas",
                    "player_server": "Hyperion",
                    "player_id": 182,
                    "pet_ids": None,
                    "role": "Healer",
                },
                {
                    "job": "Astrologian",
                    "player_name": "Isixa Voskera",
                    "player_server": "Adamantoise",
                    "player_id": 156,
                    "pet_ids": "[184]",
                    "role": "Healer",
                },
                {
                    "job": "Gunbreaker",
                    "player_name": "Akina Miyumi",
                    "player_server": "Adamantoise",
                    "player_id": 3,
                    "pet_ids": None,
                    "role": "Tank",
                },
                {
                    "job": "Paladin",
                    "player_name": "Zargabaath Galleon",
                    "player_server": "Behemoth",
                    "player_id": 180,
                    "pet_ids": None,
                    "role": "Tank",
                },
                {
                    "job": "Dancer",
                    "player_name": "Wexx Leekrusher",
                    "player_server": "Faerie",
                    "player_id": 181,
                    "pet_ids": None,
                    "role": "Physical Ranged",
                },
                {
                    "job": "Samurai",
                    "player_name": "Future Witness",
                    "player_server": "Zalera",
                    "player_id": 93,
                    "pet_ids": None,
                    "role": "Melee",
                },
                {
                    "job": "Monk",
                    "player_name": "Sang Sang",
                    "player_server": "Faerie",
                    "player_id": 94,
                    "pet_ids": None,
                    "role": "Melee",
                },
            ],
            [],
            628.239,
            encounter_name,
            1744157984802,
            0,
            None,
        )
    elif encounter_type == "multi_phase":
        return (
            "",
            fight_id,
            encounter_id,
            1744409223666,
            [
                {
                    "job": "Scholar",
                    "player_name": "Jacklyn Griffin",
                    "player_server": "Zalera",
                    "player_id": 204,
                    "pet_ids": None,
                    "role": "Healer",
                },
                {
                    "job": "Warrior",
                    "player_name": "Mercedene Oda",
                    "player_server": "Gilgamesh",
                    "player_id": 252,
                    "pet_ids": None,
                    "role": "Tank",
                },
                {
                    "job": "Dancer",
                    "player_name": "Chocolate Tea",
                    "player_server": "Jenova",
                    "player_id": 298,
                    "pet_ids": None,
                    "role": "Physical Ranged",
                },
                {
                    "job": "DarkKnight",
                    "player_name": "Mazz Murasame",
                    "player_server": "Goblin",
                    "player_id": 253,
                    "pet_ids": "[262]",
                    "role": "Tank",
                },
                {
                    "job": "Pictomancer",
                    "player_name": "Acedia Filianore",
                    "player_server": "Malboro",
                    "player_id": 258,
                    "pet_ids": None,
                    "role": "Magical Ranged",
                },
                {
                    "job": "Dragoon",
                    "player_name": "Nitian Erxing",
                    "player_server": "Adamantoise",
                    "player_id": 256,
                    "pet_ids": None,
                    "role": "Melee",
                },
                {
                    "job": "Astrologian",
                    "player_name": "Althea Winter",
                    "player_server": "Coeurl",
                    "player_id": 254,
                    "pet_ids": "[261]",
                    "role": "Healer",
                },
                {
                    "job": "Reaper",
                    "player_name": "Delmi Brunnera",
                    "player_server": "Halicarnassus",
                    "player_id": 255,
                    "pet_ids": None,
                    "role": "Melee",
                },
            ],
            [
                {
                    "job": "LimitBreak",
                    "player_name": "Limit Break",
                    "player_server": None,
                    "player_id": 281,
                    "pet_ids": None,
                    "role": "Limit Break",
                }
            ],
            825.996,
            encounter_name,
            1744409223666,
            2,
            None,
        )
