def get_edit_distance_score(value_in_cell, name_of_entity):
    return _edit_distance(value_in_cell, name_of_entity) / max(len(value_in_cell), len(name_of_entity))


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
