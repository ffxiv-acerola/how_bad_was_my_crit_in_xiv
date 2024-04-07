"""Account for job-specific mechanics that affect actions."""

from functools import reduce
import json

import numpy as np
import pandas as pd
import requests

url = "https://www.fflogs.com/api/v2/client"


# This is a fun little function which allows an arbitrary
# number of between conditions to be applied.
# This gets used to apply the any buff,
# where the number of "between" conditions could be variable
def disjunction(*conditions):
    return reduce(np.logical_or, conditions)


class DarkKnightActions(object):
    def __init__(
        self,
        salted_earth_id=1000749,
    ) -> None:
        """Apply Dark Knight-specific job mechanics to actions:

        * When Darkside was up
        * Applying Darkside to actions, including snapshotting Salted Earth and excluding Living Shadow.

        Args:
            salted_earth_id (int, optional): Buff ID of Salted Earth. Defaults to 1000749.
        """
        self.salted_earth_id = salted_earth_id
        pass

    def when_was_darkside_not_up(self, actions_df, player_id):
        """Set time intervals in seconds when Darkside is not up as `self.no_darkside_time_intervals`.
        The variable is a 2 x n numpy array where is row the time interval where Darkside is not up,
        the first column is the beginning time, and the second column is the end time.

        Args:
            actions_df (DataFrame): Action dataframe from ActionTable class
            player_id (int): FFLogs-assigned actor ID of the player.
                             Used to exclude Edge of Shadow from Living Shadow.
        """
        # A bit of preprocessing, filter to Darkside buff giving actions, keep ability name and time.
        # FIXME: change to ability ID
        darkside_df = actions_df[
            actions_df["ability_name"].isin(["Edge of Shadow", "Flood of Shadow"])
            & (actions_df["sourceID"] == player_id)
        ][["ability_name", "elapsed_time"]].reset_index(drop=True)
        # Lag by 1 to get last darkside ability usage
        darkside_df["prior_edge_time"] = darkside_df["elapsed_time"].shift(periods=1)

        # Set up initial values of darkside timer value for when we loop through the DF
        darkside_df["darkside_cd_prior"] = 0  # darkside timer value before DS extended
        darkside_df["darkside_cd_prior_falloff"] = (
            0  # darkside timer value is before DS was extended and if the value could be negative
        )
        darkside_df["darkside_cd_post"] = 30  # darkside timer value after DS extended

        # Why are we looping through?
        # Current row results depend on derived values from current and prior row.
        # This makes vectorized approaches trickier without a bunch of lag/lead columns
        # Lambda functions are just for loops anyways.
        # A fight will have maybe a 100 EoS usages at most, so performance doesn't matter.
        for idx, row in darkside_df.iterrows():
            if idx > 0:
                darkside_cd_prior = (
                    darkside_df["darkside_cd_post"].iloc[idx - 1]
                    + darkside_df["prior_edge_time"].iloc[idx]
                    - darkside_df["elapsed_time"].iloc[idx]
                )
                darkside_df.at[idx, "darkside_cd_prior"] = max(0, darkside_cd_prior)
                darkside_df.at[idx, "darkside_cd_prior_falloff"] = darkside_cd_prior
                darkside_df.at[idx, "darkside_cd_post"] = min(
                    60, max(0, darkside_cd_prior) + 30
                )
            else:
                darkside_df.at[idx, "darkside_cd_prior_falloff"] = (
                    0 - darkside_df["elapsed_time"].iloc[idx]
                )

        # The columns we really want, time intervals when DS is not up
        darkside_df["darkside_not_up_start"] = None
        darkside_df["darkside_not_up_end"] = None
        darkside_df.loc[
            darkside_df["darkside_cd_prior_falloff"] < 0, "darkside_not_up_start"
        ] = darkside_df["elapsed_time"] + darkside_df["darkside_cd_prior_falloff"]
        darkside_df.loc[
            darkside_df["darkside_cd_prior_falloff"] < 0, "darkside_not_up_end"
        ] = darkside_df["elapsed_time"]

        # Turn into an array
        self.no_darkside_time_intervals = (
            darkside_df[~darkside_df["darkside_not_up_start"].isnull()][
                ["darkside_not_up_start", "darkside_not_up_end"]
            ]
            .to_numpy()
            .astype(float)
        )

        pass

    def apply_darkside_buff(self, action_df, pet_id):
        """Apply Darkside buff to all actions. There are some gotchas, which is why it needs it's own function
            * Salted earth snapshots Darkside.
            * Living shadow does not get Darkside.

        Args:
            action_df (DataFrame): Action data frame from the ActionTable class.
            pet_id (int): FFLogs-assigned actor ID of Living Shadow.

        Returns:
            DataFrame: Action data frame with Darkside properly applied.
        """

        no_darkside_conditions = (
            action_df["elapsed_time"].between(b[0], b[1])
            for b in self.no_darkside_time_intervals
        )
        action_df["darkside_buff"] = 1
        # Add 10% Darkside buff except
        # For living shadow
        # For salted earth (this gets snapshotted)
        action_df.loc[
            ~disjunction(*no_darkside_conditions)
            & (action_df["sourceID"] != pet_id)
            & (action_df["ability_name"] != "Salted Earth (tick)"),
            "darkside_buff",
        ] *= 1.1

        ### Salted earth snapshotting ###
        # The general strategy is group salted earth ticks by usage every 90s
        # If the first tick of a group (application) has Darkside,
        # all subsequent ticks snapshot Darkside too.
        salted_earth = action_df[
            action_df["ability_name"] == "Salted Earth (tick)"
        ].copy()
        salted_earth["multiplier"] = 1
        # Time since last SE tick
        salted_earth["last_tick_time"] = salted_earth["elapsed_time"] - salted_earth[
            "elapsed_time"
        ].shift(1)
        salted_earth.loc[:, "salted_earth_application"] = 0
        # If tick > 10s, then its an application, use for snapshotting DS
        salted_earth.loc[
            (salted_earth["last_tick_time"] > 10)
            | (salted_earth["last_tick_time"].isna()),
            "salted_earth_application",
        ] = 1
        # Group with cumsum
        salted_earth["salted_earth_group"] = salted_earth[
            "salted_earth_application"
        ].cumsum()

        # Check if salted earth snapshotted Darkside
        no_darkside_conditions_se = (
            salted_earth["elapsed_time"].between(b[0], b[1])
            for b in self.no_darkside_time_intervals
        )
        salted_earth.loc[
            ~disjunction(*no_darkside_conditions_se)
            & (salted_earth["salted_earth_application"] == 1),
            "darkside_buff",
        ] = 1.1

        # Propagate darkside buff by groupby max
        salted_earth["darkside_buff"] = salted_earth.groupby("salted_earth_group")[
            "darkside_buff"
        ].transform("max")

        ### End salted earth snapshotting ###
        # Now multiply out the darkside buff to the multiplier field,
        # Remove darkside buff column
        action_df.loc[
            action_df["ability_name"] == "Salted Earth (tick)",
            ["darkside_buff", "multiplier"],
        ] = salted_earth[["darkside_buff", "multiplier"]]

        action_df["multiplier"] *= action_df["darkside_buff"]
        # Also apply darkside buff
        action_df.loc[action_df["darkside_buff"] == 1.1, "buffs"].apply(
            lambda x: x.append("Darkside")
        )
        # And add to unique name
        action_df.loc[action_df["darkside_buff"] == 1.1, "action_name"] + "_Darkside"
        return action_df.drop(columns=["darkside_buff"])

    def apply_drk_things(self, actions_df, player_id, pet_id):
        """Apply DRK-specific transformations to the actions dataframe including:
        * Estimate damage multiplier for Salted Earth.
        * Figure out when Darkside is up.
        * Apply Darkside to actions affected by Darkside.

        Args:
            actions_df (DataFrame): Actions data frame from the ActionTable class
            player_id (int): FFLogs-assigned actor ID of the player.
            pet_id (int): FFLogs-assigned actor ID of Living Shadow.

        Returns:
            DataFrame: Actions data frame with DRK-specific mechanics applied.
        """

        # Find when Darkside is not up
        self.when_was_darkside_not_up(actions_df, player_id)

        # Apply darkside buff, which will correctly:
        #   - Snapshot to Salted Earth
        #   - Not apply to Living Shadow
        actions_df = self.apply_darkside_buff(actions_df, pet_id)
        return actions_df

    pass


