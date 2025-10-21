"""Constants for app including settings and component IDs."""

# Number of days to keep a submitted job entries in the database
DAYS_DELETE_SUMBITTED = 60
# Number of days to keep an unsubmitted job entries in the database
DAYS_DELETE_NOT_SUMBITTED = 2
# Number of days to keep the logs
LOG_RETENTION_DAYS = 60

# Component IDs
# Global
ERROR_TITLE_ID = "error-title"
ERROR_MESSAGE_ID = "error-message"
ERROR_MODAL_ID = "error-modal"
NEW_JOB_LINK_ID = "new_job_link"
NAVBAR_TOGGLER_ID = "navbar_toggler"
NAVBAR_COLLAPSE_ID = "navbar_collapse"
PREPARE_INPUT_ID = "prepare_input_button"
CHECK_INPUT_ID = "check_input_button"
URL_ID = "url_id"
# Input page
INPUT_HEADER_ID = "input_header"
INPUT_MAIN_CONTENT_ID = "input_main_content"
INPUT_JOB_ID_STORE = "input_job_id_store"
# Submission page
SUBMISSION_HEADER_ID = "submission_header"
SUBMISSION_JOB_ID_STORE = "submission_job_id_store"
SUBMISSION_MAIN_CONTENT_ID = "submission_main_content"
CHANGE_INPUT_BUTTON_ID = "change_input_button"
JOB_LOGS_ID = "job_logs"
RESULT_BUTTON_ID = "result_button"
LOADING_OVERLAY_ID = "loading-overlay"
SPAWN_BUTTON_ID = "spawn_button"
SUBMIT_JOB_ID = "submit_job_button"
SUBMISSION_STATUS_ID = "submission_status"
SUBMISSION_MAIN_CONTENT_ID = "submission_main_content"
# Results page
RESULTS_JOB_ID_STORE = "results_job_id_store"
RESULTS_MAIN_CONTENT_ID = "results_main_content"
RESULTS_HEADER_ID = "results_header"
CONTROL_CONTAINER_ID = "control_container"
RESULT_CONTAINER_ID = "result_container"
RESULTS_DATE_SELECTOR_ID = "results_date_selector"
RESULTS_DUMMY_ID = "results_dummy"
RESULTS_MAP_TYPES_ID = "results_map_types"
RESULTS_MAP_BOUNDS_ID = "results_map_bounds"
RESULTS_MAP_TYPE_SELECTOR_ID = "map_type_selector"
RESULTS_SOIL_MOISTURE_MAP_ID = "soil_moisture_map"
RESULTS_COLOR_BAR_INFO_ID = "color_bar_info"
RESULTS_CURRENT_DATE_DISPLAY_ID = "current_date_display"
RESULTS_CURRENT_MAP_TYPE_DISPLAY_ID = "current_map_type_display"
RESULTS_DATE_PAGINATION_MAP_ID = "date_pagination_map"
RESULTS_DATE_PAGINATION_STATS_ID = "date_pagination_stats"
RESULTS_PREVIOUS_MAP_TYPE_STORE_ID = "previous_map_type_store"
RESULTS_CURRENT_MAP_TYPE_BOX_ID = "current_map_type_box"
RESULTS_PREVIOUS_MAP_TYPE_BOX_ID = "previous_map_type_box"
RESULTS_SWITCH_MAP_BUTTON_ID = "switch_map_button"
RESULTS_MEASUREMENTS_SWITCH_ID = "measurements_switch"
RESULTS_OPACITY_SLIDER_ID = "opacity_slider"
RESULTS_TABS_ID = "results_tabs"
RESULTS_STATS_CONTAINER_ID = "results_stats_container"
RESULTS_STATS_DATA_STORE_ID = "results_stats_data_store"
RESULTS_STATS_VIEW_SELECTOR_ID = "results_stats_view_selector"
RESULTS_CORRELATION_GRAPH_ID = "results_correlation_graph"
RESULTS_CORRELATION_FIGURE_ID = "results_correlation_figure"
RESULTS_IMPORTANCE_GRAPH_ID = "results_importance_graph"
RESULTS_IMPORTANCE_SELECTED_ID = "results_importance_selected"
RESULTS_IMPORTANCE_ALL_ID = "results_importance_all"
