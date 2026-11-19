"""Minimal application endpoint that receives ddoc drift reports.

Stands in for "your application": it accepts the DriftReport envelope
that `ddoc export drift-report --to http` POSTs to `<base_url>/drift-report`,
checks the API key, prints a one-line summary and stores the report.

    python receiver.py --port 8090 --api-key demo-key --out received

Standard library only.
"""
import argparse
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def make_handler(api_key: str, out_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/drift-report":
                self.send_error(404)
                return
            if api_key and self.headers.get("X-API-Key") != api_key:
                self.send_error(401, "bad API key")
                return
            length = int(self.headers.get("Content-Length", 0))
            report = json.loads(self.rfile.read(length))

            drift = report.get("drift", {})
            verdict = report.get("raw", {}).get("verdict", "?")
            print(
                f"received from {report.get('source', {}).get('app_id')}: "
                f"verdict={verdict} severity={drift.get('severity')} "
                f"overall={drift.get('scores', {}).get('overall')}",
                flush=True,
            )

            out_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            (out_dir / f"drift_{stamp}.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            body = json.dumps({"status": "accepted"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # keep the console to the summary line
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--api-key", default="")
    parser.add_argument("--out", default="received")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), make_handler(args.api_key, Path(args.out)))
    print(f"listening on http://127.0.0.1:{args.port}/drift-report", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
