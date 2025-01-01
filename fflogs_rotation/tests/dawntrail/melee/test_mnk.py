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


class TestMonkActions:
    """Tests for Gunbreaker job actions and rotations.

    Based of Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 6
        self.pet_ids = None

        self.main_stat = 5061
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2310
        self.speed = 420

        self.crt = 3174
        self.dh = 1470
        self.wd = 146

        self.delay = 2.80
        self.medication = 392

        self.t = 393.947

        self.mnk_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Monk",
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

        self.mnk_analysis_7_05 = Melee(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Monk",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_mnk_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 224},
                    {"base_action": "Leaping Opo", "n": 42},
                    {"base_action": "Dragon Kick", "n": 42},
                    {"base_action": "The Forbidden Chakra", "n": 33},
                    {"base_action": "Pouncing Coeurl", "n": 30},
                    {"base_action": "Rising Raptor", "n": 23},
                    {"base_action": "Twin Snakes", "n": 23},
                    {"base_action": "Demolish", "n": 15},
                    {"base_action": "Fire's Reply", "n": 7},
                    {"base_action": "Elixir Burst", "n": 5},
                    {"base_action": "Wind's Reply", "n": 5},
                    {"base_action": "Phantom Rush", "n": 3},
                    {"base_action": "Rising Phoenix", "n": 3},
                    {"base_action": "Six-Sided Star", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_mnk_7_05_action_counts(self, expected_mnk_7_05_action_counts: pd.DataFrame):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.mnk_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_mnk_7_05_action_counts)
