import json

import networkx as nx

from mantistable.process.utils.assets.assets import Assets

CC = json.loads(Assets().get_asset("CC.json"))
cc_list = json.loads(Assets().get_asset("CCKeys.json"))
ontology_graph = json.loads(Assets().get_asset("OntologyGraph.json"))


def create_graph():
    node_list = set()
    edge_list = []

    for key in ontology_graph.keys():
        sons = ontology_graph[key]

        for s in sons:
            edge_list.append((key, s))

        node_list.add(key)
        node_list.union(set(sons))

    ont_G = nx.Graph()
    ont_G.add_nodes_from(node_list)
    ont_G.add_edges_from(edge_list)

    return ont_G


def get_branches(winning_concepts_freq, ont_G):
    paths = []

    winning_concepts = winning_concepts_freq.keys()
    node_father = winning_concepts
    winning_concepts = list(filter(lambda concept: concept not in cc_list, winning_concepts))
    node_father = list(set(node_father) - set(winning_concepts))

    if len(winning_concepts) == 0:
        for node in node_father:
            paths.append([node])

    # 1
    sources = []
    for wc in winning_concepts:
        source = None
        for cc_key in CC.keys():
            if wc in CC[cc_key]:
                source = cc_key
                sources.append(source)
                break

        assert (source is not None)

        try:
            path = nx.shortest_path(ont_G, source, wc)
            paths.append(path)
        except nx.NetworkXNoPath:
            pass

    # 2: Group by cc
    cc_branches = {}
    for path in paths:
        source = path[0]
        if source in cc_branches.keys():
            cc_branches[source].append(path[1:])
        else:
            cc_branches[source] = [path[1:]]

    # 3: ArgMax
    cc_freq = {}
    for cc_key in cc_branches.keys():
        concepts = set([cc_key] + [item for sublist in cc_branches[cc_key] for item in sublist])
        cc_freq[cc_key] = sum([winning_concepts_freq.get(cname, 1) for cname in concepts])

    max_freq = max(cc_freq.values())
    max_source = [source for source in cc_freq.keys() if cc_freq[source] == max_freq][0]

    # 4: return winning paths
    return [
        tuple([max_source] + subpath)
        for subpath in cc_branches[max_source]
    ]


def get_annotation(concepts, ont_G):
    assert (len(concepts) > 0)

    branches = get_branches(concepts, ont_G)
    #max_len_branch = max([len(branch) for branch in branches])
    #max_branch = [branch for branch in branches if len(branch) == max_len_branch][0]
    """ branches = [ 
        tuple([
            concept 
            for concept in branch 
            if concept != "Thing" and concept != "Agent"
        ])
        for branch in branches
    ]
    freq_branches = {} """
    
    """ for branch in branches:
        if len(branch) == 1:
            freq_branches[branch] = concepts.get(branch[0], 1)
        else:
            freq_branches[branch] = concepts.get(branch[0], 1) + concepts.get(branch[-1], 1) """
    
    freq_branches = {
        branch: sum([concepts.get(cname, 1) for cname in branch])
        for branch in branches
    }
    #freq = concepts.get(max_branch[max_len_branch-1], 1) - 1
    """ for branch in freq_branches:
        len_branch = len(branch)
        iteration = max_len_branch - len_branch
        for i in range (0, iteration):
            freq_branches[branch] += freq """ 

    #print("FREQ BRANCHES", freq_branches)
    max_freq = max(freq_branches.values())
    max_branches = [branch for branch in freq_branches.keys() if freq_branches[branch] == max_freq]
    return {
        concept: concepts.get(concept, 1)
        for concept in max_branches[0]
        if concept != "Agent" and concept != "Thing"
    }



