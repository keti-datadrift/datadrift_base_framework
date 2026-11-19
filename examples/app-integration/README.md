# Application integration

ddoc and the application it watches share no Python code. They meet at
two points:

1. **Data in** — `ddoc fetch <uri> --dest <dir>` materializes the
   application's data locally. `file://` is built in; other schemes
   (`s3://`, `gs://`, `http(s)://`) come from plugins through the same
   `data_source_read` hook.
2. **Reports out** — `ddoc export drift-report <result.json> --to http`
   POSTs a stable JSON envelope (protocol 1.0) to
   `<base_url>/drift-report`, with an `X-API-Key` header when a key is
   configured. `--to file` writes the same envelope to a directory.

## Run the demo

```bash
pip install -e packages/ddoc
examples/app-integration/run.sh
```

It generates a baseline and a shifted sensor dataset, starts
[`receiver.py`](receiver.py) as a stand-in application endpoint, then
runs `fetch` → `diff` → `export`. Expected output ends with:

```
ddoc diff exit code: 1
received from demo-app: verdict=DRIFT severity=critical overall=0.2695
reports stored by the application:
drift_<timestamp>.json
```

Set `WORK_DIR` to keep the files somewhere specific, and
`RECEIVER_PORT` if 8090 is taken.

## The envelope

```json
{
  "protocol_version": "1.0",
  "source": {"app_id": "demo-app", "app_type": "example"},
  "drift": {
    "modality": "tabular",
    "scores": {"overall": 0.2695, "attribute": null, "embedding": null},
    "severity": "critical"
  },
  "diagnosis": {"recommendations": []},
  "raw": {"verdict": "DRIFT", "...": "the full ddoc result"},
  "sent_at": "2026-01-01T00:00:00Z"
}
```

`raw` carries the complete ddoc result, including the verdict and the
most-shifted attributes, so the application can act on whatever it
needs.

## Other ways to call ddoc

- From another service, run `ddoc analyze drift --json` as a subprocess,
  or call the REST API of [`ddoc serve`](../serve/).
- In a pipeline, chain the same steps in a YAML recipe
  (`ddoc recipe run`); see the
  [recipe tutorial](../../packages/ddoc/docs/tutorial/recipe.md).
