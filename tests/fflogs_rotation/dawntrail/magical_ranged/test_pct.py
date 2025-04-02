import pandas as pd
import pytest
from ffxiv_stats.jobs import MagicalRanged
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


class TestPictomancerActions:
    """Tests for Pictomancer job actions and rotations.

    Based off Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 4
        self.pet_ids = None

        self.main_stat = 5130
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2269
        self.speed = 420

        self.crt = 3140
        self.dh = 1993
        self.wd = 146

        self.delay = 2.96
        self.medication = 392

        self.t = 393.947

        self.pct_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Pictomancer",
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
            encounter_phases,
            pet_ids=self.pet_ids,
        )

        self.pct_analysis_7_05 = MagicalRanged(
            self.main_stat,
            400,
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
    def expected_pct_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Water in Blue", "n": 14},
                    {"base_action": "Aero in Green", "n": 14},
                    {"base_action": "Fire in Red", "n": 14},
                    {"base_action": "Thunder in Magenta", "n": 10},
                    {"base_action": "Stone in Yellow", "n": 10},
                    {"base_action": "Blizzard in Cyan", "n": 10},
                    {"base_action": "Comet in Black", "n": 9},
                    {"base_action": "Hammer Brush", "n": 8},
                    {"base_action": "Polishing Hammer", "n": 8},
                    {"base_action": "Hammer Stamp", "n": 8},
                    {"base_action": "Rainbow Drip", "n": 5},
                    {"base_action": "Star Prism", "n": 4},
                    {"base_action": "Retribution of the Madeen", "n": 3},
                    {"base_action": "Mog of the Ages", "n": 3},
                    {"base_action": "Pom Muse", "n": 3},
                    {"base_action": "Fanged Muse", "n": 3},
                    {"base_action": "Winged Muse", "n": 3},
                    {"base_action": "Clawed Muse", "n": 3},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_pct_7_05_action_counts(
        self, expected_pct_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for 7.05 log."""
        # Arrange
        actual_counts = (
            self.pct_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_pct_7_05_action_counts)


class TestPictomancerMultiTargetActions:
    """Tests for Pictomancer job actions and rotations with multiple targets.

    Based off
    https://www.fflogs.com/reports/vZRCr94LWzcXYjFq?fight=15
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "vZRCr94LWzcXYjFq"
        self.fight_id = 15
        self.level = 100
        self.phase = 4
        self.player_id = 200
        self.pet_ids = None

        self.main_stat = 5127
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2271
        self.speed = 420

        self.crt = 3140
        self.dh = 2047
        self.wd = 146

        self.delay = 2.96
        self.medication = 392

        self.t = 393.947

        self.pct_rotation_7_1 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Pictomancer",
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
            encounter_phases,
            pet_ids=self.pet_ids,
        )

        self.pct_analysis_7_1 = MagicalRanged(
            self.main_stat,
            400,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            self.pet_attack_power,
            level=self.level,
        )

    @pytest.fixture
    def expected_pct_7_1_multi_target_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Holy in White", "n": 14},
                    {"base_action": "Comet in Black", "n": 5},
                    {"base_action": "Polishing Hammer", "n": 4},
                    {"base_action": "Hammer Brush", "n": 4},
                    {"base_action": "Hammer Stamp", "n": 4},
                    {"base_action": "Star Prism", "n": 2},
                    {"base_action": "Mog of the Ages", "n": 2},
                    {"base_action": "Clawed Muse", "n": 3},
                    {"base_action": "Thunder in Magenta", "n": 2},
                    {"base_action": "Rainbow Drip", "n": 4},
                    {"base_action": "Blizzard in Cyan", "n": 2},
                    {"base_action": "Stone in Yellow", "n": 2},
                    {"base_action": "Pom Muse", "n": 2},
                    {"base_action": "Retribution of the Madeen", "n": 2},
                    {"base_action": "Fanged Muse", "n": 2},
                    {"base_action": "Aero in Green", "n": 3},
                    {"base_action": "Winged Muse", "n": 2},
                    {"base_action": "Fire in Red", "n": 3},
                    {"base_action": "Water in Blue", "n": 2},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_pct_7_10_multi_action_counts(
        self, expected_pct_7_1_multi_target_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for 7.05 log."""
        # Arrange
        actual_counts = (
            self.pct_rotation_7_1.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_pct_7_1_multi_target_action_counts)


