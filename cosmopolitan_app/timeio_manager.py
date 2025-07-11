"""This module manages the data acquisition from the STI API."""

import hashlib
import json
import logging
import time
import traceback
from asyncio.exceptions import TimeoutError
from datetime import date, datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from pprint import pformat
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import requests
from requests.exceptions import HTTPError, RequestException

from cosmopolitan_app.postgres_manager import PostgresManager
from cosmopolitan_app.timeio_info import (
    ignore_things,
    thing_datastream_dict,
    thing_info_dict,
    type_id_dict,
)

EARLIEST_START_DATE = datetime(2016, 1, 1, 0, 0, 0)


class TimeIOManager:
    """This class manages the data acquisition from the STI API."""

    base_url = "https://tsm.ufz.de/sta/crnscosmicrayneutronsens_b1b36815413f48ea92ba3a0fbc795f7b/v1.1"  # noqa: E501

    date_format = "%Y-%m-%dT%H:%M:%SZ"

    @classmethod
    def request_data(cls, query: str):
        """Request data from the STI API and yield results synchronously."""
        max_retries = 3
        original_query = query
        while query:
            try:
                response = requests.get(query, timeout=120)
                response.raise_for_status()
                data = response.json()
                for item in data.get("value", []):
                    yield query, item
                query = data.get("@iot.nextLink")
                max_retries = 3
            except (
                RequestException,
                TimeoutError,
                HTTPError,
            ) as error:
                logging.info(f"Error: {error}")
                logging.info(f"Query: {query}")
                logging.info(
                    f"Hash of query: {hashlib.md5(query.encode()).hexdigest()}"
                )
                logging.info(f"Time of error: {datetime.now()}")
                if max_retries == 0:
                    logging.error("Max retries reached. Exiting.")
                    logging.error(f"Original query: {original_query}")
                    raise error
                logging.info("Retrying request.")
                if max_retries == 3:
                    time.sleep(10)
                elif max_retries == 2:
                    time.sleep(120)
                elif max_retries == 1:
                    time.sleep(300)
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
        logging.debug(f"Requesting things from {url}")
        querys, items = cls.collect_data(url)
        return items

    @classmethod
    def get_datastreams_of_thing(cls, thing_id: int) -> list:
        """Get the datastreams for a thing from the STI API."""
        url = f"{cls.base_url}/Things({thing_id})/Datastreams?$select=id,name"
        logging.debug(f"Requesting datastreams for thing {thing_id} from {url}")
        querys, items = cls.collect_data(url)
        return items

    @classmethod
    def get_location_of_thing(cls, thing_id: int) -> Optional[Dict[str, float]]:
        """Get the location of a thing from the STI API."""
        url = f"{cls.base_url}/Things({thing_id})/Locations"
        logging.debug(f"Requesting location for thing {thing_id} from {url}")
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
        datastream_dict = thing_datastream_dict[thing_id]
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

        for datastream_id, datastream_name in thing_datastream_dict[thing_id].items():
            dates, results = cls.get_values(start_date, end_date, datastream_id)
            new_df: pd.DataFrame = pd.DataFrame({datastream_name: results}, index=dates)
            # Find duplicate indices
            duplicates = new_df.index[new_df.index.duplicated(keep=False)]
            if len(duplicates) > 0:
                logging.warning(
                    f"Duplicate timestamps for datastream {datastream_name}:"
                )
                logging.warning(new_df.loc[duplicates])

            if datastream_name == "Neutron counts":
                # Convert neutron counts to soil moisture
                new_df[datastream_name] = np.minimum(
                    0.13 * np.sqrt(new_df[datastream_name]) + 0.1, 0.6
                )
            new_df = new_df[~new_df.index.duplicated(keep="first")]
            dataframes.append(new_df)

        if not dataframes:
            return None

        if len(dataframes) == 1:
            df: pd.DataFrame = dataframes[0].reset_index()
        else:
            df: pd.DataFrame = pd.concat(dataframes, axis=1)
            df = df.reset_index()

        df.rename(columns={"index": "date_time"}, inplace=True)

        if cls.is_stationary(thing_id):
            longitude, latitude = cls.get_location_of_thing(thing_id)
            df["longitude"] = longitude
            df["latitude"] = latitude

        df["date_time"] = pd.to_datetime(df["date_time"], errors="raise")

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
        logging.info("Checking if all things are available.")
        if thing_info_dict.keys() != thing_datastream_dict.keys():
            raise ValueError("Thing info and datastream dict are not in sync")

        if thing_info_dict.keys() != type_id_dict.keys():
            raise ValueError("Thing info and type id dict are not in sync")

        things = cls.get_things()

        new_thing_datastream_dict = {}
        new_thing_info_dict = {}

        for thing in things:
            if thing["@iot.id"] in thing_info_dict:
                continue
            if thing["@iot.id"] in ignore_things:
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
                "Please add new things to datastream_ids:\n"
                + pformat(new_thing_datastream_dict)
            )
            logging.warning(
                "Please add new things to thing_info_dict:\n"
                + pformat(new_thing_info_dict)
            )


class GeoProximityTracker:
    """This class tracks the proximity of devices based on their coordinates."""

    def __init__(self, proximity_threshold_meters: float = 10):
        """
        Initialize the proximity tracker.

        :param proximity_threshold_meters: Distance threshold for considering positions
               close
        """
        self.device_positions: Dict[date, List[Tuple[float, float]]] = {}
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
        latitude: float,
        longitude: float,
        tracking_date: date,
    ) -> bool:
        """
        Check if the position is new compared to all previously recorded positions.

        :param latitude: Current latitude
        :param longitude: Current longitude
        :param tracking_date: Date of the position (defaults to today)
        :return: True if position is new, False if too close to any previous position
        """
        # If no previous positions for this device and date, add and return True
        if tracking_date not in self.device_positions:
            self.device_positions[tracking_date] = {(latitude, longitude)}
            return True

        # Check against all previous positions for this device and date
        for prev_lat, prev_lon in self.device_positions[tracking_date]:
            distance = self.haversine_distance(prev_lat, prev_lon, latitude, longitude)

            # If too close to any previous position, return False
            if distance <= self.proximity_threshold:
                return False

        # Add new position and return True
        self.device_positions[tracking_date].add((latitude, longitude))
        return True


