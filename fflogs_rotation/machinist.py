import numpy as np
import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction


class MachinistActions(BuffQuery):
    def __init__(
        self,
        headers: dict,
        report_id: int,
        fight_id: int,
        player_id: int,
        weaponskill_ids: set = {
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
        battery_gauge_amount: dict = {
            7413: 10,
            16500: 20,
            25788: 20,
            36981: 20,
        },
        wildfire_id: int = 1001946,
        queen_automaton_id: int = 16501,
    ) -> None:
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.weaponskill_ids = weaponskill_ids
        self.battery_gauge_amount = battery_gauge_amount
        self.wildfire_id = wildfire_id
        self.queen_automaton_id = queen_automaton_id
        self.pet_ability_ids = {16503, 16504, 17206, 25787}

        self.gauge_potency_map = {
            "Arm Punch (Pet)": {
                x: 120 + idx * 24 for idx, x in enumerate(range(50, 110, 10))
            },
            "Roller Dash (Pet)": {
                x: 240 + idx * 48 for idx, x in enumerate(range(50, 110, 10))
            },
            "Pile Bunker (Pet)": {
                x: 340 + idx * 68 for idx, x in enumerate(range(50, 110, 10))
            },
            "Crowned Collider (Pet)": {
                x: 390 + idx * 78 for idx, x in enumerate(range(50, 110, 10))
            },
        }

        self._set_wildfire_timings(headers)

        pass

    def _set_wildfire_timings(self, headers):
        query = """
                query machinistBuffs(
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
                            events(
                                fightIDs: $id
                                dataType: Casts
                                sourceID: $playerID
                                abilityID: $queenAutomatonID
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
            "wildfireID": self.wildfire_id,
            "queenAutomatonID": self.queen_automaton_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "machinistBuffs")
        self.wildfire_times = self._get_buff_times("wildfire")
        self.queen_summons = pd.DataFrame(
            self.request_response["data"]["reportData"]["report"]["events"]["data"]
        )[["timestamp", "abilityGameID"]]
        self.queen_summons["timestamp"] += self.report_start
        self.queen_summons["ability_name"] = "Queen Automaton"
        self.queen_summons["queen_group"] = np.arange(self.queen_summons.shape[0])
        pass

    def _wildfire_gcds(self, actions_df):
        """Find out how many GCDs occured during Wildfire to compute potency.

        Args:
            actions_df (DataFrame): Pandas DataFrame of actions

        Returns:
            DataFrame: Pandas DataFrame of actions, with a buff indicating the wildfire potency.
        """
        # Find weaponskills which occured during wildfire
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

        # Group them with cumsum if theyre null or > 10s apart
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

    def _battery_gauge(self, actions_df):
        """Figure out the battery gague level when Automaton Queen is summoned,
        which affects the potency of her actions

        Args:
            actions_df (DataFrame): pandas DataFrame of actions
        """

        # Figure out how much battery gauge was present when queen is summoned
        # Filter to battery gauage granting actiosn and queen summons
        battery_gauge = actions_df[
            actions_df["abilityGameID"].isin(self.battery_gauge_amount.keys())
            # | actions_df["abilityGameID"].isin(self.pet_ability_ids)
        ][["timestamp", "ability_name", "abilityGameID"]]
        battery_gauge = (
            pd.concat([battery_gauge, self.queen_summons])
            .sort_values("timestamp")
            .reset_index(drop=True)
        )
        # Assign battery generating actions to a queen group
        battery_gauge["queen_group"] = battery_gauge["queen_group"].bfill()

        # Filter out queen summon
        battery_gauge = battery_gauge[
            battery_gauge["abilityGameID"] != self.queen_automaton_id
        ]

        # Sum the amount of gauge filled, cap at 100
        battery_gauge["battery_amount"] = battery_gauge["abilityGameID"].replace(
            self.battery_gauge_amount
        )
        battery_gauge = (
            battery_gauge[["queen_group", "battery_amount"]]
            .groupby("queen_group")
            .sum()
            .reset_index()
        )

        # If queen group 0 not present, assume resource run and assign 100 guage.
        if battery_gauge["queen_group"].min() == 1:
            battery_gauge = pd.concat(
                [
                    battery_gauge,
                    pd.DataFrame({"queen_group": [0], "battery_amount": [100]}),
                ]
            )

        # Gauge is capped at 100
        # Also if queen is summoned with < 50 gauge, assume resource run starting with 100 gauge from last phase
        battery_gauge.loc[
            (battery_gauge["battery_amount"] > 100)
            | (battery_gauge["battery_amount"] < 50),
            "battery_amount",
        ] = 100

        # Now assign queen actions to a queen group
        self.queen_summons["next_summon"] = (
            self.queen_summons["timestamp"]
            .shift(-1)
            .fillna(actions_df["timestamp"].iloc[-1] + 5000)
        )
        pet_actions = actions_df[
            actions_df["abilityGameID"].isin(self.pet_ability_ids)
        ][["timestamp", "ability_name", "abilityGameID"]]

        # Bunch of loc conditions
        for x in self.queen_summons[
            ["timestamp", "next_summon", "queen_group"]
        ].to_numpy():
            pet_actions.loc[
                pet_actions["timestamp"].between(x[0], x[1]), "queen_group"
            ] = x[2]

        pet_actions = pet_actions.merge(battery_gauge, on="queen_group")
        pet_actions["buff_name"] = "gauge_" + pet_actions["battery_amount"].astype(str)

        actions_df = actions_df.merge(
            pet_actions[["timestamp", "abilityGameID", "buff_name"]],
            on=["timestamp", "abilityGameID"],
            how="left",
        )
        actions_df.loc[~actions_df["buff_name"].isna(), "action_name"] += (
            "_" + actions_df["buff_name"]
        )
        actions_df.loc[~actions_df["buff_name"].isna()].apply(
            lambda x: x["buffs"].append(x["buff_name"]), axis=1
        )
        return actions_df.drop(columns=["buff_name"])

    def apply_mch_potencies(self, actions_df):
        # Wildfire
        actions_df = self._wildfire_gcds(actions_df)

        # Pet actions via battery gauge:
        #   Arm Punch
        #   Roller Dash
        #   Pile Bunker
        #   Crowned Collider
        actions_df = self._battery_gauge(actions_df)
        return actions_df
