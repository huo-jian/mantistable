class Table:
    def __init__(self, name: str, data: list):
        assert (len(data) > 0)
        assert (isinstance(data[0], dict))
        self.name = name
        self.data = data

    def get_header(self):
        return list(self.data[0].keys())

    def get_row(self, idx: int):
        assert (idx < self.rows_count())

        return list(self.data[idx].values())

    def get_col(self, idx: int):
        assert (idx < self.cols_count())

        header = self.get_header()[idx]
        return [
            row[header]
            for row in self.data
        ]

    def get_content(self):
        content = []
        for row in self.data:
            for col in row.keys():
                content.append(row[col])

        return content

    def rows_count(self):
        return len(self.get_col(0))

    def cols_count(self):
        return len(self.get_header())