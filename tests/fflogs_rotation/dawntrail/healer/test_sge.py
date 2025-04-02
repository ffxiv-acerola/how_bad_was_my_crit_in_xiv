import pandas as pd
import pytest
from ffxiv_stats.jobs import Healer
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


class TestSageActions:
    """Tests for Sage job actions and rotations.

    Based off m2s
    https://www.fflogs.com/reports/Nj9P7gHwM6C1KAtQ?fight=18
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "Nj9P7gHwM6C1KAtQ"
        self.fight_id = 18
        self.level = 100
        self.phase = 0
        self.player_id = 16
        self.pet_ids = None

        self.main_stat = 5394 - 392  # potion up
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2845
        self.speed = 420

        self.crt = 3160
        self.dh = 1374
        self.wd = 146

        self.delay = 2.8
        self.medication = 392

        self.t = 503

        self.sge_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Sage",
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

        self.sge_analysis_7_05 = Healer(
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
    def expected_sge_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Dosis III", "n": 164},
                    {"base_action": "Eukrasian Dosis III (tick)", "n": 166},
                    {"base_action": "Phlegma III", "n": 14},
                    {"base_action": "Psyche", "n": 9},
                    {"base_action": "Pneuma", "n": 4},
                    {"base_action": "Toxikon II", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_sge_7_05_action_counts(
        self, expected_sge_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values against FFLogs."""
        # Arrange
        actual_counts = (
            self.sge_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_sge_7_05_action_counts)
