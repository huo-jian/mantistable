import json
import re

import mantistable.process.concept_datatype_annotation.entity_extraction as concept_annotation
import mantistable.process.utils.nlp.bag_of_words as nlp
from mantistable.models import TableData, Table, InfoTable, Linking
from mantistable.process.data_preparation.normalization.transformer import transformer
from mantistable.process.utils.publisher.console import Console
from mantistable.process.utils.nlp import utils
from mantistable.process.utils.sparql.sparql_repository import DbpediaSparqlRepository
from mantistable.process.utils.assets.assets import Assets

CEA_target = json.loads(Assets().get_asset("tables/Challenge/target_cea.json"))


def get_entity_linking(table_id, challenge=False):
    table = Table.objects.get(id=table_id)
    table_data = TableData.objects.get(table=table)
    info_table = InfoTable.objects.get(table=table)
    ne_cols = info_table.ne_cols
    table_name = info_table.table_name
       
    Console(table.id).info(f"Entity Linking started for {table.id}")

    # try:
    #     link_model = Linking.objects.get(table=table)
    #     link_model.data = []
    # except Linking.DoesNotExist:
    #     link_model = Linking(
    #         table=table,
    #         table_name=table.name,
    #         data=[]
    #     )
    #
    # if challenge:
    #     ne_cols_indexes = [int(target) for target in CEA_target[table_name].keys()]
    #     ne_cols = list(filter(lambda col: col["index"] in ne_cols_indexes, ne_cols))

    print(ne_cols)

    # for ne_col in ne_cols:
    #     concept = ne_col["type"][28:]
    #
    #     if len(list(ne_col["winning_concepts"].keys())) > 1:
    #         concept = list(ne_col["winning_concepts"].keys())[0]
    #
    #     linked_entities = _linking(concept, table_data, ne_col["index"], table_data.header, table, challenge)
    #     for le in linked_entities:
    #         link_model.data.append({
    #             "col": ne_col["index"],
    #             "row": le["row"],
    #             "linked_entity": le["linked_entity"]
    #         })
    #
    # table_data.save()
    # link_model.save()
    # info_table.save()

    Console(table.id).info(f"Entity Linking finished for {table.id}")


def _linking(ne_col_type, table_data, ne_col_idx, header, table, challenge):
    bw_header_context = nlp.get_header_context_from_header_table(header)
    row_idx = 0
    result_entities_final = []
    values = {}
    linked_entities = []
    table_id = table.id

    # col = table_data.data[ne_col_idx]
    #
    # bw_table_name = nlp.bow_set_text(concept_annotation.get_table_name_tokens(table.name))
    #
    # for row in col:
    #     # if not challenge or (challenge and str(row_idx+1) in CEA_target[table_name][str(ne_col_idx)]):
    #     data = row
    #     cell = data["value"]
    #     value_original = data["value_original"]
    #     tmp_we = values.get(cell, None)
    #
    #     if tmp_we is not None:
    #         winning_entity = tmp_we
    #     else:
    #         if col[row_idx]["value"] == "" or col[row_idx]["value_for_query"] == "":
    #             row_idx += 1
    #             continue
    #
    #         if utils.is_person(value_original):
    #             # eg. G. V. Grant -> g v grant
    #             tokens = cell.split(" ")
    #             assert len(tokens) >= 2
    #
    #             person_prefix = tokens[0]
    #             person_surname = tokens[-1]
    #
    #             results = DbpediaSparqlRepository(table_id).get_person_entities(person_prefix, person_surname)
    #             results_symmetric = DbpediaSparqlRepository(table_id).get_person_entities_symmetric(person_prefix, person_surname)
    #         else:
    #             results = DbpediaSparqlRepository(table_id).get_final_entity(row["value_for_query"], ne_col_type, False)
    #             results_symmetric = DbpediaSparqlRepository(table_id).get_final_entity_symmetric(row["value_for_query"], ne_col_type, False)
    #             if len(results) == 0 and len(cell.split(' ')) > 1:
    #                 results = DbpediaSparqlRepository(table_id).get_final_entity(cell, ne_col_type, True)
    #
    #             if len(results_symmetric) == 0 and len(cell.split(' ')) > 1:
    #                 results_symmetric = DbpediaSparqlRepository(table_id).get_final_entity_symmetric(cell, ne_col_type, True)
    #
    #         bw_row_context = nlp.get_row_context(header, {
    #             table_data.header[col_idx]: col_data[row_idx]
    #             for col_idx, col_data in enumerate(table_data.data)
    #         }, ne_col_idx)
    #
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
    #                     else:  # Not interested
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
    #         winning_entity, result_entities_final = concept_annotation._get_winning_entity(cell, data["value_original"], entities,
    #                                                                                     bw_header_context,
    #                                                                                     bw_row_context,
    #                                                                                     bw_table_name)
    #
    #     if winning_entity is None:
    #         winning_entity = ""
    #     values[cell] = winning_entity
    #
    #     col[row_idx].update({
    #         "linked_entity": winning_entity,
    #         "final_entities": result_entities_final,  # NOTE: >>>>> ALL ENTITIES <<<<<
    #     })
    #
    #     table_data.data[ne_col_idx] = col
    #     table_data.save()
    #
    #     linked_entities.append({
    #         "row": row_idx,
    #         "linked_entity": winning_entity
    #     })
    #
    #     row_idx += 1

    return linked_entities
