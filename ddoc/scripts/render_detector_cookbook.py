"""Round 15 — auto-render detector cookbook scores.

Generates a Markdown table of `overall_score` per `--detector` value
on the canonical shifted demo data for both `categorical` and
`image` modalities. The output goes to
``docs/tutorial/_detector_scores.generated.md`` so the main cookbook
can ``include`` it (or copy-paste) and stay synced with what ddoc
actually emits.

Run:
    python -m scripts.render_detector_cookbook
    python -m scripts.render_detector_cookbook --modalities categorical

The script is intentionally side-effect-light: it shells out to
`ddoc examples generate` + `ddoc analyze drift --json` (no
in-process plugin imports) so the same code path users will hit is
what the table reports.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Cookbook truth — keep in sync with docs/tutorial/detectors.md.
_DETECTOR_SETS: dict[str, list[str]] = {
    "categorical": ["default", "jensen_shannon", "overlap"],
    # `image` strategies the cookbook lists; we include them but
    # render the table conditionally — image scoring is heavy
    # (CLIP / torch) so users with --modalities=categorical can
    # opt out.
    "image": ["default", "ensemble", "mmd", "mean_shift",
              "wasserstein", "psi", "cosine"],
}

# Default output file (idempotent; checked into the repo).
_OUT_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs" / "tutorial" / "_detector_scores.generated.md"
)


def _which_ddoc() -> str | None:
    return shutil.which("ddoc")


def _generate_pair(cli: str, modality: str, out: Path) -> tuple[Path, Path]:
    proc = subprocess.run(
        [cli, "examples", "generate", modality,
         "--out", str(out), "--scenario", "shifted"],
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ddoc examples generate {modality} failed: {proc.stderr[:200]}"
        )
    return out / "ref", out / "cur"


def _analyze_drift(
    cli: str, ref: Path, cur: Path, detector: str, timeout: int = 60,
) -> dict[str, Any] | None:
    proc = subprocess.run(
        [cli, "analyze", "drift",
         "--data-path-ref", str(ref), "--data-path-cur", str(cur),
         "--detector", detector, "--json", "--quiet"],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        return None
    # The CLI may emit warnings before the envelope; take the last
    # JSON object on stdout.
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def render_table(modality: str, scores: list[tuple[str, float | None]]) -> str:
    lines = [
        f"### `{modality}` modality",
        "",
        "| detector | overall_score (shifted) | notes |",
        "|---|---|---|",
    ]
    for det, score in scores:
        score_str = "—" if score is None else f"{score:.4f}"
        note = ""
        if score is None:
            note = "skipped (CLI returned no envelope)"
        lines.append(f"| `{det}` | {score_str} | {note} |")
    lines.append("")
    return "\n".join(lines)


def run(modalities: list[str]) -> str:
    """Produce the full Markdown body for the requested modalities."""
    cli = _which_ddoc()
    if cli is None:
        raise SystemExit(
            "ddoc CLI not on PATH. Activate the project venv first: "
            "`source .venv/bin/activate`."
        )

    sections: list[str] = []
    for modality in modalities:
        detectors = _DETECTOR_SETS.get(modality)
        if not detectors:
            sections.append(f"### `{modality}` modality\n\nNo detectors documented.\n")
            continue
        with tempfile.TemporaryDirectory(prefix=f"ddoc-cookbook-{modality}-") as tmp:
            try:
                ref, cur = _generate_pair(cli, modality, Path(tmp))
            except Exception as e:  # noqa: BLE001
                sections.append(
                    f"### `{modality}` modality\n\nGeneration failed: {e}\n"
                )
                continue
            scores: list[tuple[str, float | None]] = []
            for det in detectors:
                env = _analyze_drift(cli, ref, cur, det)
                score = env.get("overall_score") if env else None
                if isinstance(score, (int, float)):
                    scores.append((det, float(score)))
                else:
                    scores.append((det, None))
            sections.append(render_table(modality, scores))
    return "\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="render_detector_cookbook",
        description="Render detector × overall_score table for the cookbook.",
    )
    p.add_argument(
        "--modalities", nargs="+", default=["categorical"],
        choices=sorted(_DETECTOR_SETS.keys()),
        help="Modalities to score (default: categorical only; add 'image' "
              "for the full vision matrix — slow).",
    )
    p.add_argument(
        "--out", type=Path, default=_OUT_PATH,
        help=f"Output file (default: {_OUT_PATH}).",
    )
    p.add_argument(
        "--print-only", action="store_true",
        help="Print to stdout instead of writing the output file.",
    )
    ns = p.parse_args(argv if argv is not None else sys.argv[1:])

    body = run(ns.modalities)
    header = (
        "<!-- Auto-generated by scripts/render_detector_cookbook.py — "
        "do not edit by hand. -->\n"
        "<!-- Sourced from running `ddoc examples generate <modality> "
        "--scenario shifted` then `ddoc analyze drift --detector <name>`. -->\n"
        "\n"
        "## Detector × score on the canonical shifted demo\n\n"
    )
    final = header + body + "\n"
    if ns.print_only:
        sys.stdout.write(final)
    else:
        ns.out.parent.mkdir(parents=True, exist_ok=True)
        ns.out.write_text(final, encoding="utf-8")
        print(f"wrote {ns.out} ({len(final)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
