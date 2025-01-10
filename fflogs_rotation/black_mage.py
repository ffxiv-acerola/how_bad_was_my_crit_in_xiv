import warnings
from typing import Dict

import numpy as np
import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction

# Suppress the specific FutureWarning from pandas
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    message="The behavior of DataFrame concatenation with empty or all-NA entries is deprecated.",
)


class BlackMageActions(BuffQuery):
    def __init__(
        self,
        headers: Dict[str, str],
        report_id: str,
        fight_id: int,
        player_id: int,
        level: int,
        patch_number: float,
        thundercloud_id: int = 1000164,
    ) -> None:
        self.report_id = report_id
        self.player_id = player_id
        self.fight_id = fight_id

        self.level = level
        self.patch_number = patch_number

        self.thundercloud_id = thundercloud_id

        self.get_transpose_umbral_soul_casts(headers)

        if self.level < 96:
            self.enochian_buff = 1.23
        elif (self.level >= 96) & (self.patch_number < 7.05):
            self.enochian_buff = 1.3
        elif (self.level >= 96) & (self.patch_number == 7.05):
            self.enochian_buff = 1.33
        else:
            self.enochian_buff = 1.32

        # Paradox and transpose are excluded because they affect both fire and ice
        # Checks are explicitly applied for these actions
        self.fire_granting_actions = {
            "Despair": {"time": 15, "stacks": 3},
            "Flare": {"time": 15, "stacks": 3},
            "Fire": {"time": 15, "stacks": 1},
            "Fire III": {"time": 15, "stacks": 3},
            "High Fire II": {"time": 15, "stacks": 3},
        }

        self.ice_granting_actions = {
            "Blizzard III": {"time": 15, "stacks": 3},
            "Umbral Soul": {"time": 15, "stacks": 1},
            "Blizzard": {"time": 15, "stacks": 1},
            "High Blizzard II": {"time": 15, "stacks": 3},
        }

        self.fire_actions = (
            "Fire",
            "Fire II",
            "Fire III",
            "Flare",
            "Fire IV",
            "Despair",
            "High Fire II",
            "Flare Star",
        )
        self.ice_actions = (
            "Blizzard",
            "Blizzard II",
            "Blizzard III",
            "Freeze",
            "Blizzard IV",
            "High Blizzard II",
        )

        self.astral_fire_stack_multiplier = {
            "fire": {1: 1.4, 2: 1.6, 3: 1.8},
            "ice": {1: 0.9, 2: 0.8, 3: 0.7},
        }

        self.umbral_ice_stack_multiplier = {
            "fire": {1: 0.9, 2: 0.8, 3: 0.7},
            "ice": {1: 1.0, 2: 1.0, 3: 1.0},
        }

        self.thunder_application_names = {"Thunder III", "High Thunder"}

        self.thunder_tick_names = {"Thunder III (tick)", "High Thunder (tick)"}

    def get_transpose_umbral_soul_casts(self, headers: Dict[str, str]) -> None:
        """
        Retrieve transpose and umbral soul casts, and thundercloud buff data.

        Parameters:
            headers (Dict[str, str]): Headers for the GraphQL query.
        """
        query = """
        query BlackMageCasts(
            $code: String!
            $id: [Int]!
            $playerID: Int!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    transpose: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 149
                    ) {
                        data
                    }
                    umbralSoul: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 16506
                    ) {
                        data
                    }
                    thundercloud: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: 1000164
                    )
                }
            }
        }
        """

        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "BlackMageCasts")

        transpose = self.request_response["data"]["reportData"]["report"]["transpose"][
            "data"
        ]
        transpose = pd.DataFrame(transpose)
        transpose["ability_name"] = "Transpose"
        transpose = transpose[["timestamp", "ability_name"]]

        umbral_soul = self.request_response["data"]["reportData"]["report"][
            "umbralSoul"
        ]["data"]

        # Check if umbral soul is used and append it
        if len(umbral_soul) > 0:
            umbral_soul = pd.DataFrame(umbral_soul)
            umbral_soul["ability_name"] = "Umbral Soul"
            umbral_soul = umbral_soul[["timestamp", "ability_name"]]
            self.transpose_umbral_soul = pd.concat([transpose, umbral_soul])

        # Otherwise just keep the transpose instances
        else:
            self.transpose_umbral_soul = transpose.copy()
        self.transpose_umbral_soul["timestamp"] += self.report_start
        self.transpose_umbral_soul["elapsed_time"] = None

        # Thundercloud buff (only for pre-Dawntrail)
        thundercloud_auras = self.request_response["data"]["reportData"]["report"][
            "thundercloud"
        ]["data"]["auras"]
        if len(thundercloud_auras) > 0:
            self.thundercloud_times = (
                pd.DataFrame(thundercloud_auras[0]["bands"]) + self.report_start
            ).to_numpy()
        # Post Dawntrail this is impossible, so just make a 1 x 2 array with impossible timestamps.
        else:
            self.thundercloud_times = np.array([[0, 0]])

    def _set_elemental_timings(self, actions_df: pd.DataFrame) -> None:
        """
        Find when Astral Fire and Umbral Ice, along with the number of.

        respective stacks. These values will be used to determine when Enochian is up
        and also apply the relevant (de)buffs to fire and ice spells.

        Parameters:
            actions_df (pd.DataFrame): DataFrame containing action data.
        """
        no_dot_actions_df = actions_df[actions_df["tick"] != True]

        # Concatenate umbral souls and transpose casts
        no_dot_actions_df = (
            pd.concat(
                [
                    no_dot_actions_df[["timestamp", "elapsed_time", "ability_name"]],
                    self.transpose_umbral_soul[
                        ["timestamp", "elapsed_time", "ability_name"]
                    ],
                ]
            )
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        # Get elapsed time
        no_dot_actions_df["elapsed_time"] = (
            no_dot_actions_df["timestamp"] - no_dot_actions_df["timestamp"].iloc[0]
        ) / 1000

        no_dot_actions_df["previous_action"] = no_dot_actions_df["ability_name"].shift(
            1
        )
        no_dot_actions_df["previous_time"] = no_dot_actions_df["elapsed_time"].shift(1)

        no_dot_actions_df = no_dot_actions_df[
            ["elapsed_time", "previous_time", "ability_name", "previous_action"]
        ]

        # Elemental_status, n_stacks, remaining_time
        elemental_status = []
        elemental_remaining_time = []
        n_stacks = []

        # Set up first action
        elemental_status.append(None)
        elemental_remaining_time.append(0)
        n_stacks.append(0)
        for idx, row in no_dot_actions_df.iloc[1:].iterrows():
            # action = row["ability_name"]
            previous_action = row["previous_action"]

            time_delta = row["elapsed_time"] - row["previous_time"]
            # Astral Fire
            if previous_action in self.fire_granting_actions.keys():
                elemental_remaining_time.append(
                    max(
                        0,
                        self.fire_granting_actions[previous_action]["time"]
                        - time_delta,
                    )
                )
                # Check that elemental effect from previous cast is still active
                if elemental_remaining_time[idx] > 0:
                    elemental_status.append("Astral Fire")
                    # Stacks: add to the previous number of stacks, but cap at 3
                    n_stacks.append(
                        min(
                            3,
                            n_stacks[idx - 1]
                            + self.fire_granting_actions[previous_action]["stacks"],
                        )
                    )
                else:
                    elemental_status.append(None)
                    n_stacks.append(0)

            # Umbral Ice
            elif previous_action in self.ice_granting_actions.keys():
                elemental_remaining_time.append(
                    max(
                        0,
                        self.ice_granting_actions[previous_action]["time"] - time_delta,
                    )
                )
                # Check that elemental effect from previous cast is still active
                if elemental_remaining_time[idx] > 0:
                    elemental_status.append("Umbral Ice")
                    # Stacks
                    # Add to the previous number of stacks, but cap at 3
                    n_stacks.append(
                        min(
                            3,
                            n_stacks[idx - 1]
                            + self.ice_granting_actions[previous_action]["stacks"],
                        )
                    )
                else:
                    elemental_status.append(None)
                    n_stacks.append(0)
            # Transpose
            # Important: Ice transpose no longer exists in Dawntrail as of 7.01
            # However, the job physically bars you from using ice transpose,
            # so no additional check is needed for BLM in Dawntrail and beyond.
            elif previous_action == "Transpose":
                time_remaining = elemental_remaining_time[idx - 1] - (time_delta)
                elemental_remaining_time.append(max(0, time_remaining))

                # Elemental effect must still be active, then check elemental status and swap
                if (elemental_status[idx - 1] == "Astral Fire") & (time_remaining > 0):
                    elemental_status.append("Umbral Ice")
                    n_stacks.append(1)
                elif (elemental_status[idx - 1] == "Umbral Ice") & (time_remaining > 0):
                    elemental_status.append("Astral Fire")
                    n_stacks.append(1)
                else:
                    elemental_status.append(None)
                    n_stacks.append(0)

            elif previous_action == "Paradox":
                # Check elemental status still active
                time_remaining = max(0, 15 - time_delta)
                if time_remaining > 0:
                    elemental_status.append(elemental_status[idx - 1])
                    elemental_remaining_time.append(time_remaining)
                    # Add one stack to active elemental status, to at most 3
                    n_stacks.append(min(3, n_stacks[idx - 1] + 1))
                else:
                    elemental_status.append(None)
                    elemental_remaining_time.append(0)
                    n_stacks.append(0)

            # Action does not change elemental status or stacks
            # Tick down time to see if elemental status falls off.
            else:
                time_remaining = elemental_remaining_time[idx - 1] - (time_delta)
                elemental_remaining_time.append(max(0, time_remaining))
                if (time_remaining > 0) & (elemental_status[idx - 1] is not None):
                    n_stacks.append(n_stacks[idx - 1])
                    elemental_status.append(elemental_status[idx - 1])
                else:
                    n_stacks.append(0)
                    elemental_status.append(None)

        # Put results in a new dataframe
        elemental_df = pd.DataFrame(
            {
                "elapsed_time": no_dot_actions_df["elapsed_time"],
                "ability_name": no_dot_actions_df["ability_name"],
                "elemental_status": elemental_status,
                "n_stacks": n_stacks,
            }
        )

        # Need to snapshot elemental status (for enochian) to thunder ticks
        thunder_3_ticks = actions_df[
            actions_df["ability_name"].isin(self.thunder_tick_names)
        ][["elapsed_time", "ability_name"]]

        thunder_3_all = pd.concat(
            [
                elemental_df[
                    elemental_df["ability_name"].isin(self.thunder_application_names)
                ],
                thunder_3_ticks,
            ]
        ).sort_values("elapsed_time")

        # Group each set of thunder applications and tick sets
        thunder_3_all["thunder_group"] = 0
        thunder_3_all.loc[
            thunder_3_all["ability_name"].isin(self.thunder_application_names),
            "thunder_group",
        ] = 1
        thunder_3_all["thunder_group"] = thunder_3_all["thunder_group"].cumsum()
        # Forward-fill elemental status by group
        thunder_3_all[["elemental_status", "n_stacks"]] = (
            thunder_3_all.groupby("thunder_group")[["elemental_status", "n_stacks"]]
            .ffill()
            .fillna(0)
        )
        thunder_3_all.drop(columns=["thunder_group"], inplace=True)

        # Now combine everything
        self.elemental_status = (
            pd.concat(
                [
                    elemental_df[
                        ~elemental_df["ability_name"].isin(
                            self.thunder_application_names
                        )
                    ],
                    thunder_3_all,
                ]
            )
            .sort_values("elapsed_time")
            .reset_index(drop=True)
        )
        self.elemental_status["n_stacks"] = self.elemental_status["n_stacks"].astype(
            int
        )

    def apply_elemental_buffs(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply buffs related to elemental job gauge:

        - Astral Fire I - III
        - Umbral Ice I - III
        - Enochian

        Parameters:
            actions_df (pd.DataFrame): DataFrame containing action data.

        Returns:
            pd.DataFrame: Updated DataFrame with applied elemental buffs.
        """

        def elemental_damage_multiplier(
            ability_name: str, elemental_status: str, n_stacks: int
        ) -> tuple:
            """
            Map ability_name, elemental_status, and n_stacks to the corresponding damage buff for fire/ice actions.

            Parameters:
            ability_name (str): Name of the ability being used.
            elemental_status (str): Which element status (AF/UI) is active.
            n_stacks (int): Number of stacks present for elemental status.

            Returns:
            tuple: Corresponding damage buff and list of buffs.
            """
            if elemental_status is None:
                return 1, []
            elif elemental_status == "Astral Fire":
                if ability_name in self.fire_actions:
                    return self.astral_fire_stack_multiplier["fire"][n_stacks], [
                        f"AF{n_stacks}"
                    ]
                elif ability_name in self.ice_actions:
                    return self.astral_fire_stack_multiplier["ice"][n_stacks], [
                        f"AF{n_stacks}"
                    ]
            elif elemental_status == "Umbral Ice":
                if ability_name in self.fire_actions:
                    return self.umbral_ice_stack_multiplier["fire"][n_stacks], [
                        f"UI{n_stacks}"
                    ]
            return 1, []

        self._set_elemental_timings(actions_df)

        # Apply enochian multiplier if an elemental status is active
        self.elemental_status["enochian_multiplier"] = 1.0
        self.elemental_status.loc[
            ~self.elemental_status["elemental_status"].isnull(), "enochian_multiplier"
        ] = self.enochian_buff

        # Apply elemental status multiplier to fire and ice spells
        # Also start to collect a list of BLM-specific buffs
        # All damage buff names are needed to uniquely name each 1-hit damage distribution
        self.elemental_status[["elemental_multiplier", "blm_buffs"]] = (
            self.elemental_status.apply(
                lambda x: elemental_damage_multiplier(
                    x.ability_name, x.elemental_status, x.n_stacks
                ),
                axis=1,
                result_type="expand",
            )
        )

        # Get the rest of the blm buffs
        # Enochian
        self.elemental_status["blm_buffs"] = self.elemental_status["blm_buffs"].apply(
            lambda x: x + ["Enochian"]
        )

        self.thundercloud_times = (
            self.thundercloud_times - actions_df["timestamp"].iloc[0]
        ) / 1000
        # Thundercloud (pre-DT only)
        thundercloud_condition = list(
            self.elemental_status["elapsed_time"].between(b[0], b[1], inclusive="right")
            for b in self.thundercloud_times
        )

        self.elemental_status.loc[
            disjunction(*thundercloud_condition)
            & (self.elemental_status["ability_name"] == "Thunder III"),
            "blm_buffs",
        ] = self.elemental_status["blm_buffs"].apply(
            lambda x: x + [str(self.thundercloud_id)]
        )

        blm_actions_df = actions_df.merge(
            self.elemental_status, on=["elapsed_time", "ability_name"], how="inner"
        )

        # Multiply out blm buffs
        blm_actions_df["multiplier"] *= (
            blm_actions_df["enochian_multiplier"]
            * blm_actions_df["elemental_multiplier"]
        )

        # Add blm buffs into buffs column and action name
        blm_actions_df["buffs"] = blm_actions_df.apply(
            lambda x: x["buffs"] + x["blm_buffs"], axis=1
        )

        # Update action names
        blm_actions_df["action_name"] = (
            blm_actions_df["action_name"].str.split("-").str[0]
            + "-"
            + blm_actions_df["buffs"].sort_values().str.join("_")
        )

        return blm_actions_df[actions_df.columns]
