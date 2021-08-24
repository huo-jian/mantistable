import sys
from typing import Dict
from urllib import error
import requests

from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE, SPARQLExceptions
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed


def alt_query_sparql(query, endpoint, timeout=30000):
    params = {
        "default-graph-uri": "http://dbpedia.org",
        "query": query,
        "format": "application/text/plain",
        "timeout": timeout
    }
    result = requests.get(endpoint, params=params)
    
    if result.status_code != 200:
        return None
   
    return result.text

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

    def get_query_results(self, query, res_format=JSON):
        """
        Execute sparql query
        :param query:
        :raises QueryBadFormed if query is invalid
        :return json result:
        """

        if res_format == JSON:
            return {
                "results": {
                    "bindings": []
                }
            }
        else:
            return ""


class DbpediaSparqlManager(SparqlManager):
    def get_query_results(self, query, res_format=JSON):
        return self._get_query_results_impl(query, res_format)

    def _get_query_results_impl(self, query, res_format=JSON):
        # endpoint = "http://149.132.176.50:8890/sparql"
        endpoint = "https://dbpedia.org/sparql"
        
        sparql = SPARQLWrapper(endpoint)
        sparql.addDefaultGraph("http://dbpedia.org")
        sparql.setQuery(query)
        
        try:
            res = alt_query_sparql(query, endpoint, 100000)
        except Exception as e:
            print(str(e))
            raise QueryBadFormed()
        
        if res is None:
            raise QueryBadFormed()
        
        return res
        """
        try:
            sparql.setReturnFormat(res_format)
            return sparql.query().convert().decode("utf-8")
        except (error.HTTPError, SPARQLExceptions.EndPointInternalError, SPARQLExceptions.EndPointNotFound,
                error.URLError) as e:
            
            if "Free-text expression" not in str(e) and "The estimated execution time" not in str(e):
                print(str(e))
                raise QueryBadFormed()
        """
                


class NoSubjectColumnException(Exception):
    pass


class SparqlRepository:
    def __init__(self, table_id, manager):
        self._sparql = manager
        self._table_id = table_id

    def _exec_query(self, query, res_format=JSON):
        try:
            result = self._sparql.get_query_results(query, res_format)
        except QueryBadFormed as e:
            print(e.msg, file=sys.stderr)

            raise QueryBadFormed

        if res_format == JSON:
            content = result["results"]["bindings"]
        else:
            content = result

        if len(content) == 0:
            if res_format == JSON:
                return []
            else:
                return ""

        return content


class DbpediaSparqlRepository(SparqlRepository):
    def __init__(self, table_id):
        super().__init__(table_id, DbpediaSparqlManager())

    def get_candidables_data(self, cell_value, query):
        query = self._sparql.make_query('''
            CONSTRUCT {{
              ?s ?p ?o.
            }} WHERE {{
             {{
               {{
                 ?s ?p ?o.
                 ?s rdfs:label ?label.
                 ?label <bif:contains> '("{cell_value}")'.
               }} UNION {{
                 ?s ?p ?o.
                 ?s rdfs:label ?label.
                 ?label <bif:contains> '({query})'.
               }} UNION {{
                 OPTIONAL {{
                   ?altName rdfs:label ?lab.
                   ?lab <bif:contains> '({query})'.
                   ?altName dbo:wikiPageRedirects ?s.
                   ?s ?p ?o.
                 }}.
               }}
             }} UNION {{
               ?o ?p ?s.
               ?s rdfs:label ?label.
               ?label <bif:contains> '({query})'.
             }}
            
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageID')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRevisionID')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/2002/07/owl#sameAs')).     
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/ns/prov#wasDerivedFrom')).
             FILTER (!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/isPrimaryTopicOf')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/2000/01/rdf-schema#comment')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/abstract')).
             FILTER (!strstarts(str(?o), 'http://dbpedia.org/class/yago/')).
            }}
        ''', {
            "cell_value": cell_value,
            "query": query
        })

        # print(query)
        return self._exec_query(query, res_format=TURTLE)

    def get_candidables_data_raw(self, raw_value):
        query = self._sparql.make_query('''
            CONSTRUCT {{
              ?s ?p ?o.
            }} WHERE {{
             {{
                ?s ?p ?o.
                {{
                   ?s rdfs:label ?label.
                   ?label <bif:contains> '("{raw_value}")'.
                }} UNION {{
                   ?s foaf:name ?name.
                   ?name <bif:contains> '("{raw_value}")'.
                }}
             }}

             FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageID')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRevisionID')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/2002/07/owl#sameAs')).     
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/ns/prov#wasDerivedFrom')).
             FILTER (!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/isPrimaryTopicOf')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/2000/01/rdf-schema#comment')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/abstract')).
             FILTER (!strstarts(str(?o), 'http://dbpedia.org/class/yago/')).
            }}
        ''', {
            "raw_value": raw_value,
        })

        # print(query)
        return self._exec_query(query, res_format=TURTLE)

    def get_person_candidables_rdf(self, person_prefix, person_surname):
        query = self._sparql.make_query('''
            CONSTRUCT {{
              ?s ?p ?o.
            }} WHERE {{
             {{
               {{
                 ?s ?p ?o.
                 ?s rdfs:label ?label.
                 ?label <bif:contains> '("{person_surname}")'.
               }} UNION {{
                 OPTIONAL {{
                   ?altName rdfs:label ?label.
                   ?label <bif:contains> '("{person_surname}")'.
                   ?altName dbo:wikiPageRedirects ?s.
                   ?s ?p ?o.
                 }}.
               }}
             }} UNION {{
               ?o ?p ?s.
               ?s rdfs:label ?label.
               ?label <bif:contains> '("{person_surname}")'.
             }}
             FILTER (strstarts(lcase(?label), "{person_prefix}"))
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
             FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageID')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRevisionID')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/2002/07/owl#sameAs')).     
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/ns/prov#wasDerivedFrom')).
             FILTER (!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/isPrimaryTopicOf')).
             FILTER (!strstarts(str(?p), 'http://www.w3.org/2000/01/rdf-schema#comment')).
             FILTER (!strstarts(str(?p), 'http://dbpedia.org/ontology/abstract')).
             FILTER (!strstarts(str(?o), 'http://dbpedia.org/class/yago/')).
            }}
        ''', {
            "person_prefix": person_prefix,
            "person_surname": person_surname,
        })

        # print(query)
        return self._exec_query(query, res_format=TURTLE)



