#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import copy
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional


API_BASE = "https://api.worldquantbrain.com"
ACCEPT_V2 = "application/json;version=2.0"
ACCEPT_V3 = "application/json;version=3.0"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_WAIT = 1800.0
DEFAULT_POLL_INTERVAL = 3.0
USER_AGENT = "worldquant-brain-cli/0.1"

DEFAULT_REGULAR_SETTINGS: Dict[str, Any] = {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 4,
    "neutralization": "SECTOR",
    "truncation": 0.08,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "ON",
    "language": "FASTEXPR",
    "visualization": False,
}

MISSING = object()


@dataclass
class ApiResponse:
    status: int
    headers: Dict[str, str]
    body: bytes
    data: Any
    url: str


class BrainApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        url: Optional[str] = None,
        payload: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.url = url
        self.payload = payload
        self.headers = headers or {}

    @classmethod
    def from_response(cls, response: ApiResponse, fallback: str) -> "BrainApiError":
        payload = response.data
        detail = extract_error_message(payload)
        message = detail or fallback
        return cls(
            message,
            status=response.status,
            url=response.url,
            payload=payload,
            headers=response.headers,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WorldQuant BRAIN alpha simulation/check/submission CLI."
    )
    parser.add_argument("--email", default=os.getenv("WQB_EMAIL"), help="BRAIN account email.")
    parser.add_argument(
        "--password",
        default=os.getenv("WQB_PASSWORD"),
        help="BRAIN account password.",
    )
    parser.add_argument(
        "--cookie-header",
        default=os.getenv("WQB_COOKIE_HEADER"),
        help="Optional raw Cookie header. When provided, the CLI skips password login.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("WQB_API_BASE", API_BASE),
        help=f"API base URL. Defaults to {API_BASE}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("WQB_TIMEOUT", DEFAULT_TIMEOUT)),
        help="Single request timeout in seconds.",
    )
    parser.add_argument(
        "--max-wait",
        type=float,
        default=float(os.getenv("WQB_MAX_WAIT", DEFAULT_MAX_WAIT)),
        help="Max wait time for async polling in seconds.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.getenv("WQB_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)),
        help="Fallback poll interval in seconds when Retry-After is absent.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output instead of compact JSON.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    options_parser = subparsers.add_parser(
        "options",
        help="Fetch /simulations OPTIONS metadata.",
    )
    options_parser.set_defaults(func=command_options)

    alpha_parser = subparsers.add_parser(
        "alpha",
        help="Fetch full alpha detail for an existing alpha id.",
    )
    alpha_parser.add_argument("--alpha-id", required=True, help="Alpha id to inspect.")
    alpha_parser.set_defaults(func=command_alpha)

    operators_parser = subparsers.add_parser(
        "operators",
        help="Fetch the operator catalog visible to the current account.",
    )
    operators_parser.set_defaults(func=command_operators)

    fields_parser = subparsers.add_parser(
        "data-fields",
        help="Fetch /data-fields/summary.",
    )
    fields_parser.set_defaults(func=command_data_fields)

    simulate_parser = subparsers.add_parser(
        "simulate",
        help="Create a simulation and wait for the alpha result.",
    )
    add_payload_args(simulate_parser)
    add_regular_setting_args(simulate_parser)
    simulate_parser.set_defaults(func=command_simulate)

    check_parser = subparsers.add_parser(
        "check",
        help="Fetch submission checks for an existing alpha id.",
    )
    check_parser.add_argument("--alpha-id", required=True, help="Alpha id to check.")
    check_parser.set_defaults(func=command_check)

    submit_parser = subparsers.add_parser(
        "submit",
        help="Submit an existing alpha id.",
    )
    submit_parser.add_argument("--alpha-id", required=True, help="Alpha id to submit.")
    submit_parser.set_defaults(func=command_submit)

    simulate_submit_parser = subparsers.add_parser(
        "simulate-submit",
        help="Simulate a regular alpha or custom payload, run checks, then submit.",
    )
    add_payload_args(simulate_submit_parser)
    add_regular_setting_args(simulate_submit_parser)
    simulate_submit_parser.add_argument(
        "--force-submit",
        action="store_true",
        help="Submit even when check results contain FAIL entries.",
    )
    simulate_submit_parser.add_argument(
        "--allow-pending-checks",
        action="store_true",
        help="Submit even when some checks are still PENDING.",
    )
    simulate_submit_parser.set_defaults(func=command_simulate_submit)

    return parser.parse_args()


