import sys
from typing import Dict
from urllib import error

from SPARQLWrapper import SPARQLWrapper, JSON, TURTLE, SPARQLExceptions
from SPARQLWrapper.SPARQLExceptions import QueryBadFormed


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
        #sparql = SPARQLWrapper("http://149.132.176.50:8890/sparql")
        sparql = SPARQLWrapper("https://dbpedia.org/sparql")
        sparql.addDefaultGraph("http://dbpedia.org")
        sparql.setQuery(query)

        try:
            sparql.setReturnFormat(res_format)
            return sparql.query().convert()
        except (error.HTTPError, SPARQLExceptions.EndPointInternalError, SPARQLExceptions.EndPointNotFound,
                error.URLError) as e:
            if "Free-text expression" not in str(e) and "The estimated execution time" not in str(e):
                print(str(e))
                raise QueryBadFormed()


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

    def get_entities(self, text_for_query, OR=False):
        if text_for_query == "":
            return []

        if OR:
            text_for_query = text_for_query.split(' ')
            tokens = list(set(list(filter(lambda item: len(item) > 3, text_for_query))))
            tokens.sort(key=len, reverse=True)
            tokens = list(map(lambda item: f'"{item}"', tokens))

            if len(tokens) == 0:
                return []
            if len(tokens) > 1:
                text_for_query = tokens[0] + ' OR ' + tokens[1]
            else:
                text_for_query = tokens[0]

        query = self._sparql.make_query('''SELECT DISTINCT ?s ?alias str(?a) as ?abstract WHERE
            {{
            {{
               SELECT DISTINCT ?s ?a ?type "None" as ?alias str(?label) as ?label WHERE
               {{
                   ?s rdfs:label ?label.
                   ?s a ?type.
                   ?s dbo:abstract ?a.
                   ?label <bif:contains> '({text_for_query})'.
               }}
            }}
            UNION
            {{
               SELECT ?s ?a ?type str(?s2) as ?alias str(?label) as ?label WHERE
               {{
                     ?s dbo:wikiPageRedirects ?s2.
                     ?s2 dbo:abstract ?a.
                     ?s2 a ?type.
                   {{
                   SELECT ?s str(?label) as ?label WHERE {{
                     ?s dbo:wikiPageRedirects ?s2.
                     ?s rdfs:label ?label.
                     ?label <bif:contains> '({text_for_query})'.
                   }}
               }}
               }}
            }}
            FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
            FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
            FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
            FILTER (lang(?a) = 'en')
            }} 
            LIMIT 50
        ''', {
            "text_for_query": text_for_query,
        })

        # print(query)
        return self._exec_query(query, JSON)

    def get_person_entities(self, person_prefix, person_surname):
        query = self._sparql.make_query('''SELECT ?s ?alias str(?a) as ?abstract WHERE
                {{
                {{
                  SELECT DISTINCT ?s ?a "None" as ?alias ?label WHERE
                  {{
                    ?s rdfs:label ?label.
                    ?s a dbo:Person.
                    ?s dbo:abstract ?a.
                    ?label <bif:contains> '("{person_surname}")'.
                  }}
                }}
                UNION
                {{
                  SELECT ?s ?a str(?s2) as ?alias ?label WHERE
                  {{
                        ?s dbo:wikiPageRedirects ?s2.
                        ?s2 dbo:abstract ?a.
                        ?s2 a dbo:Person.
                      {{
                      SELECT ?s ?label WHERE {{
                        ?s dbo:wikiPageRedirects ?s2.
                        ?s rdfs:label ?label.
                        ?label <bif:contains> '("{person_surname}")'.
                      }}
                  }}
                  }}
                }}
                FILTER(strstarts(lcase(?label), "{person_prefix}"))
                FILTER(strends(lcase(?label), "{person_surname}"))
                FILTER(!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                FILTER(!strstarts(str(?s), 'http://dbpedia.org/property/')).
                FILTER(!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
                FILTER(lang(?a) = 'en')
                }}
        ''', {
            "person_prefix": person_prefix,
            "person_surname": person_surname,
        })

        # print(query)
        return self._exec_query(query, JSON)

    def get_resource_rdf(self, resource_uri):
        query = self._sparql.make_query('''
            CONSTRUCT {{
                ?s ?p ?o.
            }} WHERE {{
                ?s ?p ?o.
                FILTER ( ?s = <{resource_uri}> ).
                FILTER ( ?p != <http://dbpedia.org/ontology/abstract> ).
                FILTER ( ?p != rdfs:comment ).
            }}
        ''', {
            "resource_uri": resource_uri
        })

        # print(query)
        return self._exec_query(query, res_format=TURTLE)

    def get_candidables_data(self, query):
        query = self._sparql.make_query('''
            CONSTRUCT {{
              ?s ?p ?o.
            }} WHERE {{
             {{
               {{
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
            ORDER BY ASC(strlen(?label))
        ''', {
            "query": query
        })

        # print(query)
        return self._exec_query(query, res_format=TURTLE).decode("utf-8")

    def get_person_candidables_rdf(self, person_prefix, person_surname):
        query = self._sparql.make_query('''
            CONSTRUCT {{
              ?s ?p ?o.
            }} WHERE {{
             {{
               {{
                 ?s ?p ?o.
                 ?s rdfs:label ?label.
                 ?s a dbo:Person.
                 ?label <bif:contains> '("{person_surname}")'.
               }} UNION {{
                 OPTIONAL {{
                   ?altName rdfs:label ?label.
                   ?label <bif:contains> '("{person_surname}")'.
                   ?altName dbo:wikiPageRedirects ?s.
                   ?s ?p ?o.
                   ?s a dbo:Person.
                 }}.
               }}
             }} UNION {{
               ?o ?p ?s.
               ?s rdfs:label ?label.
               ?s a dbo:Person.
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
            ORDER BY ASC(strlen(?label))
        ''', {
            "person_prefix": person_prefix,
            "person_surname": person_surname,
        })

        # print(query)
        return self._exec_query(query, res_format=TURTLE).decode("utf-8")



