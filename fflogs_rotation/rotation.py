import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

from fflogs_rotation.bard import BardActions
from fflogs_rotation.black_mage import BlackMageActions
from fflogs_rotation.dragoon import DragoonActions
from fflogs_rotation.job_data.game_data import patch_times
from fflogs_rotation.machinist import MachinistActions
from fflogs_rotation.monk import MonkActions
from fflogs_rotation.ninja import NinjaActions
from fflogs_rotation.reaper import ReaperActions
from fflogs_rotation.rotation_jobs import (
    DarkKnightActions,
    PaladinActions,
    SamuraiActions,
)
from fflogs_rotation.viper import ViperActions
from ffxiv_stats import Rate

url = "https://www.fflogs.com/api/v2/client"


class FFLogsClient(object):
    """Responsible for FFLogs API calls."""

    def __init__(self, api_url: str = "https://www.fflogs.com/api/v2/client"):
        self.api_url = api_url

    def gql_query(
        self, headers, query: str, variables: dict, operation_name: str
    ) -> dict:
        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": operation_name,
        }
        response = requests.post(headers=headers, url=self.api_url, json=json_payload)
        response.raise_for_status()
        return response.json()


class ActionTable(FFLogsClient):
    """
    Processes FFXIV combat log data into action tables for damage analysis.

    Responsibilities:
      - Retrieve fight and damage data via an injected FFLogsClient (for easier testing)
      - Process fight timings (start/end/down time/phase) and expose them
      - Delegate job-specific mechanics to helper methods/classes
      - Transform raw events into a structured DataFrame
    """

    def __init__(
        self,
        headers: Dict[str, str],
        report_id: str,
        fight_id: int,
        job: str,
        player_id: int,
        crit_stat: int,
        dh_stat: int,
        determination: int,
        medication_amt: int,
        level: int,
        phase: int,
        damage_buff_table: pd.DataFrame,
        critical_hit_rate_buff_table: pd.DataFrame,
        direct_hit_rate_buff_table: pd.DataFrame,
        guaranteed_hits_by_action_table: pd.DataFrame,
        guaranteed_hits_by_buff_table: pd.DataFrame,
        encounter_phases,
        pet_ids: Optional[List[int]] = None,
        debug: bool = False,
    ) -> None:
        self.report_id = report_id
        self.fight_id = fight_id
        self.job = job
        self.player_id = player_id
        self.pet_ids = pet_ids
        self.level = level
        self.phase = phase
        self.critical_hit_stat = crit_stat
        self.direct_hit_stat = dh_stat
        self.determination = determination
        self.medication_amt = medication_amt
        self.debug = debug
        self.encounter_phases = encounter_phases

        super().__init__(api_url="https://www.fflogs.com/api/v2/client")

        # Fetch fight information and set timings
        self._fetch_fight_information(headers)
        # Fetch damage events from FFLogs
        self._fetch_damage_events(headers)

        # Patch (used for echo)
        self.patch_number = self.what_patch_is_it()

        # Buff tables filtered based on fight start time
        self._filter_buff_tables(
            damage_buff_table,
            critical_hit_rate_buff_table,
            direct_hit_rate_buff_table,
            guaranteed_hits_by_buff_table,
            guaranteed_hits_by_action_table,
        )

        self.ranged_cards = self.damage_buffs[
            self.damage_buffs["buff_name"].isin(["The Bole", "The Spire", "The Ewer"])
        ]["buff_id"].tolist()
        self.melee_cards = self.damage_buffs[
            self.damage_buffs["buff_name"].isin(
                ["The Arrow", "The Balance", "The Spear"]
            )
        ]["buff_id"].tolist()

        # Build initial actions DataFrame
        self.actions_df = self.create_action_df()
        # Apply job-specific mechanics
        self._apply_job_specifics(headers)

        # Final cleanup of actions DataFrame
        # Remove unpaired actions, which still count towards gauge generation
        if "unpaired" in self.actions_df.columns:
            self.actions_df = self.actions_df[self.actions_df["unpaired"] != True]
        self.actions_df = self.actions_df.reset_index(drop=True)

        # Apply the echo, if present
        if self.has_echo:
            self.apply_the_echo()

    def what_patch_is_it(self) -> float:
        """Map log start timestamp to its associated patch.

        Patches are used to to apply the correct potencies and job gauge mechanics.
        """
        for k, v in patch_times.items():
            if (self.fight_start_time >= v["start"]) & (
                self.fight_start_time <= v["end"]
            ):
                return k
        return 0.0

    def _fetch_fight_information(self, headers: Dict[str, str]) -> None:
        """
        Retrieves fight information from the FFLogs GraphQL API for the specified.

        fight and calls `_process_fight_data()` to set core attributes (e.g., encounter
        name, start/end times, echo). Modifies class state in-place.

        Args:
            headers (Dict[str, str]): HTTP headers for GraphQL querying, including
            authentication tokens.
        """
        fight_info_variables = {"code": self.report_id, "id": [self.fight_id]}

        response = self.gql_query(
            headers,
            self._fight_information_query(),
            fight_info_variables,
            "FightInformation",
        )
        self._process_fight_data(response, headers)

    def _fight_information_query(self) -> str:
        """Fight information GQL query string."""
        return """
        query FightInformation($code: String!, $id: [Int]!) {
            reportData {
                report(code: $code) {
                    startTime
                    # masterData { abilities { name gameID } }
                    table(fightIDs: $id, dataType: DamageDone)
                    fights(fightIDs: $id, translate: true) {
                        encounterID
                        kill
                        startTime
                        endTime
                        name
                        hasEcho
                        phaseTransitions { id startTime }
                    }
                    rankings(fightIDs: $id)
                }
            }
        }
        """

    def _fight_phase_downtime_query(self) -> str:
        """Query to get the downtime of a specific phase."""
        return """
        query PhaseTime($code: String!, $id: [Int]!, $start: Float!, $end: Float!) {
            reportData {
                report(code: $code) {
                    table(
                        fightIDs: $id
                        dataType: DamageDone
                        startTime: $start
                        endTime: $end
                    )
                }
            }
        }
        """

    def _damage_events_query(self) -> str:
        """Query to retrieve damage events."""
        return """
        query DpsActions(
            $code: String!
            $id: [Int]!
            $sourceID: Int!
            $startTime: Float!
            $endTime: Float!
        ) {
            reportData {
                report(code: $code) {
                    events(
                        fightIDs: $id
                        startTime: $startTime
                        endTime: $endTime
                        dataType: DamageDone
                        sourceID: $sourceID
				        useAbilityIDs: false                    
                        limit: 10000
                    ) {
                        data
                        nextPageTimestamp
                    }
                }
            }
        }
        """

    def _process_fight_data(self, response: dict, headers: Dict[str, str]) -> None:
        """
        Parses the fight data from the FFLogs API response, setting core attributes.

        such as encounter details, start/end times, and handling phase timings.
        Updates the class state to reflect whether the fight was a kill,
        whether echo was active, and any relevant phase/downtime offsets.

        Args:
            response (dict):
                The parsed JSON response from the FFLogs API containing report
                and fight data.
            headers (Dict[str, str]):
                HTTP headers used for further GraphQL queries, if needed
                for phase/downtime details.
        """
        report = response["data"]["reportData"]["report"]
        fight = report["fights"][0]
        self.fight_name = fight["name"]
        self.encounter_id = fight["encounterID"]
        self.has_echo = fight["hasEcho"]
        self.kill = fight["kill"]

        # Fight time variables
        self.report_start_time = report["startTime"]
        self.fight_start_time = self.report_start_time
        self.fight_end_time = self.report_start_time
        if self.kill and len(report["rankings"]) > 0:
            self.ranking_duration = report["rankings"]["data"][0]["duration"]
        else:
            self.ranking_duration = None

        # Phase info
        self.phase_information = fight["phaseTransitions"]

        # If user requested a specific phase, adjust start/end times
        if self.phase > 0:
            self.phase_start_time, self.phase_end_time = (
                self._fetch_phase_start_end_time(fight["endTime"])
            )
            phase_response = self._fetch_phase_downtime(headers)
            self.downtime = self._get_downtime(phase_response)

            self.fight_start_time += self.phase_start_time
            self.fight_end_time += self.phase_end_time
        else:
            self.downtime = self._get_downtime(response)
            self.phase_start_time = None
            self.phase_end_time = None
            self.fight_start_time += fight["startTime"]
            self.fight_end_time += fight["endTime"]

        self.fight_dps_time = (
            self.fight_end_time - self.fight_start_time - self.downtime
        ) / 1000

    def _fetch_phase_start_end_time(self, fight_end_time: int):
        """
        Determines the start and end timestamps (in milliseconds) for the requested phase.

        If the next phase exists, its start becomes the current phase's end. Otherwise,
        the phase end is set to the overall fight_end_time.

        Args:
            fight_end_time (int): The timestamp (ms) identifying the fight end.

        Returns:
            tuple[int, int]: (phase_start_time, phase_end_time), both in milliseconds.
            phase_start_time is extracted from self.phase_information where id == self.phase.
            phase_end_time is either the next phase start or fight_end_time.
        """
        phase_start_time = next(
            p["startTime"] for p in self.phase_information if p["id"] == self.phase
        )

        # Phase end = fight end if either:
        # - Final phase of the fight.
        # - Final phase of a pull with a wipe.
        if (
            self.phase < max(self.encounter_phases[self.encounter_id].keys())
            and len(self.phase_information) > self.phase
        ):
            phase_end_time = next(
                p["startTime"]
                for p in self.phase_information
                if p["id"] == self.phase + 1
            )
        else:
            phase_end_time = fight_end_time

        return phase_start_time, phase_end_time

    def _fetch_phase_downtime(self, headers: Dict[str, str]) -> dict:
        """Retrieves phase-specific timing data."""
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "start": self.phase_start_time,
            "end": self.phase_end_time,
        }
        return self.gql_query(
            headers, self._fight_phase_downtime_query(), variables, "PhaseTime"
        )

    def _get_downtime(self, response: dict) -> int:
        """Extracts downtime from the response, returning 0 if not present."""
        return response["data"]["reportData"]["report"]["table"]["data"].get(
            "downtime", 0
        )

    def _fetch_damage_events(self, headers: Dict[str, str]) -> None:
        """
        Query FFLogs API for damage events from a specific fight.

        Filters to player ID and any pet IDs, if present.

        Makes a GraphQL query to fetch damage events with:
        - Source filtering by job/player
        - Pagination support (10000 events per page)
        - Combat-only events

        The query returns raw damage events containing:
        - Timestamp of action
        - Action ID and name
        - Source and target IDs
        - Damage amount and type
        - Active buffs
        - Hit type (crit/direct hit)

        Args:
            headers (Dict[str, str]): FFLogs API headers containing:
                - Content-Type: application/json
                - Authorization: Bearer token

        Sets:
            self.actions (List[Dict]): List of raw damage events from the API
                Each event is a dict with fields like timestamp, type,
                sourceID, targetID, amount, etc.
        """
        self.actions = []

        source_ids = [self.player_id]
        if self.pet_ids is not None:
            source_ids += self.pet_ids

        for i in source_ids:
            variables = {
                "code": self.report_id,
                "id": [self.fight_id],
                "sourceID": i,
                # Need to switch back to relative timestamp
                # Time filtering is needed to ensure the correct phase
                "startTime": self.fight_start_time - self.report_start_time,
                "endTime": self.fight_end_time - self.report_start_time,
            }

            response = self.gql_query(
                headers, self._damage_events_query(), variables, "DpsActions"
            )
            self.actions.extend(
                response["data"]["reportData"]["report"]["events"]["data"]
            )
        pass

    def _filter_buff_tables(
        self,
        damage_buff_table: pd.DataFrame,
        crit_rate_table: pd.DataFrame,
        dh_rate_table: pd.DataFrame,
        guaranteed_buff_table: pd.DataFrame,
        guaranteed_action_table: pd.DataFrame,
    ) -> None:
        """Filter buff tables to the relevant patch."""
        # Here damage_buffs is left as a DataFrame while the others are converted into dicts
        self.damage_buffs = damage_buff_table[
            (damage_buff_table["valid_start"] <= self.fight_start_time)
            & (self.fight_start_time <= damage_buff_table["valid_end"])
        ]
        self.critical_hit_rate_buffs = (
            crit_rate_table[
                (crit_rate_table["valid_start"] <= self.fight_start_time)
                & (self.fight_start_time <= crit_rate_table["valid_end"])
            ]
            .set_index("buff_id")["rate_buff"]
            .to_dict()
        )
        self.direct_hit_rate_buffs = (
            dh_rate_table[
                (dh_rate_table["valid_start"] <= self.fight_start_time)
                & (self.fight_start_time <= dh_rate_table["valid_end"])
            ]
            .set_index("buff_id")["rate_buff"]
            .to_dict()
        )
        self.guaranteed_hit_type_via_buff = guaranteed_buff_table
        self.guaranteed_hit_type_via_action = guaranteed_action_table.set_index(
            "action_id"
        )["hit_type"].to_dict()

    def ast_card_buff(self, card_id):
        """
        Calculate buff strength and standardized ID for AST card buffs.

        AST cards provide either 3% or 6% damage buffs based on job role matching:
        - Ranged jobs get 6% from ranged cards, 3% from melee cards
        - Melee jobs get 6% from melee cards, 3% from ranged cards

        To standardize buff tracking, cards are mapped to:
        - card3: 3% damage buff (1.03 multiplier)
        - card6: 6% damage buff (1.06 multiplier)
        This allows more actions to be grouped together. For example, Midare with The Spear
        and Midare with the Arrow both sample the same distribution.

        Args:
            card_id: FFLogs ability ID for the card buff
                    e.g. "10003242" for The Balance

        Returns:
            Tuple containing:
            - str: Standardized card ID ("card3" or "card6")
            - float: Damage multiplier (1.03 or 1.06)
        """
        ranged_jobs = [
            "WhiteMage",
            "Sage",
            "Astrologian",
            "Scholar",
            "Summoner",
            "RedMage",
            "BlackMage",
            "Dancer",
            "Bard",
            "Machinist",
        ]
        melee_jobs = [
            "Ninja",
            "Samurai",
            "Monk",
            "Reaper",
            "Dragoon",
            "DarkKnight",
            "Gunbreaker",
            "Warrior",
            "Paladin",
        ]

        if (self.job in ranged_jobs and card_id in self.ranged_cards) or (
            self.job in melee_jobs and card_id in self.melee_cards
        ):
            card_strength = 6
        else:
            card_strength = 3
        return f"card{card_strength}", 1 + card_strength / 100

    def estimate_radiant_finale_strength(self, elapsed_time):
        """
        Estimate Radiant Finale buff strength based on fight duration/phase.

        Radiant Finale's buff strength depends on number of Codas collected,
        but this isn't directly available in FFLogs. We estimate it based on
        elapsed fight time:
        - Before 100s: Assume 1 Coda (2% buff)
        - After 100s: Assume 3 Codas (6% buff)

        Args:
            elapsed_time: Fight duration in seconds
                        Must be >= 0

        Returns:
            str: Standardized buff ID:
                - "RadiantFinale1": 2% buff from 1 Coda
                - "RadiantFinale3": 6% buff from 3 Codas

        Raises:
            ValueError: If elapsed_time < 0
        """
        if elapsed_time < 0:
            raise ValueError("elapsed_time must be non-negative")

        if (elapsed_time < 100) and (self.phase <= 1):
            return "RadiantFinale1"
        else:
            return "RadiantFinale3"

    def _compute_multiplier_table(
        self, actions_df: pd.DataFrame, damage_buffs: pd.DataFrame
    ) -> pd.DataFrame:
        """Compute the multiplier table for ground effects based on actions_df and damage_buffs."""
        df = actions_df.copy()
        df["str_buffs"] = df["buffs"].astype(str)

        unique_buff_sets = df.drop_duplicates(
            subset=["str_buffs", "multiplier"]
        ).sort_values(["str_buffs", "multiplier"])[["str_buffs", "buffs", "multiplier"]]
        unique_buff_sets["multiplier"] = unique_buff_sets.groupby("str_buffs")[
            "multiplier"
        ].ffill()
        unique_buff_sets = unique_buff_sets.drop_duplicates(subset=["str_buffs"])

        buff_strengths = (
            damage_buffs.drop_duplicates(subset=["buff_id", "buff_strength"])
            .set_index("buff_id")["buff_strength"]
            .to_dict()
        )

        remainder = unique_buff_sets[unique_buff_sets["multiplier"].isna()].copy()
        remainder.loc[:, "multiplier"] = (
            remainder["buffs"]
            .apply(lambda x: list(map(buff_strengths.get, x)))
            .apply(lambda x: np.prod([y for y in x if y is not None]) if x else None)
        )

        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            multiplier_table = pd.concat(
                [unique_buff_sets[~unique_buff_sets["multiplier"].isna()], remainder]
            )
        return multiplier_table

    def _update_actions_with_ground_effect(
        self,
        actions_df: pd.DataFrame,
        multiplier_table: pd.DataFrame,
        ground_effect_id: str,
    ) -> pd.DataFrame:
        """Merge multiplier values for ground effect actions and return an updated actions_df."""
        df = actions_df.copy()
        df["str_buffs"] = df["buffs"].astype(str)

        ground_ticks_actions = df[df["abilityGameID"] == ground_effect_id].copy()
        ground_ticks_actions = ground_ticks_actions.merge(
            multiplier_table[["str_buffs", "multiplier"]],
            on="str_buffs",
            how="left",
            suffixes=("_x", "_y"),
        )
        # If a multiplier already exists (multiplier_x), use that; otherwise fallback to multiplier_y.
        ground_ticks_actions["multiplier"] = ground_ticks_actions[
            "multiplier_x"
        ].combine_first(ground_ticks_actions["multiplier_y"])
        ground_ticks_actions.drop(
            columns=["multiplier_x", "multiplier_y"], inplace=True
        )

        # Combine the updated ground effect rows back into df
        df_updated = pd.concat(
            [df[df["abilityGameID"] != ground_effect_id], ground_ticks_actions]
        ).drop(columns=["str_buffs"])
        return df_updated.sort_values("elapsed_time")

    def estimate_ground_effect_multiplier(self, ground_effect_id: str) -> pd.DataFrame:
        """
        Estimate damage multipliers for ground effect abilities.

        Ground effects (like DRK's Salted Earth or SMN's Slipstream) need their
        multipliers estimated since FFLogs doesn't provide them directly.

        The estimation process:
        1. Match sets of buffs to known multipliers from other abilities
        2. For unmatched cases, calculate from damage_buff_table values

        Args:
            ground_effect_id: FFLogs ability ID for the ground effect
                            Must be a valid ID that exists in the log

        Returns:
            pd.DataFrame: Updated actions_df with estimated multipliers for the ground effect
                        Preserves original row order and indexes
        """
        # Check if the multiplier already exists for other actions
        # Unhashable string column of buffs, which allow duplicates to be dropped
        # Buffs are always ordered the same way
        multiplier_table = self._compute_multiplier_table(
            self.actions_df, self.damage_buffs
        )
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=FutureWarning)
            self.actions_df = self._update_actions_with_ground_effect(
                self.actions_df, multiplier_table, ground_effect_id
            )

    def guaranteed_hit_type_damage_buff(
        self,
        ability_id: str,
        buff_ids: List[str],
        multiplier: float,
        ch_rate_buff: float = 0.0,
        dh_rate_buff: float = 0.0,
    ) -> Tuple[float, int]:
        """
        Calculate damage multiplier and hit type for abilities with guaranteed critical/direct hits.

        acting under hit type buffs.

        Hit types:
        0 = Normal
        1 = Critical
        2 = Direct Hit
        3 = Critical Direct Hit

        Args:
            ability_id: FFLogs ability ID
            buff_ids: List of active buff IDs
            multiplier: Base damage multiplier before hit type effects
            ch_rate_buff: Critical hit rate increase from buffs [0.0-1.0]
            dh_rate_buff: Direct hit rate increase from buffs [0.0-1.0]

        Returns:
            tuple: (final_multiplier: float, hit_type: int)
                - final_multiplier: Damage multiplier after hit type effects
                - hit_type: Hit type code (0-3)

        Example:
            ```python
            # Check Bootshine under Brotherhood
            mult, hit = guaranteed_hit_type_damage_buff(
                "53", ["110"], 1.0, ch_rate_buff=0.1
            )
            print(f"Hit Type: {hit}, Multiplier: {mult}")
            ```
        """
        hit_type = 0
        r = Rate(self.critical_hit_stat, self.direct_hit_stat, level=self.level)

        # Check if a guaranteed hit type giving buff is present
        # and if if affects the current action

        valid_buff_and_action = self.guaranteed_hit_type_via_buff[
            self.guaranteed_hit_type_via_buff["buff_id"].isin(buff_ids)
            & (self.guaranteed_hit_type_via_buff["affected_action_id"] == ability_id)
        ]
        # And if it is affecting a relevant action
        if len(valid_buff_and_action) > 0:
            hit_type = valid_buff_and_action["hit_type"].iloc[0]
            valid_action = True
        else:
            valid_action = False

        # Now check if the ability has a guaranteed hit type regardless of buff
        if ability_id in self.guaranteed_hit_type_via_action.keys():
            valid_action = True
            hit_type = self.guaranteed_hit_type_via_action[ability_id]

        # Multiplier for guaranteed hit type
        if valid_action:
            multiplier *= r.get_hit_type_damage_buff(
                hit_type,
                buff_crit_rate=ch_rate_buff,
                buff_dh_rate=dh_rate_buff,
                determination=self.determination,
            )

        return multiplier, hit_type

    def apply_the_echo(self) -> None:
        """
        Apply The Echo damage bonus based on fight timestamp.

        The Echo is a multiplicative buff automatically applied to duties after they are no
        longer current content. The strength increases with newer patches:
        - 6.57: 10% damage increase (1.10x)
        - 6.58+: 15% damage increase (1.15x)

        This method:
        1. Determines Echo strength based on fight timestamp
        2. Multiplies all action damage by Echo multiplier
        3. Adds Echo buff to action names and buff lists

        Example:
            ```python
            # Fight with 10% Echo from patch 6.57
            action_table.apply_the_echo()
            print(action_table.actions_df["multiplier"].head())
            ```

        Raises:
            ValueError: If fight_start_time is not set
        """
        # Patch timestamp constants (Unix ms)
        PATCH_657_START = 1707818400000  # Feb 13, 2024
        PATCH_658_START = 1710849600000  # Mar 19, 2024

        # Echo buff constants
        ECHO_10_MULT = 1.10
        ECHO_15_MULT = 1.15
        ECHO_10_NAME = "echo10"
        ECHO_15_NAME = "echo15"

        if not hasattr(self, "fight_start_time"):
            raise ValueError("Fight start time must be set before applying Echo")

        # 6.57: 10% echo
        if PATCH_657_START <= self.fight_start_time <= PATCH_658_START:
            echo_strength = ECHO_10_MULT
            echo_buff = ECHO_10_NAME

        # 6.58+: 15% echo
        elif self.fight_start_time >= PATCH_658_START:
            echo_strength = ECHO_15_MULT
            echo_buff = ECHO_15_NAME

        self.actions_df["multiplier"] = round(
            self.actions_df["multiplier"] * echo_strength, 6
        )
        self.actions_df["action_name"] += f"_{echo_buff}"
        self.actions_df["buffs"].apply(lambda x: x.append(echo_buff))

    def create_action_df(
        self,
        medication_id: str = "1000049",
        medication_multiplier: float = 1.05,
        radiant_finale_id: str = "1002964",
    ) -> pd.DataFrame:
        """
        Transform FFLogs damage events into a structured DataFrame for analysis.

        Creates a standardized action table with:
        - Base action information (name, ID, timestamp)
        - Calculated hit type probabilities
        - Applied buffs and multipliers
        - Pet actions and DoT effects

        Args:
            medication_id: FFLogs ability ID for medication buff (default: "1000049")
            medication_multiplier: FFLogs approximates medication as a flat 5% multiplier.
            This is removed since ffxiv-stats more accurately models it as a main stat
            increase. (default: 1.05)
            radiant_finale_id: FFLogs ability ID for Radiant Finale (default: "1002964")

        Returns:
            pd.DataFrame with columns:
                - timestamp: Unix timestamp of action
                - elapsed_time: Seconds from start of fight
                - ability_name: Human readable action name
                - multiplier: Total damage multiplier
                - p_n/p_c/p_d/p_cd: Hit type probabilities
                - main_stat_add: Main stat increases
                - buffs: List of active buff IDs
        """

        # These columns are almost always here, there can be some additional columns
        # which are checked for, depending if certain actions are used
        action_df_columns = [
            "timestamp",
            "elapsed_time",
            "type",
            "sourceID",
            "targetID",
            "packetID",
            "abilityGameID",
            "ability_name",
            "buffs",
            "amount",
            "tick",
            "multiplier",
            "bonusPercent",
            "hitType",
            "directHit",
        ]

        # Unpaired actions have a cast begin but the damage does not go out
        # These will be filtered out later, but are included because unpaired
        # actions can still grant job gauge like Darkside
        actions_df = pd.DataFrame(self.actions)

        actions_df["ability_name"] = actions_df["ability"].apply(
            lambda x: x.get("name") if isinstance(x, dict) else None
        )
        actions_df["abilityGameID"] = actions_df["ability"].apply(
            lambda x: x.get("guid") if isinstance(x, dict) else None
        )
        actions_df.drop(columns="ability", inplace=True)

        if "unpaired" in actions_df.columns:
            action_df_columns.append("unpaired")

        if "directHit" not in actions_df.columns:
            actions_df["directHit"] = False
        # Only include player ID and any of their associated pet IDs

        if "tick" not in actions_df.columns:
            actions_df["tick"] = False

        if "bonusPercent" not in actions_df.columns:
            actions_df["bonusPercent"] = pd.NA
            actions_df["bonusPercent"] = actions_df["bonusPercent"].astype("Int64")

        # Damage over time/ground effect ticks
        if "tick" in actions_df.columns:
            dots_present = True
            damage_condition = (actions_df["type"] == "calculateddamage") | (
                (actions_df["type"] == "damage") & (actions_df["tick"] == True)
            )
        else:
            action_df_columns.remove("tick")
            dots_present = False
            damage_condition = actions_df["type"] == "calculateddamage"

        # Only keep the "prepares action" or dot ticks
        actions_df = actions_df[damage_condition]

        # Buffs column won't show up if no buffs are present, so make one with nans
        # Only really happens in a striking dummy scenario
        if "buffs" not in pd.DataFrame(self.actions).columns:
            actions_df["buffs"] = pd.NA
            actions_df["buffs"] = actions_df["buffs"].astype("object")

        # Time in seconds relative to the first second
        actions_df["elapsed_time"] = (
            actions_df["timestamp"] - actions_df["timestamp"].iloc[0]
        ) / 1000
        # Create proper
        actions_df["timestamp"] = actions_df["timestamp"] + self.report_start_time
        self.fight_start_time = actions_df["timestamp"].iloc[0]
        # Filter/rename columns
        actions_df = actions_df[action_df_columns]

        # Add (tick) to a dot tick so the base ability name for
        # application and ticks are distinct - e.g., Dia and Dia (tick)
        if dots_present:
            actions_df.loc[actions_df["tick"] == True, "ability_name"] = (
                actions_df["ability_name"] + " (tick)"
            )

        actions_df.loc[actions_df["sourceID"] != self.player_id, "ability_name"] += (
            " (Pet)"
        )

        actions_df["buffs"] = actions_df["buffs"].apply(
            lambda x: x[:-1].split(".") if not pd.isna(x) else []
        )
        actions_df = actions_df.reset_index(drop=True)

        # Start to handle hit type buffs + medication
        r = Rate(self.critical_hit_stat, self.direct_hit_stat, level=self.level)

        multiplier = actions_df["multiplier"].tolist()
        name = actions_df["ability_name"].tolist()

        buff_id = actions_df["buffs"].tolist()

        main_stat_adjust = [0] * len(actions_df)
        crit_hit_rate_mod = [0] * len(actions_df)
        direct_hit_rate_mod = [0] * len(actions_df)
        p = [0] * len(actions_df)

        # Loop actions to create adjustments to hit type rates rates/main stat
        # There are enough conditionals/looping over array columns that vectorization isn't feasible.
        for idx, row in actions_df.iterrows():
            b = row["buffs"]

            # Loop through buffs and do various things depending on the buff
            for b_idx, s in enumerate(set(b)):
                # Adjust critical/direct hit rate according to hit-type buffs
                if s in self.critical_hit_rate_buffs.keys():
                    crit_hit_rate_mod[idx] += self.critical_hit_rate_buffs[s]
                if s in self.direct_hit_rate_buffs.keys():
                    direct_hit_rate_mod[idx] += self.direct_hit_rate_buffs[s]

                # Medication is treated as a 5% damage bonus.
                # ffxiv_stats directly alters the main stat, so it must be divided out
                # Ground effects have multipliers of nan, and are unaffected either way.
                if s == medication_id:
                    main_stat_adjust[idx] += self.medication_amt
                    multiplier[idx] = round(multiplier[idx] / medication_multiplier, 6)

                # Radiant Finale has the same ID regardless of strength
                # A new ID is created for each buff strength.
                # Different Radiant Finale strengths will lead to different
                # 1-hit damage distributions.
                if s == radiant_finale_id:
                    buff_id[idx][b_idx] = self.estimate_radiant_finale_strength(
                        actions_df.iloc[idx]["elapsed_time"]
                    )

                # All AST cards are lumped as either 6% buff or 3% buff.
                # only do for pre-Dawntrail.
                if (self.patch_number < 7.0) & (
                    s in self.ranged_cards + self.melee_cards
                ):
                    buff_id[idx][b_idx] = self.ast_card_buff(s)[0]

            # Check if action has a guaranteed hit type, potentially under a hit type buff.
            # Get the hit type and new damage multiplier if hit type buffs were present.
            multiplier[idx], hit_type = self.guaranteed_hit_type_damage_buff(
                row["abilityGameID"],
                b,
                multiplier[idx],
                crit_hit_rate_mod[idx],
                direct_hit_rate_mod[idx],
            )
            # Create a unique action name based on the action + all buffs present
            if b != "":
                name[idx] = name[idx] + "-" + "_".join(sorted(buff_id[idx]))

            # Probability of each hit type, accounting for hit type buffs or
            # guaranteed hit types.
            # Hit type ignores hit type buff additions if they are present
            p[idx] = r.get_p(
                round(crit_hit_rate_mod[idx], 2),
                round(direct_hit_rate_mod[idx], 2),
                guaranteed_hit_type=hit_type,
            )

        # Assemble the action dataframe with updated values
        # Later we can groupby/count to create a rotation dataframe
        actions_df["multiplier"] = multiplier
        actions_df["action_name"] = name
        actions_df[["p_n", "p_c", "p_d", "p_cd"]] = pd.DataFrame(np.array(p))
        actions_df["main_stat_add"] = main_stat_adjust
        actions_df["l_c"] = r.crit_dmg_multiplier()
        actions_df["buffs"] = (
            actions_df["buffs"].sort_values().apply(lambda x: sorted(x))
        )
        return actions_df.reset_index(drop=True)

    def _apply_job_specifics(self, headers: Dict[str, str]) -> None:
        """Delegates job-specific transformations."""
        self.job_specifics = None

        if self.job == "DarkKnight":
            self.job_specifics = DarkKnightActions()
            self.estimate_ground_effect_multiplier(
                self.job_specifics.salted_earth_id,
            )
            self.actions_df = self.job_specifics.apply_drk_things(
                self.actions_df,
                self.player_id,
                self.pet_ids[0],
            )

        elif self.job == "Paladin":
            self.job_specifics = PaladinActions(
                headers, self.report_id, self.fight_id, self.player_id
            )
            self.actions_df = self.job_specifics.apply_pld_buffs(self.actions_df)
            pass

        # FIXME:
        elif self.job == "BlackMage":
            self.job_specifics = BlackMageActions(
                self.actions_df,
                headers,
                self.report_id,
                self.fight_id,
                self.player_id,
                self.level,
                self.phase,
                self.patch_number,
                self.phase,
            )
            self.actions_df = self.job_specifics.apply_blm_buffs(self.actions_df)
            self.actions_df = self.actions_df[
                self.actions_df["ability_name"] != "Attack"
            ]

        elif self.job == "Summoner":
            self.estimate_ground_effect_multiplier(
                1002706,
            )

        # FIXME: I think arm of the destroyer won't get updated but surely no one would use that in savage.
        elif self.job == "Monk":
            self.job_specifics = MonkActions(
                headers,
                self.report_id,
                self.fight_id,
                self.player_id,
                self.patch_number,
            )

            if self.patch_number < 7.0:
                self.actions_df = self.job_specifics.apply_endwalker_mnk_buffs(
                    self.actions_df
                )
            else:
                self.actions_df = self.job_specifics.apply_dawntrail_mnk_buffs(
                    self.actions_df
                )

            self.actions_df = self.job_specifics.apply_bootshine_autocrit(
                self.actions_df,
                self.critical_hit_stat,
                self.direct_hit_stat,
                self.critical_hit_rate_buffs,
                self.level,
            )
            pass

        elif self.job == "Ninja":
            self.job_specifics = NinjaActions(
                headers,
                self.report_id,
                self.fight_id,
                self.player_id,
                self.patch_number,
            )
            self.actions_df = self.job_specifics.apply_ninja_buff(self.actions_df)
            pass

        elif self.job == "Dragoon":
            self.job_specifics = DragoonActions(
                headers,
                self.report_id,
                self.fight_id,
                self.player_id,
                self.patch_number,
            )
            # if self.patch_number >= 7.0:
            #     self.actions_df = self.job_specifics.apply_dawntrail_life_of_the_dragon_buffs(
            #         self.actions_df
            #     )
            if self.patch_number < 7.0:
                self.actions_df = (
                    self.job_specifics.apply_endwalker_combo_finisher_potencies(
                        self.actions_df
                    )
                )

        elif self.job == "Reaper":
            self.job_specifics = ReaperActions(
                headers, self.report_id, self.fight_id, self.player_id
            )
            self.actions_df = self.job_specifics.apply_enhanced_buffs(self.actions_df)
            pass

        elif self.job == "Viper":
            self.job_specifics = ViperActions(
                headers, self.report_id, self.fight_id, self.player_id
            )
            self.actions_df = self.job_specifics.apply_viper_buffs(self.actions_df)

        elif self.job == "Samurai":
            self.job_specifics = SamuraiActions(
                headers, self.report_id, self.fight_id, self.player_id
            )
            self.actions_df = self.job_specifics.apply_enhanced_enpi(self.actions_df)

        elif self.job == "Machinist":
            # wildfire can't crit...
            self.actions_df.loc[
                self.actions_df["abilityGameID"] == 1000861,
                ["p_n", "p_c", "p_d", "p_cd"],
            ] = [1.0, 0.0, 0.0, 0.0]

            self.estimate_ground_effect_multiplier(
                1000861,
            )
            self.actions_df = self.actions_df.reset_index(drop=True)
            self.job_specifics = MachinistActions(
                headers, self.report_id, self.fight_id, self.player_id
            )
            self.actions_df = self.job_specifics.apply_mch_potencies(self.actions_df)

        elif self.job == "Bard":
            self.job_specifics = BardActions()
            self.actions_df = self.job_specifics.estimate_pitch_perfect_potency(
                self.actions_df
            )
            if self.patch_number >= 7.0:
                self.actions_df = self.job_specifics.estimate_radiant_encore_potency(
                    self.actions_df
                )
        else:
            self.job_specifics = None

        # Filter out Auto Attacks for casters
        if self.job in (
            "Pictomancer",
            "RedMage",
            "Summoner",
            "Astrologian",
            "WhiteMage",
            "Sage",
            "Scholar",
        ):
            self.actions_df = self.actions_df[
                self.actions_df["ability_name"].str.lower() != "attack"
            ]


