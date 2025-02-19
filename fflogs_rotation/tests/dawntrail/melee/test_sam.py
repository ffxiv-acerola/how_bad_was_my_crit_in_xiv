import pandas as pd
import pytest
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
from ffxiv_stats.jobs import Melee


class TestSamuraiActions:
    """Tests for Samurai job actions and rotations.

    Based off https://www.fflogs.com/reports/Lw7PgrFVcA1GNqnh?fight=6
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "Lw7PgrFVcA1GNqnh"
        self.fight_id = 6
        self.level = 100
        self.phase = 0
        self.player_id = 3
        self.pet_ids = None

        self.main_stat = 5114
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 1931
        self.speed = 420

        self.crt = 3103
        self.dh = 2095
        self.wd = 146

        self.delay = 2.64
        self.medication = 392

        self.t = 515

        self.sam_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Samurai",
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

        self.sam_analysis_7_05 = Melee(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Samurai",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_sam_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 202},
                    {"base_action": "Higanbana (tick)", "n": 159},
                    {"base_action": "Gyofu", "n": 53},
                    {"base_action": "Hissatsu: Shinten", "n": 51},
                    {"base_action": "Gekko", "n": 32},
                    {"base_action": "Kasha", "n": 27},
                    {"base_action": "Yukikaze", "n": 27},
                    {"base_action": "Jinpu", "n": 16},
                    {"base_action": "Kaeshi: Setsugekka", "n": 15},
                    {"base_action": "Midare Setsugekka", "n": 15},
                    {"base_action": "Shoha", "n": 13},
                    {"base_action": "Shifu", "n": 12},
                    {"base_action": "Tendo Kaeshi Setsugekka", "n": 11},
                    {"base_action": "Tendo Setsugekka", "n": 11},
                    {"base_action": "Hissatsu: Senei", "n": 9},
                    {"base_action": "Higanbana", "n": 8},
                    {"base_action": "Hissatsu: Gyoten", "n": 7},
                    {"base_action": "Kaeshi: Namikiri", "n": 5},
                    {"base_action": "Ogi Namikiri", "n": 5},
                    {"base_action": "Zanshin", "n": 5},
                    {"base_action": "Enpi", "n": 2},
                    {"base_action": "Hissatsu: Yaten", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_sam_7_05_action_counts(
        self, expected_sam_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.sam_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_sam_7_05_action_counts)
