import pandas as pd

from fflogs_rotation.base import BuffQuery


class BardActions(BuffQuery):
    def __init__(
        self,
        # FIXME: read in from potency.csv
        d2_100_potency: int,
        patch_number: float,
        burst_shot_potency: int = 220,
        pitch_perfect_id: int = 7404,
        burst_shot_id: int = 16495,
        radiant_encore_id: int = 36977,
        apex_arrow_id: int = 16496,
    ) -> None:
        super().__init__()

        self.d2_100_potency = d2_100_potency
        self.patch_number = patch_number

        self.pitch_perfect_potencies = self.get_pitch_perfect_potency_map(
            self.patch_number
        )
        self.apex_arrow_potency = self.get_apex_arrow_potency_map(self.patch_number)
        self.burst_shot_potency = burst_shot_potency

        self.pitch_perfect_id = pitch_perfect_id
        self.burst_shot_id = burst_shot_id

        self.radiant_encore_id = radiant_encore_id
        self.apex_arrow_id = apex_arrow_id

    @staticmethod
    def get_pitch_perfect_potency_map(patch_number: float) -> dict[int, int]:
        # Currently unchanged since EW.
        return {1: 100, 2: 220, 3: 360}

    @staticmethod
    def get_apex_arrow_potency_map(patch_number: float) -> dict[int, int]:
        # Pre-DT
        # 20 Gauge -> 100 potency
        # 100 Gauge -> 500 potency
        # 25 potency / 5 gauge
        if patch_number < 7.0:
            return pd.DataFrame(
                [
                    {
                        "abilityGameID": 16496,
                        "gauge": f"gauge_{20 + idx * 5}",
                        "aa_potency": x,
                    }
                    for idx, x in enumerate(range(100, 525, 25))
                ]
            )
        # Peri-DT
        # 20 Gauge -> 120 potency
        # 100 Gauge -> 600 potency
        # 30 potency / 5 gauge
        elif patch_number >= 7.0:
            return pd.DataFrame(
                [
                    {
                        "abilityGameID": 16496,
                        "gauge": f"gauge_{20 + idx * 5}",
                        "aa_potency": x,
                    }
                    for idx, x in enumerate(range(120, 630, 30))
                ]
            )
        pass

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

        return 0.5 * (
            self.pitch_perfect_potencies[boundary_index]
            + self.pitch_perfect_potencies[boundary_index + 1]
        )

    def estimate_pitch_perfect_potency(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Estimate the potency of Pitch Perfect actions based on relative damage amounts.

        Parameters:
            actions_df (pd.DataFrame): DataFrame containing action data.

        Returns:
            pd.DataFrame: Updated DataFrame with estimated Pitch Perfect potencies.
        """
        original_columns = actions_df.columns

        dmg_boundaries = {
            "dmg_boundary_1_2": self._compute_potency_boundary(1),
            "dmg_boundary_2_3": self._compute_potency_boundary(2),
        }

        pp_filter = actions_df["abilityGameID"] == self.pitch_perfect_id

        actions_df["pp_buff"] = None

        # 1 PP stack
        actions_df.loc[
            pp_filter
            & (actions_df["estimated_potency"] < dmg_boundaries["dmg_boundary_1_2"]),
            "pp_buff",
        ] = "pp1"

        # 2 PP stacks
        actions_df.loc[
            pp_filter
            & actions_df["estimated_potency"].between(
                dmg_boundaries["dmg_boundary_1_2"],
                dmg_boundaries["dmg_boundary_2_3"],
                inclusive="both",
            ),
            "pp_buff",
        ] = "pp2"

        # 3 PP stacks
        actions_df.loc[
            pp_filter
            & (actions_df["estimated_potency"] > dmg_boundaries["dmg_boundary_2_3"]),
            "pp_buff",
        ] = "pp3"

        # Ignore potency falloff, this will be handled later.
        # Instead take the highest pp value.
        actions_df.loc[pp_filter, "pp_buff"] = (
            actions_df[pp_filter].groupby("packetID")["pp_buff"].transform("max")
        )
        # Don't use self._apply_buffs here because it is conditional
        actions_df.loc[~actions_df["pp_buff"].isna(), "action_name"] += (
            "_" + actions_df["pp_buff"]
        )
        actions_df.loc[~actions_df["pp_buff"].isna()].apply(
            lambda x: x["buffs"].append(x["pp_buff"]), axis=1
        )

        return actions_df[original_columns]

    def estimate_apex_arrow_potency(self, actions_df: pd.DataFrame):
        """Estimate the potency of Apex Arrow, added as a buff in actions_df.

        Potency scales with gauge, which is unavailable through FFLogs.
        Note that the potency difference between gauge increments can overlap due to the +/-5%
        damage roll, so values are not perfectly matched.

        Args:
            actions_df (pd.DataFrame): DataFrame with potency indicator buff added to Apex Arrow.
        """
        original_columns = actions_df.columns
        apex_arrow_df = actions_df[actions_df["abilityGameID"] == self.apex_arrow_id][
            ["packetID", "abilityGameID", "estimated_potency"]
        ].copy()
        # Average any multi target for better statistical power
        apex_arrow_df = apex_arrow_df.groupby("packetID", as_index=False).mean(
            "estimated_potency"
        )

        apex_arrow_df = apex_arrow_df.merge(
            self.apex_arrow_potency, how="left", on="abilityGameID"
        )

        # Find gauge value of closest matching potency
        apex_arrow_df["aa_potency_estimate"] = (
            apex_arrow_df["estimated_potency"] - apex_arrow_df["aa_potency"]
        ).abs()

        apex_arrow_df = (
            apex_arrow_df.sort_values(["packetID", "aa_potency_estimate"])
            .groupby("packetID", as_index=False)
            .first()
        )

        actions_df = actions_df.merge(
            apex_arrow_df[["packetID", "gauge"]], how="left", on="packetID"
        )

        # Don't use self._apply_buffs here because it is conditional
        actions_df.loc[~actions_df["gauge"].isna(), "action_name"] += (
            "_" + actions_df["gauge"]
        )
        actions_df.loc[~actions_df["gauge"].isna()].apply(
            lambda x: x["buffs"].append(x["gauge"]), axis=1
        )
        return actions_df[original_columns]

    def estimate_radiant_encore_potency(
        self, actions_df: pd.DataFrame, phase=0
    ) -> pd.DataFrame:
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
