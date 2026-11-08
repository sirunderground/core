"""Constants for the FLO Home X3 integration."""

import logging

DOMAIN = "flo_x3"
LOGGER = logging.getLogger(__package__)

CONF_API_VERSION = "api_version"
CONF_STATION_ID = "station_id"

API_BASE_URL = "https://emobility.flo.ca"
IDP_ACCOUNT_ID = "6cedc65f-98e2-4651-bdb8-88ee4936c9ba"
IDP_BASE_URL = f"https://auth.pingone.ca/{IDP_ACCOUNT_ID}/as"
CLIENT_ID = "f270e301-24ae-45fb-804d-98b9639f6183"
API_VERSIONS = ("v3.1", "v3.0")