class TestPictomancerMultiTargetActions2:
    """Tests for Pictomancer job actions and rotations with an emphasis on mutli-target.

    Based off https://www.fflogs.com/reports/ZfnF8AqRaBbzxW3w?fight=5
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "ZfnF8AqRaBbzxW3w"
        self.fight_id = 5
        self.level = 100
        self.phase = 4
        self.player_id = 25
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

        self.pct_rotation_7_1_fru_p4 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Pictomancer",
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
            encounter_phases,
            pet_ids=self.pet_ids,
        )

        self.pct_analysis_7_1_fru_p4 = MagicalRanged(
            self.main_stat,
            400,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            self.pet_attack_power,
            level=self.level,
        )

        self.pct_rotation_7_1_fru_p2 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Pictomancer",
            self.player_id,
            self.crt,
            self.dh,
            self.det,
            self.medication,
            self.level,
            2,
            damage_buff_table,
            critical_hit_rate_table,
            direct_hit_rate_table,
            guaranteed_hits_by_action_table,
            guaranteed_hits_by_buff_table,
            potency_table,
            encounter_phases,
            pet_ids=self.pet_ids,
            excluded_enemy_ids=self.excluded_enemy_ids,
        )

        self.pct_analysis_7_1_fru_p2 = MagicalRanged(
            self.main_stat,
            400,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            self.pet_attack_power,
            level=self.level,
        )

    @pytest.fixture
    def expected_pct_fru_p4_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Comet in Black", "n": 6},
                    {"base_action": "Blizzard in Cyan", "n": 5},
                    {"base_action": "Polishing Hammer", "n": 4},
                    {"base_action": "Stone in Yellow", "n": 4},
                    {"base_action": "Hammer Brush", "n": 4},
                    {"base_action": "Hammer Stamp", "n": 4},
                    {"base_action": "Water in Blue", "n": 4},
                    {"base_action": "Retribution of the Madeen", "n": 3},
                    {"base_action": "Pom Muse", "n": 3},
                    {"base_action": "Thunder in Magenta", "n": 3},
                    {"base_action": "Fire in Red", "n": 3},
                    {"base_action": "Aero in Green", "n": 3},
                    {"base_action": "Winged Muse", "n": 2},
                    {"base_action": "Star Prism", "n": 2},
                    {"base_action": "Mog of the Ages", "n": 2},
                    {"base_action": "Rainbow Drip", "n": 2},
                    {"base_action": "Fanged Muse", "n": 2},
                    {"base_action": "Holy in White", "n": 2},
                    {"base_action": "Clawed Muse", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_pct_fru_p4_action_totals(
        self, expected_pct_fru_p4_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.pct_rotation_7_1_fru_p4.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_pct_fru_p4_7_1_action_counts)

    @pytest.fixture
    def expected_pct_fru_p2_7_1_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Fire in Red", "n": 6},
                    {"base_action": "Stone in Yellow", "n": 5},
                    {"base_action": "Blizzard in Cyan", "n": 5},
                    {"base_action": "Thunder in Magenta", "n": 5},
                    {"base_action": "Water in Blue", "n": 5},
                    {"base_action": "Aero in Green", "n": 5},
                    {"base_action": "Hammer Brush", "n": 4},
                    {"base_action": "Hammer Stamp", "n": 4},
                    {"base_action": "Comet in Black", "n": 4},
                    {"base_action": "Polishing Hammer", "n": 3},
                    {"base_action": "Holy in White", "n": 4},
                    {"base_action": "Rainbow Drip", "n": 3},
                    {"base_action": "Fanged Muse", "n": 2},
                    {"base_action": "Star Prism", "n": 2},
                    {"base_action": "Mog of the Ages", "n": 2},
                    {"base_action": "Clawed Muse", "n": 2},
                    {"base_action": "Retribution of the Madeen", "n": 1},
                    {"base_action": "Winged Muse", "n": 1},
                    {"base_action": "Pom Muse", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_pct_fru_p2_action_totals(
        self, expected_pct_fru_p2_7_1_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values."""
        # Arrange
        actual_counts = (
            self.pct_rotation_7_1_fru_p2.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_pct_fru_p2_7_1_action_counts)
