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


class TestMachinistActions:
    """Tests for Machinist job actions and rotations.

    Based off Chocolate Tea's m2s
    https://www.fflogs.com/reports/VpYWQbHmkzvMGXPy?fight=32
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "VpYWQbHmkzvMGXPy"
        self.fight_id = 32
        self.level = 100
        self.phase = 0
        self.player_id = 55
        self.pet_ids = [74]

        self.main_stat = 5130
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2091
        self.speed = 420

        self.crt = 3177
        self.dh = 2134
        self.wd = 146

        self.delay = 2.64
        self.medication = 392

        self.t = 501

        self.mch_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Machinist",
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
            encounter_phases,
            pet_ids=self.pet_ids,
        )

        self.mch_analysis_7_05 = PhysicalRanged(
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
    def expected_mch_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Shot", "n": 188},
                    {"base_action": "Blazing Shot", "n": 70},
                    {"base_action": "Double Check", "n": 53},
                    {"base_action": "Checkmate", "n": 54},
                    {"base_action": "Arm Punch (Pet)", "n": 49},
                    {"base_action": "Heated Clean Shot", "n": 32},
                    {"base_action": "Heated Slug Shot", "n": 32},
                    {"base_action": "Heated Split Shot", "n": 32},
                    {"base_action": "Drill", "n": 27},
                    {"base_action": "Air Anchor", "n": 13},
                    {"base_action": "Pile Bunker (Pet)", "n": 11},
                    {"base_action": "Crowned Collider (Pet)", "n": 11},
                    {"base_action": "Excavator", "n": 9},
                    {"base_action": "Chain Saw", "n": 9},
                    {"base_action": "Full Metal Field", "n": 5},
                    {"base_action": "Wildfire (tick)", "n": 4},
                    {"base_action": "Roller Dash (Pet)", "n": 5},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_mch_7_05_action_counts(
        self, expected_mch_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values 7.05 log."""
        # Arrange
        actual_counts = (
            self.mch_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_mch_7_05_action_counts)


class TestMachinistMultiTargetActions:
    """Tests for MCH job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "ZfnF8AqRaBbzxW3w"
        self.fight_id = 5
        self.level = 100
        self.phase = 4
        self.player_id = 20
        self.pet_ids = [33]
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

        self.mch_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Machinist",
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

        self.mch_analysis_7_1_fru_p4 = PhysicalRanged(
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
    def expected_mch_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Shot", "n": 44},
                    {"base_action": "Checkmate", "n": 29},
                    {"base_action": "Double Check", "n": 27},
                    {"base_action": "Blazing Shot", "n": 20},
                    {"base_action": "Arm Punch (Pet)", "n": 11},
                    {"base_action": "Drill", "n": 7},
                    {"base_action": "Chain Saw", "n": 6},
                    {"base_action": "Excavator", "n": 6},
                    {"base_action": "Heated Clean Shot", "n": 5},
                    {"base_action": "Heated Split Shot", "n": 5},
                    {"base_action": "Full Metal Field", "n": 4},
                    {"base_action": "Air Anchor", "n": 4},
                    {"base_action": "Heated Slug Shot", "n": 4},
                    {"base_action": "Crowned Collider (Pet)", "n": 3},
                    {"base_action": "Pile Bunker (Pet)", "n": 3},
                    {"base_action": "Roller Dash (Pet)", "n": 2},
                    {"base_action": "Wildfire (tick)", "n": 1},
                    {"base_action": "Scattergun", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_mch_fru_p4_action_totals(
        self, expected_mch_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.mch_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_mch_fru_p4_7_1_action_counts)