def find_representative_points_mobile(df, proximity_threshold_meters=100):
    """Find representative points from a DataFrame based on proximity."""
    logging.debug("Finding representative points for mobile devices.")
    df["date"] = df["date_time"].dt.date
    is_representative_mask = []

    for current_date in df["date"].unique():
        daily_data = df[df["date"] == current_date].sort_values("date_time")
        tracker = GeoProximityTracker(proximity_threshold_meters)

        for idx, row in daily_data.iterrows():
            is_rep = tracker.is_position_new(
                latitude=row["latitude"],
                longitude=row["longitude"],
                tracking_date=current_date,
            )
            is_representative_mask.append(is_rep)

    df["is_representative"] = is_representative_mask
    return df.drop(columns=["date"])


def find_representative_points_stationary(df):
    """Mark the first point of each device per day as representative (stationary)."""
    logging.debug("Finding representative points for stationary devices.")
    df = df.copy()
    df["date"] = df["date_time"].dt.date

    df = df.sort_values(["date", "date_time"])

    df["is_representative"] = df.groupby(["date"]).cumcount() == 0

    return df.drop(columns=["date"])


def transfer_data_by_day(start_date: datetime) -> None:
    """Transfer data to the postgres database."""
    logging.info(f"Transferring data for {start_date.strftime('%Y-%m-%d')}")

    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    for thing_dict in TimeIOManager.get_things():
        thing_id = thing_dict["@iot.id"]
        thing_name = thing_dict["name"]
        if thing_id in ignore_things:
            continue

        logging.info(f"Processing thing: {thing_name} (ID: {thing_id})")

        if thing_id not in thing_datastream_dict:
            datastreams = TimeIOManager.get_datastreams_of_thing(thing_id)
            logging.warning(f"Thing {thing_name} with ID {thing_id} unknown.")
            logging.warning(json.dumps(datastreams, indent=4))
            continue

        df = TimeIOManager.collect_datastreams(thing_id, start_date, end_date)
        if df.empty:
            logging.debug("No data found for this thing.")
            continue
        logging.debug(f"Found {len(df)} measurements for {thing_name}.")

        if TimeIOManager.is_stationary(thing_id):
            df = find_representative_points_stationary(df)
        else:
            df = find_representative_points_mobile(df)

        df_new = df.rename(
            columns={
                "Neutron counts": "soil_moisture",
                "is_representative": "representative",
            }
        )
        df_new["error_high"] = df_new["soil_moisture"] + df_new["soil_moisture"] * 0.1
        df_new["error_low"] = df_new["soil_moisture"] - df_new["soil_moisture"] * 0.1
        df_new["sensor_name"] = thing_name
        df_new["sensor_id"] = thing_id

        # Drop all columns that are not in the Postgres table
        df_new = df_new[
            [
                "date_time",
                "soil_moisture",
                "error_high",
                "error_low",
                "sensor_name",
                "sensor_id",
                "representative",
                "longitude",
                "latitude",
            ]
        ]

        PostgresManager.insert_crns_measurements_from_df(df_new)
        logging.info(
            f"Inserted {len(df_new)} measurements for {thing_name} into the database."
        )


def update_crns_measurments() -> None:
    """Update CRNS measurements from the STI API."""
    logging.info("Updating CRNS measurements from STI API.")

    TimeIOManager.check_things()

    start_date = PostgresManager.get_earliest_missing_or_failed_date(
        EARLIEST_START_DATE
    )

    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_date = (datetime.now() - timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    while current_date <= yesterday_date:
        if PostgresManager.was_update_successful(current_date):
            current_date += timedelta(days=1)
            continue

        try:
            transfer_data_by_day(current_date)
            PostgresManager.add_update_crns(current_date)
        except Exception as e:  # noqa: BLE001
            logging.error(f"Error while transferring data for {current_date}: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")

        current_date += timedelta(days=1)


def repopulate_crns_measurements() -> None:
    """Repopulate CRNS measurements from the STI API."""
    logging.info("Repopulating CRNS measurements from STI API.")
    PostgresManager.purge_measurement_points()
    PostgresManager.reset_update_crns()
    update_crns_measurments()


def get_some_points():
    """Test function to get some points."""
    # Coordinates of the point
    lon = 12.126402  # 714635.4541364739
    lat = 51.993319  # 5764911.233944339

    # X1 714000
    # X2 715000
    # Y1 5764000
    # Y2 5766000

    # X1 649000
    # X2 650000
    # Y1 5763000
    # Y1 5764000
    # Small bbox around the point
    bbox = (lon - 0.001, lat - 0.001, lon + 0.001, lat + 0.001)

    # Find the type for sensor_id 99
    types = [t for id, t in type_id_dict.items() if 99 == id]

    # Date range covering the timestamp
    start_date = datetime(2025, 6, 17, 10, 20, 0)
    end_date = datetime(2025, 6, 17, 10, 22, 0)

    representative = True

    print(types)
    results = PostgresManager.get_measurement_points(
        bbox, types, start_date, end_date, representative
    )
    print(results[:10])


def main():
    """Run main."""
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    update_crns_measurments()
    get_some_points()


if __name__ == "__main__":
    main()
