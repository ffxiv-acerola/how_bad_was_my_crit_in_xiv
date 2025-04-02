import pandas as pd
import pytest
from ffxiv_stats.jobs import Tank
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


class TestPaladinActions:
    """Tests for Paladin job actions and rotations.

    Based off https://www.fflogs.com/reports/LP9n81AgjTQb2pXY?fight=1
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "LP9n81AgjTQb2pXY"
        self.fight_id = 1
        self.level = 100
        self.phase = 0
        self.player_id = 3
        self.pet_ids = None

        self.main_stat = 5059
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2310
        self.speed = 420

        self.crt = 3174
        self.dh = 1470
        self.wd = 146

        self.ten = 868

        self.delay = 2.24
        self.medication = 392

        self.t = 566

        self.pld_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Paladin",
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

        self.pld_analysis_7_05 = Tank(
            self.main_stat,
            self.det,
            self.speed,
            self.ten,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Paladin",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_pld_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 238},
                    {"base_action": "Holy Spirit", "n": 27},
                    {"base_action": "Supplication", "n": 25},
                    {"base_action": "Atonement", "n": 25},
                    {"base_action": "Royal Authority", "n": 25},
                    {"base_action": "Riot Blade", "n": 25},
                    {"base_action": "Fast Blade", "n": 25},
                    {"base_action": "Sepulchre", "n": 24},
                    {"base_action": "Intervene", "n": 20},
                    {"base_action": "Expiacion", "n": 19},
                    {"base_action": "Circle of Scorn", "n": 19},
                    {"base_action": "Confiteor", "n": 10},
                    {"base_action": "Blade of Honor", "n": 10},
                    {"base_action": "Blade of Valor", "n": 10},
                    {"base_action": "Blade of Truth", "n": 10},
                    {"base_action": "Blade of Faith", "n": 10},
                    {"base_action": "Goring Blade", "n": 10},
                    {"base_action": "Imperator", "n": 10},
                    {"base_action": "Circle of Scorn (tick)", "n": 91},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_pld_7_05_action_counts(
        self, expected_pld_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values against FFlogs."""
        # Arrange
        actual_counts = (
            self.pld_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_pld_7_05_action_counts)


class TestPaladinMultiTargetActions:
    """Tests for Gunbreaker job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/rJKhQHPpCk68xV3m?fight=17
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "rJKhQHPpCk68xV3m"
        self.fight_id = 17
        self.level = 100
        self.phase = 4
        self.player_id = 2
        self.pet_ids = None
        self.excluded_enemy_ids = [29]

        self.main_stat = 5059
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2310
        self.speed = 420

        self.crt = 3174
        self.dh = 1470
        self.wd = 146

        self.ten = 868

        self.delay = 2.24
        self.medication = 392

        self.t = 1

        self.pld_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Paladin",
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

        self.pld_analysis_7_1_fru_p4 = Tank(
            self.main_stat,
            self.det,
            self.speed,
            self.ten,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Paladin",
            self.pet_attack_power,
            level=self.level,
        )

    @pytest.fixture
    def expected_pld_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 48},
                    # 3 ticks happened on a boss that was dead and castlocked
                    # for a value of 0. These are excluded from analyses.
                    {"base_action": "Circle of Scorn (tick)", "n": 28},
                    {"base_action": "Expiacion", "n": 7},
                    {"base_action": "Circle of Scorn", "n": 7},
                    {"base_action": "Blade of Truth", "n": 6},
                    {"base_action": "Blade of Valor", "n": 6},
                    {"base_action": "Blade of Faith", "n": 6},
                    {"base_action": "Intervene", "n": 6},
                    {"base_action": "Confiteor", "n": 5},
                    {"base_action": "Blade of Honor", "n": 5},
                    {"base_action": "Sepulchre", "n": 5},
                    {"base_action": "Holy Spirit", "n": 5},
                    {"base_action": "Imperator", "n": 5},
                    {"base_action": "Fast Blade", "n": 5},
                    {"base_action": "Supplication", "n": 4},
                    {"base_action": "Royal Authority", "n": 4},
                    {"base_action": "Atonement", "n": 4},
                    {"base_action": "Riot Blade", "n": 4},
                    {"base_action": "Goring Blade", "n": 2},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_pld_fru_p4_action_totals(
        self, expected_pld_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.pld_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_pld_fru_p4_7_1_action_counts)
