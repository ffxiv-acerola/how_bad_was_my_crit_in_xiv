import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction


class NinjaActions(BuffQuery):
    def __init__(
        self,
        headers: dict[str, str],
        report_id: int,
        fight_id: int,
        player_id: int,
        patch_number: float,
        bhavacakra_id: int = 7402,
        zesho_meppo_id: int = 36960,
        ninjutsu_ids: set[int] = {
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
        """
        Initialize the NinjaActions class.

        Parameters:
            headers (Dict[str, str]): Headers for the GraphQL query.
            report_id (int): Report ID for the fight.
            fight_id (int): Fight ID.
            player_id (int): Player ID.
            patch_number (float): Patch number.
            bhavacakra_id (int): Bhavacakra ability ID.
            zesho_meppo_id (int): Zesho Meppo ability ID.
            ninjutsu_ids (Set[int]): Set of Ninjutsu ability IDs.
            meisui_id (int): Meisui ability ID.
            kassatsu_id (int): Kassatsu ability ID.
            aeolian_edge_id (int): Aeolian Edge ability ID.
            armor_crush_id (int): Armor Crush ability ID.
        """
        super().__init__()

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
        self.meisui_times, self.kassatsu_times = self.set_nin_buff_times(headers)

    def set_nin_buff_times(self, headers: dict[str, str]) -> None:
        """
        Perform an API call to get buff intervals for Meisui and Kassatsu.

        Sets values as a 2 x n Numpy array, where the first column is the start time
        and the second column is the end time.

        Parameters:
            headers (dict[str, str]): FFLogs API header.
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

        nin_buff_response = self.gql_query(headers, query, variables, "ninjaMeisui")
        meisui_times = self._get_buff_times(
            nin_buff_response, "meisui", add_report_start=True
        )
        kassatsu_times = self._get_buff_times(
            nin_buff_response, "kassatsu", add_report_start=True
        )

        return meisui_times, kassatsu_times

    def _track_kazematoi_gauge(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Track the Kazematoi gauge:

        - Max stacks: 5
        - Armor crush: +2
        - Aeolian edge: -1

        Parameters:
            actions_df (pd.DataFrame): Pandas DataFrame of actions.

        Returns:
            pd.DataFrame: DataFrame with tracked Kazematoi gauge.
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

    def apply_ninja_buff(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply buffs for Meisui and Kassatsu to the actions DataFrame.

        Parameters:
            actions_df (pd.DataFrame): DataFrame of actions.

        Returns:
            pd.DataFrame: Updated DataFrame with applied buffs.
        """
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
