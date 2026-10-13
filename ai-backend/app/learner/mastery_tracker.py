def update_mastery(current, signal, strength):
    delta={'understands':0.12,'successful_application':0.18,'partially_understands':0.03,'uncertainty':-0.02,'repeated_error':-0.06,'misconception':-0.08}.get(signal,0)
    return max(0,min(1,current+delta*strength))
