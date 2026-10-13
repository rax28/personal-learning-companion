def detect_gap(concept_state): return concept_state.get('mastery',0)<0.55 or concept_state.get('confidence',0)<0.4
