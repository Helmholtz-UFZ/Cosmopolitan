"""HTML ID constants for Dash components.

Naming convention: <NAME>_<TYPE>_<PAGE>_ID
- NAME: Semantic purpose (e.g., START_JOB, EMAIL)
- TYPE: Component type (BUTTON, INPUT, DIV, DROPDOWN, STORE, MODAL, ALERT, LINK, etc.)
- PAGE: Page scope (SHARED, NEW_JOB, INPUT, SUBMISSION, RESULTS, etc.)
- ID: Required suffix

See docs/conventions/html_ids.md for full details.
"""

# =============================================================================
# SHARED / GLOBAL
# =============================================================================

# --- Locations ---
URL_LOCATION_SHARED_ID = "url-location-shared-id"

# --- Modals ---
ERROR_MODAL_SHARED_ID = "error-modal-shared-id"  # nocheck - used via set_props()
LOADING_OVERLAY_MODAL_SHARED_ID = "loading-overlay-modal-shared-id"

# --- Divs ---
ERROR_TITLE_DIV_SHARED_ID = (
    "error-title-div-shared-id"  # nocheck - used via set_props()
)
ERROR_MESSAGE_DIV_SHARED_ID = (
    "error-message-div-shared-id"  # nocheck - used via set_props()
)

# --- Buttons ---
NAVBAR_TOGGLER_BUTTON_SHARED_ID = "navbar-toggler-button-shared-id"

# --- Collapses ---
NAVBAR_COLLAPSE_DIV_SHARED_ID = "navbar-collapse-div-shared-id"

# --- Links ---
NEW_JOB_LINK_SHARED_ID = "new-job-link-shared-id"  # nocheck - testing only

# =============================================================================
# NEW_JOB
# =============================================================================

# --- Buttons ---
PREPARE_INPUT_BUTTON_NEW_JOB_ID = "prepare-input-button-new-job-id"

# --- Inputs ---
JOB_INPUT_NEW_JOB_ID = "job-input-new-job-id"

# --- FormTexts ---
JOB_FEEDBACK_FORMTEXT_NEW_JOB_ID = "job-feedback-formtext-new-job-id"

# =============================================================================
# INPUT
# =============================================================================

# --- Buttons ---
CHECK_INPUT_BUTTON_INPUT_ID = (  # nocheck - used via FormFactory
    "check_input_button_input_id"  # underscores: used as dict key in callback
)
DELETE_CRNS_UPLOAD_BUTTON_INPUT_ID = "delete_crns_upload"
DELETE_PREDICTOR_UPLOAD_BUTTON_INPUT_ID = "delete_predictor_upload"

# --- Divs ---
HEADER_DIV_INPUT_ID = "header-div-input-id"
HEADER_SUBTITLE_DIV_INPUT_ID = "header-div-input-id-subtitle"
MAIN_CONTENT_DIV_INPUT_ID = "main-content-div-input-id"

# --- FormTexts ---
CRNS_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID = "crns_upload_feedback"
PREDICTOR_UPLOAD_FEEDBACK_FORMTEXT_INPUT_ID = "predictor_upload_feedback"

# --- Hiddens ---
HIDDEN_CRNS_UPLOAD_INPUT_INPUT_ID = "hidden_crns_upload"
HIDDEN_PREDICTOR_UPLOAD_INPUT_INPUT_ID = "hidden_predictor_upload"

# --- Stores ---
JOB_STORE_INPUT_ID = "job-store-input-id"

# --- Uploads ---
CRNS_UPLOAD_INPUT_ID = "crns_upload"  # nocheck - used via FormFactory
PREDICTOR_UPLOAD_INPUT_ID = "predictor_upload"  # nocheck - used via FormFactory

# =============================================================================
# SUBMISSION
# =============================================================================

