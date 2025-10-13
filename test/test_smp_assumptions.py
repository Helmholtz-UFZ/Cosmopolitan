"""These tests checks assumptions about the soil moisture prediction (SMP) module."""

from cosmopolitan_app.pydantic_models import stream_dic


def test_stream_options():
    """Test that the stream options are as expected."""
    stream_types = [
        "bdod",
        "cec",
        "cfvo",
        "clay",
        "nitrogen",
        "phh2o",
        "sand",
        "silt",
        "soc",
        "ocd",
        "ocs",
    ]

    stream_depths = [
        "0-5cm",
        "5-15cm",
        "15-30cm",
        "30-60cm",
        "60-100cm",
        "100-200cm",
    ]

    expected_streams = ["elevation_bkg"]
    for st in stream_types:
        for sd in stream_depths:
            expected_streams.append(f"{st}_{sd}")

    # New elevation models need specific attention. Results site only knows
    # elevation_bkg as an elevation model. See get_available_map_types.
    for stream in expected_streams:
        assert stream in stream_dic, f"Missing expected stream: {stream}"

    for stream in stream_dic.keys():
        assert (
            stream in expected_streams
        ), f"Found unexpected stream in stream_dic: {stream}"
