def update_confidence(current, evidence_count):
    return max(0,min(1,current + min(0.1,0.02*evidence_count)))