class RotationTable(ActionTable):
    """
    Creates gold-level rotation tables for damage distribution analysis.

    Aggregates raw action data into rotation statistics by:
    - Grouping actions by name and counting occurrences
    - Mapping actions to correct potencies
    - Handling job mechanics (combos, positionals, buffs)
    - Categorizing damage types (direct, DoT, pet)

    Inherits from ActionTable which handles raw combat log processing.

    Attributes:
        rotation_df (pd.DataFrame): Aggregated rotation statistics
        potency_table (pd.DataFrame): Action potency mappings
    """

    def __init__(
        self,
        headers: Dict[str, str],
        report_id: str,
        fight_id: int,
        job: str,
        player_id: int,
        crit_stat: int,
        dh_stat: int,
        determination: int,
        medication_amt: int,
        level: int,
        phase: int,
        damage_buff_table: pd.DataFrame,
        critical_hit_rate_buff_table: pd.DataFrame,
        direct_hit_rate_buff_table: pd.DataFrame,
        guaranteed_hits_by_action_table: pd.DataFrame,
        guaranteed_hits_by_buff_table: pd.DataFrame,
        potency_table: pd.DataFrame,
        encounter_phases,
        pet_ids: Optional[List[int]] = None,
        excluded_enemy_ids: Optional[List[int]] = None,
        debug: bool = False,
    ) -> None:
        """
        Initialize RotationTable for damage distribution analysis.

        Args:
            headers: FFLogs API headers with authorization token
            report_id: FFLogs report ID (e.g. "gbkzXDBTFAQqjxpL")
            fight_id: Fight ID within report
            job: Job name in PascalCase (e.g. "DarkKnight")
            player_id: FFLogs player ID
            crit_stat: Critical hit stat value
            dh_stat: Direct hit stat value
            determination: Determination stat value
            medication_amt: Main stat increase from medication
            level: Player level (90 max)
            phase: Fight phase number (0 for full fight)
            damage_buff_table: DataFrame of damage buff timings/values
            critical_hit_rate_buff_table: DataFrame of crit rate buff timings
            direct_hit_rate_buff_table: DataFrame of DH rate buff timings
            guaranteed_hits_by_action_table: DataFrame mapping actions to hit types
            guaranteed_hits_by_buff_table: DataFrame mapping buffs to hit types
            potency_table: DataFrame mapping actions to potencies
            pet_ids: Optional list of pet actor IDs
            excluded_enemy_ids: Target IDs of enemies to exclude from rotation_df.
            debug: Enable debug logging

        Example:
            ```python
            # Initialize rotation table for analysis
            rotation = RotationTable(
                headers=api_headers,
                report_id="abc123",
                fight_id=1,
                job="Samurai",
                player_id=1,
                crit_stat=2800,
                dh_stat=1600,
                determination=2000,
                medication_amt=165,
                level=90,
                phase=0,
                damage_buff_table=buff_df,
                critical_hit_rate_buff_table=crit_df,
                direct_hit_rate_buff_table=dh_df,
                guaranteed_hits_by_action_table=action_hits_df,
                guaranteed_hits_by_buff_table=buff_hits_df,
                potency_table=potency_df
            )
            print(rotation.rotation_df.head())
            ```
        """
        super().__init__(
            headers,
            report_id,
            fight_id,
            job,
            player_id,
            crit_stat,
            dh_stat,
            determination,
            medication_amt,
            level,
            phase,
            damage_buff_table,
            critical_hit_rate_buff_table,
            direct_hit_rate_buff_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            encounter_phases,
            pet_ids,
            debug,
        )
        self.excluded_enemy_ids = excluded_enemy_ids

        self._setup_potency_table(potency_table)
        self.rotation_df = self.make_rotation_df(self.actions_df)

        #
        if excluded_enemy_ids is None:
            self.filtered_actions_df = self.actions_df.copy()
        else:
            self.filtered_actions_df = self.actions_df.copy()[
                ~self.actions_df["targetID"].isin(self.excluded_enemy_ids)
            ]

        mismatched_actions = set(self.rotation_df.base_action) - set(
            self.actions_df.ability_name
        )
        if len(mismatched_actions) > 0:
            raise IndexError(
                f"Error matching the following actions with rotation: {', '.join(mismatched_actions)}"
            )
        pass

    def _setup_potency_table(self, potency_table: pd.DataFrame) -> None:
        """
        Filters the provided potency table based on job, level, and valid time range,.

        then converts the `potency_falloff` column into a list of numeric values.

        The method filters the table to retain only rows that:
        - Have a `valid_start` less than or equal to `fight_start_time`
        - Have a `valid_end` greater than or equal to `fight_start_time`
        - Match the current job and level

        Any missing `potency_falloff` entries are filled with `"1."` before splitting
        the string on semicolons to create lists of values.

        Args:
            potency_table (pd.DataFrame):
                Original DataFrame containing columns:
                - `valid_start`/`valid_end`: timestamps indicating when the row is valid
                - `job`: job name
                - `level`: required job level
                - `potency_falloff`: string of semicolon-separated falloff values
        """
        self.potency_table = potency_table[
            (potency_table["valid_start"] <= self.fight_start_time)
            & (self.fight_start_time <= potency_table["valid_end"])
            & (potency_table["job"] == self.job)
            & (potency_table["level"] == self.level)
        ]

        self.potency_table.loc[
            self.potency_table["potency_falloff"].isna(), "potency_falloff"
        ] = "1."
        self.potency_table.loc[:, "potency_falloff"] = self.potency_table[
            "potency_falloff"
        ].apply(lambda x: x.split(";"))

    def _filter_actions_by_timestamp(
        self,
        actions_df: pd.DataFrame,
        t_start_clip: float = None,
        t_end_clip: float = None,
        return_clipped: bool = False,
        clipped_portion: str = "end",
    ) -> pd.DataFrame:
        """Filter an actions_dataframe to a portion of the fight for analysis.

        Used primarily by party analyses to analyze kill time by clipping out
        end segments of the fight.

        Args:
            actions_df (pd.DataFrame): _description_
            t_start_clip (float, optional): _description_. Defaults to None.
            t_end_clip (float, optional): _description_. Defaults to None.
            return_clipped (bool, optional): _description_. Defaults to False.
            clipped_portion (str, optional): _description_. Defaults to "end".

        Raises:
            ValueError: _description_

        Returns:
            pd.DataFrame: _description_
        """
        if t_end_clip is None:
            t_end = self.fight_end_time
        else:
            t_end = self.fight_end_time - (t_end_clip * 1000)

        if t_start_clip is None:
            t_start = self.fight_start_time
        else:
            t_start = self.fight_start_time + (t_start_clip * 1000)

        # Count how many times each action is performed

        if return_clipped:
            if clipped_portion == "end":
                actions_df = actions_df[
                    actions_df["timestamp"].between(
                        t_end, self.fight_end_time, inclusive="right"
                    )
                ]
            elif clipped_portion == "middle":
                actions_df = actions_df[actions_df["timestamp"].between(t_start, t_end)]

            elif clipped_portion == "start":
                actions_df = actions_df[
                    actions_df["timestamp"].between(
                        self.fight_start_time, t_start, inclusive="left"
                    )
                ]
            else:
                raise ValueError(
                    f"Accepted values of `clipped_portion` are 'start', 'middle', and 'end', not {clipped_portion}"
                )
        else:
            actions_df = actions_df[actions_df["timestamp"].between(t_start, t_end)]

        return actions_df

    def _normalize_hit_types(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove hit type damage bonuses to get base damage values.

        Reverses damage multipliers from critical hits and direct hits:
        - Critical hits: Divides by crit damage multiplier (l_c/1000)
        - Direct hits: Divides by 1.25 (25% bonus)

        Args:
            actions_df: DataFrame containing columns:
                - amount: Raw damage amount
                - hitType: Hit type code (2 = crit)
                - directHit: Boolean for direct hit
                - l_c: Critical hit damage multiplier

        Returns:
            DataFrame with additional column:
                - base_damage: Damage normalized to remove hit type bonuses

        Example:
            ```python
            # Normalize 5000 damage crit direct hit to ~3571 base damage
            df = normalize_hit_types(actions_df)
            print(df["base_damage"].iloc[0])  # 3571.4
            ```
        """
        # Constants
        # 1 = not critical hit, 2 = critical (direct) hit
        CRIT_HIT_TYPE = 2
        DIRECT_HIT_MULT = 1.25

        actions_df["base_damage"] = actions_df["amount"].astype(float)

        # Remove crit damage bonus
        actions_df.loc[actions_df["hitType"] == CRIT_HIT_TYPE, "base_damage"] /= (
            actions_df.loc[actions_df["hitType"] == CRIT_HIT_TYPE, "l_c"] / 1000
        )

        # Remove direct hit bonus
        actions_df.loc[actions_df["directHit"] == True, "base_damage"] /= (
            DIRECT_HIT_MULT
        )

        return actions_df

    def _group_multi_target_hits(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Group multi-target hits by packet ID and find highest base damage.

        Actions hitting multiple targets share the same packet ID in FFLogs.
        Finding max base damage per packet ID identifies the primary target
        for calculating damage falloff on secondary targets.

        Args:
            actions_df: DataFrame containing:
                - packetID: FFLogs packet identifier
                - base_damage: Normalized damage amount

        Returns:
            DataFrame with columns:
                - packetID: Original packet ID
                - max_base: Highest base damage for that packet ID

        Notes:
            - DoT ticks and ground effects are excluded since their AoE versions
            have no damage falloff
            - Copy is returned to avoid modifying original DataFrame
        """
        # Filter out ticks because application damage + tick have same packet ID
        # Only an issue for Dia, where application pot = tick pot.
        # Caused fractional potency falloff condition to fail later.
        return (
            actions_df[actions_df["tick"] != True]
            .groupby("packetID")
            .max("base_damage")
            .reset_index()
            .rename(columns={"base_damage": "max_base"})[["packetID", "max_base"]]
        ).copy()

    def _potency_falloff_fraction(
        self, actions_df: pd.DataFrame, max_multi_hit: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate potency falloff fractions for multi-target abilities.

        Compares each hit's base damage to the highest damage for that packet ID
        to determine falloff ratios. DoTs and ground effects are set to 1.0 since
        their AoE versions have no falloff.

        Args:
            actions_df: DataFrame containing:
                - packetID: FFLogs packet identifier
                - base_damage: Normalized damage amount
                - tick: Boolean for DoT/ground effect ticks
            max_multi_hit: DataFrame containing:
                - packetID: FFLogs packet identifier
                - max_base: Maximum base damage for that packet

        Returns:
            DataFrame with additional column:
                - fractional_potency: Ratio of hit damage to max damage [0.0-1.0]

        Example:
            ```python
            # Calculate falloff for Fat Edge of Darkness hits
            df = potency_falloff_fraction(actions_df, max_hits_df)
            print(df["fractional_potency"])  # [1.0, 0.75, 0.5, ...]
            ```
        """

        actions_df = actions_df.merge(max_multi_hit, how="left", on="packetID")

        # Calculate falloff fractions
        actions_df["fractional_potency"] = (
            actions_df["base_damage"] / actions_df["max_base"]
        )

        # DoTs and ground effects have no falloff
        actions_df.loc[
            (actions_df["tick"] == True) | (actions_df["packetID"].isna()),
            "fractional_potency",
        ] = 1
        return actions_df

    def _match_potency_falloff(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Match actual potency falloff values to expected values from potency table.

        Due to FFXIV's ±5% damage variance, matches falloff values within 0.1
        of expected values from potency table. No abilities have falloff values
        within 10% of each other, preventing overlap.

        Args:
            actions_df: DataFrame containing:
                - abilityGameID: FFLogs ability identifier
                - fractional_potency: Calculated damage falloff ratio
                - elapsed_time: Time from fight start
                - packetID: FFLogs packet identifier
                - amount: Raw damage amount

        Returns:
            DataFrame with additional columns:
                - matched_falloff: Matched potency falloff value
                - ability_id: Mapped ability ID

        Example:
            ```python
            # Match Fat Edge of Darkness falloff values
            df = match_potency_falloff(actions_df)
            print(df["matched_falloff"])  # [1.0, 0.75, 0.5]
            ```
        """
        exploded_potencies = self.potency_table.explode("potency_falloff")[
            ["ability_id", "potency_falloff"]
        ]
        exploded_potencies["potency_falloff"] = exploded_potencies[
            "potency_falloff"
        ].astype(float)

        actions_df = actions_df.merge(
            exploded_potencies,
            left_on="abilityGameID",
            right_on="ability_id",
            how="left",
        )

        actions_df["potency_falloff_diff"] = (
            actions_df["fractional_potency"] - actions_df["potency_falloff"]
        ).abs()

        # Filter down to matches
        actions_df = actions_df[actions_df["potency_falloff_diff"] < 0.1]
        actions_df = actions_df.drop(columns="potency_falloff_diff").rename(
            columns={"potency_falloff": "matched_falloff"}
        )
        return actions_df.drop_duplicates(
            subset=["elapsed_time", "packetID", "amount", "matched_falloff"]
        )

    def _count_actions(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Groups actions by their distinguishing columns and counts how many times each.

        unique action occurs, then merges the result with the potency table.

        Steps:
        1. Creates a string representation of buffs in `buff_str` (including matched falloff).
        2. Excludes specified enemy IDs (`excluded_enemy_ids`).
        3. Filters out actions with zero damage.
        4. Fills NaN values in `bonusPercent` with -1.
        5. Groups by multiple columns that affect action uniqueness and counts occurrences.
        6. Merges grouped DataFrame with the potency table to retrieve potency info.
        7. Restores buffs to a list in `buff_list`.

        Args:
            actions_df (pd.DataFrame):
                DataFrame of parsed combat actions containing columns such as:
                - "buffs": Buff identifiers
                - "matched_falloff": Action potency falloff
                - "amount": Damage amount
                - "bonusPercent": Any bonus potency percentage
                - Other columns required for grouping

        Returns:
            pd.DataFrame:
                An aggregated DataFrame representing each unique action (by buffs,
                falloff, combo state, etc.), including a count of how many times
                the action occurred, tied to its potency data.
        """
        # Lists are unhashable, so make as an ordered string.
        actions_df["buff_str"] = (
            actions_df["buffs"].sort_values().apply(lambda x: sorted(x)).str.join(".")
        )
        # Need to add potency falloff so counting is correctly done later.
        actions_df["buff_str"] += "." + actions_df["matched_falloff"].astype(str)

        # Exclude any enemies in excluded_enemy_ids
        # ex: crystals of darkness in FRU
        if self.excluded_enemy_ids is not None:
            actions_df = actions_df[
                ~actions_df["targetID"].isin(self.excluded_enemy_ids)
            ]

        # Filter out any actions which do no damage.
        # This is currently only observed for DoT ticks occurring
        # on a dead, castlocked boss.
        # E.g, FRU p4 killed before CT will be castlocked for akh morn cast
        actions_df = actions_df[actions_df["amount"] > 0]

        # And you cant value count nans
        actions_df["bonusPercent"] = actions_df["bonusPercent"].fillna(-1)

        # Count actions grouping by all columns which change the underlying distribution
        group_by_columns = [
            "action_name",
            "abilityGameID",
            "bonusPercent",
            "buff_str",
            "p_n",
            "p_c",
            "p_d",
            "p_cd",
            "multiplier",
            "l_c",
            "main_stat_add",
            "matched_falloff",
        ]

        # Count actions to make a rotation DF
        # Also merge to the potency table to get the potency
        # and is later used to determine combo/positional
        rotation_df = (
            actions_df[group_by_columns]
            .value_counts()
            .reset_index()
            .merge(self.potency_table, left_on="abilityGameID", right_on="ability_id")
            .rename(
                columns={
                    "count": "n",
                    "multiplier": "buffs",
                    "ability_name": "base_action",
                }
            )
        )

        # Buffs go back to a list
        rotation_df["buff_list"] = rotation_df["buff_str"].str.split(".")
        return rotation_df

    def _apply_potency_priority(self, rotation_df: pd.DataFrame) -> pd.DataFrame:
        """
        Some jobs can have multiple potencies for the same action, depending on whether.

        certain buffs (identified by `buff_id`) are present. This produces multiple rows
        in the potency table, each with a different `buff_id`. The correct potency must
        be selected based on which buffs actually occurred.

        The following priority is used to match `buff_id` against `buff_list`:
        - Highest priority (2): `buff_id` is in `buff_list`
        - Medium priority (1): `buff_id` is `NaN` (no buff)
        - Lowest priority (0): `buff_id` is not `NaN` but is absent from `buff_list`

        For example, a Paladin's Holy Spirit can be un-buffed, buffed by Requiescat,
        or buffed by Divine Might, each having different potencies.

        Returns:
            pd.DataFrame: The input DataFrame with a new `potency_priority` column.
            The original DataFrame is also mutated in-place.
        """

        def buff_id_match(buff_id, buff_list):
            if buff_id in buff_list:
                return 2
            elif pd.isna(buff_id):
                return 1
            else:
                return 0

        rotation_df["potency_priority"] = rotation_df.apply(
            lambda x: buff_id_match(x["buff_id"], x["buff_list"]), axis=1
        )
        return rotation_df

    def _apply_bonus_potency(
        self, rotation_df: pd.DataFrame, bonus_type: str
    ) -> pd.DataFrame:
        """
        Updates the `potency` column for combo, positional, or combo_positional.

        actions based on matching the `bonusPercent` column value to the required
        `bonus_type` amount. The action name is also appended with `_bonus_type`.

        Args:
            rotation_df (pd.DataFrame):
                DataFrame containing action rows, including columns for:
                `bonusPercent`, `combo_bonus`, `combo_potency`, `positional_bonus`,
                `positional_potency`, etc. The `potency` column will be modified
                when the bonus is met.
            bonus_type (str):
                One of `combo`, `positional`, or `combo_positional`, indicating
                which bonus to check for.

        Raises:
            ValueError:
                If the bonus_type is not one of the recognized bonus types.

        Returns:
            pd.DataFrame:
                Returns the same DataFrame with updated `potency` values and
                `action_name` strings for rows that meet the specified bonus criteria.
                The original DataFrame is also mutated in-place.
        """
        if bonus_type not in ("combo", "positional", "combo_positional"):
            raise ValueError("Incorrect bonus_type")

        bonus_col_name = bonus_type + "_bonus"
        potency_col_name = bonus_type + "_potency"

        # Update potency where bonus is satisfied.
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df[bonus_col_name], "potency"
        ] = rotation_df[potency_col_name]

        # Update the name where the bonus is satisfied.
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df[bonus_col_name], "action_name"
        ] += f"_{bonus_type}"

        return rotation_df

    def _take_highest_priority_potency(self, rotation_df: pd.DataFrame) -> pd.DataFrame:
        """
        Selects the highest priority potency value from a set of actions.

        This method sorts the actions by a predefined list of columns and then groups
        them by a subset of these columns. It takes the first row in each group, which
        corresponds to the highest priority potency value.

        Args:
            rotation_df (pd.DataFrame): DataFrame containing action data, including
                columns for action name, ability ID, number of occurrences, buffs,
                hit type probabilities, main stat additions, and potency priority.

        Returns:
            pd.DataFrame: DataFrame with the highest priority potency value for each
                unique action, grouped by the specified columns.
        """
        sort_list = [
            "base_action",
            "abilityGameID",
            "n",
            "buff_str",
            "p_n",
            "p_c",
            "p_d",
            "p_cd",
            "buffs",
            "main_stat_add",
            "potency_priority",
        ]

        group_by_list = sort_list[:-1] + ["bonusPercent"]

        # Sort by these columns to get everything in the correct order
        # Do a groupby-head operation to get the first column in the group
        # Note it include bonus percent now
        rotation_df = (
            rotation_df.sort_values(sort_list, ascending=False)
            .groupby(group_by_list)
            .head(1)
        )
        return rotation_df

    def make_rotation_df(
        self,
        actions_df: pd.DataFrame,
        t_end_clip: Optional[float] = None,
        t_start_clip: Optional[float] = None,
        return_clipped: bool = False,
        clipped_portion: str = "end",
    ) -> Optional[pd.DataFrame]:
        """
        Create rotation DataFrame by aggregating actions within a time window.

        Processes raw combat actions into standardized rotation format by:
        1. Filtering to specified time window
        2. Processing multi-target hits
        3. Applying potency rules (combos, positionals)
        4. Grouping and counting actions
        5. Building final rotation table

        Args:
            actions_df: DataFrame of raw combat actions
            t_end_clip: Seconds to clip from fight end (None = no clip)
            t_start_clip: Seconds to clip from fight start (None = no clip)
            return_clipped: Return clipped portion instead of main window
            clipped_portion: Which portion to return if return_clipped=True:
                - "start": Return clipped start portion
                - "middle": Return middle window
                - "end": Return clipped end portion

        Returns:
            DataFrame with columns:
                - action_name: Full action name with modifiers
                - base_action: Original action name
                - n: Number of occurrences
                - p_n/p_c/p_d/p_cd: Hit type probabilities
                - buffs: Active damage buffs
                - l_c: Crit damage multiplier
                - main_stat_add: Added main stat
                - potency: Final potency value
                - damage_type: Action damage category
            Returns None if filtered window contains no actions

        Example:
            ```python
            # Get rotation excluding last 30s
            df = make_rotation_df(actions_df, t_end_clip=30)

            # Get just the last 30s
            df = make_rotation_df(actions_df, t_end_clip=30,
                                return_clipped=True)
            ```
        """
        actions_df = actions_df.copy()
        actions_df = self._filter_actions_by_timestamp(
            actions_df, t_start_clip, t_end_clip, return_clipped, clipped_portion
        )

        # If the DataFrame is empty, set the rotation DF as none type
        if len(actions_df) == 0:
            return None

        # Now check for multi-target actions and identify any associated potency falloffs
        # Limitations:
        # - Multi target where one target is castlocked and doesn't take damage.

        # First, undo damage bonuses from crit/direct hits
        actions_df = self._normalize_hit_types(actions_df)
        # PacketID is used to group hits together and sort damage falloff
        max_multi_hit = self._group_multi_target_hits(actions_df)
        # Assign and match potency falloff
        actions_df = self._potency_falloff_fraction(actions_df, max_multi_hit)
        actions_df = self._match_potency_falloff(actions_df)
        actions_df["action_name"] += "_" + actions_df["matched_falloff"].astype(str)

        # Count actions to determine the rotation
        # Actions are different if they sample a unique 1-hit distribution
        # Many factors influence this including:
        # - buffs (damage and hit type)
        # - combo bonus
        # - positionals
        # - potency falloff
        # - potions
        # - job-specific mechanics like gauge
        rotation_df = self._count_actions(actions_df)

        # Now determine potencies
        # Determine potency priority
        rotation_df = self._apply_potency_priority(rotation_df)

        # Check if action was a combo, positional, or combo + positional was satisfied
        # Also update the action name accordingly
        rotation_df["potency"] = rotation_df["base_potency"]

        # Combo bonus
        rotation_df = self._apply_bonus_potency(rotation_df, "combo")

        # Positional bonus
        rotation_df = self._apply_bonus_potency(rotation_df, "positional")

        # Combo bonus and positional bonus
        rotation_df = self._apply_bonus_potency(rotation_df, "combo_positional")

        rotation_df = self._take_highest_priority_potency(rotation_df)
        # Now that all correct potencies have been assigned,
        # Multiply by damage falloff
        rotation_df["potency"] = (
            rotation_df["potency"] * rotation_df["matched_falloff"]
        ).astype(int)

        # Select final columns, sort, and return
        rotation_df = rotation_df[
            [
                "action_name",
                "base_action",
                "n",
                "p_n",
                "p_c",
                "p_d",
                "p_cd",
                "buffs",
                "l_c",
                "main_stat_add",
                "potency",
                "damage_type",
            ]
        ]

        return rotation_df.sort_values(
            ["base_action", "damage_type", "n"], ascending=[True, True, False]
        )


if __name__ == "__main__":
    from crit_app.config import FFLOGS_TOKEN
    from crit_app.job_data.encounter_data import encounter_phases
    from fflogs_rotation.job_data.data import (
        critical_hit_rate_table,
        damage_buff_table,
        direct_hit_rate_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        potency_table,
    )

    api_key = FFLOGS_TOKEN  # or copy/paste your key here
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    # fflogs_client = FFLogsClient()
    # ActionTable(
    #     # fflogs_client,
    #     headers,
    #     "2p4VBGN9MDn7ZaC6",
    #     7,
    #     "Pictomancer",
    #     15,
    #     3090,
    #     1781,
    #     2585,
    #     392,
    #     100,
    #     0,
    #     damage_buff_table,
    #     critical_hit_rate_table,
    #     direct_hit_rate_table,
    #     guaranteed_hits_by_action_table,
    #     guaranteed_hits_by_buff_table,
    #     encounter_phases,
    # )

    # RotationTable(
    #     # fflogs_client,
    #     headers,
    #     "vNg4jJ1KMF9mt23q",
    #     104,
    #     "DarkKnight",
    #     422,
    #     2591,
    #     2367,
    #     2745,
    #     392,
    #     100,
    #     0,
    #     damage_buff_table,
    #     critical_hit_rate_table,
    #     direct_hit_rate_table,
    #     guaranteed_hits_by_action_table,
    #     guaranteed_hits_by_buff_table,
    #     potency_table,
    #     encounter_phases,
    #     pet_ids=[432],
    # )

    RotationTable(
        # fflogs_client,
        headers,
        "ZfnF8AqRaBbzxW3w",
        5,
        "Machinist",
        20,
        3174,
        1542,
        2310,
        392,
        100,
        5,
        damage_buff_table,
        critical_hit_rate_table,
        direct_hit_rate_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        potency_table,
        encounter_phases,
        [33],
    )
