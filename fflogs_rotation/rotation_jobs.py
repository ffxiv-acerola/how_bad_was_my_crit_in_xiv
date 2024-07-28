"""Account for job-specific mechanics that affect actions."""

from functools import reduce
import json

import numpy as np
import pandas as pd
import requests

from ffxiv_stats import Rate

url = "https://www.fflogs.com/api/v2/client"


# This is a fun little function which allows an arbitrary
# number of between conditions to be applied.
# This gets used to apply the any buff,
# where the number of "between" conditions could be variable


def disjunction(*conditions):
    return reduce(np.logical_or, conditions)


class BuffQuery(object):
    def __init__(
        self,
    ) -> None:
        """Helper class to perform GraphQL queries, get buff timings, and and apply buffs to an actions DataFrame."""
        pass

    def _perform_graph_ql_query(
        self, headers, query, variables, operation_name, report_start=True
    ):
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

    def _get_buff_times(self, buff_name, absolute_time=True):
        aura = self.request_response["data"]["reportData"]["report"][buff_name]["data"][
            "auras"
        ]
        if len(aura) > 0:
            return (
                pd.DataFrame(aura[0]["bands"]) + (self.report_start * absolute_time)
            ).to_numpy()
        else:
            return np.array([[]])

    def _apply_buffs(self, actions_df, condition, buff_id):
        """Apply a buff to an actions DataFrame.
        Updates the buffs list column and appends the buff ID to the action_name column

        Args:
            actions_df (DataFrame): Pandas DataFrame of actions
            condition (bool): condition for which actions the buffs should be applied to.
            buff_id (str): Buff to add to `buffs` and `action_name` columns
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


class DarkKnightActions(object):
    def __init__(
        self,
        salted_earth_id=1000749,
    ) -> None:
        """Apply Dark Knight-specific job mechanics to actions:

        * When Darkside was up
        * Applying Darkside to actions, including snapshotting Salted Earth and excluding Living Shadow.

        Args:
            salted_earth_id (int, optional): Buff ID of Salted Earth. Defaults to 1000749.
        """
        self.salted_earth_id = salted_earth_id
        pass

    def when_was_darkside_not_up(self, actions_df, player_id):
        """Set time intervals in seconds when Darkside is not up as `self.no_darkside_time_intervals`.
        The variable is a 2 x n numpy array where is row the time interval where Darkside is not up,
        the first column is the beginning time, and the second column is the end time.

        Args:
            actions_df (DataFrame): Action dataframe from ActionTable class
            player_id (int): FFLogs-assigned actor ID of the player.
                             Used to exclude Edge of Shadow from Living Shadow.
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
        darkside_df["darkside_cd_prior"] = 0  # darkside timer value before DS extended
        darkside_df["darkside_cd_prior_falloff"] = (
            0  # darkside timer value is before DS was extended and if the value could be negative
        )
        darkside_df["darkside_cd_post"] = 30  # darkside timer value after DS extended

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

    def apply_darkside_buff(self, action_df, pet_id):
        """Apply Darkside buff to all actions. There are some gotchas, which is why it needs it's own function
            * Salted earth snapshots Darkside.
            * Living shadow does not get Darkside.

        Args:
            action_df (DataFrame): Action data frame from the ActionTable class.
            pet_id (int): FFLogs-assigned actor ID of Living Shadow.

        Returns:
            DataFrame: Action data frame with Darkside properly applied.
        """

        no_darkside_conditions = (
            action_df["elapsed_time"].between(b[0], b[1])
            for b in self.no_darkside_time_intervals
        )
        action_df["darkside_buff"] = 1
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

    def apply_drk_things(self, actions_df, player_id, pet_id):
        """Apply DRK-specific transformations to the actions dataframe including:
        * Estimate damage multiplier for Salted Earth.
        * Figure out when Darkside is up.
        * Apply Darkside to actions affected by Darkside.

        Args:
            actions_df (DataFrame): Actions data frame from the ActionTable class
            player_id (int): FFLogs-assigned actor ID of the player.
            pet_id (int): FFLogs-assigned actor ID of Living Shadow.

        Returns:
            DataFrame: Actions data frame with DRK-specific mechanics applied.
        """

        # Find when Darkside is not up
        self.when_was_darkside_not_up(actions_df, player_id)

        # Apply darkside buff, which will correctly:
        #   - Snapshot to Salted Earth
        #   - Not apply to Living Shadow
        actions_df = self.apply_darkside_buff(actions_df, pet_id)
        return actions_df

    pass


class PaladinActions(object):
    def __init__(
        self,
        headers: dict,
        report_id: str,
        fight_id: int,
        player_id: int,
        requiescat_id=1001368,
        divine_might_id=1002673,
        holy_ids=[7384, 16458],
        blade_ids=[16459, 25748, 25749, 25750],
    ) -> None:
        """Apply Paladin-specific job mechanics to actions:
            * See when Divine Might and Requiescat are up.
            * Apply them in the correct order to actions whose potencies are
              affected by these buffs.

        Args:
            headers (dict): FFLogs API header, required to make an additional buff API call.
                            The bearer key is not saved.
            report_id (str): FFLogs report ID
            fight_id (int): Associated fight ID
            player_id (int): FFLogs-assigned actor ID to the PLD
            requiescat_id (int, optional): ID of Requiescat. Defaults to 1001368.
            divine_might_id (int, optional): ID of Divine Might. Defaults to 1002673.
            holy_ids (list, optional): ID of Holy Spirit and Holy Circle. Defaults to [7384, 16458].
            blade_ids (list, optional): IDs of Confiteor, Blade of {Faith, Truth, Valor}.
                                        Defaults to [16459, 25748, 25749, 25750]
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

    def set_pld_buff_times(self, headers):
        """Perform an API call to get buff intervals for Requiescat and Divine Might.
        Sets values as a 2 x n Numpy array, where the first column is the start time
        and the second column is the end time.

        Args:
            headers (dict): FFLogs API header.

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

    def apply_pld_buffs(self, actions_df):
        """Apply Divine Might and Requiescat to actions which are affected by them.
        This information will be used to map those actions to the correct potencies.
        This is really just to check the rotation has not gone horribly, horribly wrong,
        or some serious cooking is happening.

        Args:
            actions_df (DataFrame): Actions data frame from the ActionTable class.
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
    def __init__(
        self,
        headers: dict,
        report_id: int,
        fight_id: int,
        player_id: int,
        enpi_id: int = 7486,
        enhanced_enpi_id: int = 1001236,
    ) -> None:
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id

        self.enpi_id = enpi_id
        self.enhanced_enpi_id = enhanced_enpi_id
        self._set_enhanced_enpi_time(headers)
        pass

    def _set_enhanced_enpi_time(self, headers):
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

    def apply_enhanced_enpi(self, actions_df):
        """Apply enhanced enpi buff actions DataFrame. If no enhanced enpi is present, return the unaltered DataFrame

        Args:
            actions_df (_type_): DataFrame of actions.

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
    from config import FFLOGS_TOKEN

    api_key = FFLOGS_TOKEN  # or copy/paste your key here
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    # PaladinActions(headers, "M2ZKgJtTqnNjYxCQ", 54, 118)
    # SamuraiActions(headers, "LpHbRKxkAwynaCNv", 44, 79)
    # MachinistActions(headers, "KWZQFHRzDNjd4bth", 29, 1401)
    pass
