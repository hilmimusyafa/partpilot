import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PUBLIC = (
    "backend/db/001_schema.sql", "backend/db/009_bearing_lookup.sql",
    "backend/db/seed/009_bearing_mvp_synth.sql",
    "backend/docs/db/bearing-mvp.md", "backend/README.md",
)

def test_M01_bundle_and_original_hashes():
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    for path, digest in manifest["original_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
    for path in PUBLIC:
        assert (ROOT / path).is_file(), "missing candidate: " + path
    for name in ("001_schema.sql", "009_bearing_lookup.sql"):
        assert (ROOT / "backend/db" / name).read_bytes() == (ROOT / "db" / name).read_bytes()

def test_M02_public_safety():
    # Finite configured marker scan; not a claim about authorship.
    markers = re.compile(r"(?i)claude|chatgpt|openai|hermes|anthropic|ai-generated|jarvis|daedalus|oracle|forge|prism|sentinel|muse|bastion|relay|vector|nova|steward|scribe|merlin|warden|/srv/|/home/|/Users/|[A-Z]:\\|postgres(?:ql)?://[^\s]+:[^\s]+@|BEGIN [A-Z ]*PRIVATE KEY|(?:password|api_key|secret)\s*[:=]\s*['\"][^'\"]+['\"]")
    for path in PUBLIC:
        text = (ROOT / path).read_text()
        assert not markers.search(text), "configured public marker: " + path
    seed = (ROOT / PUBLIC[2]).read_text().lower()
    assert not re.search(r"\b(?:copy|pg_read_file|dblink)\b", seed)

def test_M03_portable_documented_order():
    # Two coherent entry points: repo root and backend root. Explicit portable
    # commands required so paths/order can be mechanically checked.
    for doc, prefix, cwd in (("backend/docs/db/bearing-mvp.md", "backend/", ROOT),
                             ("backend/README.md", "", ROOT / "backend")):
        text = (ROOT / doc).read_text()
        expected = [prefix + p for p in ("db/001_schema.sql", "db/009_bearing_lookup.sql", "db/seed/009_bearing_mvp_synth.sql")]
        paths = re.findall(r"psql[^\n]*?\s-f\s+['\"]?([^\s'\";`]+)", text)
        assert paths == expected, (doc, paths, expected)
        assert all((cwd / p).is_file() for p in paths)
