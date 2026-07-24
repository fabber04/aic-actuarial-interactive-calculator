#!/usr/bin/env python3
"""Assemble dist/AIC_v1.0_Submission/ from markdown/SVG sources (no PDF typesetting)."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist" / "AIC_v1.0_Submission"


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    mapping = [
        (ROOT / "docs/submission/HOW_TO_READ_THIS_SUBMISSION.md", DIST / "00_How_to_Read_This_Submission.md"),
        (ROOT / "docs/submission/Executive_Summary.md", DIST / "01_Executive_Summary.md"),
        (ROOT / "docs/research/paper.md", DIST / "02_Paper.md"),
        (ROOT / "docs/research/figures/export/fig01_architecture.svg", DIST / "03_Architecture_Diagram.svg"),
        (ROOT / "docs/research/ctflex_prototype_vs_aic_benchmark.md", DIST / "04_Benchmark_Report.md"),
        (ROOT / "docs/submission/Validation_Report.md", DIST / "05_Validation_Report.md"),
        (ROOT / "docs/submission/User_Guide.md", DIST / "06_User_Guide.md"),
        (ROOT / "docs/ROADMAP.md", DIST / "07_Roadmap.md"),
        (ROOT / "docs/submission/PACKAGE.md", DIST / "PACKAGE.md"),
        (ROOT / "docs/submission/RELEASE_RC1.md", DIST / "RELEASE_RC1.md"),
        (ROOT / "CHANGELOG.md", DIST / "CHANGELOG.md"),
        (ROOT / "docs/EVOLUTION.md", DIST / "EVOLUTION.md"),
        (ROOT / "docs/governance", DIST / "Governance"),
        (ROOT / "docs/submission/API_Documentation.md", DIST / "API_Documentation" / "API_Documentation.md"),
        (ROOT / "docs/research/figures/export", DIST / "Figures"),
    ]
    missing = []
    for src, dest in mapping:
        if not src.exists():
            missing.append(str(src))
            continue
        _copy(src, dest)

    readme = DIST / "README.md"
    readme.write_text(
        "# AIC v1.0 Submission Package (assembled sources)\n\n"
        "Start with `00_How_to_Read_This_Submission.md`.\n\n"
        "Markdown/SVG copies are assembled for review. Convert key documents to PDF "
        "before final judge delivery (see `PACKAGE.md`).\n\n"
        "Add `LICENSE` and `Source_Code.zip` before shipping the final archive.\n",
        encoding="utf-8",
    )

    # Lightweight source snapshot (library + docs + tests + entrypoints)
    src_zip = DIST / "Source_Code.zip"
    include_roots = ["aic", "tests", "docs", "scripts"]
    include_files = [
        "README.md",
        "CHANGELOG.md",
        "requirements.txt",
        "engine_model.py",
        "fremtpl_glm.py",
        "ct_flex_api.py",
    ]
    skip_parts = {".venv", "__pycache__", ".git", "node_modules", "dist", "archive", "Datasets"}

    with zipfile.ZipFile(src_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in include_files:
            path = ROOT / name
            if path.is_file():
                zf.write(path, arcname=name)
        for folder in include_roots:
            base = ROOT / folder
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if not path.is_file():
                    continue
                if any(part in skip_parts for part in path.parts):
                    continue
                if path.suffix in {".pyc", ".pyo"}:
                    continue
                zf.write(path, arcname=str(path.relative_to(ROOT)).replace("\\", "/"))

    print(f"Assembled {DIST}")
    if missing:
        print("Missing sources:")
        for m in missing:
            print(f"  - {m}")
        return 1
    print(f"Source snapshot: {src_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