def add_payload_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--expression",
        help="Regular alpha expression string to simulate.",
    )
    group.add_argument(
        "--expression-file",
        help="Path to a file containing a regular alpha expression.",
    )
    group.add_argument(
        "--payload-file",
        help="Path to a JSON file containing the exact /simulations request body.",
    )


def add_regular_setting_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--instrument-type", default=DEFAULT_REGULAR_SETTINGS["instrumentType"])
    parser.add_argument("--region", default=DEFAULT_REGULAR_SETTINGS["region"])
    parser.add_argument("--universe", default=DEFAULT_REGULAR_SETTINGS["universe"])
    parser.add_argument("--delay", type=int, default=DEFAULT_REGULAR_SETTINGS["delay"])
    parser.add_argument("--decay", type=int, default=DEFAULT_REGULAR_SETTINGS["decay"])
    parser.add_argument(
        "--neutralization",
        default=DEFAULT_REGULAR_SETTINGS["neutralization"],
    )
    parser.add_argument(
        "--truncation",
        type=float,
        default=DEFAULT_REGULAR_SETTINGS["truncation"],
    )
    parser.add_argument(
        "--pasteurization",
        default=DEFAULT_REGULAR_SETTINGS["pasteurization"],
    )
    parser.add_argument(
        "--unit-handling",
        default=DEFAULT_REGULAR_SETTINGS["unitHandling"],
    )
    parser.add_argument(
        "--nan-handling",
        default=DEFAULT_REGULAR_SETTINGS["nanHandling"],
    )
    parser.add_argument("--language", default=DEFAULT_REGULAR_SETTINGS["language"])
    parser.add_argument(
        "--visualization",
        action="store_true",
        help="Enable visualization in the simulation settings.",
    )


class BrainClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout: float,
        cookie_header: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookie_header = cookie_header
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

    def login(self, email: str, password: str) -> Any:
        token = base64.b64encode(f"{email}:{password}".encode("utf-8")).decode("ascii")
        headers = {"Authorization": f"Basic {token}"}
        response = self._request(
            "POST",
            "/authentication",
            headers=headers,
            accept=ACCEPT_V2,
            json_body=MISSING,
        )
        if response.status >= 400:
            raise BrainApiError.from_response(
                response,
                "Authentication failed. Check credentials or whether reCAPTCHA is required.",
            )
        return response.data

    def fetch_simulation_options(self) -> Any:
        response = self._request("OPTIONS", "/simulations", accept=ACCEPT_V3)
        if response.status >= 400:
            raise BrainApiError.from_response(
                response,
                "Failed to fetch simulation options.",
            )
        return response.data

    def fetch_alpha_detail(self, alpha_id: str) -> Any:
        path = f"/alphas/{urllib.parse.quote(alpha_id)}"
        response = self._request("GET", path, accept=ACCEPT_V2)
        if response.status >= 400:
            raise BrainApiError.from_response(
                response,
                f"Failed to fetch alpha detail for {alpha_id}.",
            )
        return response.data

    def fetch_operators(self) -> Any:
        response = self._request("GET", "/operators", accept=ACCEPT_V2)
        if response.status >= 400:
            raise BrainApiError.from_response(
                response,
                "Failed to fetch operators.",
            )
        return response.data

    def fetch_data_fields_summary(self) -> Any:
        response = self._request("GET", "/data-fields/summary", accept=ACCEPT_V2)
        if response.status >= 400:
            raise BrainApiError.from_response(
                response,
                "Failed to fetch data fields summary.",
            )
        return response.data

    def simulate(self, payload: Any, *, max_wait: float, poll_interval: float) -> Any:
        response = self._request(
            "POST",
            "/simulations",
            accept=ACCEPT_V2,
            json_body=payload,
        )
        if response.status >= 400:
            raise BrainApiError.from_response(
                response,
                "Simulation request failed.",
            )

        location = get_header(response.headers, "Location")
        if not location:
            return response.data
        return self.wait_for_simulation(location, max_wait=max_wait, poll_interval=poll_interval)

    def wait_for_simulation(
        self,
        location: str,
        *,
        max_wait: float,
        poll_interval: float,
    ) -> Any:
        deadline = time.monotonic() + max_wait
        queue = [location]
        results: list[Any] = []

        while queue:
            current = queue.pop(0)
            while True:
                if time.monotonic() > deadline:
                    raise BrainApiError(
                        f"Timed out while polling simulation result at {current}.",
                        url=current,
                    )
                response = self._request("GET", current, accept=ACCEPT_V2)
                if response.status >= 400:
                    raise BrainApiError.from_response(
                        response,
                        f"Failed while polling simulation result at {current}.",
                    )

                payload = response.data
                retry_after = parse_retry_after(get_header(response.headers, "Retry-After"))
                if retry_after is not None:
                    time.sleep(retry_after)
                    continue

                if isinstance(payload, dict) and payload.get("progress") is not None:
                    time.sleep(poll_interval)
                    continue

                if isinstance(payload, dict) and payload.get("children"):
                    child_urls = [f"/simulations/{child}" for child in payload["children"]]
                    queue = child_urls + queue
                    results.append(payload)
                    break

                results.append(payload)
                break

        if len(results) == 1:
            return results[0]
        return {"results": results}

    def check_alpha(self, alpha_id: str, *, max_wait: float, poll_interval: float) -> Any:
        path = f"/alphas/{urllib.parse.quote(alpha_id)}/check"
        deadline = time.monotonic() + max_wait
        while True:
            if time.monotonic() > deadline:
                raise BrainApiError(f"Timed out while checking alpha {alpha_id}.", url=path)
            response = self._request("GET", path, accept=ACCEPT_V2)
            if response.status >= 400:
                raise BrainApiError.from_response(
                    response,
                    f"Check request failed for alpha {alpha_id}.",
                )

            retry_after = parse_retry_after(get_header(response.headers, "Retry-After"))
            if retry_after is None:
                return response.data
            time.sleep(retry_after if retry_after > 0 else poll_interval)

    def submit_alpha(self, alpha_id: str, *, max_wait: float, poll_interval: float) -> Any:
        path = f"/alphas/{urllib.parse.quote(alpha_id)}/submit"
        response = self._request("POST", path, accept=ACCEPT_V2)
        if response.status >= 400:
            raise BrainApiError.from_response(
                response,
                f"Submit request failed for alpha {alpha_id}.",
            )

        retry_after = parse_retry_after(get_header(response.headers, "Retry-After"))
        if retry_after is None:
            return response.data

        deadline = time.monotonic() + max_wait
        while True:
            if time.monotonic() > deadline:
                raise BrainApiError(f"Timed out while submitting alpha {alpha_id}.", url=path)
            time.sleep(retry_after if retry_after > 0 else poll_interval)
            response = self._request("GET", path, accept=ACCEPT_V2)
            if response.status >= 400:
                raise BrainApiError.from_response(
                    response,
                    f"Submit polling failed for alpha {alpha_id}.",
                )
            retry_after = parse_retry_after(get_header(response.headers, "Retry-After"))
            if retry_after is None:
                return response.data

    def _request(
        self,
        method: str,
        path_or_url: str,
        *,
        accept: str,
        headers: Optional[Dict[str, str]] = None,
        json_body: Any = MISSING,
    ) -> ApiResponse:
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}/{path_or_url.lstrip('/')}"
        request_headers = {
            "User-Agent": USER_AGENT,
            "Accept": accept,
        }
        if self.cookie_header:
            request_headers["Cookie"] = self.cookie_header
        if headers:
            request_headers.update(headers)

        data = None
        if json_body is not MISSING:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        request = urllib.request.Request(url, data=data, headers=request_headers, method=method.upper())
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read()
                return ApiResponse(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=body,
                    data=maybe_json_decode(body),
                    url=response.geturl(),
                )
        except urllib.error.HTTPError as exc:
            body = exc.read()
            return ApiResponse(
                status=exc.code,
                headers=dict(exc.headers.items()),
                body=body,
                data=maybe_json_decode(body),
                url=exc.geturl(),
            )


