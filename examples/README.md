# Examples

Small, runnable examples of putting ddoc to work. Each directory has
its own README.

| Example | What it shows |
|---|---|
| [`serve/`](serve/) | Run `ddoc serve` (REST API + browser GUI) in a container with Docker Compose |
| [`ci-gate/`](ci-gate/) | Fail a CI job when data drifted, with the GitHub Action or a plain shell step |
| [`app-integration/`](app-integration/) | An application and ddoc exchanging data and drift reports with no shared Python code: `fetch` → `diff` → `analyze` → `export` to an HTTP endpoint |

All commands assume you start from the repository root.
