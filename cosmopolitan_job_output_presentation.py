"""Module defines all functionality to plot jobs."""

import json
import os

from RFoPrediction import RFoPrediction


class CosmopolitanJobOutputPresentation:
    """Class holds all functionallity to show plot of a finished job."""

    input_args_to_file_names = {
        "predictors": "predictors",
        "pred_correlation": "correlation_matrix",
        "day_measurements": "measurements_vs_distance_",
        "day_feature_imp": "feature_importance_",
        "day_prediction_map": "RF_prediction_",
        "alldays_feature_imp": "feature_importance_vs_days",
    }


if __name__ == "__main__":
    working_dir = "output/ruddy_violet_marmoset/"

    with open(os.path.join(working_dir, "parameters.json"), "r") as f_handle:
        input_data = json.loads(f_handle.read())

    rfo_prediction = RFoPrediction(input_data, working_dir)

    rfo_prediction.plot_data.plot_predictors(rfo_prediction.inData)
