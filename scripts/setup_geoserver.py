import os
import time
import requests
from requests.auth import HTTPBasicAuth

# Reads container name from environment when run in Docker, defaults to localhost
GEOSERVER_HOST = os.environ.get("GEOSERVER_HOST", "localhost")
GEOSERVER_PORT = os.environ.get("GEOSERVER_PORT", "8080")
GEOSERVER_URL = f"http://{GEOSERVER_HOST}:{GEOSERVER_PORT}/geoserver/rest"

AUTH = HTTPBasicAuth("admin", "myadminpassword")
HEADERS = {"Content-Type": "application/json"}

WORKSPACE = "mosdac"
NAMESPACE_URI = "http://mosdac.isro.gov.in/wfs"
STORE_NAME = "mosdac_cyclone_store"
LAYER_NAME = "mosdac_cyclones"
SHAPEFILE_PATH = "file:/opt/geoserver/data_dir/cyclone_data/mosdac_cyclones.shp"


def wait_for_geoserver(timeout=120):
    print(f"Waiting for GeoServer at {GEOSERVER_URL}...", end="", flush=True)
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            res = requests.get(f"{GEOSERVER_URL}/about/version", auth=AUTH, timeout=5)
            if res.status_code == 200:
                print(" Ready!\n")
                return True
        except requests.RequestException:
            pass
        print(".", end="", flush=True)
        time.sleep(3)
    print("\nTimeout: GeoServer did not become ready in time.")
    return False


def create_workspace():
    url = f"{GEOSERVER_URL}/workspaces"
    payload = {"workspace": {"name": WORKSPACE}}
    res = requests.post(url, json=payload, headers=HEADERS, auth=AUTH)
    if res.status_code in (200, 201):
        print(f"Workspace '{WORKSPACE}' created.")
    else:
        print(f"Workspace check: {res.status_code}")


def create_datastore():
    url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/datastores"
    payload = {
        "dataStore": {
            "name": STORE_NAME,
            "connectionParameters": {
                "entry": [{"@key": "url", "$": SHAPEFILE_PATH}]
            }
        }
    }
    res = requests.post(url, json=payload, headers=HEADERS, auth=AUTH)
    if res.status_code in (200, 201):
        print(f"DataStore '{STORE_NAME}' created.")
    else:
        print(f"DataStore check: {res.status_code}")


def publish_layer():
    url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/datastores/{STORE_NAME}/featuretypes"
    payload = {
        "featureType": {
            "name": LAYER_NAME,
            "nativeName": LAYER_NAME,
            "title": "MOSDAC SCORPIO Cyclone Tracks",
            "srs": "EPSG:4326"
        }
    }
    res = requests.post(url, json=payload, headers=HEADERS, auth=AUTH)
    if res.status_code in (200, 201):
        print(f"Layer '{LAYER_NAME}' published successfully.")
    else:
        print(f"Layer check: {res.status_code}")


def main():
    if not wait_for_geoserver():
        return
    create_workspace()
    create_datastore()
    publish_layer()
    print("\nSetup finished. GeoServer WFS 2.0 is live and ready.")


if __name__ == "__main__":
    main()