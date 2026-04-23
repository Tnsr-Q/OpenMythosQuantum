"""Example usage of the generated Python SDK."""

from katopu_client import ApiClient, Configuration
from katopu_client.api.default_api import DefaultApi


def main() -> None:
    cfg = Configuration(host="https://api.openmythos.local/v1")
    cfg.access_token = "replace-with-token"

    with ApiClient(cfg) as client:
        api = DefaultApi(client)
        health = api.healthz_get()
        print("healthz:", health)


if __name__ == "__main__":
    main()
