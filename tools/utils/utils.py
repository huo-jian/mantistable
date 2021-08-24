import collections
import csv
import io
import os

import ftfy
import unidecode


def get_max_freq_column_count(column_lengths: list):
    """
    Bad csv files have different number of columns. This method return the maximum frequency column count
    :param column_lengths:
    :return column count, freq:
    """
    freq_map = [(value, freq) for value, freq in dict(collections.Counter(column_lengths)).items()]
    freq_map = sorted(freq_map, key=lambda item: item[1], reverse=True)

    freq_map_tmp = []
    for i in range(0, len(freq_map) - 1):
        a = freq_map[i]
        b = freq_map[i + 1]

        if a[1] == b[1]:
            freq_map_tmp.append((max(a[0], b[0]), a[1]))
        else:
            freq_map_tmp.append(a)

            if i == len(freq_map) - 1:
                freq_map_tmp.append(b)

    if len(freq_map) > 1:
        freq_map = freq_map_tmp

    return freq_map[0][0]


def sanitize(data: str):
    """
    Tries to fix badly formatted string
    :param data:
    :return:
    """
    # print(data)

    data = ftfy.fixes.remove_control_chars(data)
    data = ftfy.fixes.decode_escapes(data)
    data = ftfy.fix_text(data)
    data = unidecode.unidecode(data)

    # print("\t", data)
    return data


def get_csv_content(filepath: str, delimiter=",", quotechar='"'):
    """
    Utility method to read csv file and return content as list
    :param filepath:
    :param delimiter:
    :param quotechar:
    :return:
    """
    assert os.path.exists(filepath) and os.path.isfile(filepath)

    with open(filepath, newline='') as csvfile:
        content = csvfile.read().replace('\\"', '\'')
        text = csv.reader(io.StringIO(content), delimiter=delimiter, quotechar=quotechar)
        rows = [row for row in text if len(row) > 0]

    assert len(rows) > 0  # NOTE: By contract the file must not be empty
    return rows

def get_csv_content_alt(filepath: str, delimiter=",", quotechar='"'):
    """
    Utility method to read csv file and return content as list
    :param filepath:
    :param delimiter:
    :param quotechar:
    :return:
    """
    assert os.path.exists(filepath) and os.path.isfile(filepath)

    with open(filepath, "r", encoding="ISO-8859-1") as csvfile:
        text = csv.reader((line.replace('\0','') for line in csvfile), delimiter=delimiter, quotechar=quotechar)
        rows = [row for row in text if len(row) > 0]

    assert len(rows) > 0  # NOTE: By contract the file must not be empty
    return rows
