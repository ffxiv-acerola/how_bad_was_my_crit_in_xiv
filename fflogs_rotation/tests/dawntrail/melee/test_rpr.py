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


class TestReaperActions:
    """Tests for Reaper job actions and rotations.

    Based off https://www.fflogs.com/reports/tGJzXfrxPjNwWB9p?fight=12
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "tGJzXfrxPjNwWB9p"
        self.fight_id = 12
        self.level = 100
        self.phase = 0
        self.player_id = 6
        self.pet_ids = None

        self.main_stat = 5129
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2258
        self.speed = 420

        self.crt = 1320
        self.dh = 2024
        self.wd = 146

        self.delay = 3.2
        self.medication = 392

        self.t = 401

        self.rpr_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Reaper",
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

        self.rpr_analysis_7_05 = Melee(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Reaper",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_rpr_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 121},
                    {"base_action": "Cross Reaping", "n": 20},
                    {"base_action": "Void Reaping", "n": 20},
                    {"base_action": "Lemure's Slice", "n": 20},
                    {"base_action": "Infernal Slice", "n": 18},
                    {"base_action": "Waxing Slice", "n": 18},
                    {"base_action": "Slice", "n": 18},
                    {"base_action": "Soul Slice", "n": 15},
                    {"base_action": "Shadow of Death", "n": 14},
                    {"base_action": "Communio", "n": 10},
                    {"base_action": "Sacrificium", "n": 10},
                    {"base_action": "Unveiled Gallows", "n": 10},
                    {"base_action": "Gibbet", "n": 9},
                    {"base_action": "Gallows", "n": 9},
                    {"base_action": "Unveiled Gibbet", "n": 9},
                    {"base_action": "Executioner's Gibbet", "n": 7},
                    {"base_action": "Executioner's Gallows", "n": 7},
                    {"base_action": "Gluttony", "n": 7},
                    {"base_action": "Perfectio", "n": 4},
                    {"base_action": "Plentiful Harvest", "n": 4},
                    {"base_action": "Harvest Moon", "n": 1},
                    {"base_action": "Harpe", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_rpr_7_05_action_counts(
        self, expected_rpr_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values against FFLogs aggregation."""
        # Arrange
        actual_counts = (
            self.rpr_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_rpr_7_05_action_counts)
