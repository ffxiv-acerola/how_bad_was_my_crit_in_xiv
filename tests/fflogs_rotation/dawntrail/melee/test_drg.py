import pandas as pd
import pytest
from ffxiv_stats.jobs import Melee
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


class TestDragoonActions:
    """Tests for Dragoon job actions and rotations.

    Eepy Oinkers m3s kill
    https://www.fflogs.com/reports/Fqar3gDdAK79bMWx?fight=10
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "Fqar3gDdAK79bMWx"
        self.fight_id = 10
        self.level = 100
        self.phase = 0
        self.player_id = 2
        self.pet_ids = None

        self.main_stat = 5130
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2150
        self.speed = 420

        self.crt = 3120
        self.dh = 2132
        self.wd = 146

        self.delay = 2.80
        self.medication = 392

        self.t = 507

        self.drg_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Dragoon",
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

        self.drg_analysis_7_05 = Melee(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Dragoon",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_drg_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Drakesbane", "n": 40},
                    {"base_action": "Attack", "n": 178},
                    {"base_action": "Nastrond", "n": 27},
                    {"base_action": "Raiden Thrust", "n": 40},
                    {"base_action": "Starcross", "n": 9},
                    {"base_action": "Heavens' Thrust", "n": 20},
                    {"base_action": "Stardiver", "n": 9},
                    {"base_action": "Wyrmwind Thrust", "n": 19},
                    {"base_action": "Chaotic Spring (tick)", "n": 159},
                    {"base_action": "High Jump", "n": 17},
                    {"base_action": "Lance Barrage", "n": 20},
                    {"base_action": "Chaotic Spring", "n": 20},
                    {"base_action": "Wheeling Thrust", "n": 20},
                    {"base_action": "Fang and Claw", "n": 20},
                    {"base_action": "Spiral Blow", "n": 20},
                    {"base_action": "Rise of the Dragon", "n": 5},
                    {"base_action": "Dragonfire Dive", "n": 5},
                    {"base_action": "Mirage Dive", "n": 17},
                    {"base_action": "Geirskogul", "n": 9},
                    {"base_action": "True Thrust", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_drg_7_05_action_counts(
        self, expected_drg_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values against FFLogs aggregation."""
        # Arrange
        actual_counts = (
            self.drg_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_drg_7_05_action_counts)
