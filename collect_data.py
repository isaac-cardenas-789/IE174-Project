import csv
from datetime import datetime
import json
import os
import urllib.request
from zoneinfo import ZoneInfo

# Public Bay Wheels (SF Bay Area) GBFS v2.3 endpoints
INFO_URL = "https://gbfs.lyft.com/gbfs/2.3/bay/en/station_information.json"
STATUS_URL = "https://gbfs.lyft.com/gbfs/2.3/bay/en/station_status.json"
CSV_FILE = "carl_cole_availability.csv"
SF_TZ = ZoneInfo("America/Los_Angeles")


def fetch_json(url):
  req = urllib.request.Request(url, headers={"User-Agent": "IE174-SimProject"})
  with urllib.request.urlopen(req, timeout=15) as response:
    return json.loads(response.read().decode("utf-8"))


def main():
  # 1. Look up station_id and dock capacity for Carl St at Cole St
  info_data = fetch_json(INFO_URL)
  stations_info = info_data["data"]["stations"]
  target_info = next(
      (
          s
          for s in stations_info
          if "carl" in s["name"].lower() and "cole" in s["name"].lower()
      ),
      None,
  )
  if not target_info:
    raise RuntimeError(
        "Could not find Carl & Cole station in station_information.json"
    )

  station_id = target_info["station_id"]
  station_name = target_info["name"]
  capacity = target_info.get("capacity", "")

  # 2. Fetch live bike and dock counts for that station_id
  status_data = fetch_json(STATUS_URL)
  stations_status = status_data["data"]["stations"]
  target_status = next(
      (s for s in stations_status if s["station_id"] == station_id), None
  )
  if not target_status:
    raise RuntimeError(
        f"Station ID {station_id} not found in station_status.json"
    )

  # 3. Convert timestamps to San Francisco local time
  now_sf = datetime.now(SF_TZ).strftime("%Y-%m-%d %H:%M:%S")
  last_reported_unix = target_status.get("last_reported")
  last_reported_sf = (
      datetime.fromtimestamp(last_reported_unix, tz=SF_TZ).strftime(
          "%Y-%m-%d %H:%M:%S"
      )
      if last_reported_unix
      else ""
  )

  total_bikes = target_status.get("num_bikes_available", 0)
  ebikes = target_status.get("num_ebikes_available", 0)
  classic_bikes = max(0, total_bikes - ebikes)

  row = {
      "poll_time_sf": now_sf,
      "station_last_reported_sf": last_reported_sf,
      "station_name": station_name,
      "station_id": station_id,
      "capacity": capacity,
      "total_bikes_available": total_bikes,
      "classic_bikes_available": classic_bikes,
      "ebikes_available": ebikes,
      "docks_available": target_status.get("num_docks_available", 0),
      "bikes_disabled": target_status.get("num_bikes_disabled", 0),
      "docks_disabled": target_status.get("num_docks_disabled", 0),
      "is_renting": target_status.get("is_renting", ""),
      "is_returning": target_status.get("is_returning", ""),
  }

  # 4. Append row to CSV (creates the file with headers on the first run)
  file_exists = os.path.isfile(CSV_FILE)
  with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(row.keys()))
    if not file_exists:
      writer.writeheader()
    writer.writerow(row)


if __name__ == "__main__":
  main()
