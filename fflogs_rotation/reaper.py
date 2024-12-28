from typing import Dict

import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction


class ReaperActions(BuffQuery):
    def __init__(
        self,
        headers: dict,
        report_id: int,
        fight_id: int,
        player_id: int,
        cross_reaping_id: int = 24396,
        gallows_id: int = 24383,
        gibbet_id: int = 24382,
        void_reaping_id: int = 24395,
        executioners_gibbet_id: int = 0,
        executioners_gallows_id: int = 0,
        plentiful_harvest_id: int = 24385,
        enhanced_cross_reaping_id: int = 1002591,
        enhanced_gallows_id: int = 1002589,
        enhanced_gibbet_id: int = 1002588,
        enhanced_void_reaping_id: int = 1002590,
        immortal_sacrifice_id: int = 1002592,
    ) -> None:
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id

        self.cross_reaping_id = cross_reaping_id
        self.gallows_id = gallows_id
        self.gibbet_id = gibbet_id
        self.void_reaping_id = void_reaping_id
        self.executioners_gibbet_id = executioners_gibbet_id
        self.executioners_gallows_id = executioners_gallows_id

        self.plentiful_harvest_id = plentiful_harvest_id

        self.enhanced_cross_reaping_id = enhanced_cross_reaping_id
        self.enhanced_gallows_id = enhanced_gallows_id
        self.enhanced_gibbet_id = enhanced_gibbet_id
        self.enhanced_void_reaping_id = enhanced_void_reaping_id
        self.immortal_sacrifice_id = immortal_sacrifice_id

        self.set_enhanced_times(headers)
        pass

    def set_enhanced_times(self, headers: Dict[str, str]) -> None:
        """
        Perform an API call to get buff intervals for enhanced abilities and immortal sacrifice stacks.

        Sets values as a 2 x n Numpy array, where the first column is the start time
        and the second column is the end time.

        Parameters:
            headers (Dict[str, str]): FFLogs API header.
        """
        query = """
        query reaperEnhanced(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $enhancedCrossReapingID: Float!
            $enhancedGallowsID: Float!
            $enhancedGibbetID: Float!
            $enhancedVoidReapingID: Float!
            $immortalSacrificeID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    enhancedCrossReaping: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $enhancedCrossReapingID
                    )
                    enhancedGallows: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $enhancedGallowsID
                    )
                    enhancedGibbet: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $enhancedGibbetID
                    )
                    enhancedVoidReaping: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $enhancedVoidReapingID
                    )
                    immortalSacrifice: events(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $immortalSacrificeID
                    ) {
                        data
                        nextPageTimestamp
                    }
                }
            }
        }
        """
        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "enhancedCrossReapingID": self.enhanced_cross_reaping_id,
            "enhancedGallowsID": self.enhanced_gallows_id,
            "enhancedGibbetID": self.enhanced_gibbet_id,
            "enhancedVoidReapingID": self.enhanced_void_reaping_id,
            "immortalSacrificeID": self.immortal_sacrifice_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "reaperEnhanced")
        self.enhanced_cross_reaping_times = self._get_buff_times("enhancedCrossReaping")
        self.enhanced_gallows_times = self._get_buff_times("enhancedGallows")
        self.enhanced_gibbet_times = self._get_buff_times("enhancedGibbet")
        self.enhanced_void_reaping_times = self._get_buff_times("enhancedVoidReaping")

        # Track immortal sacrifice stacks because sometimes dancer doesn't proc it.
        self.immortal_sacrifice_times = pd.DataFrame(
            self.request_response["data"]["reportData"]["report"]["immortalSacrifice"][
                "data"
            ]
        )
        self.immortal_sacrifice_times["prior_stacks"] = self.immortal_sacrifice_times[
            "stack"
        ].shift(1)
        # Get number of stacks
        self.immortal_sacrifice_times = self.immortal_sacrifice_times[
            self.immortal_sacrifice_times["type"].isin(["applybuff", "removebuff"])
        ][["timestamp", "type", "stack", "prior_stacks"]]

        # Get time bands
        self.immortal_sacrifice_times["prior_timestamp"] = (
            self.immortal_sacrifice_times["timestamp"].shift(1)
        )

        self.immortal_sacrifice_times = self.immortal_sacrifice_times[
            self.immortal_sacrifice_times["type"] == "removebuff"
        ][["prior_timestamp", "timestamp", "prior_stacks"]]
        # Absolute timing
        self.immortal_sacrifice_times[["timestamp", "prior_timestamp"]] += (
            self.report_start
        )
        self.immortal_sacrifice_times = self.immortal_sacrifice_times.fillna(
            self.immortal_sacrifice_times["timestamp"].iloc[-1] + 30000
        )

        self.immortal_sacrifice_times = self.immortal_sacrifice_times.astype(
            int
        ).to_numpy()
        pass

    def apply_enhanced_buffs(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply enhanced buffs to the actions DataFrame.

        Parameters:
            actions_df (pd.DataFrame): DataFrame of actions.

        Returns:
            pd.DataFrame: Updated DataFrame with applied buffs.
        """
        # Enhanced cross reaping
        enhanced_cross_reaping_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.enhanced_cross_reaping_times
        )

        enhanced_cross_reaping_condition = disjunction(
            *enhanced_cross_reaping_betweens
        ) & (actions_df["abilityGameID"] == self.cross_reaping_id)

        # Enhanced gallows
        enhanced_gallows_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.enhanced_gallows_times
        )

        enhanced_gallows_condition = disjunction(*enhanced_gallows_betweens) & (
            actions_df["abilityGameID"] == self.gallows_id
        )

        # Enhanced gibbet
        enhanced_gibbet_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.enhanced_gibbet_times
        )

        enhanced_gibbet_condition = disjunction(*enhanced_gibbet_betweens) & (
            actions_df["abilityGameID"] == self.gibbet_id
        )

        # Enhanced harpe
        enhanced_void_reaping_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.enhanced_void_reaping_times
        )

        enhanced_void_reaping_condition = disjunction(
            *enhanced_void_reaping_betweens
        ) & (actions_df["abilityGameID"] == self.void_reaping_id)

        # Immortal sacrifice stacks, which affect plentiful harvest potency.
        # Dancer is dumb because they dont always trigger a stack.
        for s in range(6, 9):
            plentiful_harvest_betweens = list(
                actions_df["timestamp"].between(b[0], b[1], inclusive="right")
                for b in self.immortal_sacrifice_times
                if b[2] == s
            )

            if len(plentiful_harvest_betweens) > 0:
                plentiful_harvest_condition = disjunction(
                    *plentiful_harvest_betweens
                ) & (actions_df["abilityGameID"] == self.plentiful_harvest_id)

                actions_df = self._apply_buffs(
                    actions_df, plentiful_harvest_condition, f"immortal_sac_{s}"
                )

        actions_df = self._apply_buffs(
            actions_df, enhanced_cross_reaping_condition, self.enhanced_cross_reaping_id
        )
        actions_df = self._apply_buffs(
            actions_df, enhanced_gallows_condition, self.enhanced_gallows_id
        )
        actions_df = self._apply_buffs(
            actions_df, enhanced_gibbet_condition, self.enhanced_gibbet_id
        )
        actions_df = self._apply_buffs(
            actions_df, enhanced_void_reaping_condition, self.enhanced_void_reaping_id
        )

        # Dawntrail actions
        # Executioner's Gibbet
        actions_df = self._apply_buffs(
            actions_df, enhanced_gibbet_condition, self.executioners_gibbet_id
        )

        # Executioners Gallows
        actions_df = self._apply_buffs(
            actions_df, enhanced_gallows_condition, self.executioners_gallows_id
        )

        return actions_df
