from knowledge.ingestion.pipeline import chunk_text
from knowledge.compression.codec import compress_lossless, decompress_lossless
from knowledge.source_knowledge.graph import SourceKnowledgeGraph

def test_source_chunking_and_lossless_codec():
    text = "A" * 100 + "\n\n" + "B" * 100
    chunks = chunk_text("nptel-1", text, max_chars=120)
    assert chunks and chunks[0].source_id == "nptel-1"
    payload = text.encode()
    assert decompress_lossless(compress_lossless(payload)) == payload

def test_source_graph_is_separate_from_learner_mastery():
    graph = SourceKnowledgeGraph()
    graph.add("two-pointers", "Two Pointers", "nptel-1")
    graph.add("palindrome", "Palindrome", "nptel-1", "two-pointers")
    assert graph.nodes["two-pointers"].children == ["palindrome"]
