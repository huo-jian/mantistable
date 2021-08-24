import json
import os
import re
import csv

import rdflib

from mantistable.process.data_preparation.normalization import transformer
from test_method.sparql import DbpediaSparqlRepository

table_dir = "/home/andrea/mantistable-tool.py/mantistable/private/tables/Challenge/converted/"

with open("./targets.json") as f:
    targets = json.loads(f.read())


def load_table(table_name):
    with open(os.path.join(table_dir, table_name) + ".json") as raw:
        table = json.loads(raw.read())

    return table


def process_table(table, subject_col, ne_cols, lit_cols):
    rows = [
        tuple(row.values())
        for row in table
    ]

    nrows = [
        normalize_row(row)
        for row in rows
    ]

    table_results = []
    for row_idx in range(0, len(rows)):
        raw_row = rows[row_idx]
        nor_row = nrows[row_idx]
        result_triples = process_row(raw_row, nor_row, subject_col, ne_cols, lit_cols)
        table_results.append(result_triples)

    print(table_results)


def get_cell_candidates(raw_cell, nor_cell_data):
    def is_person(value):
        m = re.search(r"^([A-Z]\.\s*)+(\w+\'*)+", value, re.IGNORECASE)
        return bool(m)

    nor_cell, value_for_query = nor_cell_data

    if is_person(raw_cell):
        # eg. G. V. Grant -> g v grant
        tokens = nor_cell.split(" ")
        assert len(tokens) >= 2

        person_prefix = tokens[0]
        person_surname = tokens[-1]

        entities = DbpediaSparqlRepository(1).get_person_entities(person_prefix, person_surname)
    else:
        entities = DbpediaSparqlRepository(1).get_entities(value_for_query, False)
        if len(entities) == 0 and len(nor_cell.split(' ')) > 1:
            entities = DbpediaSparqlRepository(1).get_entities(nor_cell, True)

    return entities


def process_row(raw_row, nor_row, subject_col, ne_cols, lit_cols):
    # >>>>> CEA
    data_uris = set()
    ne_cols_uris = {}
    for col_idx in ne_cols:
        raw_cell = raw_row[col_idx]
        nor_cell_data = nor_row[col_idx]

        print(raw_cell, nor_cell_data)
        candidates = get_cell_candidates(raw_cell, nor_cell_data)

        candidates_uris = set()
        for candidate in candidates:
            if candidate["alias"]["value"] == "None":
                candidates_uris.add(candidate["s"]["value"])
            else:
                candidates_uris.add(candidate["alias"]["value"])

        data_uris.update(candidates_uris)
        if col_idx not in ne_cols_uris:
            ne_cols_uris[col_idx] = set()

        ne_cols_uris[col_idx].update(candidates_uris)

    print(data_uris)
    graph = get_data_graph(data_uris)

    # >>>>> CPA
    candidates_triples = []
    for subject_candidate in ne_cols_uris[subject_col]:
        for not_subject_col in set(ne_cols) - {subject_col}:
            for ne_col_candidate in ne_cols_uris[not_subject_col]:
                print(subject_candidate, ne_col_candidate)
                for s, p, o in graph.triples((rdflib.URIRef(subject_candidate), None, rdflib.URIRef(ne_col_candidate))):
                    candidates_triples.append((s, p, o))

    return candidates_triples


def get_data_graph(data_uris):
    global_graph = rdflib.Graph()
    for uri in data_uris:

        print("Downloading", uri)
        raw_turtle = DbpediaSparqlRepository(1).get_resource_rdf(uri).decode("utf-8")

        g = rdflib.Graph()
        # g.parse(f"http://dbpedia.org/data/{resource}.n3")
        g.parse(data=raw_turtle, format="ttl")
        if len(g) == 0:
            print("\tno data")
        global_graph += g

    return global_graph


def normalize_row(row):
    nrow = []
    for cell in row:
        nrow.append(transformer.transformer(cell))

    return tuple(nrow)


def main():
    # Load table
    table_name = "v14_295"
    table = load_table(table_name)

    subject_col = 0
    ne_cols = [0, 1, 2]
    lit_cols = [3]

    assert subject_col in ne_cols

    process_table(table, subject_col, ne_cols, lit_cols)


"""
def main():
    filepaths = list(filter(lambda filename: filename.endswith(".json"), os.listdir(table_dir)))

    resources = set()
    total_cell_count = 0
    for idx, filename in enumerate(filepaths):
        print(filename, idx + 1)
        table = load_table(filename[0:-5])

        table_resources, cell_count = get_candidables(table, filename[0:-5])
        resources.update(table_resources)
        total_cell_count += cell_count


    
    #print(resources)
    #print(len(resources), total_cell_count)
    
    output = sorted(list(resources), key=lambda item: item[1])
    with open('./cells.data', 'w') as f_out:
        writer = csv.writer(f_out, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_ALL)
        for row in output:
            writer.writerow(list(row))


def get_candidables(table, table_name):
    rows = [
        tuple(row.values())
        for row in table
    ]

    nrows = [
        normalize_row(row)
        for row in rows
    ]

    ne_cols = targets[table_name]

    resources = set()
    total_cell_count = 0
    for row_idx in range(0, len(rows)):
        raw_row = rows[row_idx]
        nor_row = nrows[row_idx]

        for col_idx in ne_cols:
            nor_cell, nor_cell_query = nor_row[col_idx]
            raw_cell = raw_row[col_idx]

            resources.add((raw_cell, nor_cell, nor_cell_query))
            total_cell_count += 1

    return resources, total_cell_count
"""

if __name__ == '__main__':
    main()
