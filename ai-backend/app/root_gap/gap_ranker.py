def rank(candidates): return sorted(candidates,key=lambda x:x.get('score',0),reverse=True)
