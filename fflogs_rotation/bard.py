import pandas as pd

from fflogs_rotation.base import BuffQuery


class BardActions(BuffQuery):
    def __init__(
        self,
        # FIXME: read in from potency.csv
        pitch_perfect_potencies: dict[int, int] = {1: 100, 2: 220, 3: 360},
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

    def _normalize_damage(
        self, actions_df: pd.DataFrame, l_c: float, is_pitch_perfect: bool = False
    ) -> pd.DataFrame:
        """
        Normalize damage values by dividing out crits, direct hits, and multipliers.

        Parameters:
            actions_df (pd.DataFrame): DataFrame containing action/damage data.
            l_c (float): Crit multiplier.
            is_pitch_perfect (bool): Whether the damage is for Pitch Perfect actions.

        Returns:
            pd.DataFrame: DataFrame with normalized damage values.
        """
        actions_df["normalized_damage"] = (
            actions_df["amount"] / actions_df["multiplier"]
        )
        actions_df.loc[actions_df["hitType"] == 2, "normalized_damage"] /= l_c / 1000
        actions_df.loc[actions_df["directHit"] == True, "normalized_damage"] /= 1.25

        # Approximately factor out potion for PP
        if is_pitch_perfect:
            actions_df.loc[actions_df["main_stat_add"] > 0, "normalized_damage"] /= 1.05

        return actions_df

    def _compute_potency_boundary(self, boundary_index: int) -> float:
        """
        Compute the damage boundary for pair of Pitch Perfect stacks.

        Parameters:
            index (int): The index of the boundary to compute (1 for pp1-pp2, 2 for pp2-pp3).

        Returns:
            float: The damage boundary for the specified index.
        """
        if boundary_index > 2:
            raise ValueError("Invalid index. Use 1 for pp1-pp2 or 2 for pp2-pp3.")

        return (
            0.5
            * (
                self.pitch_perfect_potencies[boundary_index]
                + self.pitch_perfect_potencies[boundary_index + 1]
            )
            / self.burst_shot_potency
        )

    def _assign_pitch_perfect_stacks(
        self, actions_df: pd.DataFrame, dmg_boundaries: dict[str, float]
    ) -> pd.DataFrame:
        """
        Assign Pitch Perfect stacks based on relative damage amounts.

        Parameters:
            actions_df (pd.DataFrame): DataFrame containing action data.
            dmg_boundaries (Dict[str, float]): Damage boundaries for pp1-pp2 and pp2-pp3.

        Returns:
            pd.DataFrame: Updated DataFrame with assigned Pitch Perfect stacks.
        """
        pp_filter = actions_df["abilityGameID"] == self.pitch_perfect_id

        # 1 PP stack
        actions_df.loc[
            pp_filter
            & (actions_df["relative_damage"] < dmg_boundaries["dmg_boundary_1_2"]),
            "pp_buff",
        ] = "pp1"

        # 2 PP stacks
        actions_df.loc[
            pp_filter
            & actions_df["relative_damage"].between(
                dmg_boundaries["dmg_boundary_1_2"],
                dmg_boundaries["dmg_boundary_2_3"],
                inclusive="both",
            ),
            "pp_buff",
        ] = "pp2"

        # 3 PP stacks
        actions_df.loc[
            pp_filter
            & (actions_df["relative_damage"] > dmg_boundaries["dmg_boundary_2_3"]),
            "pp_buff",
        ] = "pp3"

        return actions_df

    def estimate_pitch_perfect_potency(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate the potency of Pitch Perfect actions based on relative damage amounts.

        Parameters:
            actions_df (pd.DataFrame): DataFrame containing action data.

        Returns:
            pd.DataFrame: Updated DataFrame with estimated Pitch Perfect potencies.
        """
        original_columns = actions_df.columns

        l_c = actions_df["l_c"].iloc[0]

        # Normalize burst shot damage
        burst_shot_damage = actions_df[
            actions_df["abilityGameID"] == self.burst_shot_id
        ][["amount", "hitType", "directHit", "multiplier", "main_stat_add"]]
        # Don't include burst shots with Potion
        burst_shot_damage = burst_shot_damage[burst_shot_damage["main_stat_add"] == 0]
        burst_shot_damage = self._normalize_damage(burst_shot_damage, l_c)
        burst_shot_base_dmg = burst_shot_damage["normalized_damage"].mean()

        # Normalize Pitch Perfect damage
        pp_filter = actions_df["abilityGameID"] == self.pitch_perfect_id
        actions_df = self._normalize_damage(actions_df, l_c, is_pitch_perfect=True)
        actions_df.loc[pp_filter, "relative_damage"] = (
            actions_df[pp_filter]["normalized_damage"] / burst_shot_base_dmg
        )

        # Compute damage boundaries and assign stacks
        dmg_boundaries = {
            "dmg_boundary_1_2": self._compute_potency_boundary(1),
            "dmg_boundary_2_3": self._compute_potency_boundary(2),
        }
        actions_df = self._assign_pitch_perfect_stacks(actions_df, dmg_boundaries)

        actions_df.loc[~actions_df["pp_buff"].isna(), "action_name"] += (
            "_" + actions_df["pp_buff"]
        )
        actions_df.loc[~actions_df["pp_buff"].isna()].apply(
            lambda x: x["buffs"].append(x["pp_buff"]), axis=1
        )

        return actions_df[original_columns]

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
