import enum

from pymongo import MongoClient

from app import settings
from mantistable.models import ServerState, Table, SparqlEndpoint


class Log:
    def __init__(self, log_type, body):
        self.type = log_type
        self.body = body

    def __str__(self):
        return f"{self.type}: {self.body}"


class Logger:
    class LogGroupName(enum.Enum):
        WARNINGS = "warnings"
        ERRORS = "errors"

    def __init__(self):
        self._process_all_task_id = ServerState.objects.first().current_process_all_task_id
        self._mongo_client = MongoClient(settings.DATABASES["default"]["HOST"], settings.DATABASES["default"]["PORT"])
        self._db = self._mongo_client['mantistable']
        self._log_collection = self._db["mantistable_log"]

    def warning(self, log: Log, table_id=None):
        pass
        # TODO: Reinsert logging?
        #self._write_log(log.type, log.body, Logger.LogGroupName.WARNINGS, table_id)

    def error(self, log: Log, table_id=None):
        self._write_log(log.type, log.body, Logger.LogGroupName.ERRORS, table_id)

    def _write_log(self, log_type: str, body: str, group_name: LogGroupName, table_id):
        assert len(log_type) > 0
        assert len(body) > 0
        
        table_data = {}
        if table_id is not None:
            try:
                table = Table.objects.get(id=table_id)
                table_name = table.name
                table_data = {
                    "table_id": table_id,
                    "table_name": table_name,
                }
            except Table.DoesNotExist:
                pass

        data = {
            "type": log_type,
            "body": body,
        }
        data.update(table_data)
        
        if self._log_collection.find({"task_id": self._process_all_task_id}).count():
            self._log_collection.update(
                {"task_id": self._process_all_task_id}, {
                    "$push": {
                        group_name.value: data
                    }
                })
