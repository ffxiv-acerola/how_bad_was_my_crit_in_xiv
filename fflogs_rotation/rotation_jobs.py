"""Account for job-specific mechanics that affect actions."""

import json
from functools import reduce
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import requests

url = "https://www.fflogs.com/api/v2/client"


# This is a fun little function which allows an arbitrary
# number of between conditions to be applied.
# This gets used to apply the any buff,
# where the number of "between" conditions could be variable


def disjunction(*conditions):
    return reduce(np.logical_or, conditions)


class BuffQuery(object):
    """
    Helper class to perform GraphQL queries and manage buff timings.

    Handles querying FFLogs API for buff data, processing buff timings,
    and applying buffs to action DataFrames.
    """

    def __init__(self) -> None:
        """Initialize BuffQuery instance."""
        self.request_response: Dict[str, Any] = {}
        self.report_start: int = 0

    def _perform_graph_ql_query(
        self,
        headers: Dict[str, str],
        query: str,
        variables: Dict[str, Any],
        operation_name: str,
        report_start: bool = True,
    ) -> None:
        """
        Execute GraphQL query against FFLogs API.

        Args:
            headers: Request headers including auth token
            query: GraphQL query string
            variables: Query variables dictionary
            operation_name: Name of GraphQL operation
            report_start: Whether to extract report start time
        """
        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": operation_name,
        }
        self.request_response = json.loads(
            requests.post(url=url, json=json_payload, headers=headers).text
        )

        if report_start:
            self.report_start = self.request_response["data"]["reportData"]["report"][
                "startTime"
            ]
        pass

    def _get_buff_times(self, buff_name: str, absolute_time: bool = True) -> np.ndarray:
        """
        Get buff application timing windows.

        Args:
            buff_name: Name of buff to get timings for
            absolute_time: If True, add report start time to values

        Returns:
            Array of buff timing windows [[start, end], ...]
        """
        aura = self.request_response["data"]["reportData"]["report"][buff_name]["data"][
            "auras"
        ]
        if len(aura) > 0:
            return (
                pd.DataFrame(aura[0]["bands"]) + (self.report_start * absolute_time)
            ).to_numpy()
        else:
            return np.array([[]])

    def _apply_buffs(
        self, actions_df: pd.DataFrame, condition: pd.Series, buff_id: str
    ) -> pd.DataFrame:
        """
        Apply buff to matching actions in DataFrame.

        Updates the buffs list column and appends the buff ID to action names.

        Args:
            actions_df: DataFrame of actions to update
            condition: Boolean mask for actions to apply buff to
            buff_id: Identifier for buff being applied

        Returns:
            Updated DataFrame with buff information added

        Example:
            >>> df = query._apply_buffs(actions, mask, "chain")
        """

        actions_df.loc[
            condition,
            "buffs",
        ] = actions_df["buffs"].apply(lambda x: x + [str(buff_id)])

        actions_df["action_name"] = (
            actions_df["action_name"].str.split("-").str[0]
            + "-"
            + actions_df["buffs"].sort_values().str.join("_")
        )
        return actions_df


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


