import json
import os
import re

from SPARQLWrapper.SPARQLExceptions import QueryBadFormed

import transformer
from table import Table
import sparql
from multiprocessing.dummy import Pool as ThreadPool
import multiprocessing
import collections


def get_normalized_cell_data(table_dir):
    table_filenames = list(filter(lambda item: item.endswith(".json"), os.listdir(table_dir)))

    with open("/home/andrea/mantistable-tool.py/mantistable/private/tables/Challenge/target_cta.json") as f:
        targets = json.loads(f.read())

    #table_filenames = ["v16_110.json"]

    cell_datas = set()
    cells_raw = []
    for filename in table_filenames:
        print(filename)

        with open(os.path.join(table_dir, filename)) as raw:
            table = Table(filename[0:-5], json.loads(raw.read()))

        assert table.name in targets.keys()

        for ne_col_idx in targets[table.name]:
            original = set(table.get_col(ne_col_idx))
            normalized = [
                (transformer.transformer(item)[0], transformer.transformer(item)[1], is_person(item), item)
                for item in original
            ]
            cell_datas.update(set(normalized))
            cells_raw.extend([item[0] for item in normalized])

    return cell_datas, collections.Counter(cells_raw)


def is_person(value):
    m = re.search(r"^([A-Z]\.\s*)+(\w+\'*)+", value, re.IGNORECASE)
    return bool(m)


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def generate(normalized_data):
    counter = 0
    total = len(normalized_data)
    for nor_cell, query, person, raw in normalized_data:
        print(nor_cell, round(100*(counter / total), 2))

        if nor_cell == "" or os.path.exists(f"./data/{nor_cell}.ttl"):
            continue

        try:
            if person:
                # eg. G. V. Grant -> g v grant
                tokens = nor_cell.split(" ")
                assert len(tokens) >= 2

                person_prefix = tokens[0]
                person_surname = tokens[-1]
                rdf = sparql.DbpediaSparqlRepository(1).get_person_candidables_rdf(person_prefix, person_surname)
            else:
                rdf = sparql.DbpediaSparqlRepository(1).get_candidables_data(nor_cell, query)

                if "# Empty TURTLE" in rdf:
                    raw = raw.lower()
                    raw = raw.replace("'", r"\'")
                    rdf = sparql.DbpediaSparqlRepository(1).get_candidables_data_raw(raw)

            with open(f"./data/{nor_cell}.ttl", "w") as f:
                f.write(rdf)
        except:
            with open("./errors.data", "a") as f:
                f.write(nor_cell)
                f.write("\n")

        counter += 1


def main():
    table_dir = "/home/andrea/mantistable-tool.py/mantistable/private/tables/Challenge/converted/"

    normalized_data, freq_table = get_normalized_cell_data(table_dir)
    normalized_data = list(sorted(normalized_data))
    
    most_freq_cells = dict(filter(lambda item: item[1] > 1, dict(freq_table).items()))
    print(list(most_freq_cells.keys()), len(list(most_freq_cells.keys())))

    """
    c = chunks(normalized_data, int(len(normalized_data) / 30))

    pool = ThreadPool(30)
    pool.map(generate, c)
    """
    
    c = list(chunks(normalized_data, int(len(normalized_data) / 70)))
    
    processes = [multiprocessing.Process(target=generate, args=(chunck)) for chunck in c]

    # Run processes
    for p in processes:
        p.start()

    # Exit the completed processes
    for p in processes:
        p.join()
    

    
    #generate(normalized_data)


if __name__ == '__main__':
    main()
