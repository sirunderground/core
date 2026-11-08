# FLO Home X3 (Experimental)

This is an experimental, read-only Home Assistant custom integration that polls
the FLO eMobility cloud API. It is based on the community
[`flo-x5-mqtt`](https://github.com/glavoie/flo-x5-mqtt) project. That project
documents API v3.0 for X5 chargers; a community report indicates newer models
may use v3.1. FLO Home X3 compatibility has **not** been verified.

The integration tries API v3.1, then v3.0, and exposes charger connectivity,
vehicle connection/charging state, session current, offered current, voltage,
and transferred energy. It does not expose controls.

## Installation

Copy `custom_components/flo_x3` into the `custom_components` directory of your
Home Assistant configuration, restart Home Assistant, then add **FLO Home X3
(Experimental)** from Settings → Devices & services.

Sign in with the FLO account used by the charger and select the station. The
integration uses FLO's undocumented cloud API and an observed PingOne
username/password OAuth flow. Multifactor authentication is not supported.
Tokens are kept in memory and refreshed while Home Assistant is running.

## Limitations

- X3 API compatibility, authentication behavior, and returned telemetry have
  not been tested against an actual X3 account.
- The endpoints and authentication flow are undocumented and may change or be
  restricted by FLO.
- Data is cloud-polled every 60 seconds; temporary service outages may make
  entities unavailable.
- This integration is separate from Home Assistant's built-in `flo`
  integration for Flo by Moen water monitors.

Do not share account passwords, access tokens, refresh tokens, station IDs, or
unredacted API traces when reporting issues.