class PaladinActions(object):
    def __init__(
        self,
        headers: dict,
        report_id: str,
        fight_id: int,
        player_id: int,
        requiescat_id=1001368,
        divine_might_id=1002673,
        holy_ids=[7384, 16458],
        blade_ids=[16459, 25748, 25749, 25750],
    ) -> None:
        """Apply Paladin-specific job mechanics to actions:
            * See when Divine Might and Requiescat are up.
            * Apply them in the correct order to actions whose potencies are
              affected by these buffs.

        Args:
            headers (dict): FFLogs API header, required to make an additional buff API call.
                            The bearer key is not saved.
            report_id (str): FFLogs report ID
            fight_id (int): Associated fight ID
            player_id (int): FFLogs-assigned actor ID to the PLD
            requiescat_id (int, optional): ID of Requiescat. Defaults to 1001368.
            divine_might_id (int, optional): ID of Divine Might. Defaults to 1002673.
            holy_ids (list, optional): ID of Holy Spirit and Holy Circle. Defaults to [7384, 16458].
            blade_ids (list, optional): IDs of Confiteor, Blade of {Faith, Truth, Valor}.
                                        Defaults to [16459, 25748, 25749, 25750]
        """
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.requiescat_id = requiescat_id
        self.divine_might_id = divine_might_id
        self.holy_ids = holy_ids
        self.blade_ids = blade_ids

        self.set_pld_buff_times(headers)
        pass

    def set_pld_buff_times(self, headers):
        """Perform an API call to get buff intervals for Requiescat and Divine Might.
        Sets values as a 2 x n Numpy array, where the first column is the start time
        and the second column is the end time.

        Args:
            headers (dict): FFLogs API header.

        """
        query = """
        query PaladinBuffs(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $requiescatID: Float!
            $divineMightID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    requiescat: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $requiescatID
                    )
                    divineMight: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $divineMightID
                    )
                }
            }
        }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "requiescatID": self.requiescat_id,
            "divineMightID": self.divine_might_id,
        }

        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": "PaladinBuffs",
        }
        r = requests.post(url=url, json=json_payload, headers=headers)
        r = json.loads(r.text)

        report_start = r["data"]["reportData"]["report"]["startTime"]
        requiescat_auras = r["data"]["reportData"]["report"]["requiescat"]["data"][
            "auras"
        ]
        if len(requiescat_auras) > 0:
            self.requiescat_times = (
                pd.DataFrame(requiescat_auras[0]["bands"]) + report_start
            ).to_numpy()

        divine_might_auras = r["data"]["reportData"]["report"]["divineMight"]["data"][
            "auras"
        ]
        if len(divine_might_auras) > 0:
            self.divine_might_times = (
                pd.DataFrame(divine_might_auras[0]["bands"]) + report_start
            ).to_numpy()

        pass

    def apply_pld_buffs(self, actions_df):
        """Apply Divine Might and Requiescat to actions which are affected by them.
        This information will be used to map those actions to the correct potencies.
        This is really just to check the rotation has not gone horribly, horribly wrong,
        or some serious cooking is happening.

        Args:
            actions_df (DataFrame): Actions data frame from the ActionTable class.
        """
        # Check if the timestamp is between any divine might window.
        divine_might_condition = list(
            actions_df["timestamp"].between(b[0], b[1]) for b in self.divine_might_times
        )
        # Check if timestamp is between any requiescat window.
        requiescat_condition = list(
            actions_df["timestamp"].between(b[0], b[1]) for b in self.requiescat_times
        )

        # Holy spirit/circle with Divine might:
        #    - Has Divine Might buff active
        #    - Requiescat irrelevant
        actions_df.loc[
            disjunction(*divine_might_condition)
            & actions_df["abilityGameID"].isin(self.holy_ids),
            "buffs",
        ] = actions_df["buffs"].apply(lambda x: x + [str(self.divine_might_id)])

        # Holy spirit/circle with Requiescat:
        #    - Has requiescat and not divine might buff active
        actions_df.loc[
            ~disjunction(*divine_might_condition)
            & actions_df["abilityGameID"].isin(self.holy_ids)
            & disjunction(*requiescat_condition),
            "buffs",
        ] = actions_df["buffs"].apply(lambda x: x + [str(self.requiescat_id)])
        # Confiteor -> Blade combo
        # Requiescat up
        actions_df.loc[
            disjunction(*requiescat_condition)
            & actions_df["abilityGameID"].isin(self.blade_ids),
            "buffs",
        ] = actions_df["buffs"].apply(lambda x: x + [str(self.requiescat_id)])

        # update action names with new buffs
        actions_df["action_name"] = (
            actions_df["action_name"].str.split("-").str[0]
            + "-"
            + actions_df["buffs"].sort_values().str.join("_")
        )

        return actions_df


class BlackMageActions(object):
    def __init__(
        self, headers, report_id, fight_id, player_id, thundercloud_id=1000164
    ) -> None:
        self.report_id = report_id
        self.player_id = player_id
        self.fight_id = fight_id
        self.thundercloud_id = thundercloud_id

        self.get_transpose_umbral_soul_casts(headers)

        # Paradox and transpose are exlcuded because they affect both fire and ice
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
        pass

    def get_transpose_umbral_soul_casts(self, headers):
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

        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": "BlackMageCasts",
        }
        r = requests.post(url=url, json=json_payload, headers=headers)
        r = json.loads(r.text)

        report_start = r["data"]["reportData"]["report"]["startTime"]

        transpose = r["data"]["reportData"]["report"]["transpose"]["data"]
        transpose = pd.DataFrame(transpose)
        transpose["ability_name"] = "Transpose"
        transpose = transpose[["timestamp", "ability_name"]]

        umbral_soul = r["data"]["reportData"]["report"]["umbralSoul"]["data"]
        umbral_soul = pd.DataFrame(umbral_soul)
        umbral_soul["ability_name"] = "Umbral Soul"
        umbral_soul = umbral_soul[["timestamp", "ability_name"]]

        self.transpose_umbral_soul = pd.concat([transpose, umbral_soul])
        self.transpose_umbral_soul["timestamp"] += report_start
        self.transpose_umbral_soul["elapsed_time"] = None

        # Thundercloud buff
        thundercloud_auras = r["data"]["reportData"]["report"]["thundercloud"]["data"][
            "auras"
        ]
        if len(thundercloud_auras) > 0:
            self.thundercloud_times = (
                pd.DataFrame(thundercloud_auras[0]["bands"]) + report_start
            ).to_numpy()
    
        pass

    def _set_elemental_timings(self, actions_df):
        """Find when Astral Fire and Umbral Ice, along with the number of
        respective stacks. These values will be used to determine when Enochian is up
        and also apply the relevant (de)buffs to fire and ice spells.
        """
        no_dot_actions_df = actions_df[actions_df["tick"] != True]

        # Concatenate umbral souls and tranpose casts
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
            action = row["ability_name"]
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
            actions_df["ability_name"] == "Thunder III (tick)"
        ][["elapsed_time", "ability_name"]]

        thunder_3_all = pd.concat(
            [
                elemental_df[elemental_df["ability_name"] == "Thunder III"],
                thunder_3_ticks,
            ]
        ).sort_values("elapsed_time")

        # Group each set of thunder applications and tick sets
        thunder_3_all["thunder_group"] = 0
        thunder_3_all.loc[
            thunder_3_all["ability_name"] == "Thunder III", "thunder_group"
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
                    elemental_df[elemental_df["ability_name"] != "Thunder III"],
                    thunder_3_all,
                ]
            )
            .sort_values("elapsed_time")
            .reset_index(drop=True)
        )
        self.elemental_status["n_stacks"] = self.elemental_status["n_stacks"].astype(
            int
        )
        pass

    def apply_elemental_buffs(self, actions_df):
        """Apply buffs related to elemental job guage:
        - Astral Fire I - III
        - Umbral Ice I - III
        - Enochian
        """

        def elemental_damage_multiplier(ability_name, elemental_status, n_stacks):
            """Map ability_name, elemental_status, and n_stacks to the corresponding damage buff for fire/ice actions.

            Args:
                ability_name (str): Name of the ability being used.
                elemental_status (str): Which element status (AF/UI) is active.
                n_stacks (int): Number of stacks present for elemental status.

            Returns:
                int: corresponding damage buff.
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
        self.elemental_status["enochian_multiplier"] = 1
        self.elemental_status.loc[
            ~self.elemental_status["elemental_status"].isnull(), "enochian_multiplier"
        ] = 1.23

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

        self.thundercloud_times = (self.thundercloud_times - actions_df["timestamp"].iloc[0]) / 1000
        # Thundercloud
        thundercloud_condition = list(
            self.elemental_status["elapsed_time"].between(b[0], b[1], inclusive="right") for b in self.thundercloud_times
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
        blm_actions_df["buffs"] = blm_actions_df.apply(lambda x: x["buffs"] + x["blm_buffs"], axis=1)

        # Update action names
        blm_actions_df["action_name"] = (
            blm_actions_df["action_name"].str.split("-").str[0]
            + "-"
            + blm_actions_df["buffs"].sort_values().str.join("_")
        )

        return blm_actions_df[actions_df.columns]


if __name__ == "__main__":
    from config import FFLOGS_TOKEN

    api_key = FFLOGS_TOKEN  # or copy/paste your key here
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    PaladinActions(headers, "M2ZKgJtTqnNjYxCQ", 54, 118)
    pass
