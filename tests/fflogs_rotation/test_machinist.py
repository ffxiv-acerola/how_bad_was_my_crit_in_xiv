import pandas as pd

from fflogs_rotation.machinist import MachinistActions


class DummyMachinistActions(MachinistActions):
    """
    A dummy subclass of MachinistActions that overrides the remote API calls.

    This allows testing _compute_battery_gauge_amounts without fetching live data.
    """

    def __init__(self, *args, **kwargs):
        self.battery_gauge_amount = {
            7413: 10,  # Heated Clean Shot
            16500: 20,  # Air Anchor
            25788: 20,  # Chain Saw
            36981: 20,  # Excavator
            16501: 0,  # Automaton Queen
        }
        self.battery_gauge_id_map = {
            7413: "Heated Clean Shot",
            16500: "Air Anchor",
            25788: "Chain Saw",
            36981: "Excavator",
            16501: "Automaton Queen",
        }
        # We don't need to query remote data so we simply set dummy DataFrames.
        # For the purpose of testing _compute_battery_gauge_amounts, we only need battery_gauge_df.

    # Override remote methods if needed.
    def get_wildfire_timings(self, headers):
        pass

    def _set_battery_gauge_actions(self, headers):
        # For testing, we will inject our own battery gauge DataFrame.
        pass


def test_compute_battery_gauge_amounts():
    """
    Test that _compute_battery_gauge_amounts returns the proper battery gauge value.

    The method should correctly:
      - Sum battery gauge contributions from events leading up to an "Automaton Queen" cast.
      - Cap the summed gauge to 100 if it exceeds 100.
      - Force gauge to 100 if the summed gauge is below 50 (representing a full gauge for a resource run).
    """
    expected_gauge = [80, 100, 100]
    dummy_mch = DummyMachinistActions(headers={}, report_id="dummy", fight_id=1, player_id=1)
    # Create a DataFrame from the battery_data list.
    # fmt: off
    battery_data = [
        # To get a group sum of 80, we use 4 events of 20 each, then the Automaton Queen row.
        {"timestamp": 1000, "ability_name": "Air Anchor", "abilityGameID": 16500},
        {"timestamp": 1500, "ability_name": "Air Anchor", "abilityGameID": 16500},
        {"timestamp": 2000, "ability_name": "Chain Saw", "abilityGameID": 25788},
        {"timestamp": 2500, "ability_name": "Air Anchor", "abilityGameID": 16500},
        {"timestamp": 3000, "ability_name": "Automaton Queen", "abilityGameID": 16501}, # 80
        {"timestamp": 4000, "ability_name": "Air Anchor", "abilityGameID": 16500},
        {"timestamp": 4500, "ability_name": "Chain Saw", "abilityGameID": 25788},
        {"timestamp": 5000, "ability_name": "Air Anchor", "abilityGameID": 16500},
        {"timestamp": 5500, "ability_name": "Chain Saw", "abilityGameID": 25788},
        {"timestamp": 6000, "ability_name": "Air Anchor", "abilityGameID": 16500},
        {"timestamp": 6500, "ability_name": "Chain Saw", "abilityGameID": 25788},
        {"timestamp": 7000, "ability_name": "Automaton Queen", "abilityGameID": 16501}, # 100 round down
        {"timestamp": 7500, "ability_name": "Heated Clean Shot", "abilityGameID": 7413},
        {"timestamp": 8000, "ability_name": "Air Anchor", "abilityGameID": 16500},
        {"timestamp": 8500, "ability_name": "Automaton Queen", "abilityGameID": 16501}, # 100, assume resource run
        ]
    # fmt: on

    battery_df = pd.DataFrame(battery_data)

    result_df = dummy_mch._compute_battery_gauge_amounts(battery_df)

    final_gauge = result_df["battery_gauge"].to_list()
    assert final_gauge == expected_gauge
