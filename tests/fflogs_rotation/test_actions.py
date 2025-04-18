import pytest

from fflogs_rotation.actions import ActionTable


@pytest.fixture
def mock_potion_response(request):
    response_template = {
        "potionType": {
            "data": {"auras": []},
        },
    }

    aura_append = {
        "appliedByAbilities": request.param["appliedByAbilities"],
    }
    response_template["potionType"]["data"]["auras"].append(aura_append)
    response_template["potionType"]["data"]["auras"][0]["icon"] = request.param["icon"]
    return response_template


@pytest.mark.parametrize(
    "mock_potion_response,job,expected_strength",
    [
        # Empty potions - should return 0
        ({"appliedByAbilities": [], "icon": "Sage"}, "Sage", 0),
        # Grade 3 Gemdraught tests - standard HQ for Sage (healer)
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 3 Gemdraught of Mind [HQ]",
                    }
                ],
                "icon": "Sage",
            },
            "Sage",
            461,
        ),
        # Grade 2 Gemdraught tests - standard HQ for tank
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 2 Gemdraught of Strength [HQ]",
                    }
                ],
                "icon": "Warrior",
            },
            "Warrior",
            392,
        ),
        # Grade 6 Tincture tests - standard HQ for Ninja (special dex case)
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 6 Tincture of Dexterity [HQ]",
                    }
                ],
                "icon": "Ninja",
            },
            "Ninja",
            189,
        ),
        # Non-HQ tincture test
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 3 Gemdraught of Mind",
                    }
                ],
                "icon": "Scholar",
            },
            "Scholar",
            368,
        ),
        # Multiple potions - should pick strongest valid one
        (
            {
                "appliedByAbilities": [
                    {"name": "Grade 3 Gemdraught of Mind [HQ]"},
                    {"name": "Grade 2 Gemdraught of Mind [HQ]"},
                    {"name": "Grade 3 Gemdraught of Mind"},
                    {"name": "Grade 6 Tincture of Dexterity [HQ]"},
                ],
                "icon": "Sage",
            },
            "Sage",
            461,
        ),
        # Wrong potion type for job - should return 0
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 3 Gemdraught of Strength [HQ]",
                    }
                ],
                "icon": "WhiteMage",
            },
            "WhiteMage",
            0,
        ),
        # Viper with Dexterity - special case that should work
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 3 Gemdraught of Dexterity [HQ]",
                    }
                ],
                "icon": "Viper",
            },
            "Viper",
            461,
        ),
        # Physical ranged with Dexterity - should work
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 3 Gemdraught of Dexterity [HQ]",
                    }
                ],
                "icon": "Dancer",
            },
            "Dancer",
            461,
        ),
        # Magical ranged with Intelligence - should work
        (
            {
                "appliedByAbilities": [
                    {
                        "name": "Grade 3 Gemdraught of Intelligence [HQ]",
                    }
                ],
                "icon": "BlackMage",
            },
            "BlackMage",
            461,
        ),
    ],
    indirect=["mock_potion_response"],
)
def test_get_medication_amount(mock_potion_response, job, expected_strength):
    """Test that potion strengths are correctly calculated based on job and potion type."""

    # Call the method and assert expected results
    result = ActionTable._get_medication_amount(mock_potion_response)
    assert (
        result == expected_strength
    ), f"Expected {expected_strength} for {job} with potion {mock_potion_response['potionType']['data']['auras'][0]['appliedByAbilities']}"
