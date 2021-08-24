from mantistable.process.utils.data_type import DataTypeEnum


def generate_datatype_frequency_table(num_cols, table_data):
    """
    Generate a table with data_types frequencies grouped by columns
    :param num_cols:
    :param table_data:
    :return:
    """
    freq_table = [{} for _ in range(0, num_cols)]
    for col_idx, col in enumerate(table_data.data):
        for row_idx, cell in enumerate(col):
            field_type = DataTypeEnum(cell["data_preparation"]["type"])
            if field_type not in freq_table[col_idx]:
                freq_table[col_idx][field_type] = 1
            else:
                freq_table[col_idx][field_type] += 1

    return freq_table
