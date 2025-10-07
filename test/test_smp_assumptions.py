"""These tests checks assumptions about the soil moisture prediction (SMP) module."""

from cosmopolitan_app.pydantic_models import stream_dic


def test_stream_options():
    """Test that the stream options are as expected."""
    expected_streams = [
        "elevation_bkg",
        "bdod_5-15cm",
        "clay_0-5cm",
        "clay_5-15cm",
        "clay_15-30cm",
        "clay_30-60cm",
        "clay_60-100cm",
        "clay_100-200cm",
        "silt_0-5cm",
        "silt_5-15cm",
        "silt_15-30cm",
        "silt_30-60cm",
        "silt_60-100cm",
        "silt_100-200cm",
        "sand_0-5cm",
        "sand_5-15cm",
        "sand_15-30cm",
        "sand_30-60cm",
        "sand_60-100cm",
        "sand_100-200cm",
        "soc_0-5cm",
        "soc_5-15cm",
        "soc_15-30cm",
        "soc_30-60cm",
        "soc_60-100cm",
        "soc_100-200cm",
        "phh2o_0-5cm",
        "phh2o_5-15cm",
        "phh2o_15-30cm",
        "phh2o_30-60cm",
        "phh2o_60-100cm",
        "phh2o_100-200cm",
        "cec_0-5cm",
        "cec_5-15cm",
        "cec_15-30cm",
        "cec_30-60cm",
        "cec_60-100cm",
        "cec_100-200cm",
        "bulk_density_0-5cm",
        "bulk_density_5-15cm",
        "bulk_density_15-30cm",
        "bulk_density_30-60cm",
        "bulk_density_60-100cm",
        "bulk_density_100-200cm",
    ]
    # New elevation models need specific attention. Results site only knows
    # elevation_bkg as an elevation model. See get_available_map_types.
    assert list(stream_dic.keys()) == expected_streams
