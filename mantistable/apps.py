from django.apps import AppConfig


class MantisTableConfig(AppConfig):
    name = 'mantistable'

    def ready(self):
        import mantistable.signals
