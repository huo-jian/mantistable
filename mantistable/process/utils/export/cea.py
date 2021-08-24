from django.core.exceptions import ObjectDoesNotExist

from mantistable.process.utils.export.format_exporters.csv_exporter import CSVExporter


def export(tables):
    candidable_tables = []
    for table in tables:
        try:
            table.tabledata
            candidable_tables.append(table)
        except ObjectDoesNotExist:
            pass

    table_datas = sorted([
        (table, table.tabledata)
        for table in tables
    ], key=lambda item: item[0].name)

    linkings = []
    for table, table_data in table_datas:
        for col_idx, col in enumerate(table_data.data):
            for row_idx, row in enumerate(col):
                if "linked_entity" in row and row["linked_entity"] != "":
                    linkings.append([
                        table.name,
                        col_idx,
                        row_idx + 1,
                        row["linked_entity"]
                    ])

    return CSVExporter(linkings).export()
