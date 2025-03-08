from typing import Dict, Set

import numpy as np
import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction


class MachinistActions(BuffQuery):
    def __init__(
        self,
        headers: Dict[str, str],
        report_id: str,
        fight_id: int,
        player_id: int,
        weaponskill_ids: Set[int] = {
            7410,
            7411,
            7412,
            7413,
            16497,
            16498,
            16499,
            16500,
            25786,
            25788,
            36981,
            36982,
            36978,
        },
        battery_gauge_amount: Dict[int, int] = {
            7413: 10,
            16500: 20,
            25788: 20,
            36981: 20,
            16501: 0,
        },
        wildfire_id: int = 1001946,
        queen_automaton_id: int = 16501,
    ) -> None:
        """
        Initialize the MachinistActions class.

        Parameters:
        headers (Dict[str, str]): Headers for the GraphQL query.
        report_id (str): Report ID for the fight.
        fight_id (int): Fight ID.
        player_id (int): Player ID.
        weaponskill_ids (Set[int]): Set of weaponskill IDs.
        battery_gauge_amount (Dict[int, int]): Dictionary mapping ability IDs to battery gauge amounts.
        wildfire_id (int): Wildfire ability ID.
        queen_automaton_id (int): Queen Automaton ability ID.
        """
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.weaponskill_ids = weaponskill_ids
        self.battery_gauge_amount = battery_gauge_amount
        self.wildfire_id = wildfire_id
        self.queen_automaton_id = queen_automaton_id
        self.pet_ability_ids = {16503, 16504, 17206, 25787}

        self.battery_gauge_id_map = {
            7413: "Heated Clean Shot",
            16500: "Air Anchor",
            25788: "Chain Saw",
            36981: "Excavator",
            16501: "Automaton Queen",
        }

        self._set_wildfire_timings(headers)
        self.battery_gauge_actions = self._set_battery_gauge_actions(headers)

        self.queen_battery_levels = self._compute_battery_gauge_amounts(
            self.battery_gauge_actions
        )
        self.queen_battery_gauge_bands = self._get_battery_gauge_bands(
            self.queen_battery_levels
        )

    # Query wildfire and queen bands
    def _query_wildfire_bands(self, headers: Dict[str, str]):
        query = """
                query QueenWildfire(
                    $code: String!
                    $id: [Int]!
                    $playerID: Int!
                    $wildfireID: Float!
                    $queenAutomatonID: Float!
                ) {
                    reportData {
                        report(code: $code) {
                            startTime
                            wildfire: table(
                                fightIDs: $id
                                dataType: Buffs
                                sourceID: $playerID
                                abilityID: $wildfireID
                            )
                        }
                    }
                }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "wildfireID": self.wildfire_id,
            # "queenAutomatonID": self.queen_automaton_id,
        }

        return self.gql_query(headers, query, variables, "QueenWildfire")

    def _query_battery_actions(self, headers: Dict[str, str]):
        query = """
        query MachinistBatteryCasts(
            $code: String!
            $id: [Int]!
            $playerID: Int!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    HeatedCleanShot: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 7413
                    ) {
                        data
                    }
                    AirAnchor: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 16500
                    ) {
                        data
                    }
                    ChainSaw: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 25788
                    ) {
                        data
                    }
                    Excavator: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 36981
                    ) {
                        data
                    }
                    events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        abilityID: 16501
                    ) {
                        data
                        nextPageTimestamp
                    }
                }
            }
        }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
        }

        return self.gql_query(headers, query, variables, "MachinistBatteryCasts")

    # FIXME: can probably add to base.py
    def _casts_to_gauge_df(
        self, response_report_data, ability_name=None, start_time=0
    ) -> pd.DataFrame:
        """Extracts cast response for an action and makes a DataFrame.

        If the response is empty, an empty DataFrame with the correct columns is added.
        ""
        """
        df_cols = [
            "timestamp",
            "type",
            "sourceID",
            "targetID",
            "abilityGameID",
            "fight",
        ]

        df = pd.DataFrame(response_report_data, columns=df_cols)

        df = df[df["type"] == "cast"]
        df["ability_name"] = ability_name
        df["timestamp"] += start_time

        return df

    def _set_battery_gauge_actions(self, headers: Dict[str, str]) -> None:
        battery_actions = self._query_battery_actions(headers)
        start_time = battery_actions["data"]["reportData"]["report"].pop("startTime")
        self.start_time = start_time
        battery_dfs = [
            self._casts_to_gauge_df(
                v["data"],
                start_time=start_time,
            )
            for k, v in battery_actions["data"]["reportData"]["report"].items()
        ]
        battery_df = pd.concat(battery_dfs).sort_values("timestamp")
        battery_df["ability_name"] = battery_df["abilityGameID"].replace(
            self.battery_gauge_id_map
        )
        return battery_df

    def _set_wildfire_timings(self, headers: Dict[str, str]) -> None:
        """
        Set the timings for Wildfire and Queen Automaton based on the provided headers.

        Parameters:
            headers (Dict[str, str]): Headers for the GraphQL query.
        """
        query = """
                query machinistBuffs(
                    $code: String!
                    $id: [Int]!
                    $playerID: Int!
                    $wildfireID: Float!
                ) {
                    reportData {
                        report(code: $code) {
                            startTime
                            wildfire: table(
                                fightIDs: $id
                                dataType: Buffs
                                sourceID: $playerID
                                abilityID: $wildfireID
                            )
                        }
                    }
                }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "wildfireID": self.wildfire_id,
            # "queenAutomatonID": self.queen_automaton_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "machinistBuffs")
        self.wildfire_times = self._get_buff_times("wildfire")

    def _compute_battery_gauge_amounts(
        self, battery_gauge_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Create a DataFrame containing each Queen summon and how much battery gauge is present.

        Args:
            battery_gauge_df (pd.DataFrame): _description_

        Returns:
            pd.DataFrame: _description_
        """
        queen_battery_levels = battery_gauge_df.copy()
        queen_battery_levels["queen_group"] = 0
        queen_battery_levels.loc[
            queen_battery_levels["ability_name"] == "Automaton Queen", "queen_group"
        ] = 1

        # The weird indexing is doing a reverse cumsum to assign queen group
        queen_battery_levels["queen_group"] = queen_battery_levels.loc[
            ::-1, "queen_group"
        ].cumsum()[::-1]

        # Map and sum battery generation amounts to each action
        queen_battery_levels["battery_gauge"] = queen_battery_levels[
            "abilityGameID"
        ].replace(self.battery_gauge_amount)
        queen_battery_levels["battery_gauge"] = queen_battery_levels.groupby(
            "queen_group"
        )["battery_gauge"].transform("sum")

        queen_battery_levels = queen_battery_levels[
            queen_battery_levels["ability_name"] == "Automaton Queen"
        ][["timestamp", "queen_group", "battery_gauge"]]

        # Cap gauge to 100
        # Only first value could be under 50 if resource run.
        # Assume full gauge in that case.
        queen_battery_levels.loc[
            (queen_battery_levels["battery_gauge"] > 100)
            | (queen_battery_levels["battery_gauge"] < 50),
            "battery_gauge",
        ] = 100
        return queen_battery_levels

    def _get_battery_gauge_bands(self, queen_battery_levels: pd.DataFrame):
        """Converts the battery gauge DataFrame to a dictionary with:

        - Battery gauge level
        - Timestamp bands which Queen actions are affected by this.

        Args:
            queen_battery_levels (pd.DataFrame): _description_

        Returns:
            _type_: _description_
        """
        time_bands = np.zeros((len(queen_battery_levels), 2))
        time_bands[:, 0] = queen_battery_levels["timestamp"].to_numpy()
        time_bands[:-1, 1] = queen_battery_levels["timestamp"].to_numpy()[1:]
        time_bands[-1, 1] = time_bands[-1, 0] + 30 * 1000

        return {
            int(row["queen_group"]): {
                "gauge": int(row["battery_gauge"]),
                "bands": time_bands[idx],
            }
            for idx, row in queen_battery_levels.iterrows()
        }

    def _battery_gauge(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a buff indicating the battery gauge level for each Queen action.

        For each gauge band in `self.queen_battery_gauge_bands`, this method:
        1. Identifies the time range (bands) during which the Queen Automaton's
            actions are affected by a specific battery gauge value.
        2. Finds pet actions (via `self.pet_ability_ids`) occurring in that time range.
        3. Appends a buff (e.g., 'gauge_50', 'gauge_60', etc.) to those actions.

        The result is a DataFrame where each pet action has a buff representing
        the battery gauge at the time of execution, enabling accurate potency
        assignments in later calculations.

        Args:
            actions_df (pd.DataFrame): The action log DataFrame containing columns
                such as 'timestamp', 'abilityGameID', and 'buffs'.

        Returns:
            pd.DataFrame: A modified copy of 'actions_df' with updated buffs and
            action names indicating the Queen Automaton's battery gauge value.
        """
        for v in self.queen_battery_gauge_bands.values():
            active_queen_condition = actions_df["timestamp"].between(
                v["bands"][0], v["bands"][1], inclusive="left"
            )
            is_pet_id = actions_df["abilityGameID"].isin(self.pet_ability_ids)

            actions_df = self._apply_buffs(
                actions_df, (active_queen_condition & is_pet_id), f"gauge_{v['gauge']}"
            )
        return actions_df

    def _wildfire_gcds(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Find out how many GCDs occurred during Wildfire to compute potency.

        Parameters:
            actions_df (pd.DataFrame): DataFrame of actions.

        Returns:
            pd.DataFrame: DataFrame of actions, with a buff indicating the wildfire potency.
        """
        # Find weaponskills which occurred during wildfire
        wildfire_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="both")
            for b in self.wildfire_times
        )
        n_wildfire_gcds = actions_df[
            disjunction(*wildfire_betweens)
            & actions_df["abilityGameID"].isin(self.weaponskill_ids)
        ][["elapsed_time"]]

        # Find time between the next gcd to group wildfires
        n_wildfire_gcds["next_gcd_time"] = n_wildfire_gcds["elapsed_time"].shift(1)
        n_wildfire_gcds["timediff"] = (
            n_wildfire_gcds["elapsed_time"] - n_wildfire_gcds["next_gcd_time"]
        )

        # Group them with cumsum if they're null or > 10s apart
        n_wildfire_gcds["wildfire_group"] = 0
        n_wildfire_gcds.loc[
            (n_wildfire_gcds["timediff"] > 10) | (n_wildfire_gcds["timediff"].isna()),
            "wildfire_group",
        ] = 1
        # Group with cumsum
        n_wildfire_gcds["wildfire_group"] = n_wildfire_gcds["wildfire_group"].cumsum()

        n_wildfire_gcds = (
            n_wildfire_gcds.groupby(["wildfire_group"])
            .aggregate({"elapsed_time": ["count", "max"]})
            .rename(columns={"max": "elapsed_time"})
        )
        n_wildfire_gcds.columns = n_wildfire_gcds.columns.droplevel(0)
        n_wildfire_gcds = n_wildfire_gcds.reset_index()
        # Cap at 6 GCDs because that's the in-game potency cap
        n_wildfire_gcds.loc[n_wildfire_gcds["count"] > 6, "count"] = 6

        n_wildfire_gcds["wildfire_buff_name"] = "wildfire_" + n_wildfire_gcds[
            "count"
        ].astype(str)

        buff_matched = pd.merge_asof(
            actions_df[actions_df["ability_name"] == "Wildfire (tick)"],
            n_wildfire_gcds[["elapsed_time", "wildfire_buff_name"]],
            on="elapsed_time",
            direction="backward",
            tolerance=10,
        )[["elapsed_time", "wildfire_buff_name"]]

        actions_df = actions_df.merge(buff_matched, on="elapsed_time", how="left")

        # Update buffs and action name
        actions_df[~actions_df["wildfire_buff_name"].isna()].apply(
            lambda x: x["buffs"].append(x["wildfire_buff_name"]), axis=1
        )
        (
            actions_df[~actions_df["wildfire_buff_name"].isna()]["action_name"]
            + "_"
            + actions_df[~actions_df["wildfire_buff_name"].isna()]["wildfire_buff_name"]
        )
        actions_df.loc[~actions_df["wildfire_buff_name"].isna(), "action_name"] += (
            "_"
            + actions_df[~actions_df["wildfire_buff_name"].isna()]["wildfire_buff_name"]
        )
        return actions_df.drop(columns="wildfire_buff_name")

    def apply_mch_potencies(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply potency calculations for Machinist actions.

        Parameters:
            actions_df (pd.DataFrame): DataFrame of actions.

        Returns:
            pd.DataFrame: Updated DataFrame with applied potencies.
        """
        # Wildfire
        actions_df = self._wildfire_gcds(actions_df)

        # Pet actions via battery gauge:
        #   Arm Punch
        #   Roller Dash
        #   Pile Bunker
        #   Crowned Collider
        actions_df = self._battery_gauge(actions_df)
        return actions_df


if __name__ == "__main__":
    from crit_app.config import FFLOGS_TOKEN

    api_key = FFLOGS_TOKEN  # or copy/paste your key here
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    MachinistActions(headers, "ZfnF8AqRaBbzxW3w", 5, 20)
