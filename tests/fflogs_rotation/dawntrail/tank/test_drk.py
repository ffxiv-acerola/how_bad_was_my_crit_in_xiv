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


class TestDarkKnightActions:
    """Tests for Dark Knight job actions and rotations.

    Based off Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 2
        self.pet_ids = [13]

        self.main_stat = 5084
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2310
        self.speed = 420

        self.crt = 3174
        self.dh = 1470
        self.wd = 146

        self.ten = 868

        self.delay = 2.96
        self.medication = 392

        self.t = 393.947

        self.drk_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "DarkKnight",
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

        self.drk_analysis_7_05 = Tank(
            self.main_stat,
            self.det,
            self.speed,
            self.ten,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "DarkKnight",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_drk_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 128},
                    {"base_action": "Souleater", "n": 36},
                    {"base_action": "Syphon Strike", "n": 37},
                    {"base_action": "Hard Slash", "n": 37},
                    {"base_action": "Edge of Shadow", "n": 26},
                    {"base_action": "Bloodspiller", "n": 18},
                    {"base_action": "Shadowbringer", "n": 8},
                    {"base_action": "Comeuppance", "n": 7},
                    {"base_action": "Torcleaver", "n": 7},
                    {"base_action": "Scarlet Delirium", "n": 7},
                    {"base_action": "Carve and Spit", "n": 7},
                    {"base_action": "Salt and Darkness", "n": 5},
                    {"base_action": "Salted Earth (tick)", "n": 29},
                    {"base_action": "Disesteem", "n": 4},
                    {"base_action": "Disesteem (Pet)", "n": 4},
                    {"base_action": "Shadowbringer (Pet)", "n": 4},
                    {"base_action": "Abyssal Drain (Pet)", "n": 4},
                    {"base_action": "Edge of Shadow (Pet)", "n": 4},
                    {"base_action": "Bloodspiller (Pet)", "n": 4},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_drk_7_05_action_counts(
        self, expected_drk_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.drk_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_drk_7_05_action_counts)


class TestDarkKnightMultiTargetActions:
    """Tests for Dark Knight job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "ZfnF8AqRaBbzxW3w"
        self.fight_id = 5
        self.level = 100
        self.phase = 4
        self.player_id = 26
        self.pet_ids = [32]
        self.excluded_enemy_ids = [52]

        self.main_stat = 5084
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2310
        self.speed = 420

        self.crt = 3174
        self.dh = 1470
        self.wd = 146

        self.ten = 868

        self.delay = 2.96
        self.medication = 392

        self.t = 1

        self.drk_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "DarkKnight",
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

        self.drk_analysis_7_1_fru_p4 = Tank(
            self.main_stat,
            self.det,
            self.speed,
            self.ten,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "DarkKnight",
            self.pet_attack_power,
            level=self.level,
        )

    @pytest.fixture
    def expected_drk_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                data=[
                    {"base_action": "Attack", "n": 39},
                    {"base_action": "Salted Earth (tick)", "n": 24},
                    {"base_action": "Souleater", "n": 11},
                    {"base_action": "Syphon Strike", "n": 10},
                    {"base_action": "Hard Slash", "n": 10},
                    {"base_action": "Edge of Shadow", "n": 9},
                    {"base_action": "Bloodspiller", "n": 6},
                    {"base_action": "Shadowbringer", "n": 6},
                    {"base_action": "Salt and Darkness", "n": 4},
                    {"base_action": "Comeuppance", "n": 3},
                    {"base_action": "Scarlet Delirium", "n": 3},
                    {"base_action": "Disesteem", "n": 2},
                    {"base_action": "Torcleaver", "n": 2},
                    {"base_action": "Carve and Spit", "n": 2},
                    {"base_action": "Abyssal Drain (Pet)", "n": 2},
                    {"base_action": "Shadowbringer (Pet)", "n": 2},
                    {"base_action": "Disesteem (Pet)", "n": 2},
                    {"base_action": "Edge of Shadow (Pet)", "n": 1},
                    {"base_action": "Bloodspiller (Pet)", "n": 1},
                    {"base_action": "Unmend", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_drk_fru_p4_action_totals(
        self, expected_drk_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.drk_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_drk_fru_p4_7_1_action_counts)
