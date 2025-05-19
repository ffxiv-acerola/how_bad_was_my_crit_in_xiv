from functools import reduce

import numpy as np
import pandas as pd
import requests

# from fflogs_rotation.rotation import FFLogsClient


url = "https://www.fflogs.com/api/v2/client"


# This is a fun little function which allows an arbitrary
# number of between conditions to be applied.
# This gets used to apply the any buff,
# where the number of "between" conditions could be variable
def disjunction(*conditions):
    return reduce(np.logical_or, conditions)


class FFLogsClient:
    """Responsible for FFLogs API calls."""

    def __init__(self, api_url: str = "https://www.fflogs.com/api/v2/client"):
        self.api_url = api_url

    def gql_query(
        self, headers: dict[str, str], query: str, variables: dict, operation_name: str
    ) -> dict:
        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": operation_name,
        }
        response = requests.post(headers=headers, url=self.api_url, json=json_payload)
        response.raise_for_status()
        return response.json()


class BuffQuery(FFLogsClient):
    """
    Helper class to perform GraphQL queries, get buff timings, and apply buffs to actions.

    Provides base functionality for job-specific buff tracking classes.
    """

    def __init__(self, api_url: str = "https://www.fflogs.com/api/v2/client") -> None:
        super().__init__()
        self.api_url = api_url

    def _get_buff_times(
        self,
        buff_response: dict,
        buff_name: str,
        report_start: int = 0,
        add_report_start: bool = True,
    ) -> np.ndarray:
        """
        Get buff application timing windows.

        Args:
            buff_response: Request response containing aura bands.
            buff_name: Name of buff to get timings for.
            report_start: start time of the report, shifting aura bands to absolute time instead of relative.

        Returns:
            Array of buff timing windows [[start, end], ...]
        """
        if add_report_start:
            report_start = buff_response["data"]["reportData"]["report"]["startTime"]
        aura = buff_response["data"]["reportData"]["report"][buff_name]["data"]["auras"]
        if len(aura) > 0:
            return (pd.DataFrame(aura[0]["bands"])).to_numpy() + report_start
        else:
            return np.array([[-1, -1]])

    def _get_report_start_time(self, response: dict) -> int:
        return response["data"]["reportData"]["report"]["startTime"]

    def _apply_buffs(
        self, actions_df: pd.DataFrame, condition: pd.Series, buff_id: str | int
    ) -> pd.DataFrame:
        """
        Apply a buff to an actions DataFrame.

        Appends the buff ID to `buffs` column.
        Updates the `action_name` column to include the new buff ID.

        Args:
            actions_df: DataFrame of actions
            condition: Boolean mask for which actions to apply buff to
            buff_id: ID of buff to add

        Returns:
            DataFrame with updated buff and action name columns
        """
        actions_df.loc[condition, "buffs"] = actions_df.loc[condition, "buffs"].apply(
            lambda x: x + [str(buff_id)]
        )

        actions_df["action_name"] = (
            actions_df["action_name"].str.split("-").str[0]
            + "-"
            + actions_df["buffs"].sort_values().str.join("_")
        )
        return actions_df

    @staticmethod
    def disjunction(*conditions) -> pd.Series:
        """Take a list of Pandas masks and apply `OR` to all conditions.

        Commonly used to apply buffs to multiple aura windows.

        Returns:
            pd.Series: Boolean mask
        """
        return reduce(np.logical_or, conditions)

    @staticmethod
    def normalize_damage(
        actions_df: pd.DataFrame,
        potion_multiplier: float,
    ) -> pd.DataFrame:
        """Normalize damage variance due to hit types, buffs, and medication.

        Damage bonuses are divided out. Note that the +/- 5% roll is still present.

        Args:
            actions_df (pd.DataFrame): DataFrame of actions, containing damage amount, multiplier, hitType, directHit, and main_stat_add.
            potion_multiplier (float): Damage multiplier for critical hit.

        Returns:
            pd.DataFrame: DataFrame of actions, with a `normalized_damage` field.
        """

        l_c = actions_df["l_c"].iloc[0]

        actions_df["normalized_damage"] = (
            actions_df["amount"] / actions_df["multiplier"]
        )
        actions_df.loc[actions_df["hitType"] == 2, "normalized_damage"] /= l_c / 1000
        actions_df.loc[actions_df["directHit"] == True, "normalized_damage"] /= 1.25

        # Approximately factor out medication buff
        actions_df.loc[actions_df["main_stat_add"] > 0, "normalized_damage"] /= (
            potion_multiplier
        )

        return actions_df

    @staticmethod
    def potency_estimate(
        actions_df: pd.DataFrame,
        d2_100_potency: int,
    ) -> pd.DataFrame:
        """Estimate the potency of an action based off its normalized damage and.

        base damage of a 100 potency action.

        Note that this does not adjust for the +/-5% damage roll.

        Not to be used for DoT damage as FFLogs reports damage amounts that do not
        correspond to the actual potency

        Args:
            actions_df (pd.DataFrame): Actions DataFrame with normalized damage column
            d2_100_potency (int): Base damage from an action with 100 potency.

        Returns:
            pd.DataFrame: Actions DataFrame with estimated potency.
        """
        actions_df["estimated_potency"] = (
            actions_df["normalized_damage"] / d2_100_potency * 100
        )
        return actions_df
