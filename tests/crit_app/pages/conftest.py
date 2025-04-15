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
