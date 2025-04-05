import numpy as np
import pandas as pd

from fflogs_rotation.base import disjunction


class DarkKnightActions:
    """
    Handles Dark Knight specific job mechanics and buff applications.

    Manages Darkside buff tracking, Salted Earth snapshotting, and
    Living Shadow interactions.

    Example:
        >>> drk = DarkKnightActions()
        >>> actions = drk.apply_drk_things(df, player_id=123, pet_id=456)
    """

    def __init__(self, salted_earth_id: int = 1000749) -> None:
        """Initialize Dark Knight actions handler.

        Args:
            salted_earth_id: Buff ID for Salted Earth ability
        """
        self.salted_earth_id = salted_earth_id
        self.no_darkside_time_intervals: np.ndarray = np.array([])

    def when_was_darkside_not_up(
        self, actions_df: pd.DataFrame, player_id: int
    ) -> None:
        """Calculate intervals when Darkside buff is not active.

        Args:
            actions_df: DataFrame containing action events
            player_id: FFLogs player actor ID

        Sets:
            no_darkside_time_intervals: Array of [start, end] times when buff is down
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
        darkside_df["darkside_cd_prior"] = (
            0.0  # darkside timer value before DS extended
        )
        darkside_df["darkside_cd_prior_falloff"] = (
            0.0  # darkside timer value is before DS was extended and if the value could be negative
        )
        darkside_df["darkside_cd_post"] = 30.0  # darkside timer value after DS extended

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

    def apply_darkside_buff(self, action_df: pd.DataFrame, pet_id: int) -> pd.DataFrame:
        """Apply Darkside buff to all actions.

        There are some gotchas, which is why it needs it's own function
            - Salted earth snapshots Darkside.
            - Living shadow does not get Darkside.

        Args:
            action_df: DataFrame of combat actions
            pet_id: FFLogs Living Shadow actor ID

        Returns:
            DataFrame with Darkside buffs applied to valid actions
        """

        no_darkside_conditions = (
            action_df["elapsed_time"].between(b[0], b[1])
            for b in self.no_darkside_time_intervals
        )
        action_df["darkside_buff"] = 1.0
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

    def apply_drk_things(
        self, actions_df: pd.DataFrame, player_id: int, pet_id: int
    ) -> pd.DataFrame:
        """Apply DRK-specific transformations to the actions dataframe including:

        - Estimate damage multiplier for Salted Earth.
        - Figure out when Darkside is up.
        - Apply Darkside to actions affected by Darkside.

        Args:
            actions_df: DataFrame of combat actions
            player_id: FFLogs player actor ID
            pet_id: FFLogs Living Shadow actor ID

        Returns:
            DataFrame with all DRK mechanics applied
        """

        # Find when Darkside is not up
        self.when_was_darkside_not_up(actions_df, player_id)

        # Apply darkside buff, which will correctly:
        #   - Snapshot to Salted Earth
        #   - Not apply to Living Shadow
        actions_df = self.apply_darkside_buff(actions_df, pet_id)
        return actions_df

    pass
