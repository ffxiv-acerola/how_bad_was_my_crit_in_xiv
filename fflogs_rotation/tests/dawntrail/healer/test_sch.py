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
from ffxiv_stats.jobs import Healer


class TestScholarActions:
    """Tests for Scholar job actions and rotations.

    Based of Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=38
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 5

        self.main_stat = 5048
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2803
        self.speed = 420

        self.crt = 3147
        self.dh = 1320
        self.wd = 146

        self.delay = 3.12
        self.medication = 392

        self.t = 393.947

        self.sch_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Scholar",
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
        )

        self.sch_analysis_7_05 = Healer(
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
        # self.black_cat_sch.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_sch_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return pd.DataFrame(
            [
                {"base_action": "Attack", "n": 67},
                {"base_action": "Baneful Impaction (tick)", "n": 20},
                {"base_action": "Biolysis (tick)", "n": 126},
                {"base_action": "Broil IV", "n": 136},
                {"base_action": "Energy Drain", "n": 29},
            ]
        )

    def test_sch_7_05_action_counts(
        self, expected_sch_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for 7.05 Black Cat (Savage) log."""
        # Arrange
        actual_counts = (
            self.sch_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
        )

        # Assert
        assert_frame_equal(
            actual_counts,
            expected_sch_7_05_action_counts,
        )
