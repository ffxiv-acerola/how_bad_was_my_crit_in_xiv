from fflogs_rotation.base import BuffQuery, disjunction
from ffxiv_stats import Rate
import pandas as pd
import numpy as np

class MonkActions(BuffQuery):
    def __init__(
        self,
        headers: dict,
        report_id: str,
        fight_id: int,
        player_id: int,
        patch_number: float,
        bootshine_id: int = 53,
        opo_opo_id: int = 1000107,
        formless_fist_id: int = 1002513,
        leaden_fist_id: int = 1001861,
        dragon_kick_id: int = 74,
        twin_snakes_id: int = 61,
        demolish_id: int = 66,
        leaping_opo_id: int = 36945,
        rising_raptor_id: int = 36946,
        pouncing_coeurl_id: int = 36947,
    ) -> None:
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.patch_number = patch_number

        self.opo_opo_id = opo_opo_id
        self.formless_fist_id = formless_fist_id
        self.leaden_fist_id = leaden_fist_id
        self.bootshine_id = bootshine_id

        self.dragon_kick_id = dragon_kick_id
        self.twin_snakes_id = twin_snakes_id
        self.demolish_id = demolish_id

        self.leaping_opo_id = leaping_opo_id
        self.rising_raptor_id = rising_raptor_id
        self.pouncing_coeurl_id = pouncing_coeurl_id

        self._set_mnk_buff_times(headers)
        pass

    def _set_mnk_buff_times(self, headers):
        """Perform an API call to get buff intervals for Requiescat and Divine Might.
        Sets values as a 2 x n Numpy array, where the first column is the start time
        and the second column is the end time.

        Args:
            headers (dict): FFLogs API header.

        """
        query = """
        query MonkOpoOpo(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $opoOpoID: Float!
            $formlessFistID: Float!
            $leadenFistID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    opoOpo: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $opoOpoID
                    )
                    formlessFist: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $formlessFistID
                    )
                    leadenFist: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $leadenFistID
                    )
                }
            }
        }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "opoOpoID": self.opo_opo_id,
            "formlessFistID": self.formless_fist_id,
            "leadenFistID": self.leaden_fist_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "MonkOpoOpo")
        self.opo_opo_times = self._get_buff_times("opoOpo")
        self.formless_fist_times = self._get_buff_times("formlessFist")
        self.leaden_fist_times = self._get_buff_times("leadenFist")
        pass

    def apply_endwalker_mnk_buffs(self, actions_df):
        """Apply opo opo form to the actions DF,
        which is used to account if Bootshine is guaranteed
        critical damage

        Args:
            actions_df (DataFrame): Pandas DataFrame of actions.
        """

        # Opo opo
        opo_opo_betweens = list(
            actions_df["timestamp"].between(b[0], b[1]) for b in self.opo_opo_times
        )

        opo_opo_condition = disjunction(*opo_opo_betweens) & (
            actions_df["abilityGameID"] == self.bootshine_id
        )

        # Leaden fist
        leaden_fist_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.leaden_fist_times
        )

        leaden_fist_condition = disjunction(*leaden_fist_betweens) & (
            actions_df["abilityGameID"] == self.bootshine_id
        )

        # Apply to actions df
        actions_df = self._apply_buffs(actions_df, opo_opo_condition, self.opo_opo_id)

        actions_df = self._apply_buffs(
            actions_df, leaden_fist_condition, self.leaden_fist_id
        )

        return actions_df

    def _dawntrail_one_stack_gauge(self, actions_df: pd.DataFrame, track_opo: bool):
        """Track if Leaping Opo/Rising Raptor usages have a beast gauge stack, increasing their potency.

        Args:
            actions_df (pd.DataFrame): DataFrame of actions
            track_opo (bool): Whether to track Leaping Opo (True) or Rising Raptor (False).

        Returns:
            DataFrame: DataFrame of only Leaping Opo/Rising Raptor usages, and an indicator column for whether it is buffed.
        """
        if track_opo:
            # Opo beast gauge has to be under opo-opo form to generate stacks.
            # Create condition ensuring this (also include formless fist).
            opo_opo_betweens = list(
                actions_df["timestamp"].between(b[0], b[1]) for b in np.vstack((self.opo_opo_times, self.formless_fist_times))
            )
            opo_opo_condition = disjunction(*opo_opo_betweens)

            beast_action_df = actions_df[
                (
                    (actions_df["abilityGameID"] == self.dragon_kick_id)
                    # & opo_opo_condition
                )
                | (actions_df["abilityGameID"] == self.leaping_opo_id)
            ][["abilityGameID", "ability_name"]].copy()

            gauge_generating_id = self.dragon_kick_id
            buffed_action_id = self.leaping_opo_id

        else:
            beast_action_df = actions_df[
                actions_df["abilityGameID"].isin(
                    [self.twin_snakes_id, self.rising_raptor_id]
                )
            ][["abilityGameID", "ability_name"]].copy()

            gauge_generating_id = self.twin_snakes_id
            buffed_action_id = self.rising_raptor_id

        beast_action_df["buffed_beast_action"] = 0

        # Look at prior ability
        beast_action_df["prior_ability_id"] = beast_action_df["abilityGameID"].shift(1)
        # If the prior equals the ID of the gauge-generating ability, a stack exists.
        beast_action_df.loc[
            beast_action_df["prior_ability_id"] == gauge_generating_id,
            "buffed_beast_action",
        ] = 1

        return beast_action_df[beast_action_df["abilityGameID"] == buffed_action_id][
            ["abilityGameID", "buffed_beast_action"]
        ]

    def apply_dawntrail_mnk_buffs(self, actions_df):
        """Track beast gauge stacks for Monk.

        - Opo-opo's fury: 1 stack max, generated by Dragon Kick.
        - Raptor's fury: 1 stack max, generated by Twin Snakes.
        - Coeurl's fury: 2 stacks max, both stacks generated by Demolish.


        Args:
            actions_df (DataFrame): DataFrame of actions, with beast fury gauge stacks applied.
        """

        ### Opo-opo gauge
        leaping_opo_buffs = self._dawntrail_one_stack_gauge(actions_df, track_opo=True)
        buffed_leaping_opo_indices = leaping_opo_buffs[
            leaping_opo_buffs["buffed_beast_action"] == 1
        ].index

        ### Raptor gauge
        rising_raptor_buffs = self._dawntrail_one_stack_gauge(
            actions_df, track_opo=False
        )
        buffed_rising_raptor_indices = rising_raptor_buffs[
            rising_raptor_buffs["buffed_beast_action"] == 1
        ].index

        ### Coeurl gauge
        coeurl_actions = actions_df[
            actions_df["abilityGameID"].isin(
                [self.demolish_id, self.pouncing_coeurl_id]
            )
        ].copy()

        # FIXME: Create general gauge function
        coeurl_actions["change"] = 2
        coeurl_actions.loc[
            coeurl_actions["abilityGameID"] == self.pouncing_coeurl_id, "change"
        ] = -1

        stacks = [0]
        # There isn't an easy way to broadcast this because kazematoi stacks are bounded from [0, 5]
        # For loop it is
        for idx in range(1, len(coeurl_actions)):
            # max and min function keeps stacks bounded between 0 and 5
            stacks.append(
                max(0, min(2, coeurl_actions.iloc[idx - 1]["change"] + stacks[idx - 1]))
            )

        coeurl_actions["initial_stacks"] = stacks
        coeurl_actions = coeurl_actions[
            coeurl_actions["abilityGameID"] == self.pouncing_coeurl_id
        ].copy()
        coeurl_actions["buffed_beast_action"] = 0
        coeurl_actions.loc[
            coeurl_actions["initial_stacks"] > 0, "buffed_beast_action"
        ] = 1
        buffed_pouncing_coeurl_indices = coeurl_actions[
            coeurl_actions["buffed_beast_action"] == 1
        ].index

        return self._apply_buffs(
            actions_df,
            actions_df.index.isin(
                [
                    *buffed_leaping_opo_indices,
                    *buffed_rising_raptor_indices,
                    *buffed_pouncing_coeurl_indices,
                ]
            ),
            "fury",
        )

    def apply_bootshine_autocrit(
        self,
        actions_df,
        critical_hit_stat,
        direct_hit_rate_stat,
        critical_hit_rate_buffs,
        level
    ):
        r = Rate(critical_hit_stat, direct_hit_rate_stat, level)

        def critical_hit_rate_increase(buffs, multiplier):
            valid_buffs = [
                critical_hit_rate_buffs[b]
                for b in buffs
                if b in critical_hit_rate_buffs.keys()
            ]
            if len(valid_buffs) == 0:
                p = r.get_p(guaranteed_hit_type=1)
            else:
                crit_rate_buff = sum(valid_buffs)
                p = r.get_p(crit_rate_buff, guaranteed_hit_type=1)
                multiplier = round(
                    multiplier * r.get_hit_type_damage_buff(1, crit_rate_buff), 6
                )

            return multiplier, p[0], p[1], p[2], p[3]

        actions_df.loc[
            actions_df["abilityGameID"].isin([self.bootshine_id, self.leaping_opo_id]),
            ["multiplier", "p_n", "p_c", "p_d", "p_cd"],
        ] = (
            actions_df[
                actions_df["abilityGameID"].isin(
                    [self.bootshine_id, self.leaping_opo_id]
                )
            ]
            .apply(
                lambda x: critical_hit_rate_increase(x["buffs"], x["multiplier"]),
                axis=1,
                result_type="expand",
            )
            .to_numpy()
        )

        return actions_df


if __name__ == "__main__":
    from fflogs_rotation.rotation import headers

    mnk = MonkActions(headers, "gVkPC9HXaz7tjWbn", 5, 59, 7.01)
    mnk._dawntrail_beast_gauge_tracking(None)
