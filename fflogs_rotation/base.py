import json
from functools import reduce
from typing import Any, Dict, Union

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
    Helper class to perform GraphQL queries, get buff timings, and apply buffs to actions.

    Provides base functionality for job-specific buff tracking classes.
    """

    def __init__(self, api_url: str = "https://www.fflogs.com/api/v2/client") -> None:
        self.api_url = api_url
        self.report_start: int = 0
        self.request_response: Dict[str, Any] = {}

    def gql_query(self, headers, query, variables, operation_name):
        json_payload = {
            "query": query,
            "variables": variables,
            "operationName": operation_name,
        }
        response = requests.post(
            headers=headers,
            url="https://www.fflogs.com/api/v2/client",
            json=json_payload,
        )
        response.raise_for_status()
        return response.json()

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

    def _get_buff_times(self, buff_name: str, absolute_time: bool = True) -> np.ndarray:
        """
        Get buff duration intervals from API response.

        Args:
            buff_name: Name of buff in API response
            absolute_time: Whether to convert to absolute timestamps

        Returns:
            Array of [start_time, end_time] intervals
        """
        aura = self.request_response["data"]["reportData"]["report"][buff_name]["data"][
            "auras"
        ]
        if len(aura) > 0:
            return (
                pd.DataFrame(aura[0]["bands"]) + (self.report_start * absolute_time)
            ).to_numpy()
        else:
            return np.array([[0, 0]])

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
        actions_df.loc[condition, "buffs"] = actions_df["buffs"].apply(
            lambda x: x + [str(buff_id)]
        )

        actions_df["action_name"] = (
            actions_df["action_name"].str.split("-").str[0]
            + "-"
            + actions_df["buffs"].sort_values().str.join("_")
        )
        return actions_df
