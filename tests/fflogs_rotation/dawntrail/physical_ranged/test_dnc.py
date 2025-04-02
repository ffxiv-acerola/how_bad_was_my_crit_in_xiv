import pandas as pd
import pytest
from ffxiv_stats.jobs import PhysicalRanged
from pandas.testing import assert_frame_equal

from crit_app.job_data.encounter_data import encounter_phases
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


class TestDancerActions:
    """Tests for Dancer job actions and rotations.

    Based off https://www.fflogs.com/reports/fYLK6CR7Zrh3a8W2?fight=11
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "fYLK6CR7Zrh3a8W2"
        self.fight_id = 11
        self.level = 100
        self.phase = 0
        self.player_id = 2
        self.pet_ids = None

        self.main_stat = 5130
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2145
        self.speed = 420

        self.crt = 3177
        self.dh = 2080
        self.wd = 146

        self.delay = 3.12
        self.medication = 392

        self.t = 510

        self.dnc_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Dancer",
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
            encounter_phases=encounter_phases,
            pet_ids=self.pet_ids,
        )

        self.dnc_analysis_7_05 = PhysicalRanged(
            self.main_stat,
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
    def expected_dnc_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 162},
                    {"base_action": "Saber Dance", "n": 32},
                    {"base_action": "Cascade", "n": 30},
                    {"base_action": "Fountain", "n": 28},
                    {"base_action": "Reverse Cascade", "n": 23},
                    {"base_action": "Fountainfall", "n": 20},
                    {"base_action": "Last Dance", "n": 17},
                    {"base_action": "Fan Dance", "n": 17},
                    {"base_action": "Fan Dance III", "n": 16},
                    {"base_action": "Finishing Move", "n": 9},
                    {"base_action": "Fan Dance IV", "n": 9},
                    {"base_action": "Double Standard Finish", "n": 8},
                    {"base_action": "Dance of the Dawn", "n": 5},
                    {"base_action": "Quadruple Technical Finish", "n": 5},
                    {"base_action": "Starfall Dance", "n": 5},
                    {"base_action": "Tillana", "n": 5},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_dnc_7_05_action_counts(
        self, expected_dnc_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.dnc_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_dnc_7_05_action_counts)


class TestDancerMultiTargetActions:
    """Tests for MCH job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/fpHz1tM7aQNxwkWd?fight=4&type=damage-done&source=41
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "fpHz1tM7aQNxwkWd"
        self.fight_id = 4
        self.level = 100
        self.phase = 4
        self.player_id = 41
        self.pet_ids = None
        self.excluded_enemy_ids = [68]

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

        self.dnc_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Dancer",
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
            encounter_phases=encounter_phases,
            pet_ids=self.pet_ids,
            excluded_enemy_ids=self.excluded_enemy_ids,
        )

        self.dnc_analysis_7_1_fru_p4 = PhysicalRanged(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            self.pet_attack_power,
            level=self.level,
        )

        ### P2
        self.dnc_rotation_7_1_fru_p2 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Dancer",
            self.player_id,
            self.crt,
            self.dh,
            self.det,
            self.medication,
            self.level,
            2,
            damage_buff_table,
            critical_hit_rate_table,
            direct_hit_rate_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            potency_table,
            encounter_phases=encounter_phases,
            pet_ids=self.pet_ids,
            excluded_enemy_ids=self.excluded_enemy_ids,
        )

        self.dnc_analysis_7_1_fru_p2 = PhysicalRanged(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            self.pet_attack_power,
            level=self.level,
        )

    @pytest.fixture
    def expected_dnc_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 37},
                    {"base_action": "Saber Dance", "n": 11},
                    {"base_action": "Fan Dance III", "n": 11},
                    {"base_action": "Last Dance", "n": 8},
                    {"base_action": "Cascade", "n": 8},
                    {"base_action": "Fan Dance IV", "n": 6},
                    {"base_action": "Reverse Cascade", "n": 6},
                    {"base_action": "Bloodshower", "n": 6},
                    {"base_action": "Double Standard Finish", "n": 5},
                    {"base_action": "Fountain", "n": 5},
                    {"base_action": "Fan Dance", "n": 5},
                    {"base_action": "Fan Dance II", "n": 4},
                    {"base_action": "Dance of the Dawn", "n": 2},
                    {"base_action": "Starfall Dance", "n": 2},
                    {"base_action": "Tillana", "n": 2},
                    {"base_action": "Finishing Move", "n": 2},
                    {"base_action": "Quadruple Technical Finish", "n": 2},
                    {"base_action": "Rising Windmill", "n": 2},
                    {"base_action": "Fountainfall", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_dnc_fru_dnc_p4_action_totals(
        self, expected_dnc_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.dnc_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_dnc_fru_p4_7_1_action_counts)

    @pytest.fixture
    def expected_dnc_fru_p2_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 51},
                    {"base_action": "Saber Dance", "n": 11},
                    {"base_action": "Last Dance", "n": 8},
                    {"base_action": "Double Standard Finish", "n": 6},
                    {"base_action": "Cascade", "n": 7},
                    {"base_action": "Fountainfall", "n": 6},
                    {"base_action": "Fan Dance III", "n": 6},
                    {"base_action": "Fountain", "n": 5},
                    {"base_action": "Reverse Cascade", "n": 4},
                    {"base_action": "Fan Dance", "n": 4},
                    {"base_action": "Finishing Move", "n": 3},
                    {"base_action": "Quadruple Technical Finish", "n": 3},
                    {"base_action": "Tillana", "n": 3},
                    {"base_action": "Fan Dance IV", "n": 3},
                    {"base_action": "Dance of the Dawn", "n": 2},
                    {"base_action": "Starfall Dance", "n": 2},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_dnc_fru_dnc_p2_action_totals(
        self, expected_dnc_fru_p2_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.dnc_rotation_7_1_fru_p2.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_dnc_fru_p2_7_1_action_counts)
