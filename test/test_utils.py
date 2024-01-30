import unittest
from cosmopolitan_app import utils


class TestUtils(unittest.TestCase):
    def test_error_response_args(self):
        """Test that the error response args are correct."""
        job_error_exceptions = [
            utils.InvalidJobID,
            utils.SubmittedException,
            utils.NotSubmittedException,
            utils.NotFinishedException,
        ]

        for exception in job_error_exceptions:
            try:
                raise exception("test_job")
            except Exception as job_error:
                template_kwargs, html_error_code, log_it = utils.error_response_args(
                    job_error
                )
            error_message = (
                f"Error response args are incorrect for {exception.__name__}"
            )
            self.assertIsInstance(template_kwargs, dict, error_message)
            self.assertEqual(
                set(template_kwargs.keys()),
                set(["job_id", "error_page"]),
                error_message,
            )
            self.assertEqual(template_kwargs["job_id"], "test_job", error_message)
            self.assertEqual(html_error_code, 400, error_message)
            self.assertFalse(log_it, error_message)


if __name__ == "__main__":
    unittest.main()