def command_options(args: argparse.Namespace, client: BrainClient) -> Any:
    return client.fetch_simulation_options()


def command_alpha(args: argparse.Namespace, client: BrainClient) -> Any:
    return client.fetch_alpha_detail(args.alpha_id)


def command_operators(args: argparse.Namespace, client: BrainClient) -> Any:
    return client.fetch_operators()


def command_data_fields(args: argparse.Namespace, client: BrainClient) -> Any:
    return client.fetch_data_fields_summary()


def command_simulate(args: argparse.Namespace, client: BrainClient) -> Any:
    payload = load_payload_from_args(args)
    return client.simulate(payload, max_wait=args.max_wait, poll_interval=args.poll_interval)


def command_check(args: argparse.Namespace, client: BrainClient) -> Any:
    result = client.check_alpha(
        args.alpha_id,
        max_wait=args.max_wait,
        poll_interval=args.poll_interval,
    )
    return {
        "alpha_id": args.alpha_id,
        "summary": summarize_checks(result),
        "raw": result,
    }


def command_submit(args: argparse.Namespace, client: BrainClient) -> Any:
    result = client.submit_alpha(
        args.alpha_id,
        max_wait=args.max_wait,
        poll_interval=args.poll_interval,
    )
    return {
        "alpha_id": args.alpha_id,
        "submit": result,
    }


def command_simulate_submit(args: argparse.Namespace, client: BrainClient) -> Any:
    payload = load_payload_from_args(args)
    simulation = client.simulate(payload, max_wait=args.max_wait, poll_interval=args.poll_interval)
    alpha_id = extract_alpha_id(simulation)
    checks = client.check_alpha(alpha_id, max_wait=args.max_wait, poll_interval=args.poll_interval)
    summary = summarize_checks(checks)

    if summary["failed"] and not args.force_submit:
        raise BrainApiError(
            f"Submission blocked because checks failed: {', '.join(summary['failed'])}",
            payload=checks,
        )
    if summary["pending"] and not args.allow_pending_checks:
        raise BrainApiError(
            f"Submission blocked because checks are still pending: {', '.join(summary['pending'])}",
            payload=checks,
        )

    submit = client.submit_alpha(alpha_id, max_wait=args.max_wait, poll_interval=args.poll_interval)
    return {
        "alpha_id": alpha_id,
        "simulation": simulation,
        "check_summary": summary,
        "check_raw": checks,
        "submit": submit,
    }


def load_payload_from_args(args: argparse.Namespace) -> Any:
    if getattr(args, "payload_file", None):
        return load_json_file(args.payload_file)

    expression = getattr(args, "expression", None)
    if getattr(args, "expression_file", None):
        expression = load_text_file(args.expression_file)

    if expression is None:
        raise BrainApiError("No expression or payload was provided.")

    settings = build_regular_settings(args)
    return {
        "type": "REGULAR",
        "settings": settings,
        "regular": expression,
    }


