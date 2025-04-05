import json
from functools import reduce
from typing import Any, Dict, Union

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


class FFLogsClient(object):
    """Responsible for FFLogs API calls."""

    def __init__(self, api_url: str = "https://www.fflogs.com/api/v2/client"):
        self.api_url = api_url

    def gql_query(
        self, headers, query: str, variables: dict, operation_name: str
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
        # self.report_start: int = 0
        # self.request_response: Dict[str, Any] = {}

    # def gql_query(self, headers, query, variables, operation_name):
    #     json_payload = {
    #         "query": query,
    #         "variables": variables,
    #         "operationName": operation_name,
    #     }
    #     response = requests.post(
    #         headers=headers,
    #         url="https://www.fflogs.com/api/v2/client",
    #         json=json_payload,
    #     )
    #     response.raise_for_status()
    #     return response.json()

    # FIXME: WTF was I thinking here
    def _perform_graph_ql_query(
        self,
        headers: Dict[str, str],
        query: str,
        variables: Dict[str, Any],
        operation_name: str,
        report_start: bool = True,
    ) -> None:
        """
        Perform GraphQL query to FFLogs API.

        Args:
            headers: API request headers
            query: GraphQL query string
            variables: Query variables
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

    def _get_buff_times_old(
        self, buff_name: str, absolute_time: bool = True
    ) -> np.ndarray:
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

    def _get_buff_times(
        self,
        buff_response: dict[str, dict],
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
            return (pd.DataFrame(aura[0]["bands"]) + report_start).to_numpy()
        else:
            return np.array([[-1, -1]])

    def _get_report_start_time(self, response: dict[str, dict]) -> int:
        return response["data"]["reportData"]["report"]["startTime"]

    def _apply_buffs(
        self, actions_df: pd.DataFrame, condition: pd.Series, buff_id: Union[str, int]
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
