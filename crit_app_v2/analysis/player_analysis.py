"""Helper functions for analyzing the rotation for a single player."""

DISCRETIZATION_LEVEL_MAP = {90: 4, 100: 10}


def compute_party_bonus() -> float:
    return 1.05


def correct_final_phase(fight_phase: int, last_phase_index: int) -> int:
    # Edge case example: fight analyzing phase 5 is loaded
    # user switches log url to a phase where phase 1 was reached
    # if they don't hit submit, phase 5 can still be selected, which is
    # impossible. Easy solution:
    # Just analyze the final phase reached, that's pry what they wanted anw.
    if fight_phase > last_phase_index:
        return last_phase_index
    return fight_phase
