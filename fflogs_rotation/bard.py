from typing import Dict

import pandas as pd

from fflogs_rotation.base import BuffQuery


class BardActions(BuffQuery):
    def __init__(
        self,
        # FIXME: read in from potency.csv
        pitch_perfect_potencies: Dict[int, int] = {1: 100, 2: 220, 3: 360},
        burst_shot_potency: int = 220,
        pitch_perfect_id: int = 7404,
        burst_shot_id: int = 16495,
        radiant_encore_id: int = 36977,
    ) -> None:
        super().__init__()

        self.pitch_perfect_potencies = pitch_perfect_potencies
        self.burst_shot_potency = burst_shot_potency

        self.pitch_perfect_id = pitch_perfect_id
        self.burst_shot_id = burst_shot_id

        self.radiant_encore_id = radiant_encore_id

    def estimate_pitch_perfect_potency(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate the potency of Pitch Perfect actions based on relative damage amounts.

        Parameters:
            actions_df (pd.DataFrame): DataFrame containing action data.

        Returns:
            pd.DataFrame: Updated DataFrame with estimated Pitch Perfect potencies.
        """
        l_c = actions_df["l_c"].iloc[0]

        # Find base damage, divide out crits/direct hits/buff multipliers
        burst_shot_damage = actions_df[
            actions_df["abilityGameID"] == self.burst_shot_id
        ][["amount", "hitType", "directHit", "multiplier", "main_stat_add"]]
        burst_shot_damage = burst_shot_damage[burst_shot_damage["main_stat_add"] == 0]
        burst_shot_damage["normalized_damage"] = (
            burst_shot_damage["amount"] / burst_shot_damage["multiplier"]
        )
        burst_shot_damage.loc[
            burst_shot_damage["hitType"] == 2, "normalized_damage"
        ] /= l_c / 1000
        burst_shot_damage.loc[
            burst_shot_damage["directHit"] == True, "normalized_damage"
        ] /= 1.25

        burst_shot_base_dmg = burst_shot_damage["normalized_damage"].mean()

        # Find damage relative to base burst shot damage of all pitch perfect
        pp_filter = actions_df["abilityGameID"] == self.pitch_perfect_id
        actions_df["normalized_damage"] = (
            actions_df["amount"] / actions_df["multiplier"]
        )
        actions_df.loc[
            pp_filter & (actions_df["hitType"] == 2), "normalized_damage"
        ] /= l_c / 1000
        actions_df.loc[
            pp_filter & (actions_df["directHit"] == True), "normalized_damage"
        ] /= 1.25
        actions_df.loc[
            pp_filter & (actions_df["main_stat_add"] > 0), "normalized_damage"
        ] /= 1.05
        actions_df.loc[pp_filter, "relative_damage"] = (
            actions_df[pp_filter]["normalized_damage"] / burst_shot_base_dmg
        )

        # Assign pp stacks based on relative damage amounts
        potency_1_2_boundary = 0.5 * (
            self.pitch_perfect_potencies[1] + self.pitch_perfect_potencies[2]
        )
        potency_2_3_boundary = 0.5 * (
            self.pitch_perfect_potencies[2] + self.pitch_perfect_potencies[3]
        )
        dmg_boundary_1_2 = potency_1_2_boundary / self.burst_shot_potency
        dmg_boundary_2_3 = potency_2_3_boundary / self.burst_shot_potency
        actions_df.loc[
            pp_filter & (actions_df["relative_damage"] < dmg_boundary_1_2), "pp_buff"
        ] = "pp1"
        actions_df.loc[
            pp_filter
            & actions_df["relative_damage"].between(
                dmg_boundary_1_2, dmg_boundary_2_3, inclusive="both"
            ),
            "pp_buff",
        ] = "pp2"
        actions_df.loc[
            pp_filter & (actions_df["relative_damage"] > dmg_boundary_2_3), "pp_buff"
        ] = "pp3"

        actions_df.loc[~actions_df["pp_buff"].isna(), "action_name"] += (
            "_" + actions_df["pp_buff"]
        )
        actions_df.loc[~actions_df["pp_buff"].isna()].apply(
            lambda x: x["buffs"].append(x["pp_buff"]), axis=1
        )

        return actions_df

    def estimate_radiant_encore_potency(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Incredibly simple method of estimating Radiant Encore potency:

        - elapsed time < 40 seconds -> 1 coda
        - elapsed time > 40 seconds -> 3 coda

        Parameters:
            actions_df (pd.DataFrame): Action DataFrame without Radiant Encore potency estimated.

        Returns:
            pd.DataFrame: Updated DataFrame with estimated Radiant Encore potencies.
        """
        actions_df.loc[
            (actions_df["abilityGameID"] == self.radiant_encore_id)
            & (actions_df["elapsed_time"] < 40)
        ].apply(lambda x: x["buffs"].append("c1"), axis=1)

        actions_df.loc[
            (actions_df["abilityGameID"] == self.radiant_encore_id)
            & (actions_df["elapsed_time"] >= 40)
        ].apply(lambda x: x["buffs"].append("c3"), axis=1)
        return actions_df
