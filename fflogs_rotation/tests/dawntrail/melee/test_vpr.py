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
from ffxiv_stats.jobs import Melee


class TestViperActions:
    """Tests for Viper job actions and rotations.

    Based off https://www.fflogs.com/reports/BnkfGc9vt1bRjYZm?fight=46
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "BnkfGc9vt1bRjYZm"
        self.fight_id = 46
        self.level = 100
        self.phase = 0
        self.player_id = 81
        self.pet_ids = None

        self.main_stat = 5107
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2387
        self.speed = 420

        self.crt = 3173
        self.dh = 1842
        self.wd = 146

        self.delay = 2.64
        self.medication = 392

        self.t = 414

        self.vpr_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Viper",
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

        self.vpr_analysis_7_05 = Melee(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Viper",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_vpr_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Ouroboros", "n": 11},
                    {"base_action": "Attack", "n": 178},
                    {"base_action": "First Generation", "n": 11},
                    {"base_action": "Uncoiled Fury", "n": 15},
                    {"base_action": "Reawaken", "n": 11},
                    {"base_action": "Second Generation", "n": 11},
                    {"base_action": "Third Generation", "n": 11},
                    {"base_action": "Fourth Generation", "n": 11},
                    {"base_action": "Hunter's Coil", "n": 11},
                    {"base_action": "Swiftskin's Coil", "n": 11},
                    {"base_action": "Death Rattle", "n": 24},
                    {"base_action": "Vicewinder", "n": 12},
                    {"base_action": "Third Legacy", "n": 11},
                    {"base_action": "Twinfang Bite", "n": 22},
                    {"base_action": "Twinblood Bite", "n": 22},
                    {"base_action": "Swiftskin's Sting", "n": 13},
                    {"base_action": "Reaving Fangs", "n": 13},
                    {"base_action": "First Legacy", "n": 11},
                    {"base_action": "Second Legacy", "n": 11},
                    {"base_action": "Fourth Legacy", "n": 11},
                    {"base_action": "Hunter's Sting", "n": 12},
                    {"base_action": "Steel Fangs", "n": 12},
                    {"base_action": "Flanksbane Fang", "n": 6},
                    {"base_action": "Flanksting Strike", "n": 6},
                    {"base_action": "Hindsbane Fang", "n": 6},
                    {"base_action": "Hindsting Strike", "n": 6},
                    {"base_action": "Uncoiled Twinblood", "n": 15},
                    {"base_action": "Uncoiled Twinfang", "n": 15},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_vpr_7_05_action_counts(
        self, expected_vpr_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values against FFLogs aggregation."""
        # Arrange
        actual_counts = (
            self.vpr_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_vpr_7_05_action_counts)