# --- Buttons ---
CHANGE_INPUT_BUTTON_SUBMISSION_ID = "change-input-button-submission-id"
SPAWN_BUTTON_SUBMISSION_ID = "spawn-button-submission-id"
SUBMIT_JOB_BUTTON_SUBMISSION_ID = "submit-job-button-submission-id"
RESULT_BUTTON_SUBMISSION_ID = "result-button-submission-id"

# --- Divs ---
HEADER_DIV_SUBMISSION_ID = "header-div-submission-id"
HEADER_SUBTITLE_DIV_SUBMISSION_ID = "header-div-submission-id-subtitle"
MAIN_CONTENT_DIV_SUBMISSION_ID = "main-content-div-submission-id"
JOB_LOGS_DIV_SUBMISSION_ID = "job-logs-div-submission-id"
STATUS_DIV_SUBMISSION_ID = "status-div-submission-id"

# --- Stores ---
JOB_STORE_SUBMISSION_ID = "job-store-submission-id"

# --- Icons ---
ICON_SUBMISSION_ID = "icon-submission-id"

# --- Intervals ---
INTERVAL_SUBMISSION_ID = "interval-submission-id"

# --- Accordions ---
ACCORDION_SUBMISSION_ID = "accordion-submission-id"

# --- Time displays ---
TIME_TO_LIFE_DIV_SUBMISSION_ID = "time-to-life-div-submission-id"

# =============================================================================
# RESULTS
# =============================================================================

# --- Buttons ---
SWITCH_MAP_BUTTON_RESULTS_ID = "switch-map-button-results-id"
DATE_PAGINATION_MAP_BUTTON_RESULTS_ID = "date-pagination-map-button-results-id"
DATE_PAGINATION_STATS_BUTTON_RESULTS_ID = "date-pagination-stats-button-results-id"

# --- Divs ---
HEADER_DIV_RESULTS_ID = "header-div-results-id"
HEADER_SUBTITLE_DIV_RESULTS_ID = "header-div-results-id-subtitle"
MAIN_CONTENT_DIV_RESULTS_ID = "main-content-div-results-id"
RESULT_CONTAINER_DIV_RESULTS_ID = "result-container-div-results-id"
CURRENT_DATE_DISPLAY_DIV_RESULTS_ID = "current-date-display-div-results-id"
CURRENT_MAP_TYPE_BOX_DIV_RESULTS_ID = "current-map-type-box-div-results-id"
PREVIOUS_MAP_TYPE_BOX_DIV_RESULTS_ID = "previous-map-type-box-div-results-id"
STATS_CONTAINER_DIV_RESULTS_ID = "stats-container-div-results-id"
DUMMY_DIV_RESULTS_ID = "dummy-div-results-id"
IMPORTANCE_SELECTED_DIV_RESULTS_ID = "importance-selected-div-results-id"

# --- Dropdowns ---
DATE_SELECTOR_DROPDOWN_RESULTS_ID = "date-selector-dropdown-results-id"
MAP_TYPE_SELECTOR_DROPDOWN_RESULTS_ID = "map-type-selector-dropdown-results-id"
STATS_VIEW_SELECTOR_DROPDOWN_RESULTS_ID = "stats-view-selector-dropdown-results-id"

# --- Graphs ---
SOIL_MOISTURE_MAP_GRAPH_RESULTS_ID = "soil-moisture-map-graph-results-id"
CORRELATION_GRAPH_RESULTS_ID = "correlation-graph-results-id"
CORRELATION_FIGURE_GRAPH_RESULTS_ID = "correlation-figure-graph-results-id"
IMPORTANCE_GRAPH_RESULTS_ID = "importance-graph-results-id"

# --- Sliders ---
OPACITY_SLIDER_RESULTS_ID = "opacity-slider-results-id"

# --- Stores ---
JOB_STORE_RESULTS_ID = "job-store-results-id"
MAP_TYPES_STORE_RESULTS_ID = "map-types-store-results-id"
COLOR_BAR_INFO_STORE_RESULTS_ID = "color-bar-info-store-results-id"
PREVIOUS_MAP_TYPE_STORE_RESULTS_ID = "previous-map-type-store-results-id"
STATS_DATA_STORE_RESULTS_ID = "stats-data-store-results-id"

