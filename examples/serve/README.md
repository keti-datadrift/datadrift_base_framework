# `ddoc serve` with Docker Compose

Runs ddoc's REST API and browser GUI in a container built from
[`packages/ddoc/Dockerfile`](../../packages/ddoc/Dockerfile) (ddoc core plus the
categorical and tabular plugins).

## Run

```bash
cd examples/serve
mkdir -p data
echo "DDOC_API_KEY=$(python -c 'import secrets; print(secrets.token_hex(16))')" > .env
docker compose up --build -d      # or: docker-compose up --build -d
```

Check that it is up:

```bash
curl http://127.0.0.1:8765/healthz
```

Open http://127.0.0.1:8765 for the GUI.

## Call the API

Put two datasets under `examples/serve/data/` (for example
`data/ref` and `data/cur`); the container sees them under `/data`.

```bash
source .env
curl -s -X POST http://127.0.0.1:8765/analyze/drift \
     -H "X-API-Key: $DDOC_API_KEY" -H 'Content-Type: application/json' \
     -d '{"data_path_ref": "/data/ref", "data_path_cur": "/data/cur"}'
```

Toy data to try it with:

```bash
pip install -e packages/ddoc    # from the repository root
ddoc examples generate categorical --out examples/serve/data --scenario shifted
```

The port is bound to `127.0.0.1` only. To expose it, put a TLS reverse
proxy in front; see [the deploy tutorial](../../packages/ddoc/docs/tutorial/deploy.md).

## Add plugins

Edit the install line in `packages/ddoc/Dockerfile` to add more plugins, for
example `./plugins/ddoc-plugin-timeseries` (copy its directory in the
`COPY` lines as well). The vision plugin needs torch, which makes the
image much larger.
