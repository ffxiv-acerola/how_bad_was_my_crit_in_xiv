import pandas as pd
import pytest

from fflogs_rotation.base import BuffQuery


@pytest.fixture
def buff_query():
    return BuffQuery()


@pytest.mark.parametrize(
    "amount, multiplier, hit_type, direct_hit, main_stat_add, expected",
    [
        (1000, 1.0, 1, False, 0, 1000),
        (1500, 1.5, 1, False, 0, 1000),
        (1500, 1.0, 2, False, 0, 1000),
        (2250, 1.5, 2, False, 0, 1000),
        (1250, 1.0, 1, True, 0, 1000),
        (1875, 1.5, 1, True, 0, 1000),
        (1875, 1.0, 2, True, 0, 1000),
        (2813, 1.5, 2, True, 0, 1000),
        (1050, 1.0, 1, False, 300, 1000),
    ],
)
def test_normalize_damage(
    buff_query,
    amount: int,
    multiplier: float,
    hit_type: int,
    direct_hit: bool,
    main_stat_add: int,
    expected,
):
    """Test the normalize_damage function in BuffQuery."""
    actions_df = pd.DataFrame(
        {
            "amount": [amount],
            "multiplier": [multiplier],
            "hitType": [hit_type],
            "directHit": [direct_hit],
            "main_stat_add": [main_stat_add],
            "l_c": [1500],  # Critical hit multiplier
        }
    )

    # Potion multiplier is around 1.05 for typical medication
    potion_multiplier = 1.05

    result = BuffQuery.normalize_damage(actions_df, potion_multiplier)
    assert int(result["normalized_damage"].iloc[0]) == expected
