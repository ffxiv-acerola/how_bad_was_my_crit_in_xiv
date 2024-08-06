# from .base import BuffQuery, disjunction
from fflogs_rotation.base import BuffQuery, disjunction
import pandas as pd


class DragoonActions(BuffQuery):
    def __init__(
        self,
        headers: dict,
        report_id: int,
        fight_id: int,
        player_id: int,
        patch_number: float,
        fang_and_claw_id: int = 3554,
        wheeling_thrust_id: int = 3556,
        fang_and_claw_bared_id: int = 1000802,
        wheel_in_motion_id: int = 1000803,
        life_of_the_dragon_id: int = 1003177,
    ):
        self.report_id = report_id
        self.fight_id = fight_id
        self.player_id = player_id
        self.patch_number = patch_number

        self.fang_and_claw_id = fang_and_claw_id
        self.wheeling_thrust_id = wheeling_thrust_id

        self.fang_and_claw_bared_id = fang_and_claw_bared_id
        self.wheel_in_motion_id = wheel_in_motion_id

        self.life_of_the_dragon_id = life_of_the_dragon_id
        if patch_number < 7.0:
            self._set_combo_finisher_timings(headers)

        else:
            self._set_life_of_the_dragon_timings(headers)
        pass

    def _set_combo_finisher_timings(self, headers):
        query = """
        query dragoonFinishers(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $fangBaredID: Float!
            $wheelMotionID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    fangBared: events(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $fangBaredID
                    ) {
                        data
                        nextPageTimestamp
                    }
                    
                    wheelMotion: events(
                        fightIDs: $id
                        dataType: Buffs
                        sourceID: $playerID
                        abilityID: $wheelMotionID
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
            "fangBaredID": self.fang_and_claw_bared_id,
            "wheelMotionID": self.wheel_in_motion_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "dragoonFinishers")

        #### Fang and Claw ####
        # Fang and claw timings with applying ability ID
        self.fang_and_claw_bared_times = pd.DataFrame(
            self.request_response["data"]["reportData"]["report"]["fangBared"]["data"]
        )
        # End time
        self.fang_and_claw_bared_times["next_timestamp"] = (
            self.fang_and_claw_bared_times["timestamp"].shift(-1)
        )
        # Filter to buff application and removal timings
        self.fang_and_claw_bared_times = self.fang_and_claw_bared_times[
            self.fang_and_claw_bared_times["type"] == "applybuff"
        ][["timestamp", "next_timestamp", "extraAbilityGameID"]]
        # Absolute timing
        self.fang_and_claw_bared_times[["timestamp", "next_timestamp"]] += (
            self.report_start
        )
        self.fang_and_claw_bared_times = self.fang_and_claw_bared_times.fillna(
            self.fang_and_claw_bared_times["timestamp"].iloc[-1] + 30000
        )
        self.fang_and_claw_bared_times = self.fang_and_claw_bared_times.astype(
            int
        ).to_numpy()

        #### Wheel in motion ###
        # Wheel in motion timings with applying ability ID
        self.life_of_the_dragon_times = pd.DataFrame(
            self.request_response["data"]["reportData"]["report"]["wheelMotion"]["data"]
        )
        # End time
        self.life_of_the_dragon_times["next_timestamp"] = self.life_of_the_dragon_times[
            "timestamp"
        ].shift(-1)
        # Filter to buff application and removal timings
        self.life_of_the_dragon_times = self.life_of_the_dragon_times[
            self.life_of_the_dragon_times["type"] == "applybuff"
        ][["timestamp", "next_timestamp", "extraAbilityGameID"]]
        # Absolute timing
        self.life_of_the_dragon_times[["timestamp", "next_timestamp"]] += (
            self.report_start
        )
        self.life_of_the_dragon_times = self.life_of_the_dragon_times.fillna(
            self.life_of_the_dragon_times["timestamp"].iloc[-1] + 30000
        )

        self.life_of_the_dragon_times = self.life_of_the_dragon_times.astype(
            int
        ).to_numpy()

        pass

    def _set_life_of_the_dragon_timings(self, headers):
        query = """
        query dragoonLOTD(
            $code: String!
            $id: [Int]!
            $playerID: Int!
            $lifeOfTheDragonID: Float!
        ) {
            reportData {
                report(code: $code) {
                    startTime
                    lifeOfTheDragon: table(
                            fightIDs: $id
                            dataType: Buffs
                            sourceID: $playerID
                            abilityID: $lifeOfTheDragonID
                    )
                }
            }
        }
        """

        variables = {
            "code": self.report_id,
            "id": [self.fight_id],
            "playerID": self.player_id,
            "lifeOfTheDragonID": self.life_of_the_dragon_id,
        }

        self._perform_graph_ql_query(headers, query, variables, "dragoonLOTD")

        self.life_of_the_dragon_times = pd.DataFrame(
            self.request_response["data"]["reportData"]["report"]["lifeOfTheDragon"][
                "data"
            ]["auras"][0]["bands"]
        ).astype(int).to_numpy()
        self.life_of_the_dragon_times += self.report_start
        pass

    def apply_endwalker_combo_finisher_potencies(self, actions_df):
        """
        Check if wheeling thrust/fang and claw buffs were applied by the penultimate
        or antepenultimate action in the combo. This dictates if the action gets the
        100 potency bonus.

        We have to go through all this effort to properly account for the combo finisher
        when a position is missed...
        """
        if self.patch_number >= 7.0:
            raise ValueError("This is an Endwalker-specific job mechanic and should not be applied to a post-Endwalker version of Dragoon.")

        #### Wheeling Thrust ####
        wheel_no_finisher_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.life_of_the_dragon_times
            if b[2] == 25772
        )

        wheel_no_finisher_conditions = disjunction(*wheel_no_finisher_betweens) & (
            actions_df["abilityGameID"] == self.wheeling_thrust_id
        )

        wheel_finisher_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.life_of_the_dragon_times
            if b[2] == 3554
        )

        wheel_finisher_conditions = disjunction(*wheel_finisher_betweens) & (
            actions_df["abilityGameID"] == self.wheeling_thrust_id
        )

        #### Fang and Claw ####
        fang_no_finisher_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.fang_and_claw_bared_times
            if b[2] == 25771
        )

        fang_no_finisher_conditions = disjunction(*fang_no_finisher_betweens) & (
            actions_df["abilityGameID"] == self.fang_and_claw_id
        )

        fang_finisher_betweens = list(
            actions_df["timestamp"].between(b[0], b[1], inclusive="right")
            for b in self.fang_and_claw_bared_times
            if b[2] == 3556
        )

        fang_finisher_conditions = disjunction(*fang_finisher_betweens) & (
            actions_df["abilityGameID"] == self.fang_and_claw_id
        )

        actions_df = self._apply_buffs(
            actions_df, wheel_no_finisher_conditions, "no_finisher"
        )
        actions_df = self._apply_buffs(
            actions_df, fang_no_finisher_conditions, "no_finisher"
        )

        actions_df = self._apply_buffs(
            actions_df, wheel_finisher_conditions, "combo_finisher"
        )
        actions_df = self._apply_buffs(
            actions_df, fang_finisher_conditions, "combo_finisher"
        )
        return actions_df


if __name__ == "__main__":
    from fflogs_rotation.rotation import headers

    drg = DragoonActions(headers, "n92HcfwVWKGCq8Jm", 1, 1, 7.01)
    
