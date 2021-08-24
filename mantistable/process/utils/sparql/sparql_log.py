import enum

from mantistable.models import SparqlEndpoint
from mantistable.process.utils.logger.logger import Log


class SparqlLog:
    class SparqlLogType(enum.Enum):
        EMPTY_RESULT = "sparql_empty_result"
        QUERY_BAD_FORMED = "sparql_query_bad_formed"
        NO_SPARQL_ENDPOINT = "sparql_no_endpoint"

    def empty_result(self, query):
        return Log(
            SparqlLog.SparqlLogType.EMPTY_RESULT.value,
            {
                "query": query
            }
        )

    def query_bad_formed(self, error_message, query):
        return Log(
            SparqlLog.SparqlLogType.QUERY_BAD_FORMED.value,
            {
                "error": error_message,
                "query": query
            }
        )

    def no_sparql_endpoint(self):
        endpoints = SparqlEndpoint.objects.order_by("priority")
        return Log(
            SparqlLog.SparqlLogType.NO_SPARQL_ENDPOINT.value,
            {
                "error": "No sparql endpoint available",
                "endpoints": [
                    {
                        "name": endpoint.name,
                        "url": endpoint.url,
                        "priority": endpoint.priority,
                    }
                    for endpoint in endpoints
                ]
            }
        )
