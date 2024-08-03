from dash import html

generic_variance_warning = "While other sources of damage variance are modeled, the DPS variance experienced in-game will likely be a bit larger than what is reported here."

job_warnings = {
    # "Astrologian": html.Div(
    #     [
    #         html.P(
    #             "The rotation for Astrologian has RNG-dependent elements which are not modeled in the analysis below, including Minor Arcana and the number of unique seals for Astrodyne."
    #         ),
    #         html.P(generic_variance_warning),
    #     ]
    # ),
    # "Dancer": None,
    # "Bard": None,
    # "BlackMage": None,
}
