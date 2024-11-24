import json
import time

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
    def __init__(
        self,
        headers: dict,
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
        damage_buff_table,
        critical_hit_rate_buff_table,
        direct_hit_rate_buff_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        pet_ids=None,
        debug=False,
    ) -> None:
        """Get and transform damage events from FFLogs for a specific run of a single player to analyze damage variability.

        The transformation process roughly follows a medallion
        The damage event payload table from the FFLogs API is treated as a Bronze table.
        The processed action table is a Silver table.
        The action table is aggregated into a rotation table, a Gold table.

        Args:
            headers (dict): header for request module to make an API call.
                            This should contain the content-type and Authorization via a bearer token.
                            Note that the bearer token is *not* saved, it is only temporarily passed
                            to perform API calls as needed.
                            Example: {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            report_id (str): ID of the report to query, e.g., "gbkzXDBTFAQqjxpL".
            fight_id (int): Fight ID of the report to query, e.g., 4.
            job (str): Job name in Pascal case, e.g., "DarkKnight".
            player_id (int): FFLogs-assigned actor ID of the player. Obtained via the EncounterInfo query.
            crit_stat (int): Critical hit stat value. Used for computing hit type rates.
            dh_stat (int): Direct hit rate stat value. Used for compute hit type rates
            determination (int): Determination stat value. Used to compute the damage buff
                                 granted to guaranteed direct hits affected by direct hit rate buffs.
            medication_amt (int): number of main stat points that are increased by medication.
            pet_ids (list, optional): List of pet IDs (int) if any are present. Obtained via the EncounterInfo query.
                                      Defaults to None.
            debug (bool, optional): _description_. Defaults to False.
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

    def what_patch_is_it(self):
        """Map log start timestamp to its associated patch. Patches are used to to apply the correct potencies and job gauge mechanics."""
        for k, v in patch_times.items():
            if (self.fight_start_time >= v["start"]) & (
                self.fight_start_time <= v["end"]
            ):
                return k

    def fight_information(self, headers):
        """Query a report to get report/fight information:
        - Report start time
        - Fight/phase timings
            - Start time
            - End time
            - Fight time, active time used for DPS, (end - start - downtime)
            - Phase information, if present.
        - Ability name mapping
        - Echo present

        Args:
            headers (dict): _description_
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
        """Get the downtime of a fight, if present.

        Args:
            response (dict): FFLogs fights graph response.

        Returns:
            int: Downtime in ms.
        """
        if (
            "downtime"
            in response["data"]["reportData"]["report"]["table"]["data"].keys()
        ):
            return response["data"]["reportData"]["report"]["table"]["data"]["downtime"]
        else:
            return 0

    def phase_fight_times(self, headers: dict, phase_start: int, phase_end: int):
        """
        Follow-up query to get the start time, end time, and downtime of a phase.
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

    def damage_events(self, headers):
        """
        Query the FFLogs API for damage events and other relevant information:

        * Unix timestamp of the report start time.
        * The active fight time used to compute DPS (excludes downtime).
        * The fight name.
        * List of damage events.

        Args:
            headers (dict): header for request module to make an API call.
                            This should contain the content-type and Authorization via a bearer token.
                            Note that the bearer token is *not* saved, it is only temporarily passed
                            to perform API calls as needed.
                            Example: {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
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
        """Get the buff strength of a card given the job and card tuple.
        This is necessary because the buff IDs cannot distinguish a 3% and 6% buff, only the card type.
        Since all cards either confer a 3% or 6% buff, two new IDs are created: card3 and card6.
        This allows more actions to be grouped together. For example, Midare with The Spear
        and Midare with the Arrow both sample the same distribution.

        Args:
            card_id (str): ability ID of the card, "10003242"

        Returns:
            new_card_id: New ID of a card, now indicating its buff strength as card3 (3%) or card6 (6%)
            card_multiplier: multiplier of the card, 1.03 or 1.06
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
        """Very hacky way of estimating Radiant Finale strength.
        Radiant Finale has the same ID regardless of how many codas are present.
        Values under 100s assume it's the first usage and there's only a 2% buff.
        Values over 100s assume 3 songs have been played and it's the full 6% buff.
        New buff IDs are created depending on the number of Codas collected for Radiant Finale:
            * RadiantFinale1 - 1 coda / 2% buff
            * RadiantFinale3 - 3 cods / 6% buff

        Args:
            elapsed_time (int): Fight duration that has elapsed in seconds.

        Returns:
            raidant_finale_buff_id: ID indicating how many codas the R
        """
        if elapsed_time < 100:
            return "RadiantFinale1"
        else:
            return "RadiantFinale3"

    def estimate_ground_effect_multiplier(self, ground_effect_id):
        """Estimate the multiplier for ground effects like Salted Earth (DRK) or Slipstream (SMN),
        as FFLogs does not seem to supply this.

        Multipliers are estimated in two ways:

        1. Match the set of buffs to non-ground effect action multipliers.
           This method will capture fight-specific multipliers like Damage Down or Everlasting Flight.
        2. All remainders are estimated using the `damage_buff_table` data frame.
           This will not capture fight-specific multipliers

        This currently does not account for multipliers which are fight-specific (de)buffs, like Damage Down.

        Args:
            ground_effect_id (string): ID of the ground effect

        Returns:
            actions_df: new actions_df data frame where the damage multiplier is estimated for ground effects
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
        ability_id,
        buff_ids,
        multiplier,
        ch_rate_buff=0,
        dh_rate_buff=0,
    ):
        """Check if an action is guaranteed critical and/or direct damage.
        If so, and hit-type buffs are present, then compute its damage buff.

        Args:
            ability_id (str): ID of the damage-dealing action
            buff_ids (str): ID of all buffs present
            multiplier (int): Original damage multiplier.
            guaranteed_hit_via_buff (DataFrame): Table of actions which have guaranteed hit types when certain buffs are present
            guaranteed_hit_via_action (DataFrame): Table of actions which have guaranteed hit types
            ch_buff (int, optional): The total rate [0, 1] by which critical hits have increased by critical hit rate type buffs. Defaults to 0.
            dh_buff (int, optional): The total rate [0, 1] by which direct hits have been increased by direct hit rate buffs. Defaults to 0.

        Returns:
            float: new damage multiplier accounting for hit type rate buffs acting on guaranteed hit types.
            int: hit type: 0 = normal; 1 = guaranteed critical; 2 = guaranteed direct; 3 = guaranteed critical-direct
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

    def apply_the_echo(self):
        """Apply the damage bonus from The Echo.
        The echo is a multiplicative buff whose stregnth is based on current patch.
        This is
        """
        six_point_5_7 = 1707818400000
        six_point_5_8 = 1710849600000

        # 6.57: 10% echo
        if (self.fight_start_time >= six_point_5_7) & (
            self.fight_start_time <= six_point_5_8
        ):
            echo_strength = 1.10
            echo_buff = "echo10"

        # 6.58: 15% echo
        elif self.fight_start_time >= six_point_5_8:
            echo_strength = 1.15
            echo_buff = "echo15"

        self.actions_df["multiplier"] = round(
            self.actions_df["multiplier"] * echo_strength, 6
        )
        self.actions_df["action_name"] += f"_{echo_buff}"
        self.actions_df["buffs"].apply(lambda x: x.append(echo_buff))

        pass

    def create_action_df(
        self,
        medication_id="1000049",
        medication_multiplier=1.05,
        radiant_finale_id="1002964",
    ):
        """Transform damage events from FFLogs API into a dataframe of actions.
        Some additional transformations must be performed to
            * Hit type probabilities must be computed, with hit type buffs accounted for.
            * The correct multiplier for variable damage buffs (AST cards, Radiant Finale)
              must be estimated.
            * The damage buff granted to guaranteed hit types under hit type buffs must be computed.

        Note: job-specific transformations to actions are performed later by the RotationTable class.
        This serves as the precursor to the rotation dataframe, which is grouped by unique action and counted.


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
        # # TODO: remove? I don't think buff names are needed anymore
        # actions_df.loc[:, "buff_names"] = actions_df["buffs"]

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
    def __init__(
        self,
        headers: str,
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
        damage_buff_table,
        critical_hit_rate_buff_table,
        direct_hit_rate_buff_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        potency_table,
        pet_ids: list = None,
        debug: bool = False,
    ) -> None:
        """Aggregate the Action table to a Gold-level Rotation Table,
        which is ready to compute damage distribution with `ffxiv_stats`.
        Actions are grouped by their action name and counted, and are also mapped to:
            * Potency, properly accounting for combo, positionals, and buffs which alter potency.
            * Base action name
            * Damage type: direct, DoT, pet

        Args:
            headers (dict): header for request module to make an API call.
                            This should contain the content-type and Authorization via a bearer token.
                            Note that the bearer token is *not* saved, it is only temporarily passed
                            to perform API calls as needed.
                            Example: {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            report_id (str): ID of the report to query, e.g., "gbkzXDBTFAQqjxpL".
            fight_id (int): Fight ID of the report to query, e.g., 4.
            job (str): Job name in Pascal case, e.g., "DarkKnight".
            player_id (int): FFLogs-assigned actor ID of the player. Obtained via the EncounterInfo query.
            crit_stat (int): Critical hit stat value. Used for computing hit type rates.
            dh_stat (int): Direct hit rate stat value. Used for compute hit type rates
            determination (int): Determination stat value. Used to compute the damage buff
                                 granted to guaranteed direct hits affected by direct hit rate buffs.
            medication_amt (int): number of main stat points that are increased by medication.
            pet_ids (list, optional): List of pet IDs (int) if any are present. Obtained via the EncounterInfo query.
                                      Defaults to None.
            debug (bool, optional): _description_. Defaults to False.
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

        self.potency_table.fillna({"potency_falloff": "1."}, inplace=True)
        self.potency_table["potency_falloff"] = self.potency_table[
            "potency_falloff"
        ].apply(lambda x: x.split(";"))
        self.rotation_df = self.make_rotation_df(self.actions_df)

        pass

    def normalize_hit_types(self, actions_df):
        """Undo damage bonuses from hit types, treating all hits as normal hits.

        Args:
            actions_df (_type_): _description_

        Returns:
            _type_: _description_
        """
        actions_df["base_damage"] = actions_df["amount"].astype(float)
        actions_df.loc[actions_df["hitType"] == 2, "base_damage"] /= (
            actions_df.loc[actions_df["hitType"] == 2, "l_c"] / 1000
        )
        actions_df.loc[actions_df["directHit"] == True, "base_damage"] /= 1.25
        return actions_df

    def group_multi_target_hits(self, actions_df):
        """Actions which hit multiple enemies share the same `packetID`.
        This allows us to group by packetID and compute damage falloffs.

        Exceptions are DoT ticks and ground effects, but AoE versions of these
        have no damage falloff.

        Args:
            actions_df (_type_): _description_
        """
        return (
            actions_df.groupby("packetID")
            .max("base_damage")
            .reset_index()
            .rename(columns={"base_damage": "max_base"})[["packetID", "max_base"]]
        ).copy()

    def potency_falloff_fraction(self, actions_df, max_multi_hit):
        """Compute the fractional potency of actions which hit multiple targets.
        Used later to match with

        Args:
            actions_df (_type_): _description_
            max_multi_hit (_type_): _description_

        Returns:
            _type_: _description_
        """

        actions_df = actions_df.merge(max_multi_hit, how="left", on="packetID")
        actions_df["fractional_potency"] = (
            actions_df["base_damage"] / actions_df["max_base"]
        )

        # Set DoT ticks and ground effects to a fractional potency of 1.
        # They either don't have a packet ID, is the same for multiple ticks,
        # and/or is not easy to factor out hit type damage from DoTs.
        # Either way, AoE dots and ground effects have no potency falloff.
        actions_df.loc[
            (actions_df["tick"] == True) | (actions_df["packetID"].isna()),
            "fractional_potency",
        ] = 1
        return actions_df

    def match_potency_falloff(self, actions_df):
        """Match actual potency falloff to values in the potency table.
        Because of the +/- 5% damage roll, actual falloff values must be
        within 0.1. I don't think there's any potency falloff values within 10%
        of each other where this would overlap.

        Args:
            actions_df (_type_): _description_
            potencies (_type_): _description_
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
        return actions_df

    def make_rotation_df(
        self,
        actions_df,
        t_end_clip=None,
        t_start_clip=None,
        return_clipped=False,
        clipped_portion="end",
    ):
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
        actions_df["action_name"] += ("_" + actions_df["matched_falloff"].astype(str)) 
        

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
        actions_df["buff_str"] += ("." + actions_df["matched_falloff"].astype(str)) 

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
