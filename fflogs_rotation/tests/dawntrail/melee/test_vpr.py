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
            encounter_phases=encounter_phases,
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


class TestViperMultiTargetActions:
    """Tests for Viper job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "ZfnF8AqRaBbzxW3w"
        self.fight_id = 5
        self.level = 100
        self.phase = 4
        self.player_id = 22
        self.pet_ids = None
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

        self.vpr_rotation_7_1_fru_p4 = RotationTable(
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
            encounter_phases=encounter_phases,
            pet_ids=self.pet_ids,
        )

        self.vpr_analysis_7_1_fru_p4 = Melee(
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

    @pytest.fixture
    def expected_vpr_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 44},
                    {"base_action": "Uncoiled Fury", "n": 8},
                    {"base_action": "Twinblood Bite", "n": 8},
                    {"base_action": "Twinfang Bite", "n": 8},
                    {"base_action": "Uncoiled Twinfang", "n": 8},
                    {"base_action": "Uncoiled Twinblood", "n": 8},
                    {"base_action": "Reawaken", "n": 5},
                    {"base_action": "Death Rattle", "n": 5},
                    {"base_action": "Swiftskin's Coil", "n": 4},
                    {"base_action": "Hunter's Coil", "n": 4},
                    {"base_action": "Ouroboros", "n": 4},
                    {"base_action": "Fourth Generation", "n": 4},
                    {"base_action": "Third Generation", "n": 4},
                    {"base_action": "Second Generation", "n": 4},
                    {"base_action": "First Generation", "n": 4},
                    {"base_action": "First Legacy", "n": 4},
                    {"base_action": "Third Legacy", "n": 4},
                    {"base_action": "Second Legacy", "n": 4},
                    {"base_action": "Fourth Legacy", "n": 4},
                    {"base_action": "Vicewinder", "n": 3},
                    {"base_action": "Reaving Fangs", "n": 3},
                    {"base_action": "Hunter's Sting", "n": 3},
                    {"base_action": "Steel Fangs", "n": 3},
                    {"base_action": "Flanksting Strike", "n": 2},
                    {"base_action": "Swiftskin's Sting", "n": 2},
                    {"base_action": "Flanksbane Fang", "n": 1},
                    {"base_action": "Hindsbane Fang", "n": 1},
                    {"base_action": "Hindsting Strike", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_vpr_fru_p4_action_totals(
        self, expected_vpr_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.vpr_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_vpr_fru_p4_7_1_action_counts)
