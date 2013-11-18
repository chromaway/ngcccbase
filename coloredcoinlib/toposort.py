
def toposorted(graph, parents):
    """
    Returns vertices of a directed acyclic graph in topological order.

    Arguments:
    graph -- vetices of a graph to be toposorted
    parents -- function (vertex) -> vertices to preceed
               given vertex in output
    """
    result = []
    used = set()

    def use(v, top):
        if id(v) in used:
            return
        for parent in parents(v):
            if parent is top:
                raise ValueError('graph is cyclical', graph)
            use(parent, v)
        used.add(id(v))
        result.append(v)
    for v in graph:
        use(v, v)
    return result
