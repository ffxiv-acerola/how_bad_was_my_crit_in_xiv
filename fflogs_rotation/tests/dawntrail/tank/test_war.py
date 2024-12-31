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
from ffxiv_stats.jobs import Tank


class TestWarriorActions:
    """Tests for Warrior job actions and rotations.

    Based off https://www.fflogs.com/reports/2PhAr7tRc8GpKDNa?fight=2
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "2PhAr7tRc8GpKDNa"
        self.fight_id = 2
        self.level = 100
        self.phase = 0
        self.player_id = 5
        self.pet_ids = None

        self.main_stat = 5079
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2525
        self.speed = 420

        self.crt = 3253
        self.dh = 1176
        self.wd = 146

        self.ten = 868

        self.delay = 3.36
        self.medication = 392

        self.t = 545

        self.war_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Warrior",
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

        self.war_analysis_7_05 = Tank(
            self.main_stat,
            self.det,
            self.speed,
            self.ten,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Warrior",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_war_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 159},
                    {"base_action": "Fell Cleave", "n": 48},
                    {"base_action": "Heavy Swing", "n": 44},
                    {"base_action": "Maim", "n": 43},
                    {"base_action": "Storm's Path", "n": 27},
                    {"base_action": "Onslaught", "n": 20},
                    {"base_action": "Upheaval", "n": 18},
                    {"base_action": "Inner Chaos", "n": 16},
                    {"base_action": "Storm's Eye", "n": 16},
                    {"base_action": "Primal Ruination", "n": 9},
                    {"base_action": "Primal Rend", "n": 9},
                    {"base_action": "Primal Wrath", "n": 9},
                    {"base_action": "Damnation", "n": 32},
                    {"base_action": "Tomahawk", "n": 2},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_war_7_05_action_counts(
        self, expected_war_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values against FFlogs."""
        # Arrange
        actual_counts = (
            self.war_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_war_7_05_action_counts)
