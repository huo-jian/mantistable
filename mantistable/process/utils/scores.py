import re

import unidecode

import mantistable.process.utils.nlp.bag_of_words as nlp


def get_edit_distance_score(value_in_cell, name_of_entity):
    return _edit_distance(value_in_cell, name_of_entity) / max((len(value_in_cell), len(name_of_entity), 1))


def _edit_distance(str1, str2):
    # Matrix
    distances = []
    for i in range(0, len(str1) + 1):
        distances.append([])
        for j in range(0, len(str2) + 1):
            distances[i].append(0)

    for i in range(0, len(str1) + 1):
        distances[i][0] = i

    for i in range(0, len(str2) + 1):
        distances[0][i] = i

    for j in range(1, len(str2) + 1):
        for i in range(1, len(str1) + 1):
            if str1[i - 1] == str2[j - 1]:  # if the characters are equal
                distances[i][j] = distances[i - 1][j - 1]  # no operation needed
            else:
                distances[i][j] = min([  # take the minimum between
                    distances[i - 1][j] + 1,  # a deletion
                    distances[i][j - 1] + 1,  # an insertion
                    distances[i - 1][j - 1] + 1  # a substitution
                ])

    return distances[len(str1)][len(str2)]


def get_row_context_score(bow_set_abstract, bow_set_header, bow_set_row):
    k1 = list(bow_set_abstract.keys())
    k2 = nlp.remove_stop_words(list(bow_set_header.keys()))
    k3 = nlp.remove_stop_words(list(bow_set_row.keys()))
   
    s1 = list(filter(lambda word: nlp.get_singular(word) in k2 or nlp.get_plural(nlp.get_singular(word)) in k2, k1))
    s2 = list(filter(lambda word: nlp.get_singular(word) in k3 or nlp.get_plural(nlp.get_singular(word)) in k3, k1))
    ec = s1 + s2
    
    return len(ec), ec


def get_cell_context_score(bow_set_cell, bow_set_entity, bow_set_abstract):
    k1, k2, k3 = _get_keys(bow_set_cell, bow_set_entity, bow_set_abstract)
    s1 = list(filter(lambda word: word in k2, k1))
    s2 = list(filter(lambda word: word in k3, k1))

    score = len(s1) + len(s2)

    return score    # TODO: Original code said toFixed(2), but I dont see any reason to do that...


def _get_keys(bow_set_1, bow_set_2, bow_set_3):
    k1 = bow_set_1.keys()
    k2 = bow_set_2.keys()
    k3 = bow_set_3.keys()

    return k1, k2, k3


def get_scores(cell, entity, alias, bow_set_cell, bow_set_entity, bow_set_abstract, bow_set_header_context, bow_set_row_context, result_entities):
    entity_ed = get_edit_distance_score(cell, entity)
    alias_ed = get_edit_distance_score(cell, alias)
    edit_distance_score = min(entity_ed, alias_ed)

    tmp = get_row_context_score(bow_set_abstract, bow_set_header_context, bow_set_row_context)
    row_context_score = tmp[0]
    cell_context_score = get_cell_context_score(bow_set_cell, bow_set_entity, bow_set_abstract)
    result_entities.append({
        "edit_distance_score": edit_distance_score,
        "row_context_score": row_context_score,
        "cell_context_score": cell_context_score,
        "ec": tmp[1]
    })

    return {
        "edit_distance_score": edit_distance_score,
        "row_context_score": row_context_score,
        "cell_context_score": cell_context_score,
    }, result_entities