def build_regular_settings(args: argparse.Namespace) -> Dict[str, Any]:
    settings = copy.deepcopy(DEFAULT_REGULAR_SETTINGS)
    settings.update(
        {
            "instrumentType": args.instrument_type,
            "region": args.region,
            "universe": args.universe,
            "delay": args.delay,
            "decay": args.decay,
            "neutralization": args.neutralization,
            "truncation": args.truncation,
            "pasteurization": args.pasteurization,
            "unitHandling": args.unit_handling,
            "nanHandling": args.nan_handling,
            "language": args.language,
            "visualization": bool(args.visualization),
        }
    )
    return settings


def summarize_checks(payload: Any) -> Dict[str, Any]:
    checks = []
    if isinstance(payload, dict):
        checks = (
            payload.get("is", {}).get("checks")
            or payload.get("checks")
            or []
        )
    failed = [check["name"] for check in checks if check.get("result") == "FAIL"]
    pending = [check["name"] for check in checks if check.get("result") == "PENDING"]
    passed = [check["name"] for check in checks if check.get("result") == "PASS"]
    warnings = [check["name"] for check in checks if check.get("result") == "WARNING"]
    return {
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "warning": warnings,
        "total": len(checks),
    }


def extract_alpha_id(simulation_result: Any) -> str:
    if isinstance(simulation_result, dict):
        alpha = simulation_result.get("alpha")
        if isinstance(alpha, dict) and alpha.get("id"):
            return alpha["id"]
        if isinstance(alpha, str) and alpha:
            return alpha
        if simulation_result.get("id"):
            return str(simulation_result["id"])
        results = simulation_result.get("results")
        if isinstance(results, list):
            for item in results:
                try:
                    return extract_alpha_id(item)
                except BrainApiError:
                    continue
    raise BrainApiError(
        "Unable to extract alpha id from simulation result. Provide --alpha-id to the submit command instead.",
        payload=simulation_result,
    )


def ensure_authenticated(args: argparse.Namespace, client: BrainClient) -> None:
    if args.cookie_header:
        return
    if not args.email or not args.password:
        raise BrainApiError(
            "Missing credentials. Set --email/--password or provide --cookie-header."
        )
    client.login(args.email, args.password)


def load_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read().strip()


def load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def maybe_json_decode(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw.decode("utf-8", errors="replace")


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def get_header(headers: Dict[str, str], name: str) -> Optional[str]:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def extract_error_message(payload: Any) -> Optional[str]:
    if payload is None:
        return None
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        recaptcha = payload.get("recaptcha")
        if isinstance(recaptcha, list) and recaptcha:
            return f"reCAPTCHA required or rejected: {', '.join(map(str, recaptcha))}"
        if isinstance(recaptcha, str) and recaptcha.strip():
            return f"reCAPTCHA required or rejected: {recaptcha.strip()}"
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            flat = [extract_error_message(item) or str(item) for item in errors]
            return "; ".join(flat)
        settings = payload.get("settings")
        if isinstance(settings, dict):
            items = []
            for key, value in settings.items():
                if isinstance(value, list):
                    items.extend(f"{key}: {entry}" for entry in value)
            if items:
                return "; ".join(items)
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    if isinstance(payload, list) and payload:
        parts = [extract_error_message(item) or str(item) for item in payload]
        parts = [part for part in parts if part]
        if parts:
            return "; ".join(parts)
    return None


def render_output(payload: Any, *, pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    args = parse_args()
    client = BrainClient(
        base_url=args.base_url,
        timeout=args.timeout,
        cookie_header=args.cookie_header,
    )
    try:
        ensure_authenticated(args, client)
        result = args.func(args, client)
        render_output(result, pretty=args.pretty)
        return 0
    except BrainApiError as exc:
        message = str(exc)
        if exc.status is not None:
            message = f"{message} [status={exc.status}]"
        if exc.url:
            message = f"{message} [url={exc.url}]"
        print(message, file=sys.stderr)
        if exc.payload is not None:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
