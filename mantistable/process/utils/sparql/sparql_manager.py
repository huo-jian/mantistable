from datetime import datetime
from typing import Dict
from urllib import error

from SPARQLWrapper import SPARQLWrapper, JSON, SPARQLExceptions
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed

from mantistable.models import SparqlEndpoint
from mantistable.process.utils.logger.logger import Logger
from mantistable.process.utils.sparql.sparql_log import SparqlLog


class NoSparqlEndpointAvailableException(Exception):
    pass


class SparqlManager:
    def make_query(self, query, data: Dict):
        """
        Apply parameters in query of the form {<name>}.
        Example: make_query("START QUERY {param1} END QUERY", {"param1": 123})
        :param query:
        :param data:
        :return formatted query:
        """
        return query.format_map(data)

    def get_query_results(self, query):
        """
        Execute sparql query
        :param query:
        :raises QueryBadFormed if query is invalid
        :return json result:
        """
        return {
            "results": {
                "bindings": []
            }
        }


class DbpediaSparqlManager(SparqlManager):
    def get_query_results(self, query):
        return self._get_query_results_impl(query, 0)

    def _get_query_results_impl(self, query, recursion_level=0):
        assert (recursion_level >= 0)

        if recursion_level > 5:  # TODO: Magic numbers are not good!
            return super().get_query_results(query)

        endpoint = self._get_endpoint()
        if endpoint is None:
            SparqlEndpoint.reset()
            Logger().error(SparqlLog().no_sparql_endpoint())
            raise NoSparqlEndpointAvailableException()

        print('ENDPOINT IN USE: ' + endpoint.name)

        sparql = SPARQLWrapper(endpoint.url)
        sparql.addDefaultGraph("http://dbpedia.org")
        sparql.setQuery(query)

        try:
            sparql.setReturnFormat(JSON)
            return sparql.query().convert()
        except (error.HTTPError, SPARQLExceptions.EndPointInternalError, SPARQLExceptions.EndPointNotFound,
                error.URLError) as e:
            print(f'ENDPOINT IN ERROR: {endpoint.name} {e}')
            if "Free-text expression" not in str(e) and "The estimated execution time" not in str(e):
                print('CHECK ENDPOINTS...')
                self._check_endpoint()

                # TODO: Return result (but carefull because could lead to nasty bugs...)
                return self._get_query_results_impl(query, recursion_level + 1)
            else:
                raise QueryBadFormed()

    def _get_endpoint(self):
        """
        :return Higher priority endpoint candidate or None:
        """
        endpoints = SparqlEndpoint.objects.order_by('priority').filter(error=False)

        for endpoint in endpoints:
            return endpoint

    def _check_endpoint(self):
        endpoints = SparqlEndpoint.objects.order_by('priority')

        for endpoint in endpoints:
            sparql = SPARQLWrapper(endpoint.url)
            sparql.setQuery("""
                ASK WHERE {
                    <http://dbpedia.org/resource/Asturias> rdfs:label "Asturias"@es
                }
            """)

            try:
                sparql.setReturnFormat(JSON)
                sparql.query().convert()
                endpoint.error = False
                endpoint.save()
            except (error.HTTPError, SPARQLExceptions.EndPointInternalError, SPARQLExceptions.EndPointNotFound,
                    error.URLError) as e:
                print('ENDPOINT IN ERROR: ' + endpoint.name)
                endpoint.error = True
                endpoint.checked_date = datetime.now()
                endpoint.save()


# TODO: Deprecated
class WikiDataSparqlManager(SparqlManager):
    wikidata_uri = "https://query.wikidata.org/sparql"

    def get_query_results(self, query):
        sparql = SPARQLWrapper(self.wikidata_uri)
        sparql.addDefaultGraph("http://www.bigdata.com/rdf/gas#")
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)

        try:
            return sparql.query().convert()
        except (error.HTTPError, SPARQLExceptions.EndPointInternalError, SPARQLExceptions.EndPointNotFound,
                error.URLError) as e:
            print(f'ENDPOINT IN ERROR: wikidata {e}')
            if "Free-text expression" not in str(e) and "The estimated execution time" not in str(e):
                pass
            else:
                raise QueryBadFormed()
