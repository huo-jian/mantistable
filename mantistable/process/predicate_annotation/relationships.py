import collections
import json
import re
import statistics
from typing import Dict

import dateutil.parser as dateutil
import nltk

from mantistable.models import Annotation, Table, InfoTable, TableData
from mantistable.process.data_preparation.normalization.transformer import transformer
from mantistable.process.utils import scores
from mantistable.process.utils.assets.assets import Assets
from mantistable.process.utils.nlp import utils
from mantistable.process.utils.sparql.sparql_repository import DbpediaSparqlRepository
from mantistable.process.utils.validator import Validator

CPA_target = json.loads(Assets().get_asset("tables/Challenge/target_cpa.json"))


def get_NE_relationships(table_id, challenge=False):
    table = Table.objects.get(id=table_id)
    info_table = InfoTable.objects.get(table=table)
    ne_cols = info_table.ne_cols
    lit_cols = info_table.lit_cols
    subject_col = info_table.subject_col
    table_data = TableData.objects.get(table=table).data

    table_name = info_table.table_name
    if challenge and table_name not in CPA_target:
        print("Error: challenge table not in CPA target")
        return

    # cols_we = Annotation.objects.get(table=table).cols_we
    #
    # subject_concept = list(filter(lambda item: item["index"] == subject_col, ne_cols))[0]["type"]
    # winning_entities_sub_col = " ".join(list(set([f"<{item['entity']}>" for item in cols_we.get(str(subject_col), [])])))
    #
    # for ne_col in ne_cols:
    #     if ne_col["index"] != subject_col or challenge and ne_col["index"] != 0:
    #         winning_entities = " ".join(
    #             list(set([f"<{item['entity']}>" for item in cols_we.get(str(ne_col["index"]), [])])))
    #
    #         specific_concept = ne_col["type"]
    #         if specific_concept != "":
    #             general_concept = f"http://dbpedia.org/ontology/{list(ne_col['winning_concepts'].keys())[0]}"
    #             result = DbpediaSparqlRepository(table_id).get_NE_rel(winning_entities, winning_entities_sub_col, subject_concept,
    #                                                                   general_concept, specific_concept)
    #
    #             col_idx = ne_col["index"]
    #             column_cells = [cell["value"] for cell in table_data[col_idx]]
    #             if result is not None and len(result) > 0:
    #                 predicate, score = _get_necol_winning_predicate(column_cells, result)
    #
    #                 ne_col["rel"] = predicate
    #                 ne_col["relation_results"] = list({
    #                     r["p"]["value"][28:]
    #                     for r in result
    #                 })
    #                 print(ne_col["rel"])
    #             else:
    #                 ne_col["rel"] = ""
    #
    # info_table.ne_cols = ne_cols
    #
    # result = DbpediaSparqlRepository(table_id).get_LIT_rel(winning_entities_sub_col, subject_concept, None) # datatype)
    # for lit_col in lit_cols:
    #     """
    #     sub_dt = lit_col["data_type"][0]
    #     # NOTE: Original code takes first one, so do I...
    #     if isinstance(sub_dt, list):
    #         datatype = sub_dt[0]["label"]
    #     else:
    #         datatype = sub_dt["label"]
    #
    #     if datatype == "xsd:anyURI":
    #         datatype = "xsd:string"
    #
    #     if datatype == "xsd:float" or datatype == "xsd:double" or datatype == "xsd:integer":    # TODO: HACKS!!!!
    #         datatype = "isNumeric"  # TODO: Oh gosh I'm going to puke
    #     """
    #
    #     col_idx = lit_col["index"]
    #     column_cells = [cell["value"] for cell in table_data[col_idx]]
    #     if result is not None and len(result) > 0:
    #         predicate, score = _get_litcol_winning_predicate(column_cells, result)
    #
    #         lit_col["rel"] = predicate
    #         lit_col["relation_results"] = list({
    #             r["p"]["value"][28:]
    #             for r in result
    #         })
    #         print(lit_col["rel"])
    #     else:
    #         lit_col["rel"] = ""

    info_table.save()


def jaccard_index(a, b):
    assert (len(b) > 0)

    sa = set(a)
    sb = set(b)
    return len(sa.intersection(sb)) / len(sa.union(sb))


