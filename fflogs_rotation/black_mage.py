from typing import Dict

import numpy as np
import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction


class BlackMageActions(BuffQuery):
    def __init__(
        self,
        actions_df: pd.DataFrame,
        headers: Dict[str, str],
        report_id: str,
        fight_id: int,
        player_id: int,
        level: int,
        phase: int,
        patch_number: float,
        thundercloud_id: int = 1000164,
    ) -> None:
        self.report_id = report_id
        self.player_id = player_id
        self.fight_id = fight_id
        self.phase = phase

        self.level = level
        self.patch_number = patch_number

        self.thundercloud_id = thundercloud_id

        self.fire_actions = {
            141: "Fire",
            147: "Fire II",
            152: "Fire III",
            162: "Flare",
            3577: "Fire IV",
            16505: "Despair",
            25794: "High Fire II",
            36989: "Flare Star",
        }
        self.ice_actions = {
            142: "Blizzard",
            25793: "Blizzard II",
            154: "Blizzard III",
            159: "Freeze",
            3576: "Blizzard IV",
            25795: "High Blizzard II",
        }

        self.gauge_actions = {
            149: "Transpose",
            16506: "Umbral Soul",
            25797: "Paradox",
            158: "Manafont",
        }

        self.astral_fire_stack_multiplier = {
            "fire": {1: 1.4, 2: 1.6, 3: 1.8},
            "ice": {1: 0.9, 2: 0.8, 3: 0.7},
        }

        self.umbral_ice_stack_multiplier = {
            "fire": {1: 0.9, 2: 0.8, 3: 0.7},
            "ice": {1: 1.0, 2: 1.0, 3: 1.0},
        }

        self.enochian_buff = self._get_enochian_buffs(level, patch_number)
        self.fire_granting_actions = self._get_fire_granting_actions(patch_number)
        self.ice_granting_actions = self._get_ice_granting_actions(patch_number)
        self.other_granting_actions = self._get_other_granting_actions(patch_number)

        self.thunder_application_names = {"Thunder III", "High Thunder"}

        self.thunder_tick_names = {"Thunder III (tick)", "High Thunder (tick)"}

        # All actions which affect elemental gauge state, some have to be queried.
        self.elemental_gauge_df = self._get_elemental_gauge_actions(headers, actions_df)
        # Track elemental gauge state
        self.elemental_state = self._get_elemental_state_df(self.elemental_gauge_df)
        # Changes to the elemental gauge state
        self.elemental_state_changes = self._get_elemental_state_changes(
            self.elemental_state
        )
        # Elemental state timings based on changes.
        self.elemental_state_times = self._get_elemental_state_timings(
            self.elemental_state_changes
        )
        self.enochian_times = self._enochian_times(self.elemental_state_changes)
        print("")

    @staticmethod
    def _get_enochian_buffs(level: int, patch_number: float) -> float:
        """Get enochian buff strength based on level and patch number.

        Args:
            level (int): Level
            patch_number (float): Patch

        Returns:
            float: Enochian buff strength multiplier
        """
        if level < 96:
            return 1.23
        elif (level >= 96) & (patch_number < 7.05):
            return 1.3
        elif (level >= 96) & (patch_number == 7.05):
            return 1.33
        elif (level >= 96) & (patch_number < 7.2):
            return 1.32
        elif (level >= 96) & (patch_number >= 7.2):
            return 1.27

    @staticmethod
    def _get_fire_granting_actions(patch_number: float) -> dict[str, dict[str, int]]:
        """Get dictionary of actions which exclusively grant astral fire,.

        denoting how many stacks and how they affect the elemental gauge timer.

        No gauge is simulated by very long timer values.

        Args:
            patch_number (float): Patch version

        Returns:
            dict[str, dict[str, int]]: Dictionary of fire granting actions.
        """
        TIMER_DURATION = 15

        if patch_number >= 7.2:
            # AF/UI timer is removed.
            # Recreate this by setting timers to very big number
            TIMER_DURATION = 500

        MANAFONT_TIMER = TIMER_DURATION
        MANAFONT_STACKS = 3

        if patch_number < 7.0:
            MANAFONT_TIMER = 0
            MANAFONT_STACKS = 0

        return {
            "Despair": {"time": TIMER_DURATION, "stacks": 3},
            "Flare": {"time": TIMER_DURATION, "stacks": 3},
            "Fire": {"time": TIMER_DURATION, "stacks": 1},
            "Fire III": {"time": TIMER_DURATION, "stacks": 3},
            "High Fire II": {"time": TIMER_DURATION, "stacks": 3},
            "Manafont": {
                "time": MANAFONT_TIMER,
                "stacks": MANAFONT_STACKS,
            },
        }

    @staticmethod
    def _get_ice_granting_actions(patch_number: float) -> dict:
        TIMER_DURATION = 15
        UMBRAL_TIMER_DURATION = 500

        if patch_number >= 7.2:
            # AF/UI timer is removed.
            # Recreate this by setting timers to very big number
            TIMER_DURATION = 500

        return {
            "Blizzard III": {"time": TIMER_DURATION, "stacks": 3},
            "Umbral Soul": {"time": UMBRAL_TIMER_DURATION, "stacks": 1},
            "Blizzard": {"time": TIMER_DURATION, "stacks": 1},
            "High Blizzard II": {"time": TIMER_DURATION, "stacks": 3},
        }

    @staticmethod
    def _get_other_granting_actions(patch_number: float) -> dict:
        TIMER_DURATION = 15
        PARADOX_STACKS = 1

        if patch_number >= 7.2:
            # AF/UI timer is removed.
            # Recreate this by setting timers to very big number
            TIMER_DURATION = 500
            # Paradox no longer gives stacks
            PARADOX_STACKS = 0

        return {
            "Paradox": {"time": TIMER_DURATION, "stacks": PARADOX_STACKS},
            "Transpose": {"time": TIMER_DURATION, "stacks": 1},
            "Manafont": {"time": TIMER_DURATION, "stacks": 3},
        }

    def _query_elemental_gauge_affecting_actions(self, headers: Dict[str, str]) -> None:
        """
        Get gauge actions for the full fight.

        Required when phase analysis is performed
        to properly track gauge status for the whole fight.
        """
        query = """
        query BlackMageGaugeCasts($code: String!, $id: [Int]!, $playerID: Int!) {
            reportData {
                report(code: $code) {
                    startTime
                    Fire: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 141
                    ) {
                        data
                    }
                    FireIII: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 152
                    ) {
                        data
                    }
                    HighFireII: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 25794
                    ) {
                        data
                    }
                    Flare: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 162
                    ) {
                        data
                    }
                    Paradox: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 25797
                    ) {
                        data
                    }
                    Despair: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 16505
                    ) {
                        data
                    }
                    Blizzard: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 142
                    ) {
                        data
                    }
                    BlizzardIII: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 154
                    ) {
                        data
                    }
                    Freeze: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 159
                    ) {
                        data
                    }
                    HighBlizzard: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 25795
                    ) {
                        data
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

        gauge_actions = self.gql_query(headers, query, variables, "BlackMageGaugeCasts")

        cast_dfs = []

        start_time = gauge_actions["data"]["reportData"]["report"].pop("startTime")
        self.start_time = start_time
        cast_dfs = [
            self._casts_to_gauge_df(
                v["data"],
                start_time=start_time,
            )
            for k, v in gauge_actions["data"]["reportData"]["report"].items()
        ]

        gauge_actions = pd.concat(cast_dfs).sort_values("timestamp")

        return gauge_actions.sort_values("timestamp")

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
            "duration",
        ]

        df = pd.DataFrame(response_report_data, columns=df_cols)

        df = df[df["type"] == "cast"]
        df["ability_name"] = ability_name
        df["timestamp"] += start_time

        return df

    def _thundercloud_times(self, thundercloud_auras) -> None:
        if len(thundercloud_auras) > 0:
            self.thundercloud_times = (
                pd.DataFrame(thundercloud_auras[0]["bands"]) + self.report_start
            ).to_numpy()
        # Post Dawntrail this is impossible, so just make a 1 x 2 array with impossible timestamps.
        else:
            self.thundercloud_times = np.array([[0, 0]])

    def _query_transpose_umbral_soul_manafont_casts(
        self, headers: Dict[str, str]
    ) -> None:
        """
        Retrieve transpose and umbral soul casts, manafont, and thundercloud buff data.

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
                    Manafont: events(
                        fightIDs: $id
                        dataType: Casts
                        sourceID: $playerID
                        viewOptions: 1
                        abilityID: 158
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

        response = self.gql_query(headers, query, variables, "BlackMageCasts")
        start_time = response["data"]["reportData"]["report"]["startTime"]

        transpose_df = self._casts_to_gauge_df(
            response["data"]["reportData"]["report"]["transpose"]["data"],
            start_time=start_time,
            ability_name="Transpose",
        )

        umbral_soul_df = self._casts_to_gauge_df(
            response["data"]["reportData"]["report"]["umbralSoul"]["data"],
            start_time=start_time,
            ability_name="Umbral Soul",
        )

        manafont_df = self._casts_to_gauge_df(
            response["data"]["reportData"]["report"]["Manafont"]["data"],
            start_time=start_time,
            ability_name="Manafont",
        )

        # Thundercloud buff (only for pre-Dawntrail)
        self._thundercloud_times(
            response["data"]["reportData"]["report"]["thundercloud"]["data"]["auras"]
        )
        return transpose_df, umbral_soul_df, manafont_df

    def _get_elemental_gauge_actions(
        self, headers: Dict[str, str], actions_df=None
    ) -> None:
        if self.phase > 0:
            damage_gauge_actions = self._query_elemental_gauge_affecting_actions(
                headers
            )
        else:
            damage_gauge_actions = actions_df[
                actions_df["ability_name"].isin(
                    (
                        self.fire_granting_actions
                        | self.ice_granting_actions
                        | self.other_granting_actions
                    ).keys()
                )
            ][
                [
                    "timestamp",
                    "type",
                    "sourceID",
                    "targetID",
                    "abilityGameID",
                    "ability_name",
                ]
            ].copy()

        # Non-damaging gauge actions
        transpose_df, umbral_soul_df, manafont_df = (
            self._query_transpose_umbral_soul_manafont_casts(headers)
        )

        elemental_gauge_df = (
            pd.concat([damage_gauge_actions, transpose_df, umbral_soul_df, manafont_df])
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        elemental_gauge_df["ability_name"] = (
            elemental_gauge_df["abilityGameID"]
            .replace(self.fire_actions)
            .replace(self.ice_actions)
            .replace(self.gauge_actions)
        )

        # Set up relative time in seconds and previous actions
        # IMPORTANT: this should be used used for
        elemental_gauge_df["elapsed_time"] = (
            elemental_gauge_df["timestamp"] - elemental_gauge_df["timestamp"].iloc[0]
        ) / 1000

        elemental_gauge_df["previous_action"] = elemental_gauge_df[
            "ability_name"
        ].shift(1)
        elemental_gauge_df["previous_time"] = elemental_gauge_df["elapsed_time"].shift(
            1
        )

        return elemental_gauge_df

    # Processing elemental gauge data to create times
    def _floor_gauge_time(self, proposed_time: float) -> float:
        """For a proposed time to the elemental gauge, limit it from dipping below 0 seconds."""
        return max(
            0.0,
            proposed_time,
        )

    def _ceiling_elemental_stack(self, proposed_stacks) -> int:
        """Take a proposed number of stacks and cap it at 3."""
        return min(3, proposed_stacks)

    def _elemental_time_remaining(
        self, previous_action: str, time_delta: float
    ) -> float:
        """
        Calculate the remaining elemental gauge time after a specific action and a given time lapse.

        If the previous action was "Umbral Soul", a fixed value of 1000.0 is returned. Otherwise,
        the method:
        1) Looks up the base gauge duration for the given action in fire/ice/other granting actions.
        2) Subtracts the passed time_delta from this base duration.
        3) Floors the result at zero (no negative gauge time).

        Args:
            previous_action (str): The name of the last action performed (e.g. "Fire", "Umbral Soul").
            time_delta (float): The elapsed time in seconds since the previous action.

        Raises:
            RuntimeError: If the action is not recognized in the known action dictionaries.

        Returns:
            float: The updated remaining gauge time after subtracting time_delta.
        """
        fire_ice_other = (
            self.fire_granting_actions
            | self.ice_granting_actions
            | self.other_granting_actions
        )

        if previous_action in fire_ice_other.keys():
            proposed_time = fire_ice_other[previous_action]["time"] - time_delta
        else:
            raise RuntimeError(f"Unhandled case for {previous_action}")
        return self._floor_gauge_time(proposed_time)

    def _elemental_status_active(
        self, previous_action, time_remaining, previous_elemental_status: str
    ) -> str:
        transpose_elemental_state = {
            "Astral Fire": "Umbral Ice",
            "Umbral Ice": "Astral Fire",
        }

        if time_remaining <= 0:
            return None

        # Fire actions gives Astral Fire
        elif previous_action in self.fire_granting_actions.keys():
            return "Astral Fire"

        # Ice actions gives Umbral Ice
        elif previous_action in self.ice_granting_actions.keys():
            return "Umbral Ice"

        # Transpose switches elemental state
        elif previous_action == "Transpose":
            return transpose_elemental_state.get(previous_elemental_status, None)

        # Paradox refreshes the current elemental state
        elif previous_action == "Paradox":
            return previous_elemental_status

        else:
            raise RuntimeError(
                f"Unhandled case for current elemental status: {previous_action}."
            )

    def _current_elemental_stacks(
        self, remaining_time: float, previous_action: str, prior_stacks: int
    ) -> int:
        fire_ice = self.ice_granting_actions | self.fire_granting_actions
        if remaining_time <= 0:
            return 0

        elif previous_action == "Transpose":
            return 1

        elif previous_action == "Paradox":
            return self._ceiling_elemental_stack(prior_stacks + 1)

        elif previous_action in fire_ice.keys():
            return self._ceiling_elemental_stack(
                prior_stacks + fire_ice[previous_action]["stacks"]
            )

        else:
            raise RuntimeError("Invalid state")

    def _elemental_time_granted(self, current_action: str) -> float:
        """Elemental gauge timer after an action."""
        return (
            self.fire_granting_actions
            | self.ice_granting_actions
            | self.other_granting_actions
        )[current_action]["time"]

    def _elemental_stacks_granted(
        self,
        current_action: str,
        current_elemental_stacks: int,
        current_elemental_state: str,
    ) -> int:
        """
        Calculate the total number of elemental stacks after a particular action.

        This method applies stack-incrementing logic for actions such as "Paradox" or "Umbral Soul"
        and returns a fixed stack amount for certain fire/ice actions. "Transpose" either sets
        the count to zero if there is no current elemental state, or sets it to one if there is.

        Args:
            current_action (str): The name of the action that was just used (e.g. "Fire", "Transpose").
            current_elemental_stacks (int): The number of elemental stacks active before this action.
            current_elemental_state (str): Either "Astral Fire", "Umbral Ice", or None if no state.

        Raises:
            RuntimeError: If the action is invalid or unsupported by the logic provided.

        Returns:
            int: The number of stacks that should be active following the action.
        """
        fire_ice = self.fire_granting_actions | self.ice_granting_actions

        if current_action == "Transpose":
            # Transpose with no elemental state does nothing
            if current_elemental_state is None:
                return 0
            # Otherwise always sets at 1 stack
            else:
                return 1

        # Paradox incrementer. Pre 7.2 it increments, post 7.2 it
        # does nothing
        elif current_action == "Paradox":
            return self._ceiling_elemental_stack(
                current_elemental_stacks
                + self.other_granting_actions["Paradox"]["stacks"]
            )

        # Umbral soul incrementer
        elif current_action == "Umbral Soul":
            return self._ceiling_elemental_stack(
                current_elemental_stacks
                + self.ice_granting_actions["Umbral Soul"]["stacks"]
            )

        # Otherwise return the number of stacks for the specified action
        elif current_action in fire_ice.keys():
            return fire_ice[current_action]["stacks"]

        else:
            raise RuntimeError("Invalid state")

    def _elemental_status_granted(
        self, current_action, active_elemental_state: str
    ) -> str:
        """
        Determine the new elemental state granted by a given action.

        This method checks whether the action is "Paradox", "Transpose", a fire-granting action, or
        an ice-granting action, and returns the corresponding elemental state. If "Transpose" is used
        and no elemental state is active, the state remains None. "Paradox" keeps the current state
        unchanged.

        Args:
            current_action (str): The action performed (e.g. "Fire", "Transpose").
            active_elemental_state (str): The elemental status before the action ("Astral Fire",
                "Umbral Ice", or None if no state).

        Raises:
            RuntimeError: If the action is invalid or not recognized in the known action dictionaries.

        Returns:
            str or None: The elemental state ("Astral Fire", "Umbral Ice", or None) granted by
                the specified action.
        """
        transpose_elemental_state = {
            "Astral Fire": "Umbral Ice",
            "Umbral Ice": "Astral Fire",
        }

        # Paradox doesn't change elemental state
        if current_action == "Paradox":
            return active_elemental_state
        # Transpose swaps with active state, but does nothing if no state
        elif current_action == "Transpose":
            return transpose_elemental_state.get(active_elemental_state, None)
        # Fire action gives fire state
        elif current_action in self.fire_granting_actions.keys():
            return "Astral Fire"
        # Ice action gives ice state
        elif current_action in self.ice_granting_actions.keys():
            return "Umbral Ice"
        else:
            raise RuntimeError("Invalid state")

    def _get_elemental_state_df(self, elemental_gauge_df: pd.DataFrame) -> None:
        """
        Find when Astral Fire and Umbral Ice, along with the number of.

        respective stacks. These values will be used to determine when Enochian is up
        and also apply the relevant (de)buffs to fire and ice spells.
        """

        # Elemental_status, n_stacks, remaining_time
        elemental_status_active = []
        elemental_status_granted = []

        elemental_remaining_time = []
        elemental_time_granted = []

        n_stacks_current = []
        n_stacks_granted = []

        # Set up first action
        first_action = elemental_gauge_df.iloc[0]["ability_name"]

        # Current empty state
        elemental_status_active.append(None)
        elemental_remaining_time.append(0)
        n_stacks_current.append(0)

        # Set granted actions
        elemental_status_granted.append(
            self._elemental_status_granted(first_action, active_elemental_state=None)
        )
        elemental_time_granted.append(self._elemental_time_granted(first_action))
        n_stacks_granted.append(
            self._elemental_stacks_granted(
                first_action, current_elemental_stacks=0, current_elemental_state=None
            )
        )

        for idx, row in elemental_gauge_df.iloc[1:].iterrows():
            # Row-level data
            current_action = row["ability_name"]
            previous_action = row["previous_action"]
            time_delta = row["elapsed_time"] - row["previous_time"]

            # Set active state before action
            elemental_remaining_time.append(
                self._elemental_time_remaining(previous_action, time_delta)
            )
            elemental_status_active.append(
                self._elemental_status_active(
                    previous_action,
                    elemental_remaining_time[idx],
                    elemental_status_active[idx - 1],
                )
            )
            n_stacks_current.append(
                self._current_elemental_stacks(
                    elemental_remaining_time[idx],
                    previous_action,
                    n_stacks_current[idx - 1],
                )
            )

            # Set state granted after executing action
            elemental_time_granted.append(self._elemental_time_granted(current_action))
            elemental_status_granted.append(
                self._elemental_status_granted(
                    current_action, active_elemental_state=elemental_status_active[idx]
                )
            )
            n_stacks_granted.append(
                self._elemental_stacks_granted(
                    current_action,
                    current_elemental_stacks=n_stacks_current[idx],
                    current_elemental_state=elemental_status_active[idx],
                )
            )

        return pd.DataFrame(
            {
                "timestamp": self.elemental_gauge_df["timestamp"],
                "elapsed_time": self.elemental_gauge_df["elapsed_time"],
                "ability_name": self.elemental_gauge_df["ability_name"],
                "elemental_status_active": elemental_status_active,
                "n_stacks_active": n_stacks_current,
                "remaining_time": elemental_remaining_time,
                "elemental_status_granted": elemental_status_granted,
                "n_stacks_granted": n_stacks_granted,
                "time_granted": elemental_time_granted,
            }
        )

    def _insert_dropped_status(self, elemental_changes: pd.DataFrame) -> pd.DataFrame:
        """
        Identify gauge rows where the elemental status must be dropped and insert.

        corresponding rows that mark the status as ended.

        Parameters:
            elemental_changes (pd.DataFrame): DataFrame of elemental state changes
                with columns like "timestamp", "time_granted", "elemental_status_granted",
                and "elemental_status_active".

        Returns:
            pd.DataFrame: A DataFrame containing the inserted 'dropped gauge' rows,
                where "elemental_status_granted" is None and "n_stacks_granted" is 0
                to indicate a full gauge drop.
        """

        #
        unpaired_change_condition = elemental_changes[
            "elemental_status_granted"
        ] != elemental_changes["elemental_status_active"].shift(-1)

        dropped_gauge_rows = elemental_changes[unpaired_change_condition].copy()

        dropped_gauge_rows["projected_state_drop"] = (
            dropped_gauge_rows["timestamp"] + dropped_gauge_rows["time_granted"] * 1000
        )

        # Make schema same as elemental_changes to union later
        dropped_gauge_rows = dropped_gauge_rows[
            ["projected_state_drop", "n_stacks_granted", "elemental_status_granted"]
        ]
        dropped_gauge_rows = dropped_gauge_rows.rename(
            columns={
                "projected_state_drop": "timestamp",
                "n_stacks_granted": "n_stacks_active",
                "elemental_status_granted": "elemental_status_active",
            }
        )
        dropped_gauge_rows["elemental_status_granted"] = None
        dropped_gauge_rows["n_stacks_granted"] = 0
        return dropped_gauge_rows

    def _get_elemental_state_changes(self, elemental_state):
        """Transform the self.elemental_state DataFrame to show when.

        elemental states changed, including no elemental state.
        Used to properly assign the correct buffs to certain actions and
        find when Enochian is up.
        """

        # Dataframe where elemental state changes occur
        elemental_state_changes = elemental_state[
            # Fire -> Ice or Ice -> Fire
            (
                elemental_state["elemental_status_active"]
                != elemental_state["elemental_status_granted"]
            )
            # Edge case: state doesn't change but timer is refreshed
            # and state is dropped later. The final refresh needs to be
            # retained to accurately capture the expiry time.
            | (
                elemental_state["elemental_status_active"]
                != elemental_state["elemental_status_active"].shift(-1)
            )
            # Elemental state constant but stacks change, AF1 -> AF3
            | (
                (
                    elemental_state["n_stacks_active"]
                    != elemental_state["n_stacks_granted"]
                )
                & (
                    elemental_state["elemental_status_active"]
                    == elemental_state["elemental_status_granted"]
                )
            )
        ]

        # It doesn't account for elemental state dropping, handle separately
        elemental_gauge_dropped_rows = self._insert_dropped_status(
            elemental_state_changes
        )

        elemental_state_changes = pd.concat(
            [
                elemental_state_changes[elemental_gauge_dropped_rows.columns],
                elemental_gauge_dropped_rows,
            ]
        )[
            [
                "timestamp",
                "elemental_status_active",
                "n_stacks_active",
                "elemental_status_granted",
                "n_stacks_granted",
            ]
        ].sort_values("timestamp")

        elemental_state_changes = elemental_state_changes[
            (
                elemental_state_changes["elemental_status_active"]
                != elemental_state_changes["elemental_status_granted"]
            )
            | (
                elemental_state_changes["n_stacks_active"]
                != elemental_state_changes["n_stacks_granted"]
            )
        ].reset_index(drop=True)

        # Quality of life columns for testing
        elemental_state_changes["string_change"] = (
            elemental_state_changes["elemental_status_active"].astype(str)
            + " "
            + elemental_state_changes["n_stacks_active"].astype(str)
            + " -> "
            + elemental_state_changes["elemental_status_granted"].astype(str)
            + " "
            + elemental_state_changes["n_stacks_granted"].astype(str)
        )

        elemental_state_changes["formatted_elapsed_time"] = (
            elemental_state_changes["timestamp"]
            - self.elemental_gauge_df["timestamp"].iloc[0]
        ) / 1000
        elemental_state_changes["formatted_elapsed_time"] = pd.to_datetime(
            elemental_state_changes["formatted_elapsed_time"], unit="s"
        ).dt.strftime("%M:%S")

        return elemental_state_changes

    def _get_elemental_state_timings(
        self, elemental_state_changes: pd.DataFrame
    ) -> Dict[str, np.ndarray]:
        """
        Build timing arrays for elemental gauge states: Astral Fire (AF1-3) and Umbral Ice (UI1-3).

        This function processes the DataFrame of elemental state changes to compute, for each buff
        key (e.g., "AF1", "AF2", "AF3", "UI1", "UI2", "UI3"), an n x 2 NumPy array. Each row in the
        array holds a timestamp and the next state change timestamp. If no changes are available for
        a given buff key, an array [[0, 0]] is assigned.

        Args:
            elemental_state_changes (pd.DataFrame): DataFrame containing elemental state changes with columns
                like "timestamp", "elemental_status_active", "n_stacks_active", etc.

        Returns:
            Dict[str, np.ndarray]: Dictionary mapping buff IDs ("AF1", "AF2", "AF3", "UI1", "UI2", "UI3")
                to a NumPy array of shape (n, 2) containing the start timestamps and their corresponding end times.
        """
        elemental_state_timings_df = elemental_state_changes.copy()

        # Get state end time
        elemental_state_timings_df.loc[:, "next_state_change_timestamp"] = (
            elemental_state_timings_df["timestamp"].shift(-1)
        )

        # Final state change timestamp is always null, just set to 15s,
        # maximum gauge change.
        last_index = elemental_state_timings_df.index[-1]
        elemental_state_timings_df.loc[last_index, "next_state_change_timestamp"] = (
            elemental_state_timings_df.loc[last_index, "timestamp"] + 15
        )

        # Easier to handle buff ID
        elemental_state_timings_df["buff_id"] = elemental_state_timings_df[
            "elemental_status_granted"
        ].replace(
            {"Astral Fire": "AF", "Umbral Ice": "UI"}
        ) + elemental_state_timings_df["n_stacks_granted"].astype(str)

        keys = ["AF1", "AF2", "AF3", "UI1", "UI2", "UI3"]
        elemental_state_times = {}

        # Set all gauge times
        for key in keys:
            subset = elemental_state_timings_df[
                elemental_state_timings_df["buff_id"] == key
            ]
            if not subset.empty:
                # Get an n x 2 array with columns: timestamp, next_state_change_timestamp.
                arr = (
                    subset[["timestamp", "next_state_change_timestamp"]]
                    .astype(int)
                    .to_numpy()
                )
            else:
                arr = np.array([[0, 0]])
            elemental_state_times[key] = arr
        return elemental_state_times

    def _enochian_times(self, elemental_state_changes: pd.DataFrame) -> np.ndarray:
        """
        Determine start and end timestamps for Enochian windows.

        This method identifies transitions into or out of an elemental state
        (i.e., from None to a state or from a state to None) using the provided
        DataFrame, then reshapes the timestamps into pairs representing the
        start and end times of Enochian windows.

        Args:
            elemental_state_changes (pd.DataFrame): Contains columns such as
                "timestamp", "elemental_status_active", and
                "elemental_status_granted". Each row details a change
                in elemental state.

        Returns:
            np.ndarray: A 2D NumPy array of shape (N, 2), where each row contains
            the start and end timestamps (both integers) of an Enochian window.
            If no transitions are found, an empty array is returned.
        """
        return (
            elemental_state_changes[
                elemental_state_changes["elemental_status_active"].isna()
                | elemental_state_changes["elemental_status_granted"].isna()
            ]["timestamp"]
            .astype(int)
            .to_numpy()
            .reshape(-1, 2)
        )

    def apply_blm_buffs(self, actions_df: pd.DataFrame) -> pd.DataFrame:
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
        initial_cols = actions_df.columns
        actions_df["enochian_multiplier"] = 1.0
        actions_df["elemental_state"] = None

        fire_ice_actions = self.fire_actions | self.ice_actions

        # Apply Astral Fire
        for elemental_level, time_bounds in self.elemental_state_times.items():
            elemental_betweens = list(
                actions_df["timestamp"].between(b[0], b[1], inclusive="right")
                for b in time_bounds
            )

            # Loop over all fire actions and apply
            for elemental_id in fire_ice_actions.keys():
                elemental_condition = disjunction(*elemental_betweens) & (
                    actions_df["abilityGameID"] == elemental_id
                )

                actions_df = self._apply_buffs(
                    actions_df, elemental_condition, elemental_level
                )

                # Column for elemental state, used for buff multiplication later
                actions_df.loc[elemental_condition, "elemental_state"] = elemental_level

        # Apply enochian
        # Patch 7.2 onwards, this is always active
        if self.patch_number >= 7.2:
            actions_df["buffs"].apply(lambda x: x + ["enochian"])
            actions_df["enochian_multiplier"] = self.enochian_buff

        # Pre-7.2 BLM where enochian status was tied to Astral Fire /
        # Umbral Ice being active
        else:
            # Exclude ticks, are snapshotted later
            no_tick = actions_df["tick"] != True

            # Loop over all enochian time bounds
            for elemental_level in self.enochian_times:
                enochian_bounds = actions_df["timestamp"].between(
                    elemental_level[0], elemental_level[1], inclusive="right"
                )
                # Update buff list
                actions_df.loc[enochian_bounds & no_tick, "buffs"] = actions_df[
                    "buffs"
                ].apply(lambda x: x + ["enochian"])
                # Enochian indicator
                actions_df.loc[enochian_bounds & no_tick, "enochian_multiplier"] *= (
                    self.enochian_buff
                )

            # Snapshot thunder ticks. Application and tick share the same packet ID
            thunder_tick_ids = (36986, 1003871, 36987, 1003872)
            actions_df.loc[
                actions_df["abilityGameID"].isin(thunder_tick_ids),
                ["buffs", "enochian_multiplier"],
            ] = (
                actions_df[actions_df["abilityGameID"].isin(thunder_tick_ids)]
                .groupby("packetID")[["buffs", "enochian_multiplier"]]
                .transform("first")
            )

        # Update all the action names
        actions_df["action_name"] = (
            actions_df["action_name"].str.split("-").str[0]
            + "-"
            + actions_df["buffs"].sort_values().str.join("_")
        )

        # Apply buff multipliers to everything
        # Set up action elemental types for damage multipliers
        actions_df.loc[
            actions_df["abilityGameID"].isin(self.fire_actions.keys()), "elemental_type"
        ] = "fire"
        actions_df.loc[
            actions_df["abilityGameID"].isin(self.ice_actions.keys()), "elemental_type"
        ] = "ice"

        # Multiply out elemental buff, depending on the state and action elemental type
        # Defaults to 1 if no dictionary match.
        actions_df["elemental_multiplier"] = actions_df.apply(
            lambda row: (
                self.astral_fire_stack_multiplier.get(row["elemental_type"], {}).get(
                    int(row["elemental_state"][-1]), 1
                )
            )
            if pd.notna(row["elemental_state"])
            and row["elemental_state"].startswith("AF")
            else (
                self.umbral_ice_stack_multiplier.get(row["elemental_type"], {}).get(
                    int(row["elemental_state"][-1]), 1
                )
            )
            if pd.notna(row["elemental_state"])
            and row["elemental_state"].startswith("UI")
            else 1,
            axis=1,
        )

        actions_df["multiplier"] *= (
            actions_df["enochian_multiplier"] * actions_df["elemental_multiplier"]
        )
        return actions_df[initial_cols]


if __name__ == "__main__":
    from crit_app.config import FFLOGS_TOKEN

    api_key = FFLOGS_TOKEN  # or copy/paste your key here
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    # BlackMageActions(headers, "HGACPMDRzwcFmYqv", 1, 2, 100, 0, 7.1)
    a = BlackMageActions(headers, "NFdBg9z8vWYHq7k1", 15, 306, 100, 0, 7.1)
    # Example with dropping enochian
    # BlackMageActions(headers, "HZNndMrBxj6ywL7z", 7, 4, 100, 0, 7.1)

    a.apply_blm_buffs(None)
