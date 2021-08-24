from mantistable.process.utils.export.format_exporters.csv_exporter import CSVExporter
from django.core.exceptions import ObjectDoesNotExist


def export(tables: list):
    candidable_tables = []
    for table in tables:
        try:
            table.infotable
            candidable_tables.append(table)
        except ObjectDoesNotExist:
            pass

    table_datas = sorted([
        (table, table.infotable.ne_cols)
        for table in candidable_tables
    ], key=lambda item: item[0].name)

    annotations = []
    for table, ne_cols in table_datas:
        for ne_col in ne_cols:
            annotations.append([
                table.name,
                ne_col["index"],
                " ".join([
                    f"http://dbpedia.org/ontology/{concept}"
                    for concept in ne_col["winning_concepts"].keys()
                ]),
            ])

    return CSVExporter(annotations).export()
