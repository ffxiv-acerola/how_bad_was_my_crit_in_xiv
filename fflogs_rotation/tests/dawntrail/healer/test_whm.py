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


class TestWhiteMageActions:
    """Tests for White Mage job actions and rotations.

    Based off m2s
    https://www.fflogs.com/reports/8k7xvmRyg6AVMTW1?fight=12
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "8k7xvmRyg6AVMTW1"
        self.fight_id = 12
        self.level = 100
        self.phase = 0
        self.player_id = 24
        self.pet_ids = None

        self.main_stat = 5052
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2803
        self.speed = 420

        self.crt = 3147
        self.dh = 1320
        self.wd = 146

        self.delay = 2.8
        self.medication = 392

        self.t = 511

        self.whm_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "WhiteMage",
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

        self.whm_analysis_7_05 = Healer(
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
    def expected_whm_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Dia (tick)", "n": 168},
                    {"base_action": "Glare III", "n": 147},
                    {"base_action": "Dia", "n": 18},
                    {"base_action": "Glare IV", "n": 15},
                    {"base_action": "Assize", "n": 13},
                    {"base_action": "Afflatus Misery", "n": 8},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_whm_7_05_action_counts(
        self, expected_whm_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values against FFLogs."""
        # Arrange
        actual_counts = (
            self.whm_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_whm_7_05_action_counts)


class TestAstrologianMultiTargetActions:
    """Tests for Astrologian job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/v2ZnTdW67wfXN3gQ?fight=11&type=damage-done&source=5
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "v2ZnTdW67wfXN3gQ"
        self.fight_id = 11
        self.level = 100
        self.phase = 2
        self.player_id = 5
        self.pet_ids = None
        self.excluded_enemy_ids = [35]

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

        self.whm_rotation_7_1_fru_p2 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "WhiteMage",
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

        self.whm_analysis_7_1_fru_p2 = Healer(
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
        self.whm_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "WhiteMage",
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
    def expected_whm_fru_p2_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Dia (tick)", "n": 44},
                    {"base_action": "Glare III", "n": 40},
                    {"base_action": "Assize", "n": 6},
                    {"base_action": "Glare IV", "n": 6},
                    {"base_action": "Dia", "n": 5},
                    {"base_action": "Afflatus Misery", "n": 3},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_whm_fru_p2_action_totals(
        self, expected_whm_fru_p2_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.whm_rotation_7_1_fru_p2.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_whm_fru_p2_7_1_action_counts)

    @pytest.fixture
    def expected_whm_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Dia (tick)", "n": 45},
                    {"base_action": "Glare III", "n": 24},
                    {"base_action": "Assize", "n": 7},
                    {"base_action": "Afflatus Misery", "n": 6},
                    {"base_action": "Glare IV", "n": 6},
                    {"base_action": "Dia", "n": 6},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_whm_fru_p4_action_totals(
        self, expected_whm_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.whm_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_whm_fru_p4_7_1_action_counts)
