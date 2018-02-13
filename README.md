# Experimental mock consent app

This is a mock consent app for our Hydra install.

* [Docker hub
    page](https://hub.docker.com/r/uisautomation/experimental-mock-consent-app)

## Configuration

The following environment variables must be set for the container to run.

* **CLIENT_ID** - OAuth2 client id to authenticate to hydra
* **CLIENT_SECRET** - OAuth2 client secret to authenticate to hydra
* **TOKEN_ENDPOINT** - Hydra token endpoint
* **CONSENT_ENDPOINT** - Hydra consent endpoint
