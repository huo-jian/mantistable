import csv
import io

from mantistable.process.utils.export.format_exporters.format_exporter import FormatExporter


class CSVExporter(FormatExporter):
    def __init__(self, data: list):
        self.data = data

    def export(self):
        csv_data = io.StringIO()
        cta_writer = csv.writer(csv_data, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        cta_writer.writerows(self.data)

        return csv_data.getvalue()
