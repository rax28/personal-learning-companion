PREREQS={'backpropagation':['chain rule','derivative','functions'],'chain rule':['derivative','functions'],'recursion':['functions'],'binary search':['search space reduction','ordered data'],'two pointers':['ordered data']}
class RootGapDetector:
    def find(self,model,goal,evidence):
        c=evidence['concept']
        if any(m['status']=='open' and m['concept']==c for m in model.misconceptions): return c
        if c=='two pointers': return c
        for p in PREREQS.get(c,[]):
            if model.knowledge.get(p,{}).get('mastery',0)<0.55:return p
        return c