# --- Switches ---
MEASUREMENTS_SWITCH_RESULTS_ID = "measurements-switch-results-id"

# --- Tabs ---
TABS_RESULTS_ID = "tabs-results-id"

# =============================================================================
# WORKER_MANAGEMENT
# =============================================================================

# --- Buttons ---
REFRESH_BUTTON_WORKER_MANAGEMENT_ID = "refresh-button-worker-management-id"
KILL_BUTTON_WORKER_MANAGEMENT_ID = "kill-button-worker-management-id"
CANCEL_BUTTON_WORKER_MANAGEMENT_ID = "cancel-button-worker-management-id"
KILL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID = (
    "kill-modal-cancel-button-worker-management-id"
)
KILL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID = (
    "kill-modal-confirm-button-worker-management-id"
)
CANCEL_MODAL_CANCEL_BUTTON_WORKER_MANAGEMENT_ID = (
    "cancel-modal-cancel-button-worker-management-id"
)
CANCEL_MODAL_CONFIRM_BUTTON_WORKER_MANAGEMENT_ID = (
    "cancel-modal-confirm-button-worker-management-id"
)

# --- Divs ---
DUMMY_DIV_WORKER_MANAGEMENT_ID = "dummy-div-worker-management-id"
STATS_CARD_DIV_WORKER_MANAGEMENT_ID = "stats-card-div-worker-management-id"
LAST_REFRESH_DIV_WORKER_MANAGEMENT_ID = "last-refresh-div-worker-management-id"
KILL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID = (
    "kill-modal-task-info-div-worker-management-id"
)
CANCEL_MODAL_TASK_INFO_DIV_WORKER_MANAGEMENT_ID = (
    "cancel-modal-task-info-div-worker-management-id"
)

# --- Modals ---
KILL_MODAL_WORKER_MANAGEMENT_ID = "kill-modal-worker-management-id"
CANCEL_MODAL_WORKER_MANAGEMENT_ID = "cancel-modal-worker-management-id"

# --- Tables ---
ACTIVE_TASKS_TABLE_WORKER_MANAGEMENT_ID = "active-tasks-table-worker-management-id"
RESERVED_TASKS_TABLE_WORKER_MANAGEMENT_ID = "reserved-tasks-table-worker-management-id"
SCHEDULED_TASKS_TABLE_WORKER_MANAGEMENT_ID = (
    "scheduled-tasks-table-worker-management-id"
)
REVOKED_TASKS_TABLE_WORKER_MANAGEMENT_ID = "revoked-tasks-table-worker-management-id"

# =============================================================================
# CRNS_ADMIN
# =============================================================================

# --- Buttons ---
SAVE_CONFIG_BUTTON_CRNS_ADMIN_ID = "save-config-button-crns-admin-id"
START_UPDATE_BUTTON_CRNS_ADMIN_ID = "start-update-button-crns-admin-id"
PURGE_BUTTON_CRNS_ADMIN_ID = "purge-button-crns-admin-id"
REFRESH_BUTTON_CRNS_ADMIN_ID = "refresh-button-crns-admin-id"
PURGE_MODAL_CANCEL_BUTTON_CRNS_ADMIN_ID = "purge-modal-cancel-button-crns-admin-id"
PURGE_MODAL_CONFIRM_BUTTON_CRNS_ADMIN_ID = "purge-modal-confirm-button-crns-admin-id"

# --- Divs ---
DUMMY_DIV_CRNS_ADMIN_ID = "dummy-div-crns-admin-id"
FAILED_COUNT_DIV_CRNS_ADMIN_ID = "failed-count-div-crns-admin-id"
LAST_RUN_INFO_DIV_CRNS_ADMIN_ID = "last-run-info-div-crns-admin-id"