# TODO: Heavy refactoring needed!!!
def edit_distance(column_cells: list, predicates: Dict, predicate_freq: Dict):
    assert (len(column_cells) > 0)
    assert (len(list(predicates.keys())) > 0)

    # TODO: Extract
    def isdate(s):
        try:
            dateutil.parse(s)
            return True
        except (ValueError, OverflowError):
            return False

    p_scores = {}
    # for pred in predicates.keys():
    #     pred_scores = []
    #     for value in predicates[pred]:
    #         value_scores = []
    #         for cell_value in column_cells:
    #             # TODO: Technically this is not an edit distance score... extract it
    #             if Validator.is_decimal(cell_value) and Validator.is_decimal(value):
    #                 edit_dist_score = 1.0 - abs(float(cell_value) - float(value))/(max([abs(float(cell_value)), abs(float(value)), 1.0]))
    #             elif isdate(cell_value) and isdate(value):
    #                 d1 = dateutil.parse(cell_value).toordinal()
    #                 d2 = dateutil.parse(value).toordinal()
    #                 edit_dist_score = 1.0 - abs(d1 - d2) / max([d1, d2, 1])
    #             else:
    #                 if isdate(cell_value) != isdate(value) or Validator.is_decimal(cell_value) != Validator.is_decimal(value):
    #                     continue
    #
    #                 value = transformer(value)[0]
    #                 if utils.is_person(cell_value):
    #                     tokens = value.split(" ")
    #                     tokens[0] = tokens[0][0]
    #
    #                     edit_dist_score = 1.0 - scores.get_edit_distance_score(cell_value, " ".join(tokens))
    #                 else:
    #                     if Validator.is_description(cell_value):
    #                         edit_dist_score = 0.0
    #                         ms = max(len(cell_value), len(value))
    #                         if cell_value in value:
    #                             edit_dist_score = len(cell_value) / ms
    #                         elif value in cell_value:
    #                             edit_dist_score = len(value) / ms
    #
    #                         """
    #                         token_value = value.split(" ")
    #                         token_cell_value = cell_value.split(" ")
    #
    #                         print(token_cell_value, token_value)
    #
    #                         if len(token_value) == len(token_cell_value) == 0:
    #                             edit_dist_score = 1.0
    #                         else:
    #                             edit_dist_score = 1.0 - jaccard_index(token_value, token_cell_value)
    #                         """
    #                     else:
    #                         edit_dist_score = 1.0 - scores.get_edit_distance_score(cell_value, value)
    #
    #             value_scores.append(edit_dist_score)
    #
    #         if len(value_scores) > 0:
    #             pred_scores.append(statistics.mean(value_scores) * predicate_freq[pred])
    #
    #     if len(pred_scores) > 0:
    #         max_pred_score = max(pred_scores)
    #         if max_pred_score / predicate_freq[pred] > 0.25:
    #             p_scores[pred] = max_pred_score

    print(p_scores)

    if len(p_scores) > 0:
        # (predicate, score)
        return max(p_scores.items(), key=lambda item: item[1])   # TODO: Similar structure

    return "", 0.0


def _get_necol_winning_predicate(column_cells: list, result: list):
    assert (len(column_cells) > 0)
    assert (len(result) > 0)

    rows = set()
    predicates = []
    # for row in result:
    #     pred = row["p"]["value"][28:]
    #     value = row["l"]["value"]
    #     rows.add((pred, value))
    #     predicates.append(pred)

    return _get_winning_predicate(column_cells, list(rows), dict(collections.Counter(predicates)))


def _get_litcol_winning_predicate(column_cells: list, result: list):
    assert (len(column_cells) > 0)
    assert (len(result) > 0)

    # 0) Reiterate result structure
    rows = set()
    predicates = []
    # for row in result:
    #     pred = row["p"]["value"][28:]
    #     value = row["o"]["value"]
    #     xsd_type = row["o"]["type"]
    #
    #     if '"^^<http://' in value:
    #         value = value[1:value.find('"^^<http://')]
    #
    #     if xsd_type == "uri" and "http://dbpedia.org/resource/" in value:
    #         value = value[28:]
    #
    #     rows.add((pred, value))
    #     predicates.append(pred)

    return _get_winning_predicate(column_cells, list(rows), dict(collections.Counter(predicates)))


def _get_winning_predicate(column_cells: list, result: list, predicate_freq: dict):
    assert (len(column_cells) > 0)
    assert (len(result) > 0)

    # 1) extract values
    predicates = {}
    # for row in result:
    #     pred, value = row
    #
    #     if pred not in predicates.keys():
    #         predicates[pred] = []
    #
    #     predicates[pred].append(value)
    #
    # # 2) compute hybrid metrics
    # # TODO: No more hybrid metrics
    # scores = [
    #     edit_distance(column_cells, predicates, predicate_freq),
    # ]
    #
    # # 3) compute winning predicate
    candidates = {}
    # for score in scores:
    #     if score[0] not in candidates.keys():
    #         candidates[score[0]] = 0.0
    #
    #     candidates[score[0]] += score[1]

    print(scores, candidates, column_cells, predicates)

    # (predicate, score)
    return max(candidates.items(), key=lambda item: item[1])
