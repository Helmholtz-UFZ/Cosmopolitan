"""This module manages the data acquisition from the STI API."""

import json
import logging
import time
from asyncio.exceptions import TimeoutError
from datetime import date, datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import requests
from requests.exceptions import RequestException

from cosmopolitan_app.postgres_manager import PostgresManager


class TimeIOManager:
    """This class manages the data acquisition from the STI API."""

    base_url = "https://tsm.ufz.de/sta/crnscosmicrayneutronsens_b1b36815413f48ea92ba3a0fbc795f7b/v1.1"  # noqa: E501
    values_list = [
        "Atmospheric pressure",
        "Air temperature",
        "Relative humidity",
        "Neutron counts",
    ]

    thing_datastream_dict = {
        44: {
            3180: "Neutron counts",
        },
        85: {
            3762: "Neutron counts",
        },
        92: {
            3716: "Neutron counts",
        },
        93: {
            3808: "Neutron counts",
        },
        94: {
            3898: "Neutron counts",
        },
        95: {
            3921: "Neutron counts",
        },
        97: {
            3831: "Neutron counts",
        },
        99: {
            3739: "Neutron counts",
        },
        107: {
            3785: "Neutron counts",
        },
    }
    thing_info_dict = {
        44: "CRNS - Hohes Holz 4m",
        85: "CRNS - Hordorf",
        92: "CRNS - Cunnersdorf",
        93: "CRNS - Grosses Bruch",
        94: "CRNS - Harzgerode",
        95: "CRNS - Falkenberg",
        97: "CRNS - Zugspitze",
        99: "CRNS - Zerbst",
        107: "CRNS - Svalbard",
    }
    ignore_things = [145]

    date_format = "%Y-%m-%dT%H:%M:%SZ"

    @classmethod
    def request_data(cls, query: str):
        """Request data from the STI API and yield results synchronously."""
        max_retries = 5
        logging.debug(f"Query: {query}")
        while query:
            try:
                start_time = datetime.now()
                response = requests.get(query, timeout=60)
                response.raise_for_status()
                data = response.json()
                logging.debug(f"Request took {datetime.now() - start_time}")
                for item in data.get("value", []):
                    yield query, item
                query = data.get("@iot.nextLink")
                logging.debug(f"Next link: {query}")
            except (
                RequestException,
                TimeoutError,
            ) as error:
                if max_retries == 0:
                    raise error
                logging.warning(f"Error: {error}")
                logging.warning(f"Query: {query}")
                logging.warning("Retrying request.")
                time.sleep(10)
                max_retries -= 1

    @classmethod
    def collect_data(cls, query: str) -> Tuple[list, list]:
        """Collect data from the STI API."""
        querys = []
        items = []
        for query, item in cls.request_data(query):
            querys.append(query)
            items.append(item)
        return querys, items

    @classmethod
    def get_things(cls) -> list:
        """Get the things from the STI API."""
        url = f"{cls.base_url}/Things?$select=id,name"
        querys, items = cls.collect_data(url)
        return items

    @classmethod
    def get_datastreams_of_thing(cls, thing_id: int) -> list:
        """Get the datastreams for a thing from the STI API."""
        url = f"{cls.base_url}/Things({thing_id})/Datastreams?$select=id,name"
        querys, items = cls.collect_data(url)
        return items

    @classmethod
    def get_location_of_thing(cls, thing_id: int) -> Optional[Dict[str, float]]:
        """Get the location of a thing from the STI API."""
        url = f"{cls.base_url}/Things({thing_id})/Locations"
        querys, items = cls.collect_data(url)
        if not items:
            return None
        location = items[0]["location"]
        if not location:
            return None
        longitude = location["coordinates"][0]
        latitude = location["coordinates"][1]
        return longitude, latitude

    @classmethod
    def is_stationary(cls, thing_id: int) -> bool:
        """Check if the thing is stationary."""
        datastream_dict = cls.thing_datastream_dict[thing_id]
        return "longitude" not in datastream_dict.values()

    @classmethod
    def collect_datastreams(
        cls, thing_id: str, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """Collect datastreams for a thing and combine them into a single dataframe.

        Args:
            thing_id: The ID of the thing to get datastreams for
            start_date: The start date for fetching values
            end_date: The end date for fetching values

        Returns:
            A pandas DataFrame with all datastreams merged by date_time, or None if no
            data
        """
        dataframes: List[pd.DataFrame] = []

        for datastream_id, datastream_name in cls.thing_datastream_dict[
            thing_id
        ].items():
            dates, results = cls.get_values(start_date, end_date, datastream_id)
            new_df: pd.DataFrame = pd.DataFrame({datastream_name: results}, index=dates)
            dataframes.append(new_df)

        if not dataframes:
            return None

        if len(dataframes) == 1:
            df: pd.DataFrame = dataframes[0].reset_index()
            df.rename(columns={"index": "date_time"}, inplace=True)
            return df

        df = pd.concat(dataframes, axis=1)

        df = df.reset_index()
        df.rename(columns={"index": "date_time"}, inplace=True)

        if cls.is_stationary(thing_id):
            longitude, latitude = cls.get_location_of_thing(thing_id)
            df["longitude"] = longitude
            df["latitude"] = latitude

        return df

    @classmethod
    def get_values(
        cls,
        start_date: Union[datetime, None],
        end_date: datetime,
        data_stream_id: int,
    ):
        """Get the values from the STI API."""
        select_query = "$select=phenomenonTime,result"  # noqa: E501
        filter_string = "$filter="
        if start_date is None:
            filter_string += f"Datastream/id eq {data_stream_id}"
        elif start_date is not None:
            # Format dates to ISO 8601 format
            start_iso = start_date.strftime(cls.date_format)
            end_iso = end_date.strftime(cls.date_format)
            date_filter = (
                f"phenomenonTime ge {start_iso} and phenomenonTime le {end_iso}"
            )
            filter_string += f"{date_filter} and Datastream/id eq {data_stream_id}"

        query = f"{cls.base_url}/Observations?{filter_string}&{select_query}"
        dates = []
        results = []

        for _query, measurment in cls.request_data(query):
            dates.append(
                datetime.strptime(measurment["phenomenonTime"], "%Y-%m-%dT%H:%M:%SZ")
            )
            results.append(measurment["result"])

        return dates, results

    @classmethod
    def check_things(cls) -> None:
        """Check if the known things are available."""
        if cls.thing_info_dict.keys() != cls.thing_datastream_dict.keys():
            raise ValueError("Thing info and datastream dict are not in sync")
        things = cls.get_things()
        new_thing_datastream_dict = {}
        new_thing_info_dict = {}
        for thing in things:
            if thing["@iot.id"] in cls.thing_info_dict:
                continue
            if thing["@iot.id"] in cls.ignore_things:
                continue
            thing_name = thing["name"]
            thing_id = thing["@iot.id"]
            logging.warning(f"Thing {thing_name} with id {thing_id} unknown")
            new_thing_info_dict[thing_id] = thing_name
            new_thing_datastream_dict[thing_id] = {}
            datastreams = cls.get_datastreams_of_thing(thing_id)
            for datastream in datastreams:
                datastreams_id = datastream["@iot.id"]
                datastreams_name = datastream["name"]
                new_thing_datastream_dict[thing_id][datastreams_id] = (
                    datastreams_name.split(":")[-2]
                )

        if len(new_thing_datastream_dict) > 0:
            logging.warning(
                f"Please add new things to datastream_ids:\n{json.dumps(new_thing_datastream_dict, indent=4)}"  # noqa
            )
            logging.warning(
                f"Please add new things to thing_info_dict:\n{json.dumps(new_thing_info_dict, indent=4)}"  # noqa
            )


class GeoProximityTracker:
    """This class tracks the proximity of devices based on their coordinates."""

    def __init__(self, proximity_threshold_meters: float = 10):
        """
        Initialize the proximity tracker.

        :param proximity_threshold_meters: Distance threshold for considering positions
               close
        """
        self.device_positions: Dict[Tuple[str, date], List[Tuple[float, float]]] = {}
        self.proximity_threshold = proximity_threshold_meters

    def haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """
        Calculate the great circle distance between two points on Earth.

        :param lat1: Latitude of first point
        :param lon1: Longitude of first point
        :param lat2: Latitude of second point
        :param lon2: Longitude of second point
        :return: Distance in meters
        """
        # Earth's radius in meters
        R = 6371000

        # Convert degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        distance = R * c

        return distance

    def is_position_new(
        self,
        device_id: str,
        latitude: float,
        longitude: float,
        tracking_date: date,
    ) -> bool:
        """
        Check if the position is new compared to all previously recorded positions.

        :param device_id: Unique identifier for the device
        :param latitude: Current latitude
        :param longitude: Current longitude
        :param tracking_date: Date of the position (defaults to today)
        :return: True if position is new, False if too close to any previous position
        """
        # Use today's date if no date provided
        if tracking_date is None:
            tracking_date = date.today()

        device_key = (device_id, tracking_date)

        # If no previous positions for this device and date, add and return True
        if device_key not in self.device_positions:
            self.device_positions[device_key] = {(latitude, longitude)}
            return True

        # Check against all previous positions for this device and date
        for prev_lat, prev_lon in self.device_positions[device_key]:
            distance = self.haversine_distance(prev_lat, prev_lon, latitude, longitude)

            # If too close to any previous position, return False
            if distance <= self.proximity_threshold:
                return False

        # Add new position and return True
        self.device_positions[device_key].add((latitude, longitude))
        return True


def update_crns_measurments() -> None:
    """Transfer data to the postgres database."""
    last_update = PostgresManager.last_update_crns()
    if last_update is None:
        start_date = None
        end_date = None
    else:
        start_date = last_update
        end_date = datetime.combine(datetime.now().date(), datetime.min.time())

    start_date = datetime.utcnow() - timedelta(days=1)
    end_date = datetime.utcnow()
    for thing_dict in TimeIOManager.get_things():
        thing_id = thing_dict["@iot.id"]
        thing_name = thing_dict["name"]
        if thing_id in TimeIOManager.ignore_things:
            continue

        logging.info(f"Processing thing: {thing_name} (ID: {thing_id})")

        if thing_id not in TimeIOManager.thing_datastream_dict:
            datastreams = TimeIOManager.get_datastreams_of_thing(thing_id)
            logging.warning(f"Thing {thing_name} with ID {thing_id} unknown.")
            logging.warning(json.dumps(datastreams, indent=4))
            continue

        df = TimeIOManager.collect_datastreams(thing_id, start_date, end_date)
        if TimeIOManager.is_stationary(thing_id):
            print(df)

        print(df)

    return
    for data_stream_id, data_stream_name in TimeIOManager.thing_datastream_dict.get(
        thing_id, {}
    ).items():
        if data_stream_name not in TimeIOManager.values_list:
            continue
        logging.info(
            f"Processing datastream: {data_stream_name} (ID: {data_stream_id})"
        )
        dates, results = TimeIOManager.get_values(start_date, end_date, data_stream_id)
        for date_time, value in zip(dates, results):
            data_to_insert = {
                "date_time": date_time,
                "value": value,
                "thing_id": thing_id,
                "data_stream_id": data_stream_id,
            }
            PostgresManager.add_crns_measurement(data_to_insert)
    geo_proximity_tracker = GeoProximityTracker()

    loop_variabel_dict = {}
    for measurement in TimeIOManager.get_neutron_counts(start_date, end_date):
        (
            query,
            date_time,
            soil_moisture,
            error_high,
            error_low,
            latitude,
            longitude,
            sensor_name,
            sensor_id,
        ) = measurement
        entry = (
            date_time,
            soil_moisture,
            error_high,
            error_low,
            latitude,
            longitude,
            sensor_name,
            sensor_id,
        )
        for prev_query, prev_entry in loop_variabel_dict.items():
            if entry == prev_entry:
                logging.info("Duplicate measurement found.")
                logging.info(f"Query: {query}")
                logging.info(f"Pervious query: {prev_query}")
                logging.info(entry)

        loop_variabel_dict[query] = entry

        if start_date > date_time or end_date < date_time:
            logging.info(f"Measurement out of range: {date_time}")
        representative = geo_proximity_tracker.is_position_new(
            sensor_name, latitude, longitude, date_time.date()
        )
        data_to_insert = {
            "date_time": date_time,
            "soil_moisture": soil_moisture,
            "error_high": error_high,
            "error_low": error_low,
            "latitude": latitude,
            "longitude": longitude,
            "sensor_name": sensor_name,
            "sensor_id": sensor_id,
            "representative": representative,
        }
        PostgresManager.add_soil_moisture(data_to_insert)


async def collect_values():
    """Run main."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    today = datetime.utcnow()
    yesterday = None
    today = None
    # for thing_id, data_streams in TimeIOManager.thing_datastream_dict.items():
    #     print(f"Thing: {thing_id}, {TimeIOManager.thing_info_dict[thing_id]}")
    #     for data_stream_id, data_stream_name in data_streams.items():
    #         async for date_time, value, position in TimeIOManager.get_values(
    #             yesterday, today, data_stream_id
    #         ):
    #             if thing_id in TimeIOManager.stationary_things and position != []:
    #                 print("Stationary thing with position")
    #                 print(date_time, value, position)
    #                 break
    #             if position == []:
    #                 print("No position")
    #                 print(date_time, value, position)
    #                 break

    for thing_id, data_streams in TimeIOManager.thing_datastream_dict.items():
        print(f"Thing: {thing_id}, {TimeIOManager.thing_info_dict[thing_id]}")
        for data_stream_id, data_stream_name in data_streams.items():
            async for date_time, value in TimeIOManager.get_values(
                yesterday, today, data_stream_id
            ):
                print(date_time, value)


def main():
    """Run main."""
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    update_crns_measurments()


if __name__ == "__main__":
    main()

# query_url = build_sti_query(yesterday, today)
# print(query_url)
#
# response = requests.get(query_url, timeout=5)
#
# if response.status_code != 200:
#     logging.warning("Requst failed.")
#     logging.warning(f"Status code: {response.status_code}")
#     logging.warning(f"URL: {query_url}")
#     logging.warning("Response:")
#     try:
#         logging.warning(json.dumps(response.json(), indent=2))
#     except IndexError:
#         logging.warning("No json returned!")
#     response.raise_for_status()
#
# information = response.json()
# print(json.dumps(information, indent=2))
# for station in information["value"]:
#     print(f"Station: {station['@iot.id']}")
#     print(f"Name: {station['name']}")
#     print(
#         f"Location: {station['location']['type']} at {station['location']['coordinates']}"  # noqa: E501
#     )
