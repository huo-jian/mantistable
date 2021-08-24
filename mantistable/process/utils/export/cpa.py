from django.core.exceptions import ObjectDoesNotExist

from mantistable.process.utils.export.format_exporters.csv_exporter import CSVExporter


def export(tables):
    candidable_tables = []
    for table in tables:
        try:
            table.infotable
            candidable_tables.append(table)
        except ObjectDoesNotExist:
            pass

    table_datas = sorted([
        (table, table.infotable)
        for table in candidable_tables
    ], key=lambda item: item[0].name)

    relations = []
    for data in table_datas:
        table = data[0]
        ne_cols = data[1].ne_cols
        lit_cols = data[1].lit_cols
        sub_col = max(data[1].subject_col, 0)

        if len(ne_cols) > 0:
            object_ne_cols = list(filter(lambda col: col["index"] != sub_col, ne_cols))
            object_lit_cols = lit_cols

            for ne_col in object_ne_cols:
                if "rel" in ne_col.keys() and ne_col["rel"] != "":
                    relations.append([
                        table.name,
                        sub_col,
                        ne_col["index"],
                        ne_col["rel"],
                    ])

            for lit_col in object_lit_cols:
                if "rel" in lit_col.keys() and lit_col["rel"] != "":
                    relations.append([
                        table.name,
                        sub_col,
                        lit_col["index"],
                        lit_col["rel"],
                    ])

    return CSVExporter(relations).export()