# --- Alerts ---
STATUS_ALERT_CRNS_ADMIN_ID = "status-alert-crns-admin-id"

# --- Inputs ---
START_DATE_INPUT_CRNS_ADMIN_ID = "start-date-input-crns-admin-id"
END_DATE_INPUT_CRNS_ADMIN_ID = "end-date-input-crns-admin-id"

# --- Modals ---
PURGE_MODAL_CRNS_ADMIN_ID = "purge-modal-crns-admin-id"

# --- Tables ---
LOGS_TABLE_CRNS_ADMIN_ID = "logs-table-crns-admin-id"

# =============================================================================
# JOB_MANAGEMENT
# =============================================================================

# --- Buttons ---
DELETE_BUTTON_JOB_MANAGEMENT_ID = "delete-button-job-management-id"
CLEAN_BUTTON_JOB_MANAGEMENT_ID = "clean-button-job-management-id"
REFRESH_BUTTON_JOB_MANAGEMENT_ID = "refresh-button-job-management-id"

# --- Stores ---
DUMMY_STORE_JOB_MANAGEMENT_ID = "dummy-store-job-management-id"

# --- Tables ---
JOBS_TABLE_JOB_MANAGEMENT_ID = "jobs-table-job-management-id"

# =============================================================================
# SENSOR_MANAGEMENT
# =============================================================================

# --- Alerts ---
SYNC_STATUS_ALERT_SENSOR_MANAGEMENT_ID = "sync-status-alert-sensor-management-id"

# --- Buttons ---
REFRESH_DATABASE_BUTTON_SENSOR_MANAGEMENT_ID = (
    "refresh-database-button-sensor-management-id"
)
SUBMIT_EDIT_BUTTON_SENSOR_MANAGEMENT_ID = "submit-edit-button-sensor-management-id"

# --- Feedbacks ---
DATASTREAMS_FEEDBACK_SENSOR_MANAGEMENT_ID = "datastreams-feedback-sensor-management-id"

# --- Inputs ---
EDIT_SENSOR_INPUT_SENSOR_MANAGEMENT_ID = "edit-sensor-input-sensor-management-id"
EDIT_SENSOR_NAME_INPUT_SENSOR_MANAGEMENT_ID = (
    "edit-sensor-name-input-sensor-management-id"
)

# --- Selects ---
EDIT_SENSOR_TYPE_SELECT_SENSOR_MANAGEMENT_ID = (
    "edit-sensor-type-select-sensor-management-id"
)

# --- Stores ---
DATABASE_SENSORS_STORE_SENSOR_MANAGEMENT_ID = (
    "database-sensors-store-sensor-management-id"
)
API_SENSORS_STORE_SENSOR_MANAGEMENT_ID = "api-sensors-store-sensor-management-id"
REFRESH_STORE_SENSOR_MANAGEMENT_ID = "refresh-store-sensor-management-id"

# --- Switches ---
EDIT_IGNORED_SWITCH_SENSOR_MANAGEMENT_ID = "edit-ignored-switch-sensor-management-id"

# --- Tables ---
DATABASE_SENSORS_TABLE_SENSOR_MANAGEMENT_ID = (
    "database-sensors-table-sensor-management-id"
)
API_SENSORS_TABLE_SENSOR_MANAGEMENT_ID = "api-sensors-table-sensor-management-id"

# --- Textareas ---
EDIT_DATASTREAMS_TEXTAREA_SENSOR_MANAGEMENT_ID = (
    "edit-datastreams-textarea-sensor-management-id"
)

# =============================================================================
# LOGS
# =============================================================================

# --- DatePickers ---
DATE_RANGE_DATEPICKER_LOGS_ID = "date-range-datepicker-logs-id"

# --- Divs ---
LOG_OUTPUT_DIV_LOGS_ID = "log-output-div-logs-id"
TIME_ERROR_DIV_LOGS_ID = "time-error-div-logs-id"

