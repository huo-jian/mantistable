from abc import abstractmethod


class FormatExporter:
    @abstractmethod
    def export(self):
        raise NotImplemented()
