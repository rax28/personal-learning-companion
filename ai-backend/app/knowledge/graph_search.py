def traverse(root, graph):
    seen=set(); stack=[root]
    while stack:
        c=stack.pop()
        if c in seen: continue
        seen.add(c); stack.extend(graph.prerequisites_of(c))
    return seen
