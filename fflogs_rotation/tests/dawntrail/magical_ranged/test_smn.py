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
from ffxiv_stats.jobs import MagicalRanged


class TestSummonerActions:
    """Tests for Summoner job actions and rotations.

    Based off https://www.fflogs.com/reports/9AtPB2XfjnRNvdhx?fight=36
    """

    def setup_method(self):
        """Setup method to initialize common variables and RotationTable."""
        self.report_id = "9AtPB2XfjnRNvdhx"
        self.fight_id = 36
        self.level = 100
        self.phase = 0
        self.player_id = 8
        self.pet_ids = [400, 208, 224, 179, 192, 127, 162]

        self.main_stat = 5129
        self.pet_attack_power = self.main_stat // 1.05
        self.det = 2108
        self.speed = 528

        self.crt = 3061
        self.dh = 2125
        self.wd = 146

        self.delay = 3.12
        self.medication = 392

        self.t = 555

        self.smn_rotation_7_05 = RotationTable(
            headers,
            self.report_id,
            self.fight_id,
            "Summoner",
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

        self.smn_analysis_7_05 = MagicalRanged(
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
    def expected_smn_7_05_action_counts(self) -> pd.DataFrame:
        """Fixture providing expected action count data."""
        return (
            pd.DataFrame(
                [
                    {"base_action": "Attack", "n": 126},
                    {"base_action": "Slipstream (tick)", "n": 47},
                    {"base_action": "Topaz Rite", "n": 36},
                    {"base_action": "Emerald Rite", "n": 36},
                    {"base_action": "Mountain Buster", "n": 36},
                    {"base_action": "Umbral Impulse", "n": 30},
                    {"base_action": "Luxwave (Pet)", "n": 20},
                    {"base_action": "Necrotize", "n": 19},
                    {"base_action": "Ruby Rite", "n": 18},
                    {"base_action": "Astral Impulse", "n": 17},
                    {"base_action": "Fountain of Fire", "n": 12},
                    {"base_action": "Wyrmwave (Pet)", "n": 11},
                    {"base_action": "Ruin III", "n": 10},
                    {"base_action": "Energy Drain", "n": 10},
                    {"base_action": "Earthen Fury (Pet)", "n": 9},
                    {"base_action": "Aerial Blast (Pet)", "n": 9},
                    {"base_action": "Inferno (Pet)", "n": 9},
                    {"base_action": "Ruin IV", "n": 9},
                    {"base_action": "Crimson Cyclone", "n": 9},
                    {"base_action": "Crimson Strike", "n": 9},
                    {"base_action": "Slipstream", "n": 9},
                    {"base_action": "Scarlet Flame (Pet)", "n": 8},
                    {"base_action": "Exodus (Pet)", "n": 5},
                    {"base_action": "Sunflare", "n": 5},
                    {"base_action": "Searing Flash", "n": 5},
                    {"base_action": "Akh Morn (Pet)", "n": 3},
                    {"base_action": "Deathflare", "n": 3},
                    {"base_action": "Revelation (Pet)", "n": 2},
                ]
            )
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

    def test_smn_7_05_action_counts(
        self, expected_smn_7_05_action_counts: pd.DataFrame
    ):
        """Test that action counts match expected values for 7.05 log."""
        # Arrange
        actual_counts = (
            self.smn_rotation_7_05.rotation_df.groupby("base_action")
            .sum("n")
            .reset_index()[["base_action", "n"]]
            .sort_values(["n", "base_action"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Assert
        assert_frame_equal(actual_counts, expected_smn_7_05_action_counts)
