import numpy as np
import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction


class SamuraiActions(BuffQuery):
    """
    Handles Samurai specific job mechanics and buff applications.

    Manages Enhanced Enpi buff tracking and application to actions.
    Inherits from BuffQuery for FFLogs API interactions.
    """

    def __init__(
        self,
        headers: dict[str, str],
        report_id: str,
        fight_id: int,
        player_id: int,
        enpi_id: int = 7486,
        enhanced_enpi_id: int = 1001236,
    ) -> None:
        """Initialize Samurai actions handler.

        Args:
            headers: FFLogs API headers with auth token
            report_id: FFLogs report identifier
            fight_id: Fight ID within report
            player_id: FFLogs player actor ID
            enpi_id: Ability ID for Enpi
            enhanced_enpi_id: Buff ID for Enhanced Enpi
        """

        super().__init__()

        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id

        self.enpi_id = enpi_id
        self.enhanced_enpi_id = enhanced_enpi_id

        self.enhanced_enpi_times = self.get_enhanced_enpi_times(headers)
        pass

    def get_enhanced_enpi_times(self, headers: dict[str, str]) -> np.ndarray:
        """Query FFLogs API to get enhanced Enpi bands.

        Args:
            headers (dict[str, str]): Authorization headers

        Returns:
            np.ndarray: n x 2 numpy array of buff times, (buff start, buff end]
        """
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
                    enhancedEnpi: table(
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

        response = self.gql_query(headers, query, variables, "samuraiEnpi")
        return self._get_buff_times(response, "enhancedEnpi", add_report_start=True)

    def apply_enhanced_enpi(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """Apply Enhanced Enpi buff to actions.

        Args:
            actions_df: DataFrame of combat actions

        Returns:
            pd.DataFrame: Actions DataFrame with enhanced Enpi buff applied.
        """

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
