import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from fflogs_rotation.job_data.data import (
    critical_hit_rate_table,
    damage_buff_table,
    direct_hit_rate_table,
    guaranteed_hits_by_action_table,
    guaranteed_hits_by_buff_table,
    potency_table,
)
from fflogs_rotation.rotation import RotationTable
from fflogs_rotation.tests.config import headers
from ffxiv_stats.jobs import Healer


class TestAstrologianActions:
    """Tests for Astrologian job actions and rotations.

    Based of Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 8
        self.pet_ids = [12]

        self.main_stat = 5091
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 3043
        self.speed = 528

        self.crt = 2922
        self.dh = 1050
        self.wd = 146

        self.delay = 3.2
        self.medication = 392

        self.t = 393.947

        self.ast_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Astrologian",
            self.player_id,
            self.crt,
            self.dh,
            self.det,
            self.medication,
            self.level,
            self.phase,
            damage_buff_table,
            critical_hit_rate_table,
            direct_hit_rate_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            potency_table,
            pet_ids=self.pet_ids,
        )

        self.ast_analysis_7_05 = Healer(
            self.main_stat,
            400,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_ast_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                {
                    "base_action": [
                        "Fall Malefic",
                        "Combust III (tick)",
                        "Oracle",
                        "Stellar Explosion (Pet)",
                        "Lord of Crowns",
                        "Macrocosmos",
                    ],
                    "n": [138, 127, 4, 7, 4, 2],
                }
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_ast_7_05_action_counts(
        self, expected_ast_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.ast_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_ast_7_05_action_counts)


class TestAstrologianMultiTargetActions:
    """Tests for Astrologian job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "ZfnF8AqRaBbzxW3w"
        self.fight_id = 5
        self.level = 100
        self.phase = 2
        self.player_id = 27
        self.pet_ids = [30]
        self.excluded_enemy_ids = [52]

        self.main_stat = 5129
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 3043
        self.speed = 420

        self.crt = 2922
        self.dh = 1050
        self.wd = 146

        self.delay = 3.2
        self.medication = 392

        self.t = 1

        self.ast_rotation_7_1_fru_p2 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Astrologian",
            self.player_id,
            self.crt,
            self.dh,
            self.det,
            self.medication,
            self.level,
            self.phase,
            damage_buff_table,
            critical_hit_rate_table,
            direct_hit_rate_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            potency_table,
            pet_ids=self.pet_ids,
            excluded_enemy_ids=self.excluded_enemy_ids,
        )

        self.ast_analysis_7_1_fru_p2 = Healer(
            self.main_stat,
            400,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

        ####### P4
        self.ast_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Astrologian",
            self.player_id,
            self.crt,
            self.dh,
            self.det,
            self.medication,
            self.level,
            4,
            damage_buff_table,
            critical_hit_rate_table,
            direct_hit_rate_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            potency_table,
            pet_ids=self.pet_ids,
            excluded_enemy_ids=self.excluded_enemy_ids,
        )

    @pytest.fixture
    def expected_ast_fru_p2_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                {
                    "base_action": [
                        "Fall Malefic",
                        "Combust III (tick)",
                        "Oracle",
                        "Lord of Crowns",
                        "Stellar Explosion (Pet)",
                    ],
                    "n": [49, 49, 2, 3, 4],
                }
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_ast_fru_p2_action_totals(
        self, expected_ast_fru_p2_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.ast_rotation_7_1_fru_p2.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_ast_fru_p2_7_1_action_counts)

    @pytest.fixture
    def expected_ast_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                {
                    "base_action": [
                        "Combust III (tick)",
                        "Gravity II",
                        "Fall Malefic",
                        "Stellar Explosion (Pet)",
                        "Oracle",
                        "Lord of Crowns",
                        "Macrocosmos",
                    ],
                    "n": [48, 20, 14, 3, 2, 2, 2],
                }
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_ast_fru_p4_action_totals(
        self, expected_ast_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.ast_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_ast_fru_p4_7_1_action_counts)
