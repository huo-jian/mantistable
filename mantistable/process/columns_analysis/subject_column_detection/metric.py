from abc import ABC, abstractmethod

from mantistable.models import TableData
from mantistable.process.columns_analysis.subject_column_detection.utils import generate_datatype_frequency_table
from mantistable.process.utils.data_type import DataTypeEnum
from mantistable.process.utils.nlp import utils


class Metric(ABC):
    @abstractmethod
    def compute(self):
        raise NotImplemented

    @abstractmethod
    def normalized(self, score, score_list):
        raise NotImplemented


class EMCMetric(Metric):
    def __init__(self, table, col_idx):
        self.table = table
        self.col_idx = col_idx

    def compute(self):
        """
        For every column => number of 'empty' / number of rows
        :return {number}:
        """
        assert (self.table is not None)

        table_data = TableData.objects.get(table=self.table)

        data_types_freq_map = generate_datatype_frequency_table(self.table.num_cols, table_data)
        empty_cells = 0

        for k in data_types_freq_map[self.col_idx]:
            if k == DataTypeEnum.EMPTY:
                empty_cells = data_types_freq_map[self.col_idx][k]

        return 10 * (empty_cells / self.table.num_rows)

    def normalized(self, score, score_list):
        norm = 0
        if score != 0:
            norm = score / max(score_list)

        return norm


class UCMetric(Metric):
    def __init__(self, table, col_idx):
        self.table = table
        self.col_idx = col_idx

    def compute(self):
        """
        It counts, taken an element, how many times it occurs
        :return {number}:
        """

        assert (self.table is not None)

        col = TableData.objects.get(table=self.table).data[self.col_idx]
        unique_cells = set()

        for row in col:
            unique_cells.add(row["value"])

        # Number of groups for every column / number of rows
        return len(unique_cells) / self.table.num_rows

    def normalized(self, score, score_list):
        return score / max(score_list)


class AWMetric(Metric):
    def __init__(self, table, col_idx):
        self.table = table
        self.col_idx = col_idx

    def compute(self):
        """
        It returns an average of words of every column
        :return {number}:
        """
        assert (self.table is not None)

        col = TableData.objects.get(table=self.table).data[self.col_idx]
        text_result = [row["value"] for row in col]

        number_of_words = utils.remove_punctuations(" ".join(text_result))
        number_of_words = utils.remove_extra_spaces(number_of_words)
        number_of_words = utils.remove_stopwords(number_of_words.split(' '))
        number_of_words = " ".join(number_of_words)
        number_of_words = len(number_of_words.split(' '))

        return number_of_words / self.table.num_rows

    def normalized(self, score, score_list):
        return score / max(score_list)


class DFMetric(Metric):
    def __init__(self, col_idx, first_ne):
        self.col_idx = col_idx
        self.first_ne = first_ne

    def compute(self):
        return self.col_idx - self.first_ne

    def normalized(self, score, score_list):
        return score + 1
