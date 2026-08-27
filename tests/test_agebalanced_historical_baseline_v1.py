import hashlib
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_frozen_baseline_config_hash_matches_declared_value():
    path = REPOSITORY_ROOT / "configs" / "mmwave_reanalysis_v2" / "agebalanced_historical_baseline_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    declared_hash = payload.pop("config_hash_sha256")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    actual_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert actual_hash == declared_hash
