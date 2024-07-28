# from ..rotation_jobs.base import BuffQuery, disjunction
from .base import BuffQuery, disjunction


class NinjaActions(BuffQuery):
    def __init__(
        self,
        headers: dict,
        report_id: int,
        fight_id: int,
        player_id: int,
        patch_number: float,
        bhavacakra_id: int = 7402,
        zesho_meppo_id: int = 36960,
        ninjutsu_ids: set = {  # why are there so many dupes
            2265,
            18873,
            18874,
            18875,
            18876,
            2267,
            18877,
            2271,
            18881,
            16491,
            16492,
            18879,
            2269,
            18881,
        },
        meisui_id: int = 1002689,
        kassatsu_id: int = 1000497,
        aeolian_edge_id: int = 2255,
        armor_crush_id: int = 3563,
    ) -> None:
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.patch_number = patch_number
        self.bhavacakra_id = bhavacakra_id
        self.zesho_meppo_id = zesho_meppo_id
        self.ninjutsu_id = ninjutsu_ids
        self.meisui_id = meisui_id
        self.kassatsu_id = kassatsu_id
        self.aeolian_edge_id = aeolian_edge_id
        self.armor_crush_id = armor_crush_id
        self.set_meisui_times(headers)
        pass

    def set_meisui_times(self, headers):
        """Perform an API call to get buff intervals for Requiescat and Divine Might.
        Sets values as a 2 x n Numpy array, where the first column is the start time
        and the second column is the end time.

        Args:
            headers (dict): FFLogs API header.

        """
        query = """
        query ninjaMeisui(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $meisuiID: Float!
            $kassatsuID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    meisui: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $meisuiID
                    )
                    kassatsu: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $kassatsuID
                    )
                }
            }
        }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "meisuiID": self.meisui_id,
            "kassatsuID": self.kassatsu_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "ninjaMeisui")
        self.meisui_times = self._get_buff_times("meisui")
        self.kassatsu_times = self._get_buff_times("kassatsu")
        pass

    def _track_kazematoi_gauge(self, actions_df):
        """Track the Kazematoi gauge:
        - Max stacks: 5
        - Armor crush: +2
        - Aeolian edge: -1

        Args:
            actions_df (DataFrame): Pandas DataFrame of actions
        """
        kazematoi_df = actions_df[
            actions_df["abilityGameID"].isin(
                [self.aeolian_edge_id, self.armor_crush_id]
            )
        ][["elapsed_time", "abilityGameID", "ability_name"]].sort_values("elapsed_time")

        # FIXME: Create general gauge function
        kazematoi_df["change"] = 2
        kazematoi_df.loc[kazematoi_df["abilityGameID"] == 2255, "change"] = -1

        stacks = [0]
        # There isn't an easy way to broadcast this because kazematoi stacks are bounded from [0, 5]
        # For loop it is
        for idx in range(1, len(kazematoi_df)):
            # max and min function keeps stacks bounded between 0 and 5
            stacks.append(
                max(0, min(5, kazematoi_df.iloc[idx - 1]["change"] + stacks[idx - 1]))
            )

        kazematoi_df["initial_stacks"] = stacks
        return kazematoi_df

    def apply_ninja_buff(self, actions_df):
        meisui_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.meisui_times
        )

        meisui_condition = disjunction(*meisui_betweens) & (
            actions_df["abilityGameID"].isin([self.zesho_meppo_id, self.bhavacakra_id])
        )

        kassatsu_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.kassatsu_times
        )

        kassatsu_conditions = disjunction(*kassatsu_betweens) * actions_df[
            "abilityGameID"
        ].isin(self.ninjutsu_id)
        actions_df = self._apply_buffs(actions_df, meisui_condition, self.meisui_id)
        actions_df = self._apply_buffs(
            actions_df, kassatsu_conditions, self.kassatsu_id
        )

        actions_df.loc[
            kassatsu_conditions & actions_df["abilityGameID"].isin(self.ninjutsu_id),
            "multiplier",
        ] *= 1.3

        # Kazematoi is a 7.0 change
        # Ignore if actions are from Endwalker or earlier.
        if self.patch_number >= 7.0:
            kazematoi_df = self._track_kazematoi_gauge(actions_df)
            buffed_aeolian_indices = kazematoi_df[
                (kazematoi_df["change"] == -1) & (kazematoi_df["initial_stacks"] > 0)
            ].index

            return self._apply_buffs(
                actions_df, actions_df.index.isin(buffed_aeolian_indices), "kazematoi"
            )

        else:
            return actions_df
