import json
from typing import Any, Dict, List, Optional, Tuple

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


class ActionTable(object):
    """
    Processes FFXIV combat log data into action tables for damage analysis.

    Handles parsing FFLogs data, applying buffs and combat mechanics, and creating
    standardized action tables for further analysis.

    The transformation process follows a medallion pattern:
    - Bronze: Raw damage event payload from FFLogs API
    - Silver: Processed action table
    - Gold: Aggregated rotation table
    """

    def __init__(
        self,
        headers: Dict[str, str],
        report_id: str,
        fight_id: str,
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
        pet_ids: Optional[List[int]] = None,
        debug: bool = False,
    ) -> None:
        """
        Initialize ActionTable instance.

        Args:
            headers: FFLogs API headers
            report_id: FFLogs report ID (e.g. "gbkzXDBTFAQqjxpL")
            fight_id: Fight ID within report (e.g. 4)
            job: Job name in PascalCase (e.g. "DarkKnight")
            player_id: FFLogs player ID
            crit_stat: Critical hit stat value
            dh_stat: Direct hit stat value
            determination: Determination stat value
            medication_amt: Main stat increase from medication
            level: Player level
            phase: Fight phase number
            damage_buff_table: Table of damage buffs
            critical_hit_rate_buff_table: Table of crit rate buffs
            direct_hit_rate_buff_table: Table of DH rate buffs
            guaranteed_hits_by_action_table: Table of guaranteed hits by action
            guaranteed_hits_by_buff_table: Table of guaranteed hits by buff
            pet_ids: Optional list of pet IDs
            debug: Enable debug logging
        """

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
        self.fight_information(headers)
        self.damage_events(headers)
        self.ability_name_mapping_str = dict(
            zip(
                [str(x) for x in self.ability_name_mapping.keys()],
                self.ability_name_mapping.values(),
            )
        )
        self.fight_start_time = self.report_start_time + self.actions[0]["timestamp"]
        self.patch_number = self.what_patch_is_it()
        # Buff information, filtered to the relevant timestamp
        # Just about everything is handled as dictionaries except for
        # hit types via buffs because they are matched on two keys,
        # buff and action. This is simpler to do in pandas.

        # Everything ends up as an ID : multiplier/rate/hit type relationship
        self.damage_buffs = (
            damage_buff_table[
                (damage_buff_table["valid_start"] <= self.fight_start_time)
                & (self.fight_start_time <= damage_buff_table["valid_end"])
            ]
            # .set_index("buff_id")["buff_strength"]
            # .to_dict()
        )

        self.critical_hit_rate_buffs = (
            critical_hit_rate_buff_table[
                (critical_hit_rate_buff_table["valid_start"] <= self.fight_start_time)
                & (self.fight_start_time <= critical_hit_rate_buff_table["valid_end"])
            ]
            .set_index("buff_id")["rate_buff"]
            .to_dict()
        )

        self.direct_hit_rate_buffs = (
            direct_hit_rate_buff_table[
                (direct_hit_rate_buff_table["valid_start"] <= self.fight_start_time)
                & (self.fight_start_time <= direct_hit_rate_buff_table["valid_end"])
            ]
            .set_index("buff_id")["rate_buff"]
            .to_dict()
        )

        # Guaranteed hit types
        self.guaranteed_hit_type_via_buff = guaranteed_hits_by_buff_table[
            (guaranteed_hits_by_buff_table["valid_start"] <= self.fight_start_time)
            & (self.fight_start_time <= guaranteed_hits_by_buff_table["valid_end"])
        ]

        self.guaranteed_hit_type_via_action = (
            guaranteed_hits_by_action_table[
                (
                    guaranteed_hits_by_action_table["valid_start"]
                    <= self.fight_start_time
                )
                & (
                    self.fight_start_time
                    <= guaranteed_hits_by_action_table["valid_end"]
                )
            ]
            .set_index("action_id")["hit_type"]
            .to_dict()
        )

        self.ranged_cards = self.damage_buffs[
            self.damage_buffs["buff_name"].isin(["The Bole", "The Spire", "The Ewer"])
        ]["buff_id"].tolist()
        self.melee_cards = self.damage_buffs[
            self.damage_buffs["buff_name"].isin(
                ["The Arrow", "The Balance", "The Spear"]
            )
        ]["buff_id"].tolist()

        self.actions_df = self.create_action_df()

        # Use delegation to handle job-specific mechanics,
        # since exact transformations will depend on the job.
        self.job_specifics = None

        if self.job == "DarkKnight":
            self.job_specifics = DarkKnightActions()
            self.actions_df = self.estimate_ground_effect_multiplier(
                self.job_specifics.salted_earth_id,
            )
            self.actions_df = self.job_specifics.apply_drk_things(
                self.actions_df,
                self.player_id,
                self.pet_ids[0],
            )

        elif self.job == "Paladin":
            self.job_specifics = PaladinActions(headers, report_id, fight_id, player_id)
            self.actions_df = self.job_specifics.apply_pld_buffs(self.actions_df)
            pass

        elif self.job == "BlackMage":
            self.job_specifics = BlackMageActions(
                headers, report_id, fight_id, player_id, self.level, self.patch_number
            )
            self.actions_df = self.job_specifics.apply_elemental_buffs(self.actions_df)
            self.actions_df = self.actions_df[
                self.actions_df["ability_name"] != "Attack"
            ]

        elif self.job == "Summoner":
            self.actions_df = self.estimate_ground_effect_multiplier(
                1002706,
            )

        elif self.job in (
            "Pictomancer",
            "RedMage",
            "Summoner",
            "Astrologian",
            "WhiteMage",
            "Sage",
        ):
            self.actions_df = self.actions_df[
                self.actions_df["ability_name"] != "Attack"
            ]

        # FIXME: I think arm of the destroyer won't get updated but surely no one would use that in savage.
        elif self.job == "Monk":
            self.job_specifics = MonkActions(
                headers, report_id, fight_id, player_id, self.patch_number
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
                headers, report_id, fight_id, player_id, self.patch_number
            )
            self.actions_df = self.job_specifics.apply_ninja_buff(self.actions_df)
            pass

        elif self.job == "Dragoon":
            self.job_specifics = DragoonActions(
                headers, report_id, fight_id, player_id, self.patch_number
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
            self.job_specifics = ReaperActions(headers, report_id, fight_id, player_id)
            self.actions_df = self.job_specifics.apply_enhanced_buffs(self.actions_df)
            pass

        elif self.job == "Viper":
            self.job_specifics = ViperActions(headers, report_id, fight_id, player_id)
            self.actions_df = self.job_specifics.apply_viper_buffs(self.actions_df)

        elif self.job == "Samurai":
            self.job_specifics = SamuraiActions(headers, report_id, fight_id, player_id)
            self.actions_df = self.job_specifics.apply_enhanced_enpi(self.actions_df)

        elif self.job == "Machinist":
            # wildfire can't crit...
            self.actions_df.loc[
                self.actions_df["abilityGameID"] == 1000861,
                ["p_n", "p_c", "p_d", "p_cd"],
            ] = [1.0, 0.0, 0.0, 0.0]

            self.actions_df = self.estimate_ground_effect_multiplier(
                1000861,
            )
            self.job_specifics = MachinistActions(
                headers, report_id, fight_id, player_id
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
        # Unpaired didn't have damage go off, filter these out.
        # This column wont exist if there aren't any unpaired actions though.
        # This is done at the very end because unpaired actions can still give gauge,
        # which is important for tracking actions like Darkside.
        if "unpaired" in self.actions_df.columns:
            self.actions_df = self.actions_df[self.actions_df["unpaired"] != True]

        self.actions_df = self.actions_df.reset_index(drop=True)

        if self.has_echo:
            self.apply_the_echo()
        pass

    def what_patch_is_it(self) -> float:
        """Map log start timestamp to its associated patch.

        Patches are used to to apply the correct potencies and job gauge mechanics.
        """
        for k, v in patch_times.items():
            if (self.fight_start_time >= v["start"]) & (
                self.fight_start_time <= v["end"]
            ):
                return k

    def fight_information(self, headers: Dict[str, str]) -> None:
        """
        Query FFLogs API to get fight information and initialize fight-related attributes.

        Makes a GraphQL query to get:
        - Report start time
        - Fight/phase timings (start time, end time, fight duration)
        - Phase transition information if present
        - Ability name mappings
        - Echo buff status

        Sets the following instance attributes:
        - fight_name: Name of the fight/encounter
        - ability_name_mapping: Dict mapping ability IDs to human readable names
        - has_echo: Boolean indicating if Echo buff is present
        - report_start_time: Base timestamp for the report
        - phase_information: List of phase transition details
        - fight_start_time: Absolute start time of the fight/phase
        - fight_end_time: Absolute end time of the fight/phase
        - fight_time: Duration in seconds (excluding downtime)

        Args:
            headers (Dict[str, str]): FFLogs API request headers containing authorization
        """

        query = """
        query FightInformation($code: String!, $id: [Int]!) {
            reportData {
                report(code: $code) {
                    startTime
                    masterData {
                        abilities {
                            name
                            gameID
                        }
                    }
                    rankings(fightIDs: $id)
                    table(fightIDs: $id, dataType: DamageDone)
                    fights(fightIDs: $id, translate: true) {
                        encounterID
                        kill
                        startTime
                        endTime
                        name
                        hasEcho
                        phaseTransitions {
                            id
                            startTime
                        }
                    }
                }
            }
        }
        """

        # Initial query that gets the fight duration
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
        }
        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": "FightInformation",
        }
        r = requests.post(url=url, json=json_payload, headers=headers)
        r = json.loads(r.text)

        # Fight name
        self.fight_name = r["data"]["reportData"]["report"]["fights"][0]["name"]

        # Map ability ID with ability name so they're human readable
        self.ability_name_mapping = r["data"]["reportData"]["report"]["masterData"][
            "abilities"
        ]
        self.ability_name_mapping = {
            x["gameID"]: x["name"] for x in self.ability_name_mapping
        }

        # If true, an additional multiplicative buff is added later.
        self.has_echo = r["data"]["reportData"]["report"]["fights"][0]["hasEcho"]
        # All other timestamps are relative to this one
        self.report_start_time = r["data"]["reportData"]["report"]["startTime"]

        self.phase_information = r["data"]["reportData"]["report"]["fights"][0][
            "phaseTransitions"
        ]
        # Check if it was selected to analyze a phase.
        # If there is, this affects the start/end time and any downtime, if present
        # A follow-up query is required to correctly that information.
        if self.phase > 0:
            phase_start_time = [
                p["startTime"] for p in self.phase_information if p["id"] == self.phase
            ][0]
            phase_end_time = [
                p["startTime"]
                for p in self.phase_information
                if p["id"] == self.phase + 1
            ][0]
            phase_response = self.phase_fight_times(
                headers, phase_start_time, phase_end_time
            )
            downtime = self.get_downtime(phase_response)

            self.fight_start_time = self.report_start_time + phase_start_time
            self.fight_end_time = self.report_start_time + phase_end_time

        # If no phase is present, all the information is there.
        else:
            self.fight_start_time = (
                self.report_start_time
                + r["data"]["reportData"]["report"]["fights"][0]["startTime"]
            )
            self.fight_end_time = (
                self.report_start_time
                + r["data"]["reportData"]["report"]["fights"][0]["endTime"]
            )
            downtime = self.get_downtime(r)

        self.fight_time = (
            self.fight_end_time - self.fight_start_time - downtime
        ) / 1000

        pass

    def get_downtime(self, response: dict) -> int:
        """
        Extract fight downtime from FFLogs API response.

        Downtime represents periods where combat is paused during a fight,
        such as phase transitions or cutscenes. This time is excluded from
        DPS calculations.

        Args:
            response (dict): FFLogs API response containing:
                data.reportData.report.table.data.downtime

        Returns:
            int: Total downtime in milliseconds, 0 if no downtime present

        Raises:
            KeyError: If response missing expected data structure
        """
        if (
            "downtime"
            in response["data"]["reportData"]["report"]["table"]["data"].keys()
        ):
            return response["data"]["reportData"]["report"]["table"]["data"]["downtime"]
        else:
            return 0

    def phase_fight_times(
        self, headers: Dict[str, str], phase_start: int, phase_end: int
    ) -> Dict[str, Any]:
        """
        Query FFLogs API for timing details of a specific fight phase.

        Makes a GraphQL query to get damage table data for a phase-specific time window.
        Used to calculate phase durations and downtime periods.

        Args:
            headers: FFLogs API headers with authorization token
            phase_start: Phase start time in milliseconds (relative to report start)
            phase_end: Phase end time in milliseconds (relative to report start)

        Returns:
            Dict containing FFLogs API response with structure:
                data.reportData.report.table
                    - startTime: Phase start timestamp
                    - endTime: Phase end timestamp
                    - data.downtime: Phase downtime in ms

        Raises:
            requests.RequestException: If API request fails
            KeyError: If response missing required data
            ValueError: If phase_end <= phase_start
        """
        phased_query = """
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

        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "start": phase_start,
            "end": phase_end,
        }

        json_payload = {
            "query": phased_query,
            "variables": variables,
            "operationName": "PhaseTime",
        }
        r = requests.post(url=url, json=json_payload, headers=headers)
        r = json.loads(r.text)
        return r

    def damage_events(self, headers: Dict[str, str]) -> None:
        """
        Query FFLogs API for damage events from a specific fight.

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

        # Then remove that because damage done table and fight table doesn't need to be queried for every new page.
        # There might be a more elegant way to do this, but this is good enough.
        query = """
        query DpsActions(
            $code: String!
            $id: [Int]!
            $job: String!
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
                        sourceClass: $job
                        limit: 10000
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
            "job": self.job,
            "startTime": self.fight_start_time - self.report_start_time,
            "endTime": self.fight_end_time - self.report_start_time,
        }

        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": "DpsActions",
        }
        r = requests.post(url=url, json=json_payload, headers=headers)
        r = json.loads(r.text)
        self.actions.extend(r["data"]["reportData"]["report"]["events"]["data"])
        pass

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

        Example:
            >>> card_id, mult = ast_card_buff("10003242")  # The Balance on SAM
            >>> print(card_id, mult)
            card6 1.06
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
        Estimate Radiant Finale buff strength based on fight duration.

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

        Example:
            >>> # Early in fight with 1 Coda
            >>> estimate_radiant_finale_strength(50)
            'RadiantFinale1'
            >>> # Later with 3 Codas
            >>> estimate_radiant_finale_strength(150)
            'RadiantFinale3'
        """
        if elapsed_time < 0:
            raise ValueError("elapsed_time must be non-negative")

        if elapsed_time < 100:
            return "RadiantFinale1"
        else:
            return "RadiantFinale3"

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

        Raises:
            ValueError: If ground_effect_id not found in actions
            KeyError: If required columns missing from DataFrame

        Example:
            ```python
            # Estimate Salted Earth multipliers
            actions_df = estimate_ground_effect_multiplier("1000815")
            print(actions_df.loc[actions_df["abilityGameID"] == "1000815", "multiplier"])
            ```
        """
        # Check if the multiplier already exists for other actions
        # Unhashable string column of buffs, which allow duplicates to be dropped
        # Buffs are always ordered the same way
        self.actions_df["str_buffs"] = self.actions_df["buffs"].astype(str)

        # Sort of buff fact table, grouped by buff and associated multiplier
        unique_buff_sets = self.actions_df.drop_duplicates(
            subset=["str_buffs", "multiplier"]
        ).sort_values(["str_buffs", "multiplier"])[["str_buffs", "buffs", "multiplier"]]

        # Ground effects have a null multiplier, but can be imputed if
        # there exists the same set of buffs for a non ground effect
        unique_buff_sets["multiplier"] = unique_buff_sets.groupby("str_buffs")[
            "multiplier"
        ].ffill()
        unique_buff_sets = unique_buff_sets.drop_duplicates(subset=["str_buffs"])

        buff_strengths = (
            self.damage_buffs.drop_duplicates(subset=["buff_id", "buff_strength"])
            .set_index("buff_id")["buff_strength"]
            .to_dict()
        )

        # TODO: Could probably improve this by looking for the closest set of buffs with a multiplier
        # and then just make a small change to that
        remainder = unique_buff_sets[unique_buff_sets["multiplier"].isna()]
        remainder.loc[:, "multiplier"] = (
            remainder["buffs"]
            .apply(lambda x: list(map(buff_strengths.get, x)))
            .apply(lambda x: np.prod([y for y in x if y is not None]))
        )
        multiplier_table = pd.concat(
            [unique_buff_sets[~unique_buff_sets["multiplier"].isna()], remainder]
        )

        # Apply multiplier to ground effect ticks
        ground_ticks_actions = self.actions_df[
            self.actions_df["abilityGameID"] == ground_effect_id
        ]
        ground_ticks_actions = ground_ticks_actions.merge(
            multiplier_table[["str_buffs", "multiplier"]], on="str_buffs"
        )
        # If for whatever reason a multiplier already existed,
        # use that first instead of the derived one
        # combine_first is basically coalesce
        ground_ticks_actions["multiplier"] = ground_ticks_actions[
            "multiplier_x"
        ].combine_first(ground_ticks_actions["multiplier_y"])
        ground_ticks_actions.drop(
            columns=["multiplier_y", "multiplier_x"], inplace=True
        )

        # Recombine,
        # drop temporary scratch columns,
        # Re sort values
        self.actions_df = (
            pd.concat(
                [
                    self.actions_df[
                        self.actions_df["abilityGameID"] != ground_effect_id
                    ],
                    ground_ticks_actions,
                ]
            )
            .drop(columns=["str_buffs"])
            .sort_values("elapsed_time")
        )

        return self.actions_df

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

        Example:
            ```python
            actions_df = action_table.create_action_df()
            print(f"Found {len(actions_df)} actions")
            print(actions_df[["ability_name", "multiplier"]].head())
            ```

        Notes:
            - Job-specific mechanics are handled later by RotationTable
            - Ground effects/pets are included if present
            - Unpaired actions are filtered out
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

        # Whether to include damage from pets by their source ID
        source_id_filters = [self.player_id]
        if self.pet_ids is not None:
            source_id_filters += self.pet_ids

        # Unpaired actions have a cast begin but the damage does not go out
        # These will be filtered out later, but are included because unpaired
        # actions can still grant job gauge like Darkside
        actions_df = pd.DataFrame(self.actions)
        actions_df = actions_df[actions_df["sourceID"].isin(source_id_filters)]

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

        actions_df["ability_name"] = actions_df["abilityGameID"].map(
            self.ability_name_mapping
        )
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
        pet_ids: Optional[List[int]] = None,
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
            pet_ids,
            debug,
        )

        self.potency_table = potency_table[
            (potency_table["valid_start"] <= self.fight_start_time)
            & (self.fight_start_time <= potency_table["valid_end"])
            & (potency_table["job"] == job)
            & (potency_table["level"] == level)
        ]

        self.potency_table.loc[
            self.potency_table["potency_falloff"].isna(), "potency_falloff"
        ] = "1."
        self.potency_table.loc[:, "potency_falloff"] = self.potency_table[
            "potency_falloff"
        ].apply(lambda x: x.split(";"))
        self.rotation_df = self.make_rotation_df(self.actions_df)

        pass

    def normalize_hit_types(self, actions_df: pd.DataFrame) -> pd.DataFrame:
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

    def group_multi_target_hits(self, actions_df: pd.DataFrame) -> pd.DataFrame:
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

        Example:
            ```python
            # Group Fat Edge of Darkness hits on multiple targets
            hits_df = group_multi_target_hits(actions_df)
            print(hits_df.head())
            ```
        """
        return (
            actions_df.groupby("packetID")
            .max("base_damage")
            .reset_index()
            .rename(columns={"base_damage": "max_base"})[["packetID", "max_base"]]
        ).copy()

    def potency_falloff_fraction(
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

    def match_potency_falloff(self, actions_df: pd.DataFrame) -> pd.DataFrame:
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
        2. Processing multi-target hits:
        - Normalizing damage values to identify primary hits
        - Calculating potency falloff for secondary hits
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
        if t_end_clip is None:
            t_end = self.fight_end_time
        else:
            t_end = self.fight_end_time - (t_end_clip * 1000)

        if t_start_clip is None:
            t_start = self.fight_start_time
        else:
            t_start = self.fight_start_time + (t_start_clip * 1000)

        # Count how many times each action is performed

        actions_df = actions_df.copy()

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

        if len(actions_df) == 0:
            return None
            # raise RuntimeWarning(
            #     f"Cliping the DataFrame by {t_start_clip} from the start and {t_end_clip} seconds from the end led to any empty DataFrame. Either change the amount to clip the DataFrame by or the portion which is returned"
            # )

        # First step is looking for multi-target and identifying any associated potency falloffs
        # Potency falloff is identified, and then applied to the final potency

        actions_df = self.normalize_hit_types(actions_df)
        max_multi_hit = self.group_multi_target_hits(actions_df)
        actions_df = self.potency_falloff_fraction(actions_df, max_multi_hit)
        actions_df = self.match_potency_falloff(actions_df)
        actions_df["action_name"] += "_" + actions_df["matched_falloff"].astype(str)

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

        # Lists are unhashable, so make as an ordered string.
        actions_df["buff_str"] = (
            actions_df["buffs"].sort_values().apply(lambda x: sorted(x)).str.join(".")
        )
        # Need to add potency falloff so counting is correctly done later.
        actions_df["buff_str"] += "." + actions_df["matched_falloff"].astype(str)

        # And you cant value count nans
        actions_df["bonusPercent"] = actions_df["bonusPercent"].fillna(-1)
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

        # Back to a list
        rotation_df["buff_list"] = rotation_df["buff_str"].str.split(".")

        # Some jobs get different potencies depending if certain buffs are present, which corresponds to
        # multiple rows in the potency table with different `buff_id` values.
        # The corresponding potency needs to be correctly matched depending which buffs are present (or not).

        # The following priority is used by comparing the list of buffs to buff_id values:
        # Highest priority: buff_id column is in the list of buffs
        # Next highest priority: buff_id is nan, meaning no buff was present (the majority of actions).
        # Lowest priority: the buff_id column is not nan and isnt in the list of buffs.

        # For example, PLD's Holy Spirit can be bufed with Requiescat or Divine Might or be unbuffed.
        # All of these different scenarios have different potencies.
        def buff_id_match(buff_id, buff_list):
            if buff_id in buff_list:
                return 2
            elif pd.isna(buff_id):
                return 1
            else:
                return 0

        # Determine potency priority
        rotation_df["potency_priority"] = rotation_df.apply(
            lambda x: buff_id_match(x["buff_id"], x["buff_list"]), axis=1
        )

        # Assign potency based on whether combo, positional, or combo + positional was satisfied
        # Also update the action name
        rotation_df["potency"] = rotation_df["base_potency"]
        # Combo bonus
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df["combo_bonus"], "potency"
        ] = rotation_df["combo_potency"]
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df["combo_bonus"], "action_name"
        ] += "_combo"

        # Positional bonus
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df["positional_bonus"], "potency"
        ] = rotation_df["positional_potency"]
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df["positional_bonus"],
            "action_name",
        ] += "_positional"

        # Combo bonus and positional bonus
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df["combo_positional_bonus"],
            "potency",
        ] = rotation_df["combo_positional_potency"]
        rotation_df.loc[
            rotation_df["bonusPercent"] == rotation_df["combo_positional_bonus"],
            "action_name",
        ] += "_combo_positional"

        # Take the highest potency priority value by unique action
        sort_list = [
            "base_action",
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
        rotation_df = (
            rotation_df.sort_values(sort_list, ascending=False)
            .groupby(sort_list[:-1] + ["bonusPercent"])
            .head(1)
        )

        # Now that all correct potencies have been assigned,
        # Multiply by damage falloff
        rotation_df["potency"] = (
            rotation_df["potency"] * rotation_df["matched_falloff"]
        ).astype(int)
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
    job = "DarkKnight"
    # TODO: turn these into tests
    # RotationTable(
    #     headers,
    #     "2yDY81rxKFqPTdZC",
    #     10,
    #     "DarkKnight",
    #     4,
    #     2576,
    #     940,
    #     2182,
    #     254,
    #     damage_buff_table,
    #     critical_hit_rate_table,
    #     direct_hit_rate_table,
    #     guaranteed_hits_by_action_table,
    #     guaranteed_hits_by_buff_table,
    #     potency_table,
    #     pet_ids=[15],
    # )

    # RotationTable(
    #     headers,
    #     "bLcB1DYCKxq8tdf6",
    #     6,
    #     "Machinist",
    #     7,
    #     2002,
    #     2220,
    #     2607,
    #     351,
    #     100,
    #     damage_buff_table,
    #     critical_hit_rate_table,
    #     direct_hit_rate_table,
    #     guaranteed_hits_by_action_table,
    #     guaranteed_hits_by_buff_table,
    #     potency_table,
    #     pet_ids=[13],
    # )

    # RotationTable(
    #     headers,
    #     "TxzfCRDj9WrkGp6H",
    #     14,
    #     "BlackMage",
    #     4,
    #     4341,
    #     2032,
    #     2064,
    #     351,
    #     90,
    #     damage_buff_table,
    #     critical_hit_rate_table,
    #     direct_hit_rate_table,
    #     guaranteed_hits_by_action_table,
    #     guaranteed_hits_by_buff_table,
    #     potency_table,
    #     pet_ids=None,
    # )

    RotationTable(
        headers,
        "ZTHC2AVM3wcxXhKz",
        2,
        "Viper",
        7,
        4341,
        2032,
        2064,
        351,
        100,
        damage_buff_table,
        critical_hit_rate_table,
        direct_hit_rate_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        potency_table,
        pet_ids=None,
    )
