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


class TestBlackMageActions:
    """Tests for Black Mage job actions and rotations.

    Based off
    https://www.fflogs.com/reports/yWvADHcK8XJCj4pF?fight=19
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "yWvADHcK8XJCj4pF"
        self.fight_id = 19
        self.level = 100
        self.phase = 0
        self.player_id = 104
        self.pet_ids = None

        self.main_stat = 5126
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 1572
        self.speed = 1047

        self.crt = 3321
        self.dh = 1882
        self.wd = 146

        self.delay = 3.28
        self.medication = 392

        self.t = 432

        self.blm_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "BlackMage",
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

        self.blm_analysis_7_05 = MagicalRanged(
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
    def expected_blm_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Fire IV", "n": 73},
                    {"base_action": "Paradox", "n": 20},
                    {"base_action": "Xenoglossy", "n": 18},
                    {"base_action": "High Thunder", "n": 15},
                    {"base_action": "Despair", "n": 13},
                    {"base_action": "Flare Star", "n": 11},
                    {"base_action": "Fire III", "n": 10},
                    {"base_action": "Blizzard IV", "n": 8},
                    {"base_action": "Blizzard III", "n": 8},
                    {"base_action": "High Thunder (tick)", "n": 143},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_blm_7_05_action_counts(
        self, expected_blm_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for 7.05 log."""
        # Arrange
        actual_counts = (
            self.blm_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_blm_7_05_action_counts)
