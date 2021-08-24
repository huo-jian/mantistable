import enum

import requests

from mantistable.process.utils.logger.logger import Log


class LookupLog:
    class LookupLogType(enum.Enum):
        LOOKUP_ENDPOINT_UNREACHABLE = "lookup_endpoint_unreachable"
        LOOKUP_ENDPOINT_ERROR = "lookup_endpoint_error"
        LOOKUP_BAD_RESULT = "lookup_bad_result"

    def lookup_endpoint_unreachable(self, url):
        return Log(
            LookupLog.LookupLogType.LOOKUP_ENDPOINT_UNREACHABLE.value,
            {
                "error": "Dbpedia Lookup endpoint was unreachable",
                "url": url,
            }
        )

    def lookup_endpoint_error(self, response: requests.Response):
        return Log(
            LookupLog.LookupLogType.LOOKUP_ENDPOINT_UNREACHABLE.value,
            {
                "error": "Dbpedia Lookup endpoint was unreachable",
                "url": response.url,
                "status_code": response.status_code,
            }
        )

    def lookup_bad_result(self, url, data):
        return Log(
            LookupLog.LookupLogType.LOOKUP_BAD_RESULT.value,
            {
                "error": "Dbpedia Lookup endpoint sent bad result",
                "url": url,
                "response": data,
            }
        )