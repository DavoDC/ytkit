"""
Clean already-downloaded .vtt transcript files into plain deduplicated .txt.
Reuses ytkit's clean_vtt() so there's one canonical implementation.

Usage:
  python scripts/clean_transcripts.py <path/to/dir-or-files.vtt> [...]
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from ytkit import clean_vtt  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean_transcripts.py <dir-or-.vtt-files...>")
        sys.exit(1)

    targets = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            targets.extend(sorted(p.glob("*.vtt")))
        else:
            targets.append(p)

    # Prefer non "-orig" variant when both exist for the same video id.
    preferred = [t for t in targets if "-orig" not in t.name]
    seen_stems = {t.name.split("].")[0] for t in preferred}
    final = preferred + [t for t in targets if "-orig" in t.name and t.name.split("].")[0] not in seen_stems]

    for vtt_path in final:
        cleaned = clean_vtt(vtt_path)
        txt_path = vtt_path.with_suffix("").with_suffix(".txt")
        txt_path.write_text(cleaned, encoding="utf-8")
        print(f"{vtt_path.name} -> {txt_path.name} ({len(cleaned)} chars)")


if __name__ == "__main__":
    main()
