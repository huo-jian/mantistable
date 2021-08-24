import collections
import csv
import json
import os
import re
from multiprocessing.pool import ThreadPool
import multiprocessing

import rdflib

import transformer
import scores
from bag_of_words import get_name_from_entity
import sparql
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from table import Table

import networkx as nx

data_dir = "./data"
chall_dir = "/home/andrea/mantistable-tool.py/mantistable/private/tables/Challenge/"
table_dir = os.path.join(chall_dir, "converted")
targets_dir = chall_dir
infotable_dir = "./"
export_dir = "./"
last_export_cea = "./CEA_Export_last.csv"


def read_export_cea(filename):
    if os.path.exists(filename):
        lines = open(filename).read().strip().split("\n")
        data = {}
        for line in lines:
            tmp = line[1:len(line) - 1]
            tmp = tmp.split('", "')
            table_name = tmp[0]
            col = int(tmp[1])
            row = int(tmp[2])
            ann = tmp[3]

            data[(table_name, col, row)] = ann
        return data

    return {}

CEA_last = read_export_cea(last_export_cea)

with open(os.path.join(targets_dir, "target_cea.json")) as f:
    CEA_target = json.loads(f.read())

with open(os.path.join(targets_dir, "target_cpa.json")) as f:
    CPA_target = json.loads(f.read())

with open(os.path.join(targets_dir, "target_cta.json")) as f:
    targets = json.loads(f.read())


cache = {}


def cache_resource_graph(name):
    if name not in cache.keys():
        filepath = os.path.join(data_dir, f"{name}.ttl")
        if not os.path.exists(filepath):
            return None

        with open(filepath) as f:
            content = f.read()

        g = rdflib.Graph()
        g.parse(data=content, format="ttl")
        cache[name] = g

    return cache[name]


def get_resource_graph(name):
    if name not in cache.keys():
        filepath = os.path.join(data_dir, f"{name}.ttl")
        if not os.path.exists(filepath):
            return None

        with open(filepath) as f:
            content = f.read()

        g = rdflib.Graph()
        g.parse(data=content, format="ttl")

        return g

    return cache[name]


