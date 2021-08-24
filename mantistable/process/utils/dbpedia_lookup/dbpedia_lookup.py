from json import JSONDecodeError

import requests
from requests.exceptions import ConnectionError, Timeout

from app import settings
from mantistable.process.utils.logger.logger import Logger


class DbpediaLookup:
    _local_url = f"http://149.132.176.50:18888/api/search/PrefixSearch"
    _fallback_url = "http://lookup.dbpedia.org/api/search.asmx/PrefixSearch"

    def __init__(self, table_id):
        self.url = DbpediaLookup._local_url
        if settings.DEBUG:
            self.url = DbpediaLookup._fallback_url

        self._table_id = table_id
        self._logger = Logger()

    def get_entities(self, query_string, limit=5):
        results = self.search(query_string, limit)
        entities = {}
        for idx, concept in enumerate(results["results"]):
            label = concept["label"]
            cls = []
            for type_class in concept["classes"]:
                uri = type_class["uri"]

                if "http://dbpedia.org/ontology/" in uri and uri != "http://dbpedia.org/ontology/Agent" and uri != "http://dbpedia.org/ontology/Thing":
                    cls.append(uri[28:])

            if len(cls) > 0:
                entities[label] = cls

        return entities

    def search(self, query_string, limit=5):
        return self.raw_query({
            "QueryClass": "",
            "MaxHits": limit,
            "QueryString": query_string,
        })

    def raw_query(self, params):
        result = self._handle_request(params)
        if result is None:
            return {"results": []}

        try:
            json_result = result.json()
        except JSONDecodeError:
            print("ERROR: Dbpedia lookup bad json result")

            # TODO: dbpedia lookup is bugged, makes way too many logs and make mongo crash
            # self._logger.error(LookupLog().lookup_bad_result(self.url, result.text), self._table_id)
            json_result = {"results": []}

        return json_result

    def _handle_request(self, params):
        try:
            result = requests.get(self.url, params=params, headers={"Accept": "application/json"}, timeout=10)
        except (ConnectionError, Timeout):
            print(f"ERROR: Dbpedia lookup connection error: {self.url} {params}")
            # TODO: dbpedia lookup is bugged, makes way too many logs and make mongo crash
            # self._logger.error(LookupLog().lookup_endpoint_unreachable(self.url), self._table_id)
            return None

        if result.status_code != 200:
            print(f"ERROR: Dbpedia lookup endpoint error: {result.status_code} {result.url}")
            # TODO: dbpedia lookup is bugged, makes way too many logs and make mongo crash
            # self._logger.error(LookupLog().lookup_endpoint_error(result), self._table_id)
            return None

        return result
