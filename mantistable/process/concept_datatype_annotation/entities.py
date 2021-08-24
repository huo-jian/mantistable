import copy
import json
import math
import re

import mantistable.process.utils.nlp.bag_of_words as nlp
from mantistable.models import TableData, Annotation, Table, InfoTable, GoldStandardsEnum
from mantistable.process.concept_datatype_annotation import branching, entity_extraction
from mantistable.process.data_preparation.normalization import transformer
from mantistable.process.utils import scores
from mantistable.process.utils.assets.assets import Assets
from mantistable.process.utils.dbpedia_lookup.dbpedia_lookup import DbpediaLookup
from mantistable.process.utils.nlp import utils
from mantistable.process.utils.sparql.sparql_repository import DbpediaSparqlRepository

number_of_rows = 30
ontology_class = json.loads(Assets().get_asset("OntologyClass.json"))
ontology_graph = json.loads(Assets().get_asset("OntologyGraph.json"))
ontology_graph_ct = json.loads(Assets().get_asset("OntologyGraphCT.json"))

T2D_target = json.loads(Assets().get_asset("tables/T2Dv2/target.json"))
# CTA_target = json.loads(Assets().get_asset("tables/Round2/Target_CTA_CPA_CEA.json"))
CTA_target = json.loads(Assets().get_asset("tables/Challenge/target_cta.json"))


def get_entities(table_id, challenge=False):
    table = Table.objects.get(id=table_id)

    table_data = TableData.objects.get(table=table)
    info_table = InfoTable.objects.get(table=table)
    ne_cols = info_table.ne_cols
    total_rows_table = table.num_rows
    cols = table_data.data
    sub_col = info_table.subject_col

    # if table.gs_type == GoldStandardsEnum.T2D.value:
    #     target_sub_col = T2D_target[table.name]
    #     info_table.subject_col = target_sub_col
    #
    #     if len(list(filter(lambda col: col["index"] == target_sub_col, ne_cols))) == 0:
    #         info_table.ne_cols.append({
    #             "index": target_sub_col,
    #             "header": table_data.header[target_sub_col],
    #             "score": [],
    #             "type": "",
    #             "winning_concepts": {},
    #         })
    #
    #         info_table.lit_cols = list(filter(lambda col: col["index"] != target_sub_col, info_table.lit_cols))
    #         info_table.no_ann_cols = list(filter(lambda col: col["index"] != target_sub_col, info_table.no_ann_cols))
    #
    #     info_table.save()
    #
    # header = table_data.header
    # header_context = nlp.get_header_context_from_header_table(header)
    # indexes = _get_indexes_rows(total_rows_table)
    #
    # if challenge:
    #     concept_res = CTA_target.get(table.file_name[0:-5], None)
    #     if concept_res is not None:
    #         cols_target = [index for index in concept_res]
    #     else:
    #         cols_target = []
    #
    #     # ne_cols = list(filter(lambda col: col["index"] in cols_target, ne_cols))
    #     ne_cols = []
    #     for target in cols_target:
    #         ne_cols.append({
    #             "index": target,
    #             "header": table_data.header[target],
    #             "score": [],
    #             "type": "",
    #             "winning_concepts": {},
    #         })
    #
    #     sub_col = 0
    #
    # we_cols = {}
    # new_no_ann_cols_index = []
    # for ne_col in ne_cols:
    #     winning_entities = entity_extraction.get_entities_and_disambiguation(table.name, table_data, cols,
    #                                                                          cols[ne_col["index"]], indexes,
    #                                                                          header_context, header, table_id)
    #
    #     if "lookup_concepts" not in ne_col.keys():
    #         lookup_classes = get_lookup_entities(indexes, cols[ne_col["index"]], table_id)
    #     else:
    #         lookup_classes = ne_col["lookup_concepts"]
    #
    #     # no_annotation = _is_no_annotation(winning_entities)
    #     no_annotation = False  # TODO: What?
    #     if not challenge and no_annotation and ne_col["index"] != sub_col:
    #         new_no_ann_cols_index.append(ne_col["index"])
    #     else:
    #         cell_type, winning_concepts, global_concepts, final_concepts = _get_type(winning_entities, total_rows_table,
    #                                                                  header[ne_col["index"]], table_id,
    #                                                                  lookup_classes)
    #
    #         if cell_type is not None:
    #             ne_col["type"] = f"http://dbpedia.org/ontology/{cell_type}"
    #         else:
    #             ne_col["type"] = ''
    #
    #         ne_col["winning_concepts"] = winning_concepts
    #         ne_col["global_concepts"] = global_concepts
    #         ne_col["final_concepts"] = final_concepts
    #         ne_col["lookup_concepts"] = list(lookup_classes)
    #         we_cols[ne_col["index"]] = winning_entities
    #
    # info_table.ne_cols = ne_cols
    # info_table.save()
    #
    # table_data.data = cols
    table_data.save()

    # TODO: Get or create pattern
    # try:
    #     ann = Annotation.objects.get(table=table)
    # except Annotation.DoesNotExist:
    #     ann = Annotation(table=table, cols_we=we_cols)
    #
    # ann.cols_we = we_cols
    #ann.save()


