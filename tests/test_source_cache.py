from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai-backend"))
from app.source_cache import CompressedSourceCache


def test_compressed_source_cache_round_trip_and_retrieval(tmp_path: Path):
    cache = CompressedSourceCache(str(tmp_path / "cache.json"))
    text = "SOURCE_TEST_V8\nMy favorite compression experiment is called BLUE-PENGUIN-4821.\nIt uses arithmetic coding."
    meta = cache.put(text, "manual://source-test")
    assert meta["source_id"]
    assert meta["compressed_bytes"] > 0
    assert cache.get(meta["source_id"]) == text
    hits = cache.search(meta["source_id"], "What is my compression experiment called?")
    assert hits
    assert "BLUE-PENGUIN-4821" in hits[0]["text"]