def load_initial_graph_cache():
    table_filenames = list(filter(lambda item: item.endswith(".json"), os.listdir(table_dir)))

    cells_raw = []
    for filename in table_filenames:
        print(filename)

        with open(os.path.join(table_dir, filename)) as raw:
            table = Table(filename[0:-5], json.loads(raw.read()))

        assert table.name in targets.keys()

        for ne_col_idx in targets[table.name]:
            original = set(table.get_col(ne_col_idx))
            normalized = [
                (transformer.transformer(item)[0], transformer.transformer(item)[1], is_person(item))
                for item in original
            ]
            cells_raw.extend([item[0] for item in normalized])

    print("Loading cache")
    freq_table = collections.Counter(cells_raw)
    most_freq_cells = list(dict(filter(lambda item: item[1] > 1, dict(freq_table).items())).keys())
    total_cells = len(most_freq_cells)
    for idx, freq_resource_name in enumerate(most_freq_cells):
        print(f"{idx + 1}/{total_cells}")
        cache_resource_graph(freq_resource_name)


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def isinteger(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def load_infotable(filename):
    with open(filename) as f:
        contents = f.read()

    lines = contents.split('\n')
    lines.pop()

    infotable_raw = [json.loads(line) for line in lines]

    infotable = {}
    for table in infotable_raw:
        infotable[table["table_name"]] = table

    return infotable


infotable = load_infotable(os.path.join(infotable_dir, "infotable_round4.json"))


def get_necols_index(table_name):

    necols = [
        necol["index"]
        for necol in infotable[table_name]["ne_cols"]
    ]

    necols.extend(
        nocol["index"]
        for nocol in infotable[table_name]["no_ann_cols"]
        if nocol["index"] in targets[table_name]
    )

    return necols


def get_litcols_index(table_name):
    necols = get_necols_index(table_name)
    litcols = [
        litcol["index"]
        for litcol in infotable[table_name]["lit_cols"]
    ]

    litcols.extend(
        nocol["index"]
        for nocol in infotable[table_name]["no_ann_cols"]
        if nocol["index"] not in necols
    )

    return litcols


def get_litcol_datatype(table_name, litcol_idx):
    lits = list(filter(lambda item: item["index"] == litcol_idx, infotable[table_name]["lit_cols"]))

    if len(lits) == 0:
        return rdflib.XSD.string

    lit = lits[0]

    if len(lit["type_freq_table"]) > 0:
        types = {
            t["name"]: t["rate"]
            for t in lit["type_freq_table"]
        }

        max_datatype = max(list(types.keys()), key=lambda k: types[k])

        map_datatype = {
            "": rdflib.XSD.string,
            "empty": rdflib.XSD.string,
            "geo_coordinates": rdflib.XSD.string,
            "hex_color": rdflib.XSD.string,
            "numeric": (rdflib.XSD.decimal, rdflib.XSD.integer, rdflib.XSD.float, rdflib.XSD.double),
            "ip": rdflib.XSD.string,
            "credit_card": rdflib.XSD.string,
            "image": rdflib.XSD.string,
            "url": rdflib.XSD.anyURI,
            "email": rdflib.XSD.string,
            "isbn": rdflib.XSD.integer,
            "iso8601": rdflib.XSD.integer,
            "boolean": rdflib.XSD.boolean,
            "date": rdflib.XSD.date,
            "description": rdflib.XSD.string,
            "currency": (rdflib.XSD.float, rdflib.XSD.double),
            "iata": rdflib.XSD.string,
            "address": rdflib.XSD.string,
            "id": rdflib.XSD.string,
            "no_annotation": rdflib.XSD.string,
        }

        return map_datatype.get(max_datatype, rdflib.XSD.string)

    else:
        return rdflib.XSD.integer


def get_subject_col(table_name):
    return infotable[table_name]["subject_col"]


def is_person(value):
    m = re.search(r"^([A-Z]\.\s*)+(\w+\'*)+", value, re.IGNORECASE)
    return bool(m)


# CEA -----------------------------------


def get_row_candidates(row, necols, candidate_resources):
    row_candidates = []
    row_graph = rdflib.Graph()
    for cell_idx, cell in enumerate(row):
        nor_cell = transformer.transformer(cell)[0]

        if nor_cell in candidate_resources and cell_idx in necols:
            g = get_resource_graph(nor_cell)
            if g is None:
                continue

            row_graph += g
            row_candidates.append(list(set(g.subjects())))
        else:
            row_candidates.append(nor_cell)

    return row_candidates, row_graph


def get_matching_triples(row_candidates, row_graph, subjcol, necols, litcols, table_name):
    def fuzzy_match_literal(literal, cell, xsd_datatype):
        if isinstance(xsd_datatype, tuple):
            for datatype in xsd_datatype:
                if (datatype == rdflib.XSD.decimal and cell.isdecimal() and str(literal).isdecimal()) or\
                   (datatype == rdflib.XSD.float and isfloat(cell) and isfloat(str(literal))):
                    ccell = float(cell)
                    cliteral = float(literal)
                elif datatype == rdflib.XSD.integer and isfloat(cell) and isfloat(str(literal)):
                    ccell = int(cell)
                    cliteral = int(cell)
                else:
                    return False

                if abs(cliteral - ccell) < 0.2:
                    return True
        else:
            #return str(literal).lower() == cell.lower()
            return transformer.transformer(literal)[0] == cell

    triples = {
        col: []
        for col in necols + litcols
    }

    nx_graph = rdflib_to_networkx_multidigraph(row_graph)
    nx_graph.remove_nodes_from([
        node
        for node, degree in dict(nx_graph.out_degree()).items()
        if degree == 0
    ])
    """ NOTE: For some tables this is too much filtering :(
    nx_graph.remove_nodes_from([
        node
        for node, degree in dict(nx_graph.in_degree()).items()
        if degree == 0
    ])
    nx_graph.remove_nodes_from([
        node
        for node, degree in dict(nx_graph.out_degree()).items()
        if degree == 0
    ])
    """

    nx_graph = nx.to_undirected(nx_graph)

    candidates = []
    for col in row_candidates:
        candidates.append([
            cand
            for cand in col
            if cand in nx_graph.nodes()
        ])
        
    for subject_candidate in set(candidates[subjcol]):
        for necol_idx in set(necols) - {subjcol}:
            for necol_candidate in set(candidates[necol_idx]):
                # IF there are incomplete linking due to bad data, I could match the most similar missing entity from other ne_cols
                for s, p, o in row_graph.triples((subject_candidate, None, necol_candidate)):
                    if p.startswith("http://dbpedia.org/ontology/"):
                        triples[necol_idx].append((s, p, o))

        for litcol_idx in litcols:
            cell = row_candidates[litcol_idx]
            xsd_datatype = get_litcol_datatype(table_name, litcol_idx)

            found_exact = False
            if isinstance(xsd_datatype, tuple):
                found_xsd = False
                for datatype in xsd_datatype:
                    if (datatype == rdflib.XSD.decimal and cell.isdecimal()) or (datatype == rdflib.XSD.float and isfloat(cell)):
                        ccell = float(cell)
                    elif datatype == rdflib.XSD.integer and isfloat(cell):
                        ccell = int(cell)
                    else:
                        ccell = cell
                        datatype = rdflib.XSD.string

                    for s, p, o in row_graph.triples((subject_candidate, None, rdflib.Literal(ccell, datatype=datatype))):
                        triples[litcol_idx].append((s, p, o))
                        found_xsd = True
                        found_exact = True

                    if found_xsd:
                        break
            else:
                for s, p, o in row_graph.triples((subject_candidate, None, rdflib.Literal(row_candidates[litcol_idx], datatype=xsd_datatype))):
                    found_exact = True
                    triples[litcol_idx].append((s, p, o))

            if not found_exact:
                for s, p, o in row_graph.triples((subject_candidate, None, None)):
                    if isinstance(o, rdflib.Literal):
                        if fuzzy_match_literal(o, cell, xsd_datatype):
                            triples[litcol_idx].append((s, p, o))

    #print(triples)
    return triples


def get_winning_linked_entities(triples, nor_row, subjcol):
    necol_subjects = {}
    for necol_idx in triples.keys():
        necol_subjects[necol_idx] = {triple[0] for triple in triples[necol_idx]}

    subjects = []
    for necol_val in necol_subjects.values():
        for val in necol_val:
            subjects.append(val)
    subjects = list(subjects)
    subject_score = collections.Counter(subjects)

    for subject in subject_score:
        nor_cell = nor_row[subjcol]
        label = get_name_from_entity(str(subject))
        ed = 1.0 - scores.get_edit_distance_score(nor_cell, label)
        subject_score[subject] += ed

    winning_triples = {
        necol_idx: []
        for necol_idx in triples
    }
    if len(subject_score.keys()) > 0:
        winning_subject = max(subject_score.keys(), key=lambda subj: subject_score[subj])
        for necol_idx in triples.keys():
            for necol_triples in triples[necol_idx]:
                if necol_triples[0] == winning_subject:
                    winning_triples[necol_idx].append(necol_triples)

    return winning_triples


def row_linking_phase1(row, subjcol, necols, litcols, candidate_resources, table_name):
    #print(row, "w macgregor" in candidate_resources)
    row_candidates, row_graph = get_row_candidates(row, necols, candidate_resources)
    triples = get_matching_triples(row_candidates, row_graph, subjcol, necols, litcols, table_name)

    nor_row = [
        transformer.transformer(cell)[0]
        for cell in row
    ]
    return get_winning_linked_entities(triples, nor_row, subjcol)


def predicate_phase2(table_model, subjcol):
    predicates = {}
    for row in table_model:
        for col_idx in row.keys():
            if subjcol == col_idx:
                continue
            else:
                triples = row[col_idx]
                for triple in triples:
                    if col_idx not in predicates.keys():
                        predicates[col_idx] = []

                    if triple[1].startswith("http://dbpedia.org/ontology/"):
                        predicates[col_idx].append(triple[1])

    winning_predicates = {}
    for col_idx in predicates.keys():
        column_freq = dict(collections.Counter(predicates[col_idx]))

        if len(column_freq) > 0:
            winning_predicates[col_idx] = max(column_freq, key=lambda k: column_freq[k])

    return winning_predicates


def export_CEA(table_name, table_model, output_filename, mode="w"):
    l = multiprocessing.Lock()
    with open(output_filename, mode) as f:
        with l:
            for row_idx, row in enumerate(table_model):
                for col_idx in row.keys():
                    if str(col_idx) in CEA_target[table_name]:
                        linked = str(row[col_idx])
                        if linked != "None":
                            f.write(f'"{table_name}", "{col_idx}", "{row_idx}", "{linked}"')
                            f.write("\n")


def export_CPA(table_name, predicates, subjcol, output_filename, mode="w"):
    l = multiprocessing.Lock()
    with open(output_filename, mode) as f:
        with l:
            for col_idx in predicates.keys():
                if col_idx in CPA_target[table_name]:
                    predicate = predicates[col_idx]

                    if "/" in predicate[28:]:
                        continue

                    f.write(f'"{table_name}", "{subjcol}", "{col_idx}", "{predicate}"')
                    f.write("\n")


def compute_table(filename):
    candidates = [item[0:-4] for item in filter(lambda item: item.endswith(".ttl"), os.listdir(data_dir))]

    with open(os.path.join(table_dir, filename)) as raw:
        table = Table(filename[0:-5], json.loads(raw.read()))

    necols = get_necols_index(table.name)
    litcols = get_litcols_index(table.name)
    subj_col = get_subject_col(table.name)

    # assert subj_col in necols
    if subj_col not in necols:
        return

    table_model = []
    for row_idx in range(0, table.rows_count()):
        row = table.get_row(row_idx)

        #print([(table.name, nec, row_idx) in CEA_last for nec in necols])
        if not all([(table.name, nec, row_idx) in CEA_last for nec in necols]):
            winning = row_linking_phase1(row, subj_col, necols, litcols, candidates, table.name)
            table_model.append(winning)
        else:
            print("JUMP")

    winning_predicates = predicate_phase2(table_model, subj_col)
    #print(winning_predicates)
    #print("=========================================")

    # CEA 2
    winning_table_model = []
    for row in table_model:
        winning_table_model.append({})
        for col_idx in row.keys():
            if col_idx in necols:
                winning_table_model[-1][col_idx] = None

                if col_idx == subj_col:
                    other_col_idx = (subj_col + 1) % len(row)

                    while other_col_idx in row and len(row[other_col_idx]) == 0:
                        other_col_idx = (other_col_idx + 1) % len(row)
                        if other_col_idx == subj_col:
                            break

                    if other_col_idx in row and len(row[other_col_idx]) > 0:
                        triple = row[other_col_idx][0]
                        sub = triple[0]
                        winning_table_model[-1][col_idx] = sub

                if col_idx in winning_predicates.keys():
                    for triple in row[col_idx]:
                        if triple[1] == winning_predicates[col_idx] and isinstance(triple[2], rdflib.URIRef):
                            winning_table_model[-1][col_idx] = triple[2]

    # print(winning_table_model)
    export_CEA(table.name, winning_table_model, os.path.join(export_dir, "CEA_Export_test.csv"), "a")
    export_CPA(table.name, winning_predicates, subj_col, os.path.join(export_dir, "CPA_Export_test.csv"), "a")

def compute_tables(data):
    
    list_filenames, index_p = data
    total = len(list_filenames)
    for idx, filename in enumerate(list_filenames):
        print(filename, index_p)#idx + 1, total)
        compute_table(filename)

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def main():
    # load_initial_graph_cache()        # TODO <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    tables = list(filter(lambda item: item.endswith(".json"), os.listdir(table_dir)))
    #tables = ["v16_110.json"]
    # filename = "v10_1380.json"

    c = list(chunks(tables, int(len(tables) / 4)))
    print(c)
    
    processes = [multiprocessing.Process(target=compute_tables, args=(tuple([chunck, idx]),)) for idx, chunck in enumerate(c)]

    # Run processes
    for p in processes:
        p.start()

    # Exit the completed processes
    for p in processes:
        p.join()
    
    """
    pool = ThreadPool(30)
    pool.map(compute_tables, [(chunck, idx) for idx, chunck in enumerate(c)])
    """

    #compute_tables(tables)


if __name__ == '__main__':
    main()
