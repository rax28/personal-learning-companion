def missing_prerequisites(concept,graph,knowledge): return [p for p in graph.prerequisites_of(concept) if knowledge.get(p,{}).get('mastery',0)<0.55]
