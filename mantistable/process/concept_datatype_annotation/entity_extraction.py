import re

import ftfy
import unidecode
import urllib
import mantistable.process.utils.nlp.bag_of_words as nlp
from mantistable.process.data_preparation.normalization.transformer import transformer
from mantistable.process.utils import scores
from mantistable.process.utils.dbpedia_lookup.dbpedia_lookup import DbpediaLookup
from mantistable.process.utils.nlp import utils
from mantistable.process.utils.sparql.sparql_repository import DbpediaSparqlRepository


# TODO: Change name: this function get ALL possible data for a cell
def get_entities_and_disambiguation(table_name, table_data, columns, col, indexes, header_context, header, table_id):
    winning_entities = []

    # bow_set_table = nlp.bow_set_text(get_table_name_tokens(table_name))
    # for i in range(0, len(indexes)):
    #     index = indexes[i]
    #     row = col[index]
    #     value_in_cell = row["value"]
    #     value_original = row["value_original"]
    #
    #     if value_in_cell == "" or row["value_for_query"] == "":
    #         continue
    #
    #     if "result_entities" not in col[index].keys():
    #         if utils.is_person(value_original):
    #             # eg. G. V. Grant -> g v grant
    #             tokens = value_in_cell.split(" ")
    #             assert len(tokens) >= 2
    #
    #             person_prefix = tokens[0]
    #             person_surname = tokens[-1]
    #
    #             results = DbpediaSparqlRepository(table_id).get_person_entities(person_prefix, person_surname)
    #             results_symmetric = DbpediaSparqlRepository(table_id).get_person_entities_symmetric(person_prefix, person_surname)
    #         else:
    #             results = DbpediaSparqlRepository(table_id).get_entities(row["value_for_query"], False)
    #             results_symmetric = DbpediaSparqlRepository(table_id).get_entities(row["value_for_query"], False)
    #             if len(results) == 0 and len(value_in_cell.split(' ')) > 1:
    #                 results = DbpediaSparqlRepository(table_id).get_entities(value_in_cell, True)
    #
    #             if len(results_symmetric) == 0 and len(value_in_cell.split(' ')) > 1:
    #                 results_symmetric = DbpediaSparqlRepository(table_id).get_entities_symmetric(value_in_cell, True)
    #
    #
    #         bw_row_context = nlp.get_row_context(header, {
    #             table_data.header[col_idx]: col[index]
    #             for col_idx, col in enumerate(columns)
    #         }, index)
    #
    #         # TODO: >>>>>>>>>>>>>>> HACKS! <<<<<<<<<<<<<<<
    #         # Union between result and result symmetric
    #         results.extend(results_symmetric)
    #
    #         entities = {}
    #         # Group by candidate entity
    #         for resultrow in results:
    #             subj = resultrow["s"]["value"]
    #             pred = resultrow["p"]["value"]
    #
    #             # Object parsing
    #             obj = resultrow["o"]["value"].strip()
    #             # Lang tags / datatypes
    #             if obj.startswith('"'):
    #                 if '"@' in obj:
    #                     if obj.endswith('"@en'):
    #                         obj = obj[1:-4]
    #                     else:   # Not interested
    #                         continue
    #                 elif '"^^<http://' in obj:
    #                     obj = obj[1:obj.rfind('"^^<http://')]
    #             # UriRef
    #             if obj.startswith('http://') or obj.startswith('https://'):
    #                 obj = nlp.get_name_from_entity(obj)
    #
    #             obj = transformer(obj)[0]
    #
    #             # Alias parsing
    #             if resultrow["alias"]["value"] == "None":
    #                 alias = None
    #             else:
    #                 alias = resultrow["alias"]["value"][28:]
    #
    #             if subj not in entities.keys():
    #                 entities[subj] = [{}, alias]
    #
    #             if pred not in entities[subj][0]:
    #                 entities[subj][0][pred] = set()
    #
    #             entities[subj][0][pred].add(obj)
    #
    #         # TODO: >>>>>>>>>>>>>>> END OF HACKS! <<<<<<<<<<<<<<<
    #
    #         winning_entity, result_entities = _get_winning_entity(value_in_cell, row["value_original"], entities, header_context, bw_row_context, bow_set_table)
    #     else:
    #         winning_entity, result_entities = _compute_winning_entity(value_in_cell, col[index]["result_entities"])
    #
    #     # >>>>> RESULT ENTITIES <<<<<
    #     col[index].update({
    #         "result_entities": result_entities
    #     })
    #
    #     if winning_entity is not None:
    #         tmp = list(filter(lambda item: item["entity"] == winning_entity, result_entities))[0]
    #         winning_entities.append(tmp)
            
    return winning_entities




