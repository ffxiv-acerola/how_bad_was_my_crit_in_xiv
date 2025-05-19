import pandas as pd

from fflogs_rotation.base import BuffQuery, disjunction


class PaladinActions(BuffQuery):
    """
    Handles Paladin specific job mechanics and buff applications.

    Manages Requiescat and Divine Might buff tracking and their
    application to Holy Spirit/Circle and blade combo actions.

    Example:
        >>> pld = PaladinActions(headers, "abc123", 1, 16)
        >>> actions = pld.apply_pld_buffs(df)
    """

    def __init__(
        self,
        headers: dict[str, str],
        report_id: str,
        fight_id: int,
        player_id: int,
        requiescat_id: int = 1001368,
        divine_might_id: int = 1002673,
        holy_ids: list[int] = [7384, 16458],
        blade_ids: list[int] = [16459, 25748, 25749, 25750],
    ) -> None:
        """Initialize Paladin actions handler.

        Args:
            headers: FFLogs API headers with auth token
            report_id: FFLogs report identifier
            fight_id: Fight ID within report
            player_id: FFLogs player actor ID
            requiescat_id: Buff ID for Requiescat
            divine_might_id: Buff ID for Divine Might
            holy_ids: Ability IDs for Holy Spirit/Circle
            blade_ids: Ability IDs for blade combo
        """

        super().__init__()

        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.requiescat_id = requiescat_id
        self.divine_might_id = divine_might_id
        self.holy_ids = holy_ids
        self.blade_ids = blade_ids

        self.divine_might_times, self.requiescat_times = self.set_pld_buff_times(
            headers
        )

        pass

    def set_pld_buff_times(self, headers: dict[str, str]) -> dict:
        """Query and set buff timing windows.

        Gets start/end times for Requiescat and Divine Might buffs
        from FFLogs API and stores a a numpy array where each row is [start, end].

        Args:
            headers: FFLogs API headers with auth token
        """
        query = """
        query PaladinBuffs(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $requiescatID: Float!
            $divineMightID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    requiescat: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $requiescatID
                    )
                    divineMight: table(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $divineMightID
                    )
                }
            }
        }
        """

        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "requiescatID": self.requiescat_id,
            "divineMightID": self.divine_might_id,
        }

        pld_response = self.gql_query(headers, query, variables, "PaladinBuffs")
        divine_might_times = self._get_buff_times(
            pld_response, "divineMight", add_report_start=True
        )
        requiescat_times = self._get_buff_times(
            pld_response, "requiescat", add_report_start=True
        )

        return divine_might_times, requiescat_times

    def apply_pld_buffs(self, actions_df: pd.DataFrame) -> pd.DataFrame:
        """Apply Paladin buff effects to actions.

        Applies Divine Might and Requiescat buffs to Holy Spirit/Circle
        and blade combo actions based on buff timing windows.

        Args:
            actions_df: DataFrame of combat actions

        Returns:
            DataFrame with Paladin buffs applied
        """
        # Check if the timestamp is between any divine might window.
        divine_might_condition = list(
            actions_df["timestamp"].between(b[0], b[1]) for b in self.divine_might_times
        )
        # Check if timestamp is between any requiescat window.
        requiescat_condition = list(
            actions_df["timestamp"].between(b[0], b[1]) for b in self.requiescat_times
        )

        # Holy spirit/circle with Divine might:
        #    - Has Divine Might buff active
        #    - Requiescat irrelevant
        actions_df = self._apply_buffs(
            actions_df,
            (
                disjunction(*divine_might_condition)
                & actions_df["abilityGameID"].isin(self.holy_ids)
            ),
            self.divine_might_id,
        )

        # Holy spirit/circle with Requiescat:
        #    - Has requiescat and not divine might buff active
        actions_df = self._apply_buffs(
            actions_df,
            (
                ~disjunction(*divine_might_condition)
                & actions_df["abilityGameID"].isin(self.holy_ids)
                & disjunction(*requiescat_condition)
            ),
            self.requiescat_id,
        )

        # Confiteor -> Blade combo
        # Requiescat up
        actions_df = self._apply_buffs(
            actions_df,
            (
                disjunction(*requiescat_condition)
                & actions_df["abilityGameID"].isin(self.blade_ids)
            ),
            self.requiescat_id,
        )

        return actions_df
