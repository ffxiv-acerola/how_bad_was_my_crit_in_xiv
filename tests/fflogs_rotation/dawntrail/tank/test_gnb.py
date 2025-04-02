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


class TestGunbreakerActions:
    """Tests for Gunbreaker job actions and rotations.

    Based off Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 9
        self.pet_ids = None

        self.main_stat = 5061
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2310
        self.speed = 420

        self.crt = 3174
        self.dh = 1470
        self.wd = 146

        self.ten = 868

        self.delay = 2.80
        self.medication = 392

        self.t = 393.947

        self.gnb_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Gunbreaker",
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

        self.gnb_analysis_7_05 = Tank(
            self.main_stat,
            self.det,
            self.speed,
            self.ten,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Gunbreaker",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_gnb_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 137},
                    {"base_action": "Sonic Break (tick)", "n": 60},
                    {"base_action": "Bow Shock (tick)", "n": 35},
                    {"base_action": "Solid Barrel", "n": 26},
                    {"base_action": "Brutal Shell", "n": 26},
                    {"base_action": "Keen Edge", "n": 27},
                    {"base_action": "Blasting Zone", "n": 13},
                    {"base_action": "Wicked Talon", "n": 13},
                    {"base_action": "Savage Claw", "n": 13},
                    {"base_action": "Gnashing Fang", "n": 13},
                    {"base_action": "Eye Gouge", "n": 13},
                    {"base_action": "Abdomen Tear", "n": 13},
                    {"base_action": "Jugular Rip", "n": 13},
                    {"base_action": "Burst Strike", "n": 11},
                    {"base_action": "Hypervelocity", "n": 10},
                    {"base_action": "Double Down", "n": 7},
                    {"base_action": "Bow Shock", "n": 7},
                    {"base_action": "Sonic Break", "n": 6},
                    {"base_action": "Lion Heart", "n": 4},
                    {"base_action": "Noble Blood", "n": 4},
                    {"base_action": "Reign of Beasts", "n": 4},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_gnb_7_05_action_counts(
        self, expected_gnb_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.gnb_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_gnb_7_05_action_counts)


class TestGunbreakerMultiTargetActions:
    """Tests for Gunbreaker job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "ZfnF8AqRaBbzxW3w"
        self.fight_id = 5
        self.level = 100
        self.phase = 4
        self.player_id = 21
        self.pet_ids = None
        self.excluded_enemy_ids = [52]

        self.main_stat = 5061
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2310
        self.speed = 420

        self.crt = 3174
        self.dh = 1470
        self.wd = 146

        self.ten = 868

        self.delay = 2.80
        self.medication = 392

        self.t = 1

        self.gnb_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Gunbreaker",
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

        self.gnb_analysis_7_1_fru_p4 = Tank(
            self.main_stat,
            self.det,
            self.speed,
            self.ten,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Gunbreaker",
            self.pet_attack_power,
            level=self.level,
        )

    @pytest.fixture
    def expected_gnb_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 42},
                    {"base_action": "Bow Shock (tick)", "n": 26},
                    {"base_action": "Sonic Break (tick)", "n": 22},
                    {"base_action": "Brutal Shell", "n": 8},
                    {"base_action": "Keen Edge", "n": 8},
                    {"base_action": "Double Down", "n": 6},
                    {"base_action": "Solid Barrel", "n": 6},
                    {"base_action": "Bow Shock", "n": 6},
                    {"base_action": "Wicked Talon", "n": 5},
                    {"base_action": "Eye Gouge", "n": 5},
                    {"base_action": "Blasting Zone", "n": 4},
                    {"base_action": "Savage Claw", "n": 4},
                    {"base_action": "Gnashing Fang", "n": 4},
                    {"base_action": "Abdomen Tear", "n": 4},
                    {"base_action": "Jugular Rip", "n": 4},
                    {"base_action": "Sonic Break", "n": 3},
                    {"base_action": "Lion Heart", "n": 2},
                    {"base_action": "Reign of Beasts", "n": 2},
                    {"base_action": "Noble Blood", "n": 2},
                    {"base_action": "Burst Strike", "n": 2},
                    {"base_action": "Fated Circle", "n": 2},
                    {"base_action": "Hypervelocity", "n": 2},
                    {"base_action": "Fated Brand", "n": 2},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_gnb_fru_p4_action_totals(
        self, expected_gnb_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.gnb_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_gnb_fru_p4_7_1_action_counts)
