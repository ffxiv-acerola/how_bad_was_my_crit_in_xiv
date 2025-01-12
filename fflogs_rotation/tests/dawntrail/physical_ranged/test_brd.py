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
from ffxiv_stats.jobs import PhysicalRanged


class TestBardActions:
    """Tests for Bard job actions and rotations.

    Based of Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 3
        self.pet_ids = None

        self.main_stat = 5130
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2091
        self.speed = 474

        self.crt = 3177
        self.dh = 2080
        self.wd = 146

        self.delay = 3.04
        self.medication = 392

        self.t = 393.947

        self.brd_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Bard",
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

        self.brd_analysis_7_05 = PhysicalRanged(
            self.main_stat,
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
    def expected_brd_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Burst Shot", "n": 96},
                    {"base_action": "Refulgent Arrow", "n": 41},
                    {"base_action": "Heartbreak Shot", "n": 50},
                    {"base_action": "Shot", "n": 133},
                    {"base_action": "Pitch Perfect", "n": 19},
                    {"base_action": "Empyreal Arrow", "n": 26},
                    {"base_action": "Blast Arrow", "n": 6},
                    {"base_action": "Radiant Encore", "n": 4},
                    {"base_action": "Apex Arrow", "n": 6},
                    {"base_action": "Resonant Arrow", "n": 4},
                    {"base_action": "Stormbite (tick)", "n": 129},
                    {"base_action": "Sidewinder", "n": 7},
                    {"base_action": "Caustic Bite (tick)", "n": 128},
                    {"base_action": "Iron Jaws", "n": 10},
                    {"base_action": "Caustic Bite", "n": 1},
                    {"base_action": "Stormbite", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_brd_7_05_action_counts(
        self, expected_brd_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.brd_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_brd_7_05_action_counts)
