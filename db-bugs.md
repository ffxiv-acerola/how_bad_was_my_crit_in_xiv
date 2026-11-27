Bugs to fix or flag while moving
- unflag_party_report_recompute updates report and sets redo_party_report_flag. It should probably update party_report and set redo_analysis_flag. The get_party_analysis_encounter_info query reads redo_analysis_flag from party_report.
- read_player_analysis_info returns before closing the connection when there are no rows.
- retrieve_player_analysis_information indexes result["pet_ids"] when result can be None.
- get_party_analysis_player_build has a return annotation and docstring that say three values, but it returns two.
- get_party_analysis_calculation_info compares the job to "LimitBreak". compute_party_bonus and get_player_analysis_job_records compare the role to "Limit Break". Check that these match the data.
- compute_party_bonus is annotated as returning str but returns a float.
- insert_error_party_analysis passes main_stat_multiplier (a list) instead of main_stat_multiplier[a].
- search_prior_player_analyses reads the flags by negative position. Selecting named columns would be safer.
