"""The same live HTTP scenario for A and B. Ground truth stays outside case evidence."""
import argparse
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request


def now():
    return datetime.now(timezone.utc).isoformat()


class Session:
    def __init__(self, base):
        parsed = urlparse(base)
        if parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1"):
            raise ValueError("Scenario only accepts local HTTP laboratories")
        self.base, self.cookies = base.rstrip("/"), CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookies))

    def request(self, method, path, data=None, json_body=False):
        headers = {"Referer": self.base + "/", "User-Agent": "TASI-controlled-scenario/1"}
        token = next((cookie.value for cookie in self.cookies if cookie.name == "csrftoken"), "")
        if token:
            headers["X-CSRFToken"] = token
        if data is not None:
            headers["Content-Type"] = "application/json" if json_body else "application/x-www-form-urlencoded"
            data = (json.dumps(data) if json_body else urlencode(data, doseq=True)).encode()
        request = Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=30) as response:
                return response.status, response.read(), dict(response.headers)
        except HTTPError as error:
            return error.code, error.read(), dict(error.headers)

    def login(self, username, password):
        self.request("GET", "/")
        code, _, _ = self.request("POST", "/", {"username": username, "password": password})
        code, _, _ = self.request("GET", "/api/records/")
        if code != 200:
            raise RuntimeError("Laboratory login failed")


def run(args):
    if args.output.exists():
        raise ValueError("Ground-truth output already exists")
    values = dict(line.split("=", 1) for line in args.env_file.read_text().splitlines() if "=" in line)
    operator, admin = Session(args.base_url), Session(args.base_url)
    operator.login("lab_operator", values["LAB_DEMO_PASSWORD"])
    admin.login("lab_admin", values["LAB_DEMO_PASSWORD"])
    truth = {"scenario": "scenario-01", "environment": args.environment, "started_at_utc": now(),
             "rules": "Only the initial city correction and temporary contact maintenance are authorized. Other seeded-client mutations and removals violate the scenario authorization.", "operations": []}
    state = {i: {"first_name": name, "last_name": "Ficticio", "email": f"client{i}@example.test", "phone": f"90000000{i}",
                 "address": f"Laboratorio {i}", "city": "Lima", "state": "Lima", "zipcode": "12345"}
             for i, name in enumerate(("Ana", "Luis", "Rosa"), 1)}

    def operation(session, method, path, data, action, channel, ids, expected_status, legitimate,
                  changes=None, classification="change", json_body=False):
        started = now()
        status, body, headers = session.request(method, path, data, json_body)
        finished = now()
        if status != expected_status:
            raise RuntimeError(f"Scenario failed at {method} {path}: HTTP {status}")
        for pk in ids:
            before = dict(state[pk]) if pk in state else {}
            if action == "CREATE":
                state[pk] = dict(data)
            elif action == "UPDATE" and classification != "rejected":
                state[pk].update(changes or {})
            after = dict(state.get(pk, {}))
            if action == "DELETE":
                del state[pk]
                after = {}
            truth["operations"].append({"operation_id": f"OP-{len(truth['operations']) + 1:03}", "started_at_utc": started,
                "finished_at_utc": finished, "status": status, "action": action, "channel": channel, "record_id": pk,
                "actor_username": "lab_admin" if session is admin else "lab_operator", "classification": classification,
                "expected_before": before if action != "CREATE" else {}, "expected_after": after if action != "DELETE" else {},
                "legitimate": legitimate, "rule": "Authorized maintenance" if legitimate else "Seeded-client change/removal outside authorization"})
        # Check effects through a separate read, without using audit evidence to manufacture truth.
        if classification == "change":
            for pk in ids:
                read_status, raw, _ = admin.request("GET", f"/api/records/{pk}/")
                if action == "DELETE":
                    if read_status != 404:
                        raise RuntimeError("Expected deletion was not confirmed")
                elif read_status != 200 or any(json.loads(raw).get(key) != value for key, value in state[pk].items()):
                    raise RuntimeError("Expected persisted fields were not confirmed")

    temporary = {**state[1], "first_name": "Temporal", "email": "temporary@example.test"}
    operation(operator, "POST", "/record/add/", temporary, "CREATE", "web", [4], 200, True)
    operation(operator, "POST", "/record/1/update/", {**state[1], "city": "Arequipa"}, "UPDATE", "web", [1], 200, True, {"city": "Arequipa"})
    operation(operator, "PATCH", "/api/records/1/", {"email": "changed@example.test"}, "UPDATE", "api", [1], 200, False, {"email": "changed@example.test"}, json_body=True)
    operation(operator, "PATCH", "/api/records/1/", {"phone": "988888888"}, "UPDATE", "api", [1], 200, False, {"phone": "988888888"}, json_body=True)
    operation(admin, "POST", "/admin/website/record/1/change/", {**state[1], "city": "Piura"}, "UPDATE", "admin", [1], 200, False, {"city": "Piura"})
    operation(operator, "DELETE", "/api/records/2/", None, "DELETE", "api", [2], 204, False)
    operation(admin, "POST", "/admin/website/record/add/", temporary, "CREATE", "admin", [5], 200, True)
    operation(operator, "POST", "/record/4/delete/", {}, "DELETE", "web", [4], 200, True)
    operation(admin, "POST", "/admin/website/record/", {"action": "delete_selected", "_selected_action": [3, 5], "post": "yes"}, "DELETE", "admin", [3, 5], 200, False)
    operation(operator, "PATCH", "/api/records/1/", {"phone": "988888888"}, "UPDATE", "api", [1], 200, True, {"phone": "988888888"}, classification="noop", json_body=True)
    operation(Session(args.base_url), "POST", "/api/records/", temporary, "CREATE", "api", [99], 403, False, classification="rejected", json_body=True)
    truth["finished_at_utc"] = now()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(truth, stream, ensure_ascii=False, indent=2)
    print(f"{args.environment}: {len(truth['operations'])} observations; truth stored separately at {args.output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--environment", choices=["A", "B"], required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
