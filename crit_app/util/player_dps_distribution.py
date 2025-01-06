from dataclasses import dataclass
from typing import Dict

import numpy as np
from numpy.typing import ArrayLike

@dataclass
class JobAnalysis:
    active_dps_t: float
    analysis_t: float
    rotation_mean: float
    rotation_variance: float
    rotation_std: float
    rotation_skewness: float
    rotation_dps_distribution: ArrayLike
    rotation_dps_support: ArrayLike
    unique_actions_distribution: Dict

    def interpolate_distributions(self, rotation_n=5000, action_n=5000):
        """Interpolate supplied distributions so the arrays have a fewer number of elements.

        Used after all convolving is complete

        Args:
            rotation_n (int, optional): Number of data points for rotation damage distribution. Defaults to 5000.
            action_n (int, optional): Number of data points for action damage distributions. Defaults to 5000.
        """
        lower, upper = self.rotation_dps_support[0], self.rotation_dps_support[-1]
        new_support = np.linspace(lower, upper, num=rotation_n)
        new_pdf = np.interp(
            new_support, self.rotation_dps_support, self.rotation_dps_distribution
        )

        self.rotation_dps_support = new_support
        self.rotation_dps_distribution = new_pdf

        for k, v in self.unique_actions_distribution.items():
            lower, upper = v["support"][0], v["support"][-1]
            new_support = np.linspace(lower, upper, num=action_n)
            new_pdf = np.interp(new_support, v["support"], v["dps_distribution"])

            self.unique_actions_distribution[k]["support"] = new_support
            self.unique_actions_distribution[k]["dps_distribution"] = new_pdf

        pass

def job_analysis_to_data_class(job_analysis_object, active_dps_time):
    return JobAnalysis(
        active_dps_time,
        job_analysis_object.t,
        job_analysis_object.rotation_mean,
        job_analysis_object.rotation_variance,
        job_analysis_object.rotation_std,
        job_analysis_object.rotation_skewness,
        job_analysis_object.rotation_dps_distribution,
        job_analysis_object.rotation_dps_support,
        job_analysis_object.unique_actions_distribution,
    )