class PaladinActions:
    """
    Handles Paladin specific job mechanics and buff applications.

    Manages Requiescat and Divine Might buff tracking and their
    application to Holy Spirit/Circle and blade combo actions.

    Example:
        >>> pld = PaladinActions(headers, "abc123", 1, 16)
        >>> actions = pld.apply_pld_buffs(df)
    """

    def __init__(
        self,
        headers: Dict[str, str],
        report_id: str,
        fight_id: int,
        player_id: int,
        requiescat_id: int = 1001368,
        divine_might_id: int = 1002673,
        holy_ids: List[int] = [7384, 16458],
        blade_ids: List[int] = [16459, 25748, 25749, 25750],
    ) -> None:
        """Initialize Paladin actions handler.

        Args:
            headers: FFLogs API headers with auth token
            report_id: FFLogs report identifier
            fight_id: Fight ID within report
            player_id: FFLogs player actor ID
            requiescat_id: Buff ID for Requiescat
            divine_might_id: Buff ID for Divine Might
            holy_ids: Ability IDs for Holy Spirit/Circle
            blade_ids: Ability IDs for blade combo
        """
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.requiescat_id = requiescat_id
        self.divine_might_id = divine_might_id
        self.holy_ids = holy_ids
        self.blade_ids = blade_ids

        self.set_pld_buff_times(headers)
        pass

    def set_pld_buff_times(self, headers: Dict[str, str]) -> None:
        """Query and set buff timing windows.

        Gets start/end times for Requiescat and Divine Might buffs
        from FFLogs API and stores a a numpy array where each row is [start, end].

        Args:
            headers: FFLogs API headers with auth token
        """
        query = """
        query PaladinBuffs(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $requiescatID: Float!
            $divineMightID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    requiescat: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $requiescatID
                    )
                    divineMight: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $divineMightID
                    )
                }
            }
        }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "requiescatID": self.requiescat_id,
            "divineMightID": self.divine_might_id,
        }

        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": "PaladinBuffs",
        }
        r = requests.post(url=url, json=json_payload, headers=headers)
        r = json.loads(r.text)

        report_start = r["data"]["reportData"]["report"]["startTime"]
        requiescat_auras = r["data"]["reportData"]["report"]["requiescat"]["data"][
            "auras"
        ]
        if len(requiescat_auras) > 0:
            self.requiescat_times = (
                pd.DataFrame(requiescat_auras[0]["bands"]) + report_start
            ).to_numpy()

        divine_might_auras = r["data"]["reportData"]["report"]["divineMight"]["data"][
            "auras"
        ]
        if len(divine_might_auras) > 0:
            self.divine_might_times = (
                pd.DataFrame(divine_might_auras[0]["bands"]) + report_start
            ).to_numpy()

        pass

    def apply_pld_buffs(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """Apply Paladin buff effects to actions.

        Applies Divine Might and Requiescat buffs to Holy Spirit/Circle
        and blade combo actions based on buff timing windows.

        Args:
            actions_df: DataFrame of combat actions

        Returns:
            DataFrame with Paladin buffs applied
        """
        # Check if the timestamp is between any divine might window.
        divine_might_condition = list(
            actions_df["timestamp"].between(b[0], b[1]) for b in self.divine_might_times
        )
        # Check if timestamp is between any requiescat window.
        requiescat_condition = list(
            actions_df["timestamp"].between(b[0], b[1]) for b in self.requiescat_times
        )

        # Holy spirit/circle with Divine might:
        #    - Has Divine Might buff active
        #    - Requiescat irrelevant
        actions_df.loc[
            disjunction(*divine_might_condition)
            & actions_df["abilityGameID"].isin(self.holy_ids),
            "buffs",
        ] = actions_df["buffs"].apply(lambda x: x + [str(self.divine_might_id)])

        # Holy spirit/circle with Requiescat:
        #    - Has requiescat and not divine might buff active
        actions_df.loc[
            ~disjunction(*divine_might_condition)
            & actions_df["abilityGameID"].isin(self.holy_ids)
            & disjunction(*requiescat_condition),
            "buffs",
        ] = actions_df["buffs"].apply(lambda x: x + [str(self.requiescat_id)])
        # Confiteor -> Blade combo
        # Requiescat up
        actions_df.loc[
            disjunction(*requiescat_condition)
            & actions_df["abilityGameID"].isin(self.blade_ids),
            "buffs",
        ] = actions_df["buffs"].apply(lambda x: x + [str(self.requiescat_id)])

        # update action names with new buffs
        actions_df["action_name"] = (
            actions_df["action_name"].str.split("-").str[0]
            + "-"
            + actions_df["buffs"].sort_values().str.join("_")
        )

        return actions_df


class SamuraiActions(BuffQuery):
    """
    Handles Samurai specific job mechanics and buff applications.

    Manages Enhanced Enpi buff tracking and application to actions.
    Inherits from BuffQuery for FFLogs API interactions.
    """

    def __init__(
        self,
        headers: Dict[str, str],
        report_id: str,
        fight_id: int,
        player_id: int,
        enpi_id: int = 7486,
        enhanced_enpi_id: int = 1001236,
    ) -> None:
        """Initialize Samurai actions handler.

        Args:
            headers: FFLogs API headers with auth token
            report_id: FFLogs report identifier
            fight_id: Fight ID within report
            player_id: FFLogs player actor ID
            enpi_id: Ability ID for Enpi
            enhanced_enpi_id: Buff ID for Enhanced Enpi
        """
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id

        self.enpi_id = enpi_id
        self.enhanced_enpi_id = enhanced_enpi_id
        self._set_enhanced_enpi_time(headers)
        pass

    def _set_enhanced_enpi_time(self, headers: Dict[str, str]) -> None:
        """Query and set Enhanced Enpi buff timing windows.

        Args:
            headers: FFLogs API headers with auth token
        """
        query = """
        query samuraiEnpi(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $enhancedEnpiID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    ehancedEnpi: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $enhancedEnpiID
                    )
                }
            }
        }
        """

        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "enhancedEnpiID": self.enhanced_enpi_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "samuraiEnpi")
        self.enhanced_enpi_times = self._get_buff_times("ehancedEnpi")
        pass

    def apply_enhanced_enpi(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """Apply Enhanced Enpi buff to actions.

        Args:
            actions_df: DataFrame of combat actions

        Returns:
            DataFrame with Enhanced Enpi buff applied if present,
            otherwise returns unmodified DataFrame
        """

        if self.enhanced_enpi_times.size == 0:
            return actions_df

        enhanced_enpi_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.enhanced_enpi_times
        )

        enhanced_enpi_condition = disjunction(*enhanced_enpi_betweens) & (
            actions_df["abilityGameID"] == self.enpi_id
        )

        return self._apply_buffs(
            actions_df, enhanced_enpi_condition, self.enhanced_enpi_id
        )


if __name__ == "__main__":
    # from config import FFLOGS_TOKEN

    # api_key = FFLOGS_TOKEN  # or copy/paste your key here
    # headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    # PaladinActions(headers, "M2ZKgJtTqnNjYxCQ", 54, 118)
    # SamuraiActions(headers, "LpHbRKxkAwynaCNv", 44, 79)
    # MachinistActions(headers, "KWZQFHRzDNjd4bth", 29, 1401)
    pass
