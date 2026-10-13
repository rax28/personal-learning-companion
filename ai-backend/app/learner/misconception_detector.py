def detect_misconception(evidence): return evidence.get('signal')=='misconception' and evidence.get('confidence',0)>=0.65
