import pandas as pd

from fflogs_rotation.base import BuffQuery


class EncounterSpecifics(BuffQuery):
    def __init__(self):
        super().__init__()
        pass

    def fru_apply_vuln_p2(
        self,
        headers: dict[str, str],
        report_id: str,
        fight_id: int,
        actions_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Apply vulnerability down debuff to ice veil from FRU.

        Queries FFLogs for the vulnerability down debuff (ID: 1002198) and applies a
        50% damage reduction to actions that occurred while the debuff was active.

        Args:
            headers (dict[str, str]): Headers for the FFLogs API request
            report_id (str): The FFLogs report ID
            fight_id (int): The specific fight ID within the report
            actions_df (pd.DataFrame): DataFrame containing combat actions

        Returns:
            pd.DataFrame: Modified DataFrame with vulnerability down multipliers applied
        """
        query = """
        query vulnDown(
            $code: String!
            $id: [Int]!
            ) {
            reportData {
                report(code: $code) {
                startTime
                vulnDown: table(
                    fightIDs: $id
                    dataType: Buffs
                    abilityID: 1002198
                    hostilityType: Enemies
                )
                }
            }
        }
        """
        variables = {"code": report_id, "id": [fight_id]}
        response = self.gql_query(headers, query, variables, "vulnDown")

        vuln_times = self._get_buff_times(response, "vulnDown", add_report_start=True)

        # No buff data, do nothing.
        if vuln_times[0][0] == -1:
            return actions_df

        target_id = response["data"]["reportData"]["report"]["vulnDown"]["data"][
            "auras"
        ][0]["id"]
        vuln_condition = (
            actions_df["timestamp"].between(vuln_times[0][0], vuln_times[0][1])
        ) & (actions_df["targetID"] == target_id)

        actions_df = self._apply_buffs(actions_df, vuln_condition, "vuln_down")
        actions_df.loc[vuln_condition, "multiplier"] *= 0.5

        return actions_df

    def m5s_apply_perfect_groove(
        self, headers: dict[str, str], actions_df: pd.DataFrame
    ):
        pass

        if self.encounter_id != 97:
            return actions_df

        GROOVE_BUFF_STRENGTH = 1.03

        query = """
        query groove(
            $code: String!
            $id: [Int]!
            ) {
            reportData {
                report(code: $code) {
                startTime
                inTheGroove: table(
                    fightIDs: $id
                    dataType: Buffs
                    abilityID: 1004464
                )
                }
            }
        }
        """
        variables = {"code": self.report_id, "id": [self.fight_id]}
        response = self.gql_query(headers, query, variables, "groove")

        df = pd.DataFrame(
            response["data"]["reportData"]["report"]["inTheGroove"]["data"]["auras"]
        )

        # Set empty if no Perfect Groove buff
        if df.empty:
            player_buffs = pd.DataFrame()
        else:
            player_buffs = df[df["id"] == self.player_id]

        # Set empty if no pets or no perfect groove buff
        if (self.pet_ids is None) | (df.empty):
            pet_buffs = pd.DataFrame()
        else:
            pet_buffs = df[df["id"].isin(self.pet_ids)]

        if not player_buffs.empty:
            player_buff_times = player_buffs.iloc[0]["bands"]
            player_buff_times = (
                pd.DataFrame(player_buff_times).to_numpy() + self.report_start_time
            )
            groove_betweens = list(
                actions_df["timestamp"].between(b[0], b[1], inclusive="right")
                for b in player_buff_times
            )
            groove_condition = (
                actions_df["sourceID"] == self.player_id
            ) & self.disjunction(*groove_betweens)

            # Update buff list and action name
            actions_df = self._apply_buffs(actions_df, groove_condition, "groove")
            # Apply buff to multiplier
            actions_df.loc[groove_condition, "multiplier"] *= GROOVE_BUFF_STRENGTH
            # TODO: snapshot dots

        # Multiple pets (SMN) can get the buff
        pet_buff_times_dict = {}
        if not pet_buffs.empty:
            for _, row in pet_buffs.iterrows():
                pet_id = row["id"]
                pet_buff_times_dict[pet_id] = (
                    pd.DataFrame(row["bands"]).to_numpy() + self.report_start_time
                )
                groove_betweens = list(
                    actions_df["timestamp"].between(b[0], b[1], inclusive="right")
                    for b in pet_buff_times_dict[pet_id]
                )
                groove_condition = (
                    actions_df["sourceID"] == pet_id
                ) & self.disjunction(*groove_betweens)

                # Update buff list and action name
                actions_df = self._apply_buffs(actions_df, groove_condition, "groove")
                # Apply buff to multiplier
                actions_df.loc[groove_condition, "multiplier"] *= GROOVE_BUFF_STRENGTH
        return actions_df

    def m7s_exclude_final_blooming(self, actions_df, blooming_abomination_game_id: int):
        """Mark the final set of Blooming Abominations to be excluded by.

        Args:
            actions_df (_type_): _description_
            blooming_abomination_game_id (int): _description_
        """

        # We want to keep the first set but exclude the second set.
        # As of now, both sets are marked to be removed by their excluded_enemy_ids.
        # First set is before 200s, make the targetID negative so it doesn't get filtered out.
        # Negative ID is guaranteed to be unique.
        actions_df.loc[
            (actions_df["targetID"] == blooming_abomination_game_id)
            & (actions_df["elapsed_time"] < 200),
            "targetID",
        ] *= -1
        return actions_df
