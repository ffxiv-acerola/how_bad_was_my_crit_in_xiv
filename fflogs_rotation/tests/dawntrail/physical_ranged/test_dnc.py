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
from ffxiv_stats.jobs import PhysicalRanged


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
