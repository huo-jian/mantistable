from mantistable.process.columns_analysis.subject_column_detection import metric, utils
from mantistable.process.data_preparation.normalization.transformer import transformer
from mantistable.process.utils.data_type import DataTypeEnum
from mantistable.models import TableData, Table, InfoTable


def set_info_table(table_id):
    table = Table.objects.get(id=table_id)
    table_data = TableData.objects.get(table=table)

    num_rows = table.num_rows
    num_cols = table.num_cols
    keys = [transformer(header)[0] for header in table.header]

    freq_table = utils.generate_datatype_frequency_table(num_cols, table_data)

    lit_cols = []
    ne_cols = []
    no_ann_cols = []

    for i in range(0, num_cols):
        data_types_freq_map = freq_table[i]

        num_type = 0
        num_empty = 0
        max_occurrences = 0
        type_max = None
        
        for data_type in data_types_freq_map:
            if data_type == DataTypeEnum.NONE:
                # num_no_type = data_types_freq_map[data_type]  # TODO: dangling variable...
                pass
            elif data_type == DataTypeEnum.EMPTY:
                num_empty += data_types_freq_map[data_type]
            else:
                num_type += data_types_freq_map[data_type]

            if data_types_freq_map[data_type] > max_occurrences:
                max_occurrences = data_types_freq_map[data_type]
                type_max = data_type

        value_type = None
        description = False
        if metric.AWMetric(table, i).compute() > 6:
            description = True
            type_max = DataTypeEnum.DESCRIPTION
        if num_type > ((num_rows - num_empty) * 0.60) and (num_empty <= (num_rows * 0.70)) or description:
            value_type = type_max

        # Header check, empty string in key fields
        if keys[i] == '':
            keys[i] = '-'

        if num_empty >= num_rows * 0.7 or value_type == DataTypeEnum.NOANNOTATION or value_type == DataTypeEnum.ID:
            no_ann_cols.append({
                "index": i,
                "header": keys[i],
                "type": ""
            })
        elif value_type is not None:
            type_freq = []
            field_types = []
            field_data_types = []
            for data_type in data_types_freq_map:
                assert (num_rows != 0)
                rate = data_types_freq_map[data_type] / num_rows
                type_freq.append({
                    "name": data_type.value,
                    "occurrences": data_types_freq_map[data_type],
                    "rate": rate,
                })

                field_types.append(data_type.value)
                field_data_types.append(DataTypeEnum.get_datatype_info(data_type))

            lit_cols.append({
                "index": i,
                "header": keys[i],
                "regex_type": field_types,
                "data_type": field_data_types,
                "type_freq_table": type_freq
            })
        else:
            ne_cols.append({
                "index": i,
                "header": keys[i],
                "score": [],
                "type": "",
                "winning_concepts": {},
            })
            
    try:
        infotable = InfoTable.objects.get(table=table)
        infotable.table_name = table.name
        infotable.lit_cols = lit_cols
        infotable.ne_cols = ne_cols
        infotable.no_ann_cols = no_ann_cols
    except InfoTable.DoesNotExist:
        infotable = InfoTable(
            table=table,
            table_name = table.name,
            lit_cols=lit_cols,
            ne_cols=ne_cols,
            no_ann_cols=no_ann_cols,
        )

    infotable.save()