# --- Dropdowns ---
LOG_LEVELS_DROPDOWN_LOGS_ID = "log-levels-dropdown-logs-id"
LOG_TAGS_DROPDOWN_LOGS_ID = "log-tags-dropdown-logs-id"

# --- Input Groups ---
TIME_INPUT_GROUP_LOGS_ID = "time-input-group-logs-id"

# --- Inputs ---
START_HOUR_INPUT_LOGS_ID = "start-hour-input-logs-id"
START_MINUTE_INPUT_LOGS_ID = "start-minute-input-logs-id"
END_HOUR_INPUT_LOGS_ID = "end-hour-input-logs-id"
END_MINUTE_INPUT_LOGS_ID = "end-minute-input-logs-id"
PID_INPUT_LOGS_ID = "pid-input-logs-id"

# --- Buttons ---
REFRESH_BUTTON_LOGS_ID = "refresh-button-logs-id"

# --- Checklists ---
PID_RADIO_CHECKLIST_LOGS_ID = "pid-radio-checklist-logs-id"
LIVE_MODE_CHECKLIST_LOGS_ID = "live-mode-checklist-logs-id"

# --- Dropdowns (continued) ---
MODULE_EXCLUDE_DROPDOWN_LOGS_ID = "module-exclude-dropdown-logs-id"

# --- Intervals ---
AUTO_POLL_INTERVAL_LOGS_ID = "auto-poll-interval-logs-id"

# =============================================================================
# MEASUREMENT_VIEW
# =============================================================================

# --- Buttons ---
LOAD_BUTTON_MEASUREMENT_VIEW_ID = "load-button-measurement-view-id"
EXPORT_BUTTON_MEASUREMENT_VIEW_ID = "export-button-measurement-view-id"

# --- DatePickers ---
DATE_RANGE_PICKER_MEASUREMENT_VIEW_ID = "date-range-picker-measurement-view-id"

# --- Divs ---
STATS_CONTENT_DIV_MEASUREMENT_VIEW_ID = "stats-content-div-measurement-view-id"
PREVIEW_IMAGE_DIV_MEASUREMENT_VIEW_ID = "preview-image-div-measurement-view-id"
CURRENT_DATA_STORE_DIV_MEASUREMENT_VIEW_ID = (
    "current-data-store-div-measurement-view-id"
)

# --- Downloads ---
DOWNLOAD_CSV_MEASUREMENT_VIEW_ID = "download-csv-measurement-view-id"

# --- Dropdowns ---
TYPE_DROPDOWN_MEASUREMENT_VIEW_ID = "type-dropdown-measurement-view-id"

# --- Feedbacks ---
TRANSFORMATION_FEEDBACK_MEASUREMENT_VIEW_ID = (
    "transformation-feedback-measurement-view-id"
)

# --- Input Groups ---
BBOX_INPUT_GROUP_MEASUREMENT_VIEW_ID = "bbox-input-group-measurement-view-id"

# --- Inputs ---
BBOX_MIN_LON_INPUT_MEASUREMENT_VIEW_ID = "bbox-min-lon-input-measurement-view-id"
BBOX_MIN_LAT_INPUT_MEASUREMENT_VIEW_ID = "bbox-min-lat-input-measurement-view-id"
BBOX_MAX_LON_INPUT_MEASUREMENT_VIEW_ID = "bbox-max-lon-input-measurement-view-id"
BBOX_MAX_LAT_INPUT_MEASUREMENT_VIEW_ID = "bbox-max-lat-input-measurement-view-id"
PROJECTION_INPUT_MEASUREMENT_VIEW_ID = "projection-input-measurement-view-id"

# --- Switches ---
REPRESENTATIVE_SWITCH_MEASUREMENT_VIEW_ID = "representative-switch-measurement-view-id"

# --- Tables ---
MEASUREMENTS_TABLE_MEASUREMENT_VIEW_ID = "measurements-table-measurement-view-id"
