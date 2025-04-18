import pandas as pd

from fflogs_rotation.base import BuffQuery


class EncounterSpecifics(BuffQuery):
    def __init__(self):
        super().__init__()
        pass

    def fru_apply_vuln_p2(self):
        pass

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
