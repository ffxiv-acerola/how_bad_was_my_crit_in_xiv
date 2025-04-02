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


class TestRedMageActions:
    """Tests for Red Mage job actions and rotations.

    Based off https://www.fflogs.com/reports/bXCKzB4DYgN6jfVr?fight=7
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "bXCKzB4DYgN6jfVr"
        self.fight_id = 7
        self.level = 100
        self.phase = 0
        self.player_id = 2
        self.pet_ids = None

        self.main_stat = 5127
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2108
        self.speed = 474

        self.crt = 3061
        self.dh = 2179
        self.wd = 146

        self.delay = 3.44
        self.medication = 392

        self.t = 545

        self.rdm_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "RedMage",
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

        self.rdm_analysis_7_05 = MagicalRanged(
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
    def expected_rdm_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Veraero III", "n": 39},
                    {"base_action": "Verthunder III", "n": 34},
                    {"base_action": "Verfire", "n": 24},
                    {"base_action": "Fleche", "n": 22},
                    {"base_action": "Verstone", "n": 20},
                    {"base_action": "Engagement", "n": 17},
                    {"base_action": "Resolution", "n": 16},
                    {"base_action": "Scorch", "n": 16},
                    {"base_action": "Enchanted Redoublement", "n": 16},
                    {"base_action": "Contre Sixte", "n": 16},
                    {"base_action": "Enchanted Zwerchhau", "n": 16},
                    {"base_action": "Enchanted Riposte", "n": 16},
                    {"base_action": "Corps-a-Corps", "n": 16},
                    {"base_action": "Grand Impact", "n": 11},
                    {"base_action": "Verflare", "n": 8},
                    {"base_action": "Verholy", "n": 8},
                    {"base_action": "Prefulgence", "n": 5},
                    {"base_action": "Vice of Thorns", "n": 5},
                    {"base_action": "Enchanted Reprise", "n": 5},
                    {"base_action": "Jolt III", "n": 5},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_rdm_7_05_action_counts(
        self, expected_rdm_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for 7.05 log."""
        # Arrange
        actual_counts = (
            self.rdm_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_rdm_7_05_action_counts)
