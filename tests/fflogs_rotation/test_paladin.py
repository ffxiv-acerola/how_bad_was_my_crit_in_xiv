import numpy as np
import pandas as pd
import pytest

from fflogs_rotation.paladin import PaladinActions

pld_id_map = {
    "Holy Spirit": 7384,
    "Blade of x": 25748,
    "Divine Might": 1002673,
    "Requiescat": 1001368,
}


@pytest.fixture
def mock_pld(monkeypatch):
    """Mock buff times function, as this is replaced.

    Args:
        monkeypatch (_type_): _description_
    """

    def mock_pld_buff_times(*args, **kwargs):
        return np.array([[-1, -1]]), np.array([[-1, -1]])

    monkeypatch.setattr(PaladinActions, "set_pld_buff_times", mock_pld_buff_times)

    pass


@pytest.mark.parametrize(
    "timestamp, abilityGameID, divine_times, requiescat_times, expected",
    [
        # Holy action (holy id) in divine window only -> Divine Might buff applied
        (
            1500,
            pld_id_map["Holy Spirit"],
            [[1000, 2000]],
            [[3000, 4000]],
            [str(pld_id_map["Divine Might"])],
        ),
        # Holy action in requiescat window only -> Requiescat buff applied
        (
            3500,
            16458,
            [
                [
                    -1,
                    -1,
                ]
            ],
            [[3000, 4000]],
            [str(pld_id_map["Requiescat"])],
        ),
        # Holy action in both windows -> Divine Might takes precedence
        (
            1500,
            pld_id_map["Holy Spirit"],
            [[1000, 2000]],
            [[1000, 2000]],
            [str(pld_id_map["Divine Might"])],
        ),
        # Holy action outside any buff windows -> No buff applied
        (2500, pld_id_map["Holy Spirit"], [[1000, 2000]], [[3000, 4000]], []),
        # Blade action (blade id) in requiescat window -> Requiescat buff applied
        (
            3500,
            pld_id_map["Blade of x"],
            [[1000, 2000]],
            [[3000, 4000]],
            [str(pld_id_map["Requiescat"])],
        ),
        # Blade action in divine window only (blade actions use only requiescat) -> No buff applied
        (1500, pld_id_map["Blade of x"], [[1000, 2000]], [[-1, -1]], []),
        # Blade action outside any buff windows -> No buff applied
        (2500, pld_id_map["Blade of x"], [[1000, 2000]], [[3000, 4000]], []),
    ],
)
def test_apply_pld_buffs(
    timestamp,
    abilityGameID,
    divine_times,
    requiescat_times,
    expected,
    monkeypatch,
    mock_buff_query,
    mock_pld,
):
    # Instantiate PaladinActions with dummy parameters
    pld = PaladinActions({}, "dummy", 1, 1)
    # Override buff windows manually
    pld.divine_might_times = np.array(divine_times)
    pld.requiescat_times = np.array(requiescat_times)
    # Create a dummy DataFrame with one row event
    df = pd.DataFrame(
        {
            "timestamp": [timestamp],
            "abilityGameID": [abilityGameID],
            "buffs": [[]],
            "action_name": ["dummy-action"],
        }
    )
    result = pld.apply_pld_buffs(df)
    assert result.loc[0, "buffs"] == expected