def get_lookup_entities(indexes, col, table_id):
    lookup_classes = set()
    # for i in range(0, len(indexes)):
    #     index = indexes[i]
    #     row = col[index]
    #     value_in_cell = row["value"]
    #     value_original = row["value_original"]
    #
    #     if value_in_cell == "" or row["value_for_query"] == "" or utils.is_person(value_original):
    #         continue
    #
    #     lookup_cl = get_lookup_cell_entity(value_in_cell, table_id)
    #     for label in lookup_cl.keys():
    #         ed = scores.get_edit_distance_score(value_in_cell, transformer.transformer(label)[0])
    #
    #         if ed < 0.2:
    #             print(value_in_cell, transformer.transformer(label)[0], lookup_cl[label])
    #             for cl in lookup_cl[label]:
    #                 lookup_classes.add(cl)

    return lookup_classes


def get_lookup_cell_entity(cell_value, table_id):
    if len(cell_value.strip().split(" ")) > 3:
        tokens = sorted(cell_value.strip().split(" "), key=lambda word: len(word), reverse=True)[0:3]
        query_string = " ".join(tokens)
    else:
        query_string = cell_value

    return DbpediaLookup(table_id).get_entities(query_string)


def _is_no_annotation(winning_entities):
    count = 0
    we_map = {}
    # for we in winning_entities:
    #     if we_map.get(we["entity"], None) is None and we["edit_distance_score"] < 0.4:
    #         count += 1
    #
    #     we_map[we["entity"]] = True
    #
    # we_count = len(we_map.items())
    # if we_count > 0:
    #     return (count / we_count) < 0.50

    return True


def _get_indexes_rows(table_rows):
    indexes = []
    # if table_rows <= number_of_rows:
    #     for i in range(0, table_rows):
    #         indexes.append(i)
    # else:
    #     step = math.floor(number_of_rows / 3.0)
    #
    #     for i in range(0, step):
    #         indexes.append(i)
    #
    #     tmp = math.floor(table_rows / 3.0) + 1
    #     for i in range(tmp, tmp + step):
    #         indexes.append(i)
    #
    #     tmp = table_rows - step
    #     for i in range(tmp, tmp + step):
    #         indexes.append(i)
            
    return indexes


def _get_type(winning_entities, total_rows_table, header_attribute, table_id, lookup_concepts):
    global_concepts = {}
    final_concepts = {}

    # for e in winning_entities:
    #     entity = e["entity"]
    #     if e["alias"] is not None:
    #         entity = e["alias"]
    #
    #     cell_types = DbpediaSparqlRepository(table_id).get_type(entity)
    #     e["type"] = [cell_type["type"]["value"] for cell_type in cell_types]
    #     cell_types = _extract_types(cell_types)
    #
    #     local_concepts = {}
    #     for cell_type in cell_types:
    #         if cell_type in ontology_class:
    #             if global_concepts.get(cell_type, None) is None:
    #                 global_concepts[cell_type] = {}
    #                 global_concepts[cell_type]["frequency"] = 0
    #                 global_concepts[cell_type]["row"] = 0
    #
    #             if local_concepts.get(cell_type, None) is None:
    #                 local_concepts[cell_type] = True
    #                 global_concepts[cell_type]["row"] += 1
    #
    #             global_concepts[cell_type]["frequency"] += 1
    #
    # if number_of_rows > total_rows_table:
    #     weight_rows = total_rows_table
    # else:
    #     weight_rows = number_of_rows
    #
    # final_concepts = copy.deepcopy(global_concepts)
    # lookup_intersection = set(filter(lambda type_class: type_class in final_concepts.keys(), lookup_concepts))
    # for cl in lookup_intersection:
    #     # NOTE 30 percent of table sample
    #     final_concepts[cl]["frequency"] += int(0.30 * weight_rows)
    #     # final_concepts[cl]["row"] += int(0.30 * weight_rows)
    #
    # header_concepts = _find_possible_concept_in_header(header_attribute)
    # header_intersection = set(filter(lambda type_class: type_class in final_concepts.keys(), header_concepts))
    # for cl in header_intersection:
    #     final_concepts[cl]["frequency"] += weight_rows
    #     final_concepts[cl]["row"] = weight_rows

    winning_concepts = {}

    # max_freq = float("-inf")
    # if len(final_concepts) > 0:
    #     max_freq = max([v["frequency"] for v in final_concepts.values()])
    # for key in final_concepts:
    #     # if final_concepts[key]["row"] / weight_rows > 0.40 and final_concepts[key]["frequency"] / max_freq > 0.40:
    #     if final_concepts[key]["frequency"] / max_freq > 0.30:
    #         winning_concepts[key] = final_concepts[key]["row"]

    # TODO: Debug
    print(global_concepts)
    print(final_concepts)
    print(winning_concepts)
    
    max_type = None
    # if len(winning_concepts) > 0:
    #     # TODO: Singleton??? ont_G?
    #     ont_G = branching.create_graph()
    #     winning_concepts = branching.get_annotation(winning_concepts, ont_G)
    #     max_type = None
    #
    #     if len(winning_concepts.keys()) > 0:
    #         max_type = list(winning_concepts.keys())[-1]
    #
    #     print("BRANCHING", winning_concepts)
    #     print("BRANCHING", max_type)
    # print("maxType: ", max_type)

    return max_type, winning_concepts, global_concepts, final_concepts


def _extract_types(cell_types):
    result = ''
    for cell_type in cell_types:
        tmp = cell_type["type"]["value"]
        result += tmp[tmp.rfind("/") + 1:len(tmp)] + " "

    result = result.strip()
    cell_types = result.split(" ")
    return cell_types


def _find_possible_concept_in_header(header):
    header_tokens = header.split(" ")
    concepts = []

    for token in header_tokens:
        for cl in ontology_class:
            if cl.lower() == token:
                concepts.append(cl)

    return concepts
