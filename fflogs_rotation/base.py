import json
from functools import reduce

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