def _get_winning_entity(cell, cell_orig, entities, bw_header_context, bw_row_context, table_id):
    def get_name_from_entity(entity):
        def decode_uri_component(uri):
            return urllib.parse.unquote(uri)

        entity = decode_uri_component(entity)

        tokens = entity[28:].split("_")
        if len(tokens[0]) > 0:
            tokens[0] = tokens[0][0]

        name = " ".join(tokens).lower()
        return transformer(name)[0]

    result_entities = []
    row_context_score_max = 1
    cell_context_score_max = 1

    for j in range(0, len(entities.keys())):
        subj = list(entities.keys())[j]
        objs = set()

        for ob in entities[subj][0].values():
            for value in ob:
                for token in re.sub("\s+", " ", re.sub(r'[^a-zA-Z]', ' ', value)).split(" "):
                    try:
                        float(token)
                    except ValueError:
                        objs.add(token)

        objects_as_str = " ".join(list(objs))
        entity = nlp.get_name_from_entity(subj)

        bow_set_cell, bow_set_entity, bow_set_abstract = nlp.get_bow_set(cell, subj, objects_as_str)

        if utils.is_person(cell_orig):
            entity = get_name_from_entity(subj)

        if entities[subj][1] is not None:
            alias = nlp.get_name_from_entity(entities[subj][1])
        else:
            alias = entity

        ent_scores, result_entities = scores.get_scores(cell, entity, alias, bow_set_cell, bow_set_entity, bow_set_abstract,
                                                        bw_header_context, bw_row_context, result_entities)

        if ent_scores["row_context_score"] > row_context_score_max:
            row_context_score_max = ent_scores["row_context_score"]

        if ent_scores["cell_context_score"] > cell_context_score_max:
            cell_context_score_max = ent_scores["cell_context_score"]

        result_entities[j]["entity"] = subj
        result_entities[j]["alias"] = entities[subj][1]

    for j in range(0, len(result_entities)):
        row_context_score_normalized = result_entities[j]["row_context_score"] / row_context_score_max
        cell_context_score_normalized = result_entities[j]["cell_context_score"] / cell_context_score_max

        result_entities[j]["row_context_score_normalized"] = row_context_score_normalized
        result_entities[j]["cell_context_score_normalized"] = cell_context_score_normalized

    return _compute_winning_entity(cell, result_entities)



def _compute_winning_entity(cell, result_entities):
    winning_entity = None
    winning_entity_idx = -1
    max_score = float("-inf")

    # for j in range(0, len(result_entities)):
    #     row_context_score_normalized = result_entities[j]["row_context_score_normalized"]
    #     cell_context_score_normalized = result_entities[j]["cell_context_score_normalized"]
    #
    #     final_score = row_context_score_normalized + cell_context_score_normalized - 2*result_entities[j]["edit_distance_score"]
    #
    #     if final_score > max_score:
    #         max_score = final_score
    #         winning_entity = result_entities[j]["entity"]
    #         winning_entity_idx = j
    #
    #     result_entities[j]["final_score"] = final_score
    #     result_entities[j]["winning"] = "false"
    #     result_entities[j]["value"] = cell
    #
    # if winning_entity_idx >= 0:
    #     result_entities[winning_entity_idx]["winning"] = "true"

    return winning_entity, result_entities


def get_lookup_entities(cell_value, table_id):
    if len(cell_value.strip().split(" ")) > 3:
        query_string = sorted(cell_value.strip().split(" "), key=lambda word: len(word), reverse=True)[0]
    else:
        query_string = cell_value

    return DbpediaLookup(table_id).get_entities(query_string)


def get_table_name_tokens(table_name):
    """
    Table title query
    :param table_name:
    :param table_id:
    :return:
    """

    title = table_name.lower()
    title = ftfy.fixes.decode_escapes(title)
    title = ftfy.fixes.unescape_html(title)
    title = ftfy.fix_text(title)
    title = urllib.parse.unquote(title)
    title = unidecode.unidecode(title)
    title = title.replace("_-_", " ")
    title = title.replace("_", " ")
    title = title.replace("(", "")
    title = title.replace(")", "")
    counter_char_index = title.find("#")  # delete all after this character
    if counter_char_index > 0:
        title = title[0:counter_char_index]

    return title.split(" ")
