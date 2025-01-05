import pytest
import pandas as pd
from crit_app.util.party_dps_distribution import lb_damage_after_clipping

@pytest.fixture
def lb_events_df():
    return pd.DataFrame({
        'timestamp': [10.0, 20.0],
        'amount': [5000, 7000]
    })

def test_lb_damage_after_clipping_no_filter(lb_events_df):
    """Test when filter time is after all events"""
    result = lb_damage_after_clipping(lb_events_df, 25.0)
    assert result == 12000  # 5000 + 7000

def test_lb_damage_after_clipping_one_filtered(lb_events_df):
    """Test when filter time is between events"""
    result = lb_damage_after_clipping(lb_events_df, 15.0)
    assert result == 5000  # Only first event included

def test_flb_damage_after_clipping_all_filtered(lb_events_df):
    """Test when filter time is before all events"""
    result = lb_damage_after_clipping(lb_events_df, 5.0)
    assert result == 0  # No events included