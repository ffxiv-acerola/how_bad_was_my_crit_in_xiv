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


class TestNinjaActions:
    """Tests for Ninja job actions and rotations.

    Based of Reality's speed kill for m1s
    https://www.fflogs.com/reports/B3gxKdn4j1W8NML9#fight=3
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "B3gxKdn4j1W8NML9"
        self.fight_id = 3
        self.level = 100
        self.phase = 0
        self.player_id = 7
        self.pet_ids = [15]

        self.main_stat = 5105
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2387
        self.speed = 420

        self.crt = 3173
        self.dh = 1482
        self.wd = 146

        self.delay = 2.56
        self.medication = 392

        self.t = 393.947

        self.nin_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Ninja",
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

        self.nin_analysis_7_05 = Melee(
            self.main_stat,
            self.det,
            self.speed,
            self.crt,
            self.dh,
            self.wd,
            self.delay,
            "Ninja",
            self.pet_attack_power,
            level=self.level,
        )
        # self.black_cat_ast.attach_rotation(self.black_cat_rotation.rotation_df, self.t)

    @pytest.fixture
    def expected_sam_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 167},
                    {"base_action": "Spinning Edge", "n": 38},
                    {"base_action": "Gust Slash", "n": 37},
                    {"base_action": "Aeolian Edge", "n": 26},
                    {"base_action": "Bhavacakra", "n": 22},
                    {"base_action": "Dream Within a Dream", "n": 21},
                    {"base_action": "Fleeting Raiju", "n": 18},
                    {"base_action": "Raiton", "n": 18},
                    {"base_action": "Armor Crush", "n": 13},
                    {"base_action": "Fleeting Raiju (Pet)", "n": 11},
                    {"base_action": "Hyosho Ranryu", "n": 7},
                    {"base_action": "Kunai's Bane", "n": 7},
                    {"base_action": "Suiton", "n": 11},
                    {"base_action": "Tenri Jindo", "n": 4},
                    {"base_action": "Zesho Meppo", "n": 4},
                    {"base_action": "Fuma Shuriken", "n": 4},
                    {"base_action": "Dokumori", "n": 4},
                    {"base_action": "Phantom Kamaitachi (Pet)", "n": 3},
                    {"base_action": "Aeolian Edge (Pet)", "n": 3},
                    {"base_action": "Gust Slash (Pet)", "n": 3},
                    {"base_action": "Spinning Edge (Pet)", "n": 2},
                    {"base_action": "Armor Crush (Pet)", "n": 1},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_nin_7_05_action_counts(self, expected_sam_7_05_action_counts: pd.DataFrame):
        """Test that action counts match expected values for Black Cat log."""
        # Arrange
        actual_counts = (
            self.nin_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_sam_7_05_action_counts)
