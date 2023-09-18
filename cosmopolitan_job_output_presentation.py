"""Module defines all functionality to plot jobs."""


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
