"""Deploy the Pages artifact by its ID and confirm the result."""
import json
import os
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def request(url, token, payload=None, *, github=False):
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    if github:
        headers.update({"Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28"})
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    with urlopen(Request(url, data=data, headers=headers), timeout=20) as response:
        return json.load(response)


def deploy(artifact_id):
    api = os.environ["GITHUB_API_URL"] + "/repos/" + os.environ["GITHUB_REPOSITORY"] + "/pages/deployments"
    token = os.environ["GH_TOKEN"]
    oidc = request(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"],
                   os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"])["value"]
    result = request(api, token, {
        "artifact_id": artifact_id,
        "pages_build_version": os.environ["GITHUB_SHA"],
        "oidc_token": oidc,
    }, github=True)
    deployment_id = result.get("id") or result.get("status_url", "").rstrip("/").rsplit("/", 1)[-1]
    if not deployment_id:
        deployment_id = os.environ["GITHUB_SHA"]
    status_url = api + "/" + quote(str(deployment_id), safe="")
    end = time.monotonic() + 480
    while time.monotonic() < end:
        try:
            status = request(status_url, token, github=True)["status"]
        except HTTPError as exc:
            if exc.code not in {404, 429, 500, 502, 503, 504}:
                raise
        else:
            if status == "succeed":
                page_url = result.get("page_url", "")
                if re.fullmatch(r"https?://[^\s]+", page_url):
                    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                        output.write(f"page_url={page_url}\n")
                print("GitHub Pages ha confermato il deploy.")
                return
            if status in {"failed", "cancelled", "canceled", "deployment_cancelled",
                          "deployment_content_failed", "deployment_perms_error", "purged", "superseded"}:
                raise RuntimeError("GitHub Pages ha interrotto il deploy: " + status)
        time.sleep(5)
    raise RuntimeError("GitHub Pages non ha confermato il deploy entro il tempo previsto.")


if __name__ == "__main__":
    try:
        deploy(int(sys.argv[1]))
    except HTTPError as exc:
        sys.exit(f"La richiesta di deploy è stata respinta (HTTP {exc.code}).")
    except URLError:
        sys.exit("La richiesta di deploy non ha raggiunto il servizio.")
    except (KeyError, ValueError):
        sys.exit("Configurazione o risposta del deploy incompleta.")
    except RuntimeError as exc:
        sys.exit(str(exc))
