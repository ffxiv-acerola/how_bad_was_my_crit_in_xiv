import pandas as pd

from fflogs_rotation.actions import ActionTable

url = "https://www.fflogs.com/api/v2/client"


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
        headers: dict[str, str],
        report_id: str,
        fight_id: int,
        job: str,
        player_id: int,
        crit_stat: int,
        dh_stat: int,
        determination: int,
        level: int,
        phase: int,
        damage_buff_table: pd.DataFrame,
        critical_hit_rate_buff_table: pd.DataFrame,
        direct_hit_rate_buff_table: pd.DataFrame,
        guaranteed_hits_by_action_table: pd.DataFrame,
        guaranteed_hits_by_buff_table: pd.DataFrame,
        potency_table: pd.DataFrame,
        encounter_phases,
        pet_ids: list[int] | None = None,
        excluded_enemy_ids: list[int] | None = None,
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
            level,
            phase,
            damage_buff_table,
            critical_hit_rate_buff_table,
            direct_hit_rate_buff_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            encounter_phases,
            pet_ids,
            excluded_enemy_ids,
            debug,
        )

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
        t_end_clip: float | None = None,
        t_start_clip: float | None = None,
        return_clipped: bool = False,
        clipped_portion: str = "end",
    ) -> pd.DataFrame | None:
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

    r = RotationTable(
        # fflogs_client,
        headers,
        "HkwxMGAdLrcyanFB",
        23,
        "Pictomancer",
        327,
        3174,
        1542,
        2310,
        100,
        0,
        damage_buff_table,
        critical_hit_rate_table,
        direct_hit_rate_table,
        guaranteed_hits_by_action_table,
        guaranteed_hits_by_buff_table,
        potency_table,
        encounter_phases,
        excluded_enemy_ids=[425],
        # pet_ids=[36, 35, 38, 34, 32, 37],
    )
    print("")
