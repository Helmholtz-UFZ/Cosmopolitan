"""Set up mock input data for testing in development and production."""

import importlib.resources
import json
from io import BytesIO

from soil_moisture_prediction.create_usage_information import file_exeptions
from werkzeug.datastructures import MultiDict


def iterate_test_data():
    """Yield the file paths of the test data.

    Yields:
        str: Full path of a file in the 'test_data' directory.
    """
    package = importlib.import_module("soil_moisture_prediction")
    test_data_dir = importlib.resources.files(package) / "test_data"

    for file_path in test_data_dir.iterdir():
        if file_path.is_file() and file_path.name not in file_exeptions:
            yield file_path


def load_parameters():
    """Load the parameters from the 'parameters.json' file.

    Returns:
        dict: The parameters loaded from the 'parameters.json' file.
    """
    for file_path in iterate_test_data():
        if str(file_path.name) == "parameters.json":
            with file_path.open("r") as file:
                return json.load(file)
    raise FileNotFoundError("No 'parameters.json' file found.")


def create_valid_form_data():
    """Create a MultiDict object representing a valid form data.

    The data is contained in the soil_moisture_prediction package. Many parameters are
    found in the paramaters.json file. The input are available as well.
    """
    return MultiDict(
        {
            "job_id": "valid_form_data",
            "previous_job_id": "valid_form_data",
            "email": "test@test.de",
            "area_x1": parameters["geometry"][0],
            "area_x2": parameters["geometry"][1],
            "area_y1": parameters["geometry"][2],
            "area_y2": parameters["geometry"][3],
            "area_res": parameters["geometry"][4],
            "projection": parameters["projection"],
            "pred_streams": "remove_all",
            "pred_files": create_input_files("pred"),
            "crn_file": create_input_files("crn")[0],
            "selected_pred_input": "",
            "selected_crn_file": "",
            "monte_carlo_iterations": parameters["monte_carlo_iterations"],
            "monte_carlo_soil_moisture": "y",
            "monte_carlo_predictor": "y",
            "past_prediction_as_feature": "y",
            "allow_nan_in_training": "y",
            "monte_carlo_predictors": "y",
            "predictor_qmc_sampling": "y",
            "compute_slope": "y",
            "compute_aspect": "y",
        }
    )


def create_pre_invalid_form_data():
    """Create a MultiDict object representing an invalid form data.

    Should fail at the checks by field.
    """
    return MultiDict(
        {
            "job_id": "invalid_form_data",
            "previous_job_id": "invalid_form_data",
            "email": "testtest.de",
            "area_x1": parameters["geometry"][0],
            "area_x2": parameters["geometry"][0] - 1,
            "area_y1": parameters["geometry"][2],
            "area_y2": parameters["geometry"][3],
            "area_res": parameters["geometry"][4],
            "projection": parameters["projection"],
            "pred_files": create_invalid_files(["pdf"]),
            "pred_streams": "remove_all",
            "crn_file": create_invalid_files(["pdf"])[0],
            "selected_pred_input": "",
            "selected_crn_file": "",
            "monte_carlo_iterations": -1,
            "monte_carlo_soil_moisture": "y",
            "monte_carlo_predictor": "y",
            "past_prediction_as_feature": "y",
            "allow_nan_in_training": "y",
            "monte_carlo_predictors": "y",
            "predictor_qmc_sampling": "y",
            "compute_slope": "y",
            "compute_aspect": "y",
        }
    )


def create_post_invalid_form_data():
    """Create a MultiDict object representing an invalid form data.

    Should fail at the checks betweeen field.
    """
    return MultiDict(
        {
            "job_id": "valid_form_data",
            "previous_job_id": "valid_form_data",
            "email": "test@test.de",
            "area_x1": parameters["geometry"][0],
            "area_x2": parameters["geometry"][0],
            "area_y1": parameters["geometry"][2],
            "area_y2": parameters["geometry"][2],
            "area_res": parameters["geometry"][4],
            "projection": parameters["projection"],
            "pred_streams": "remove_all",
            "pred_files": create_invalid_files(["empty"]),
            "crn_file": create_invalid_files(["empty"])[0],
            "selected_pred_input": "",
            "selected_crn_file": "",
            "monte_carlo_iterations": parameters["monte_carlo_iterations"],
            "monte_carlo_soil_moisture": "y",
            "monte_carlo_predictor": "y",
            "past_prediction_as_feature": "y",
            "allow_nan_in_training": "y",
            "monte_carlo_predictors": "y",
            "predictor_qmc_sampling": "y",
            "compute_slope": "y",
            "compute_aspect": "y",
        }
    )


def create_invalid_files(input_type):
    """Create a list of MockFileStorage objects as invalid input files."""
    mock_file_list = []
    pdf_content = b"%PDF-1.6\r%\xe2\xe3\xcf\xd3\r\n471 0 obj\n<</Filter/FlateDecode"
    if "pdf" in input_type:
        mock_file_list.append(MockFileStorage(filename="some.pdf", content=pdf_content))
    if "empty" in input_type:
        mock_file_list.append(MockFileStorage(filename="", content=b""))
    return mock_file_list


def create_input_files(input_type):
    """Create a list of MockFileStorage objects as input files.

    Args:
        input_type (str): The type of input files to create, either "pred" or "crn".

    Returns:
        list: A list of MockFileStorage objects representing the input files.
    """
    mock_file_list = []
    for file_path in iterate_test_data():
        if input_type in str(file_path.name):
            with file_path.open("rb") as file:
                mock_file_list.append(
                    MockFileStorage(filename=file_path.name, content=file.read())
                )
    return mock_file_list


class MockFileStorage:
    """A mock up for files passed from the request to flask.

    Attributes:
        filename (str): The name of the file.
        content_type (str): The content type of the file.
        streamIO (BytesIO): A BytesIO object containing the file content.
    """

    def __init__(
        self, filename="", content_type="application/octet-stream", content=b""
    ):
        """Init."""
        self.filename = filename
        self.content_type = content_type
        self.content = content
        self.streamIO = BytesIO(content)

    @property
    def stream(self):
        """Return a BytesIO object representing the file content.

        The stream is reset to the beginning before returning.
        """
        try:
            self.streamIO.seek(0)
        except ValueError:
            self.streamIO = BytesIO(self.content)
        return self.streamIO


parameters = load_parameters()
valid_form_data = create_valid_form_data()
pre_invalid_form_data = create_pre_invalid_form_data()
post_invalid_form_data = create_post_invalid_form_data()
