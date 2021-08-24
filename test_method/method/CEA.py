import collections
import json
import os
import re
from multiprocessing.pool import ThreadPool

import rdflib

from mantistable.process.data_preparation.normalization import transformer
from mantistable.process.utils import scores
from mantistable.process.utils.data_type import DataTypeEnum
from mantistable.process.utils.nlp.bag_of_words import get_name_from_entity
from test_method import sparql
from test_method.method.table import Table

data_dir = "./data"
#test
table_dir = "/home/andrea/mantistable-tool.py/mantistable/private/tables/Challenge/converted/"

with open("target_cea.json") as f:
    CEA_target = json.loads(f.read())

with open("target_cpa.json") as f:
    CPA_target = json.loads(f.read())


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

infotable = load_infotable("./infotable.json")

def get_necols_index(table_name):

    return [
        necol["index"]
        for necol in infotable[table_name]["ne_cols"]
    ]


def get_litcols_index(table_name):
    litcols = [
        litcol["index"]
        for litcol in infotable[table_name]["lit_cols"]
    ]

    litcols.extend(
        nocol["index"]
        for nocol in infotable[table_name]["no_ann_cols"]
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
            "numeric": rdflib.XSD.integer,
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
            "currency": rdflib.XSD.float,
            "iata": rdflib.XSD.string,
            "address": rdflib.XSD.string,
            "id": rdflib.XSD.string,
            "no_annotation": rdflib.XSD.string,
        }

        return map_datatype.get(max_datatype, rdflib.XSD.string)

    else:
        return rdflib.XSD.integer


def get_subject_col(table_name):
    infotable = load_infotable("./infotable.json")

    return infotable[table_name]["subject_col"]


def is_person(value):
    m = re.search(r"^([A-Z]\.\s*)+(\w+\'*)+", value, re.IGNORECASE)
    return bool(m)


# CEA -----------------------------------

cache = {}

def get_resource_graph(name):
    if name not in cache.keys():
        with open(f"./data/{name}.ttl") as f:
            content = f.read()

        g = rdflib.Graph()
        g.parse(data=content, format="ttl")
        cache[name] = g

    return cache[name]


def get_row_candidates(row, litcols, candidate_resources):
    row_candidates = []
    row_graph = rdflib.Graph()
    for cell_idx, cell in enumerate(row):
        nor_cell = transformer.transformer(cell)[0]

        if nor_cell in candidate_resources:
            g = get_resource_graph(nor_cell)
            row_graph += g

            row_candidates.append(list(set(g.subjects())))
        else:
            row_candidates.append(nor_cell)


    return row_candidates, row_graph


def get_matching_triples(row_candidates, row_graph, subjcol, necols, litcols, table_name):
    triples = {
        col: []
        for col in necols + litcols
    }
    for subject_candidate in row_candidates[subjcol]:
        for necol_idx in set(necols) - {subjcol}:
            for necol_candidate in row_candidates[necol_idx]:
                for s, p, o in row_graph.triples((subject_candidate, None, necol_candidate)):
                    triples[necol_idx].append((s, p, o))

        for litcol_idx in litcols:
            for s, p, o in row_graph.triples((subject_candidate, None, rdflib.Literal(row_candidates[litcol_idx], datatype=get_litcol_datatype(table_name, litcol_idx)))):
                triples[litcol_idx].append((s, p, o))

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
    print(row)
    row_candidates, row_graph = get_row_candidates(row, litcols, candidate_resources)
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

                    predicates[col_idx].append(triple[1])

    winning_predicates = {}
    for col_idx in predicates.keys():
        column_freq = dict(collections.Counter(predicates[col_idx]))

        if len(column_freq) > 0:
            winning_predicates[col_idx] = max(column_freq, key=lambda k: column_freq[k])

    return winning_predicates


def export_CEA(table_name, table_model, output_filename, mode="w"):
    with open(output_filename, mode) as f:
        for row_idx, row in enumerate(table_model):
            for col_idx in row.keys():
                if str(col_idx) in CEA_target[table_name]:
                    linked = str(row[col_idx])
                    if linked != "None":
                        f.write(f'"{table_name}", "{col_idx}", "{row_idx}", "{linked}"')
                        f.write("\n")


def export_CPA(table_name, predicates, subjcol, output_filename, mode="w"):
    with open(output_filename, mode) as f:
        for col_idx in predicates.keys():
            if col_idx in CPA_target[table_name]:
                predicate = predicates[col_idx]

                if "/" in predicate[28:]:
                    continue

                f.write(f'"{table_name}", "{subjcol}", "{col_idx}", "{predicate}"')
                f.write("\n")


def compute_table(filename):
    candidates = [item[0:-4] for item in filter(lambda item: item.endswith(".ttl"), os.listdir("./data"))]

    with open(os.path.join(table_dir, filename)) as raw:
        table = Table(filename[0:-5], json.loads(raw.read()))

    necols = get_necols_index(table.name)
    litcols = get_litcols_index(table.name)
    subj_col = get_subject_col(table.name)

    assert subj_col in necols

    table_model = []
    for row_idx in range(0, table.rows_count()):
        row = table.get_row(row_idx)
        winning = row_linking_phase1(row, subj_col, necols, litcols, candidates, table.name)
        table_model.append(winning)

    winning_predicates = predicate_phase2(table_model, subj_col)
    #print(winning_predicates)

    # CEA 2
    winning_table_model = []
    for row in table_model:
        winning_table_model.append({})
        for col_idx in row.keys():
            if col_idx in necols:
                winning_table_model[-1][col_idx] = None

                if col_idx == subj_col:
                    other_col_idx = (subj_col + 1) % len(row)
                    if len(row[other_col_idx]) > 0:
                        triple = row[other_col_idx][0]
                        sub = triple[0]
                        winning_table_model[-1][col_idx] = sub

                if col_idx in winning_predicates.keys():
                    for triple in row[col_idx]:
                        if triple[1] == winning_predicates[col_idx] and isinstance(triple[2], rdflib.URIRef):
                            winning_table_model[-1][col_idx] = triple[2]

    #print(winning_table_model)
    export_CEA(table.name, winning_table_model, f"CEA_Export_test.csv", "a")
    export_CPA(table.name, winning_predicates, subj_col, f"CPA_Export_test.csv", "a")

def compute_tables(data):
    list_filenames = data
    total = len(list_filenames)
    for idx, filename in enumerate(list_filenames):
        print(filename, idx + 1, total)
        compute_table(filename)

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def main():
    tables = list(filter(lambda item: item.endswith(".json"), os.listdir(table_dir)))
    # tables = ["v10_100.json"]
    # filename = "v10_1380.json"

    c = list(chunks(tables, int(len(tables) / 30)))

    #pool = ThreadPool(30)
    #pool.map(compute_tables, [(chunck, idx) for idx, chunck in enumerate(c)])


    # compute_tables(c[0])
    # compute_tables(c[1])
    compute_tables(tables)


if __name__ == '__main__':
    main()
