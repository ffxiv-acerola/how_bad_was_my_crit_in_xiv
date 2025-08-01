import warnings

import numpy as np
import pandas as pd
from ffxiv_stats import Rate
from ffxiv_stats.jobs import Healer, MagicalRanged, Melee, PhysicalRanged, Tank

from crit_app.job_data.encounter_data import patch_times, patch_times_cn, patch_times_ko
from fflogs_rotation.bard import BardActions
from fflogs_rotation.base import BuffQuery
from fflogs_rotation.black_mage import BlackMageActions
from fflogs_rotation.dark_knight import DarkKnightActions
from fflogs_rotation.dragoon import DragoonActions
from fflogs_rotation.encounter_specifics import EncounterSpecifics
from fflogs_rotation.machinist import MachinistActions
from fflogs_rotation.monk import MonkActions
from fflogs_rotation.ninja import NinjaActions
from fflogs_rotation.paladin import PaladinActions
from fflogs_rotation.reaper import ReaperActions
from fflogs_rotation.samurai import SamuraiActions
from fflogs_rotation.viper import ViperActions


class ActionTable(BuffQuery):
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
        headers: dict[str, str],
        report_id: str,
        fight_id: int,
        job: str,
        player_id: int,
        crit_stat: int,
        dh_stat: int,
        determination: int,
        main_stat: int,
        weapon_damage: int,
        level: int,
        phase: int,
        damage_buff_table: pd.DataFrame,
        critical_hit_rate_buff_table: pd.DataFrame,
        direct_hit_rate_buff_table: pd.DataFrame,
        guaranteed_hits_by_action_table: pd.DataFrame,
        guaranteed_hits_by_buff_table: pd.DataFrame,
        encounter_phases,
        pet_ids: list[int] | None = None,
        excluded_enemy_ids: list[int] | None = None,
        tenacity: int | None = None,
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
        self.main_stat = main_stat
        self.weapon_damage = weapon_damage
        self.determination = determination
        self.debug = debug
        self.encounter_phases = encounter_phases
        self.tenacity = tenacity

        super().__init__(api_url="https://www.fflogs.com/api/v2/client")

        self.excluded_enemy_ids = excluded_enemy_ids

        # Fetch fight information and set timings
        fight_info_response = self._query_fight_information(headers)
        self._set_fight_information(headers, fight_info_response)

        self.d2_100 = self._get_100_potency_d2_value(
            main_stat,
            determination,
            weapon_damage,
            level,
            job,
            self.medication_amt,
            tenacity,
        )

        self.medication_multiplier = self._estimate_medication_multiplier(
            self.medication_amt,
            self.main_stat,
            self.determination,
            self.weapon_damage,
            self.level,
            self.job,
            tenacity,
        )

        # Fetch damage events from FFLogs
        self.actions = self._query_damage_events(headers)

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

        self.actions_df = self.normalize_damage(
            self.actions_df, self.medication_multiplier
        )
        self.actions_df = self.potency_estimate(self.actions_df, self.d2_100)

        # Apply job-specific mechanics
        self._apply_job_specifics(headers)
        self._apply_encounter_specifics(headers)

        # Final cleanup of actions DataFrame
        # Remove unpaired actions, which still count towards gauge generation
        if "unpaired" in self.actions_df.columns:
            self.actions_df = self.actions_df[self.actions_df["unpaired"] != True]
        self.actions_df = self.actions_df.reset_index(drop=True)

        # Apply the echo, if present
        if self.has_echo:
            self.apply_the_echo()

    def _query_fight_information(self, headers: dict[str, str]) -> None:
        """
        Retrieves fight information from the FFLogs GraphQL API for the specified.

        fight and calls `_process_fight_data()` to set core attributes (e.g., encounter
        name, start/end times, echo). Modifies class state in-place.

        Args:
            headers (dict[str, str]): HTTP headers for GraphQL querying, including
            authentication tokens.
        """
        fight_info_variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "sourceID": self.player_id,
        }

        response = self.gql_query(
            headers,
            self._fight_information_query(),
            fight_info_variables,
            "FightInformation",
        )

        # TODO: check for valid response
        return response["data"]["reportData"]["report"]

    def _fight_information_query(self) -> str:
        """Fight information GQL query string."""
        return """
        query FightInformation($code: String!, $id: [Int]!, $sourceID: Int!) {
            reportData {
                report(code: $code) {
                    startTime
                    region{
                        name,
                        compactName
                    }
                    # masterData { abilities { name gameID } }
                    potionType: table(
                        fightIDs: $id
                        dataType: Buffs
                        abilityID: 1000049
                        sourceID: $sourceID
                    )
                    table(fightIDs: $id, dataType: DamageDone)
                    fights(fightIDs: $id, translate: true) {
                        encounterID
                        kill
                        startTime
                        endTime
                        name
                        hasEcho
                        difficulty
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

    def _set_fight_information(
        self, headers: dict[str, str], fight_info_response: dict
    ) -> None:
        self.report_start_time = self._get_report_start_time(fight_info_response)
        self.fight_name = self._get_fight_name(fight_info_response)
        self.encounter_id = self._get_encounter_id(fight_info_response)
        self.has_echo = self._get_has_echo(fight_info_response)
        self.kill = self._get_was_kill(fight_info_response)
        self.region = self._get_region(fight_info_response)
        self.patch_number = self._get_patch_number(self.report_start_time, self.region)
        self.difficulty = self._get_difficulty(fight_info_response)
        try:
            self.medication_amt = self._get_medication_amount(fight_info_response)
        except Exception:
            self.medication_amt = 262
        self.phase_information = self._get_phase_transitions(fight_info_response)
        self.ranking_duration = self._get_ranking_duration(fight_info_response)
        (
            self.fight_start_time,
            self.fight_end_time,
            self.phase_start_time,
            self.phase_end_time,
            self.downtime,
            self.fight_dps_time,
        ) = self._process_fight_data(headers, fight_info_response)
        pass

    @staticmethod
    def _get_report_start_time(fight_info_response) -> str:
        return fight_info_response["startTime"]

    @staticmethod
    def _get_fight_name(fight_info_response) -> str:
        return fight_info_response["fights"][0]["name"]

    @staticmethod
    def _get_encounter_id(fight_info_response) -> int:
        return fight_info_response["fights"][0]["encounterID"]

    @staticmethod
    def _get_region(fight_info_response) -> int:
        return fight_info_response["region"]["compactName"]

    @staticmethod
    def _get_difficulty(fight_info_response) -> int:
        return fight_info_response["fights"][0]["difficulty"]

    @staticmethod
    def _get_patch_number(fight_start_time, region) -> float:
        # Korean and Chinese servers have different patch cadence.
        if region == "CN":
            for k, v in patch_times_cn.items():
                if (fight_start_time >= v["start"]) & (fight_start_time <= v["end"]):
                    return k
        elif region == "KR":
            for k, v in patch_times_ko.items():
                if (fight_start_time >= v["start"]) & (fight_start_time <= v["end"]):
                    return k
        else:
            for k, v in patch_times.items():
                if (fight_start_time >= v["start"]) & (fight_start_time <= v["end"]):
                    return k
        return 0.0

    @staticmethod
    def _get_has_echo(fight_info_response) -> bool:
        return fight_info_response["fights"][0]["hasEcho"]

    @staticmethod
    def _get_was_kill(fight_info_response) -> bool:
        return fight_info_response["fights"][0]["kill"]

    @staticmethod
    def _get_phase_transitions(fight_info_response):
        return fight_info_response["fights"][0]["phaseTransitions"]

    @staticmethod
    def _get_ranking_duration(fight_info_response) -> str:
        if len(fight_info_response["rankings"]["data"]) > 0:
            return fight_info_response["rankings"]["data"][0]["duration"]
        return None

    @staticmethod
    def _get_medication_amount(fight_info_response) -> str:
        potion_strengths = []
        potion_auras = fight_info_response["potionType"]["data"]["auras"]
        if len(potion_auras) == 0:
            return 0

        potion_auras = [p for p in potion_auras if "appliedByAbilities" in p.keys()]
        if len(potion_auras[0]["appliedByAbilities"]) == 0:
            return 0
        else:
            for x in range(len(potion_auras[0]["appliedByAbilities"])):
                potion_name = potion_auras[0]["appliedByAbilities"][x]["name"]
                job = potion_auras[0]["icon"]

                potion_split = potion_name.split(" ")
                processed_potion_name = " ".join(potion_split[:3]) + (
                    " [HQ]" if potion_split[-1] == "[HQ]" else ""
                )

                potion_type = potion_split[4]

                potion_strengths.append(
                    ActionTable._validate_potion_strength(
                        processed_potion_name, potion_type, job
                    )
                )

        return max(potion_strengths)

    @staticmethod
    def _validate_potion_strength(
        processed_potion_name: str, potion_type: str, job: str
    ) -> int:
        """Get the potion strength, accounting for if the potion type matches the job.

        Args:
            processed_potion_name (str): Potion name
            potion_type (str): Type of the potion, e.g., "Dexterity"

        Returns:
            int: Correct potion strength
        """
        from crit_app.job_data.roles import role_mapping
        from fflogs_rotation.job_data.tinctures import (
            ad_hoc_job_tincture_map,
            role_tincture_map,
            tincture_strengths,
        )

        role = role_mapping[job]
        # Check if the potion type matches the correct role
        # or if it's a job with a special tincture type (e.g. nin/vpr using dex)
        if (role_tincture_map[role] == potion_type) | (
            ad_hoc_job_tincture_map.get(job, "None") == potion_type
        ):
            # Tracks back to grade 1 tinctures, otherwise set strength to 100
            return tincture_strengths.get(processed_potion_name, 100)
        else:
            # No bonus for incorrect potion type
            return 0

    def _process_fight_data(self, headers: dict[str, str], fight_info_response) -> None:
        """
        Parses the fight data from the FFLogs API response, setting core attributes.

        such as encounter details, start/end times, and handling phase timings.
        Updates the class state to reflect whether the fight was a kill,
        whether echo was active, and any relevant phase/downtime offsets.

        Args:
            response (dict):
                The parsed JSON response from the FFLogs API containing report
                and fight data.
            headers (dict[str, str]):
                HTTP headers used for further GraphQL queries, if needed
                for phase/downtime details.
        """
        fight = fight_info_response["fights"][0]

        fight_start_time = self.report_start_time
        fight_end_time = self.report_start_time

        # If user requested a specific phase, adjust start/end times
        if self.phase > 0:
            phase_start_time, phase_end_time = self._fetch_phase_start_end_time(
                fight["endTime"]
            )
            phase_response = self._fetch_phase_downtime(
                headers, phase_start_time, phase_end_time
            )
            downtime = self._get_downtime(phase_response)

            fight_start_time += phase_start_time
            fight_end_time += phase_end_time
        else:
            downtime = self._get_downtime(fight_info_response)
            phase_start_time = None
            phase_end_time = None
            fight_start_time += fight["startTime"]
            fight_end_time += fight["endTime"]

        fight_dps_time = (fight_end_time - fight_start_time - downtime) / 1000

        return (
            fight_start_time,
            fight_end_time,
            phase_start_time,
            phase_end_time,
            downtime,
            fight_dps_time,
        )

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

    def _fetch_phase_downtime(
        self, headers: dict[str, str], phase_start_time: int, phase_end_time: int
    ) -> dict:
        """Retrieves phase-specific timing data."""
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "start": phase_start_time,
            "end": phase_end_time,
        }
        return self.gql_query(
            headers, self._fight_phase_downtime_query(), variables, "PhaseTime"
        )["data"]["reportData"]["report"]

    def _get_downtime(self, response: dict) -> int:
        """Extracts downtime from the response, returning 0 if not present."""
        return response["table"]["data"].get("downtime", 0)

    def _query_damage_events(self, headers: dict[str, str]) -> None:
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
            headers (dict[str, str]): FFLogs API headers containing:
                - Content-Type: application/json
                - Authorization: Bearer token

        Sets:
            self.actions (List[Dict]): List of raw damage events from the API
                Each event is a dict with fields like timestamp, type,
                sourceID, targetID, amount, etc.
        """
        # Querying by playerID also includes pets
        # neat...
        actions = []
        # source_ids = [self.player_id]

        # for i in source_ids:
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "sourceID": self.player_id,
            # Need to switch back to relative timestamp
            # Time filtering is needed to ensure the correct phase
            "startTime": self.fight_start_time - self.report_start_time,
            "endTime": self.fight_end_time - self.report_start_time,
        }

        response = self.gql_query(
            headers, self._damage_events_query(), variables, "DpsActions"
        )
        actions.extend(response["data"]["reportData"]["report"]["events"]["data"])
        return actions

    @staticmethod
    def _get_100_potency_d2_value(
        main_stat: int,
        determination: int,
        weapon_damage: int,
        level: int,
        job: str,
        medication_amount: int = 0,
        tenacity: int | None = None,
    ) -> int:
        from crit_app.job_data.roles import role_mapping

        role = role_mapping[job]

        # Crit/DH/delay/speed have no bearing on direct damage base value.
        base_stats = {
            "det": determination,
            "crit_stat": 1000,
            "dh_stat": 1000,
            "weapon_damage": weapon_damage,
            "delay": 3.0,
            "level": level,
            "pet_attack_power": 1000,
        }

        if role == "Healer":
            base_stats["mind"] = main_stat
            base_stats["strength"] = 400
            base_stats["spell_speed"] = 500
            role_obj = Healer(**base_stats)

        elif role == "Tank":
            base_stats["strength"] = main_stat
            base_stats["skill_speed"] = 500
            base_stats["tenacity"] = tenacity
            base_stats["job"] = job
            role_obj = Tank(**base_stats)

        elif role == "Magical Ranged":
            base_stats["intelligence"] = main_stat
            base_stats["strength"] = 400
            base_stats["spell_speed"] = 500
            role_obj = MagicalRanged(**base_stats)

        elif role == "Physical Ranged":
            base_stats["dexterity"] = main_stat
            base_stats["skill_speed"] = 500
            role_obj = PhysicalRanged(**base_stats)

        elif role == "Melee":
            base_stats["main_stat"] = main_stat
            base_stats["skill_speed"] = 500
            base_stats["job"] = job
            role_obj = Melee(**base_stats)

        d2 = role_obj.direct_d2(100, medication_amount)
        return d2

    @staticmethod
    def _estimate_medication_multiplier(
        medication_amount: int,
        main_stat: int,
        determination: int,
        weapon_damage: int,
        level: int,
        job: str,
        tenacity: int | None = None,
    ) -> float:
        """Estimate the damage multiplier medication confers.

        Args:
            medication_amount (int): Number of main stat points increased by medication.
            main_stat (int): Main stat amount.
            determination (int): Determination stat amount.
            weapon_damage (int): Weapon damage stat.
            level (int): Level.
            job (str): Job name.

        Returns:
            float: Medication multiplier strength.
        """

        medication_multiplier = ActionTable._get_100_potency_d2_value(
            main_stat,
            determination,
            weapon_damage,
            level,
            job,
            medication_amount,
            tenacity,
        ) / ActionTable._get_100_potency_d2_value(
            main_stat, determination, weapon_damage, level, job, 0, tenacity
        )

        return medication_multiplier

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
            (damage_buff_table["valid_start"] <= self.patch_number)
            & (self.patch_number < damage_buff_table["valid_end"])
        ]
        self.critical_hit_rate_buffs = (
            crit_rate_table[
                (crit_rate_table["valid_start"] <= self.patch_number)
                & (self.patch_number < crit_rate_table["valid_end"])
            ]
            .set_index("buff_id")["rate_buff"]
            .to_dict()
        )
        self.direct_hit_rate_buffs = (
            dh_rate_table[
                (dh_rate_table["valid_start"] <= self.patch_number)
                & (self.patch_number < dh_rate_table["valid_end"])
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
        buff_ids: list[str],
        multiplier: float,
        ch_rate_buff: float = 0.0,
        dh_rate_buff: float = 0.0,
    ) -> tuple[float, int]:
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
            "targetInstance",
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

        if "targetInstance" not in actions_df.columns:
            actions_df["targetInstance"] = 1

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

    def _apply_job_specifics(self, headers: dict[str, str]) -> None:
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

            self.actions_df = self.job_specifics._estimate_six_sided_star_potency(
                self.actions_df
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

            if self.patch_number >= 7.2:
                self.actions_df = self.job_specifics.apply_enhanced_piercing_talon(
                    self.actions_df
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
            self.job_specifics = BardActions(self.d2_100, self.patch_number)
            self.actions_df = self.job_specifics.estimate_pitch_perfect_potency(
                self.actions_df
            )
            self.actions_df = self.job_specifics.estimate_apex_arrow_potency(
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
        self.actions_df = self.actions_df.reset_index(drop=True)

    def _apply_encounter_specifics(self, headers: dict[str, str]) -> None:
        # Apply Groove buff, 3%
        if self.encounter_id == 97:
            pass

        if (self.encounter_id == 99) & (self.difficulty == 101):
            self.actions_df = EncounterSpecifics().m7s_exclude_final_blooming(
                self.actions_df, self.excluded_enemy_ids[0]
            )

        # FRU ice crystals, only for p2 or whole fight analysis.
        if (self.encounter_id == 1079) & (self.phase in (0, 2)):
            self.actions_df = EncounterSpecifics().fru_apply_vuln_p2(
                headers, self.report_id, self.fight_id, self.actions_df
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
    )

    api_key = FFLOGS_TOKEN  # or copy/paste your key here
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    a = ActionTable(
        headers,
        "BThRPZj72C9x4HLn",
        17,
        "Monk",
        8,
        3446,
        1600,
        2141,
        5845 // 1.05,
        152,
        100,
        0,
        damage_buff_table,
        critical_hit_rate_table,
        direct_hit_rate_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        encounter_phases,
        # excluded_enemy_ids=[425],
    )

    # ActionTable._estimate_medication_multiplier(0, 5925, 5000, 100, "DarkKnight")
    # print()
