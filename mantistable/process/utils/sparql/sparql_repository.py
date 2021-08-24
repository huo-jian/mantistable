import sys

from SPARQLWrapper.SPARQLExceptions import QueryBadFormed

from mantistable.process.utils.logger.logger import Logger
from mantistable.process.utils.sparql.sparql_log import SparqlLog
from mantistable.process.utils.sparql.sparql_manager import DbpediaSparqlManager, WikiDataSparqlManager


class NoSubjectColumnException(Exception):
    pass


class SparqlRepository:
    def __init__(self, table_id, manager):
        self._sparql = manager
        self._table_id = table_id
        self._logger = Logger()

    def _exec_query(self, query):
        try:
            result = self._sparql.get_query_results(query)
        except QueryBadFormed as e:
            print(e.msg, file=sys.stderr)
            self._logger.error(SparqlLog().query_bad_formed(str(e.msg), query), self._table_id)
            return []

        content = result["results"]["bindings"]
        if len(content) == 0:
            self._logger.warning(SparqlLog().empty_result(query), self._table_id)
            return []

        return content


class DbpediaSparqlRepository(SparqlRepository):
    def __init__(self, table_id):
        super().__init__(table_id, DbpediaSparqlManager())

    def get_final_entity(self, text_for_query, cell_type, OR_flag):
        if OR_flag:
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

        query = self._sparql.make_query('''SELECT DISTINCT ?s ?alias ?p ?o WHERE {{
            ?s ?p ?o.
            {{
            {{
               SELECT DISTINCT ?s "None" as ?alias WHERE
               {{
                   ?s rdfs:label ?label.
                   ?s dbo:abstract ?a.
                   ?label <bif:contains> '({text_for_query})'.
                   FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                   FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                   FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
               }} ORDER BY ASC(strlen(str(?s))) LIMIT 50
            }}
            UNION
            {{
               SELECT DISTINCT ?s str(?s2) as ?alias WHERE {{
                      ?s2 dbo:wikiPageRedirects ?s.
                      ?s2 rdfs:label ?label.
                      ?label <bif:contains> '({text_for_query})'.
                      FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                      FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                      FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
               }} ORDER BY ASC(strlen(str(?s))) LIMIT 50
            }}
            }}
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageID')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRevisionID')).
            FILTER(!strstarts(str(?p), 'http://www.w3.org/2002/07/owl#sameAs')).     
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
            FILTER(!strstarts(str(?p), 'http://www.w3.org/ns/prov#wasDerivedFrom')).
            FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/isPrimaryTopicOf')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/property/term')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageExternalLink')).
            FILTER(!strstarts(str(?p), 'http://www.w3.org/2000/01/rdf-schema#comment')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/thumbnail'))
            FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/depiction'))
            FILTER(!strstarts(str(?o), 'http://dbpedia.org/class/yago/')).
            FILTER(!strstarts(str(?o), 'http://www.wikidata.org/entity/')).
            FILTER(!strstarts(str(?o), 'http://www.ontologydesignpatterns.org/ont/dul/')).
            FILTER(!strstarts(str(?o), 'http://www.w3.org/2002/07/owl')).
            FILTER(!strstarts(str(?o), 'http://www.w3.org/2002/07/owl')).
            }}
        ''', {
            "type": cell_type,
            "text_for_query": text_for_query
        })
        print(query)
        return self._exec_query(query)

    def get_final_entity_symmetric(self, text_for_query, cell_type, OR_flag):
        if OR_flag:
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

        query = self._sparql.make_query('''SELECT DISTINCT ?s ?alias ?p ?o WHERE {{
           ?o ?p ?s.
           {{
           {{
              SELECT DISTINCT ?s "None" as ?alias WHERE
              {{
                  ?s rdfs:label ?label.
                  ?s dbo:abstract ?a.
                  ?label <bif:contains> '({text_for_query})'.
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
              }} ORDER BY ASC(strlen(str(?s))) LIMIT 50
           }}
           UNION
           {{
              SELECT DISTINCT ?s str(?s2) as ?alias WHERE {{
                     ?s2 dbo:wikiPageRedirects ?s.
                     ?s2 rdfs:label ?label.
                     ?label <bif:contains> '({text_for_query})'.
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
              }} ORDER BY ASC(strlen(str(?s))) LIMIT 50
           }}
           }}
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageDisambiguates')).
            FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/primaryTopic')).
            }}
        ''', {
            "text_for_query": text_for_query
        })
        print(query)
        return self._exec_query(query)

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

        query = self._sparql.make_query('''SELECT DISTINCT ?s ?alias ?p ?o WHERE {{
            ?s ?p ?o.
            {{
            {{
               SELECT DISTINCT ?s "None" as ?alias WHERE
               {{
                   ?s rdfs:label ?label.
                   ?s a ?type.
                   ?s dbo:abstract ?a.
                   ?label <bif:contains> '({text_for_query})'.
                   FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                   FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                   FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
               }} ORDER BY ASC(strlen(str(?s))) LIMIT 50
            }}
            UNION
            {{
               SELECT DISTINCT ?s str(?s2) as ?alias WHERE {{
                      ?s2 dbo:wikiPageRedirects ?s.
                      ?s2 rdfs:label ?label.
                      ?label <bif:contains> '({text_for_query})'.
                      FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                      FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                      FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
               }} ORDER BY ASC(strlen(str(?s))) LIMIT 50
            }}
            }}
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageID')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRevisionID')).
            FILTER(!strstarts(str(?p), 'http://www.w3.org/2002/07/owl#sameAs')).     
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
            FILTER(!strstarts(str(?p), 'http://www.w3.org/ns/prov#wasDerivedFrom')).
            FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/isPrimaryTopicOf')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/property/term')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageExternalLink')).
            FILTER(!strstarts(str(?p), 'http://www.w3.org/2000/01/rdf-schema#comment')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/thumbnail'))
            FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/depiction'))
            FILTER(!strstarts(str(?o), 'http://dbpedia.org/class/yago/')).
            FILTER(!strstarts(str(?o), 'http://www.wikidata.org/entity/')).
            FILTER(!strstarts(str(?o), 'http://www.ontologydesignpatterns.org/ont/dul/')).
            FILTER(!strstarts(str(?o), 'http://www.w3.org/2002/07/owl')).
            FILTER(!strstarts(str(?o), 'http://www.w3.org/2002/07/owl')).
            }}
        ''', {
            "text_for_query": text_for_query,
        })

        print(query)
        return self._exec_query(query)

    def get_entities_symmetric(self, text_for_query, OR=False):
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

        query = self._sparql.make_query('''SELECT DISTINCT ?s ?alias ?p ?o WHERE {{
           ?o ?p ?s.
           {{
           {{
              SELECT DISTINCT ?s "None" as ?alias WHERE
              {{
                  ?s rdfs:label ?label.
                  ?s a ?type.
                  ?s dbo:abstract ?a.
                  ?label <bif:contains> '({text_for_query})'.
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
              }}  ORDER BY ASC(strlen(str(?s))) LIMIT 50
           }}
           UNION
           {{
              SELECT DISTINCT ?s str(?s2) as ?alias WHERE {{
                     ?s2 dbo:wikiPageRedirects ?s.
                     ?s2 rdfs:label ?label.
                     ?label <bif:contains> '({text_for_query})'.
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
              }} ORDER BY ASC(strlen(str(?s))) LIMIT 50
           }}
           }}
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
            FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageDisambiguates')).
            FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/primaryTopic')).
            }}
        ''', {
            "text_for_query": text_for_query,
        })

        print(query)
        return self._exec_query(query)

    def get_person_entities(self, person_prefix, person_surname):
        query = self._sparql.make_query('''SELECT DISTINCT ?s ?alias ?p ?o WHERE {{
           ?s ?p ?o.
           {{
           {{
              SELECT DISTINCT ?s "None" as ?alias ?label WHERE
              {{
                  ?s rdfs:label ?label.
                  ?s a dbo:Person.
                  ?s dbo:abstract ?a.
                  ?label <bif:contains> '("{person_surname}")'.
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                  FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
              }} ORDER BY ASC(strlen(str(?s)))
           }}
           UNION
           {{
              SELECT DISTINCT ?s str(?s2) as ?alias ?label WHERE {{
                     ?s2 dbo:wikiPageRedirects ?s.
                     ?s2 rdfs:label ?label.
                     ?s2 a dbo:Person.
                     ?label <bif:contains> '("{person_surname}")'.
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                     FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
              }} ORDER BY ASC(strlen(str(?s)))
           }}
           }}
           FILTER (strstarts(lcase(?label), "{person_prefix}")).
           FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageID')).
           FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRevisionID')).
           FILTER(!strstarts(str(?p), 'http://www.w3.org/2002/07/owl#sameAs')).
           FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
           FILTER(!strstarts(str(?p), 'http://www.w3.org/ns/prov#wasDerivedFrom')).
           FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/isPrimaryTopicOf')).
           FILTER(!strstarts(str(?p), 'http://dbpedia.org/property/term')).
           FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageExternalLink')).
           FILTER(!strstarts(str(?p), 'http://www.w3.org/2000/01/rdf-schema#comment')).
           FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/thumbnail'))
           FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/depiction'))
           FILTER(!strstarts(str(?o), 'http://dbpedia.org/class/yago/')).
           FILTER(!strstarts(str(?o), 'http://www.wikidata.org/entity/')).
           FILTER(!strstarts(str(?o), 'http://www.ontologydesignpatterns.org/ont/dul/')).
           FILTER(!strstarts(str(?o), 'http://www.w3.org/2002/07/owl')).
           FILTER(!strstarts(str(?o), 'http://www.w3.org/2002/07/owl')).
           }} LIMIT 30000
                ''', {
            "person_prefix": person_prefix,
            "person_surname": person_surname,
        })

        print(query)
        return self._exec_query(query)

    def get_person_entities_symmetric(self, person_prefix, person_surname):
        query = self._sparql.make_query('''SELECT DISTINCT ?s ?alias ?p ?o WHERE {{
          ?o ?p ?s.
          {{
          {{
             SELECT DISTINCT ?s "None" as ?alias ?label WHERE
             {{
                 ?s rdfs:label ?label.
                 ?s a dbo:Person.
                 ?s dbo:abstract ?a.
                 ?label <bif:contains> '("{person_surname}")'.
                 FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                 FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                 FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
             }} ORDER BY ASC(strlen(str(?s)))
          }}
          UNION
          {{
             SELECT DISTINCT ?s str(?s2) as ?alias ?label WHERE {{
                    ?s2 dbo:wikiPageRedirects ?s.
                    ?s2 rdfs:label ?label.
                    ?s2 a dbo:Person.
                    ?label <bif:contains> '("{person_surname}")'.
                    FILTER (!strstarts(str(?s), 'http://dbpedia.org/resource/Category:')).
                    FILTER (!strstarts(str(?s), 'http://dbpedia.org/property/')).
                    FILTER (!strstarts(str(?s), 'http://dbpedia.org/ontology/')).
             }} ORDER BY ASC(strlen(str(?s)))
          }}
          }}
          FILTER (strstarts(lcase(?label), "{person_prefix}")).
          FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageRedirects')).
          FILTER(!strstarts(str(?p), 'http://dbpedia.org/ontology/wikiPageDisambiguates')).
          FILTER(!strstarts(str(?p), 'http://xmlns.com/foaf/0.1/primaryTopic')).
          }}
          LIMIT(30000)
        ''', {
            "person_prefix": person_prefix,
            "person_surname": person_surname,
        })

        print(query)
        return self._exec_query(query)

    def get_type(self, winning_entities):
        """
        It returns the list of classes relatives about the winning entity
        :param winning_entities:
        :return:
        """
        query = self._sparql.make_query('''SELECT DISTINCT str(?type) as ?type
            WHERE {{
              {{
                <{winningEntities}> a ?type.
                FILTER(!strstarts(str(?type), 'http://dbpedia.org/class/yago/Wikicat')).
              }}
            }}
        ''', {
            "winningEntities": winning_entities
        })

        return self._exec_query(query)

    """
        RELATIONSHIP ANNOTATION QUERY
    """
    def get_NE_rel(self, winning_entities, subject_entity, subject_concept, col_concept_general, col_concept_specific):
        if len(subject_concept.strip()) == 0:
            raise NoSubjectColumnException()

        if len(col_concept_general.strip()) == 0 or len(col_concept_specific.strip()) == 0:
            return []

        query = self._sparql.make_query('''
        SELECT DISTINCT ?p str(?l) as ?l
             WHERE {{
              {{
                ?s ?p ?o.
                ?o rdfs:label ?l.
                VALUES ?s {{{subjectEntity}}}.
                VALUES ?o {{{winningEntities}}}.
              }}
             FILTER(lang(?l) = "en")
             FILTER (strstarts(str(?p), str("http://dbpedia.org/ontology/"))).
             }}
        ''', {
            "winningEntities": winning_entities,
            "subjectEntity": subject_entity,
        })

        print(query)

        return self._exec_query(query)

    def get_LIT_rel(self, winning_entities, subject_concept, col_data_type):
        query = self._sparql.make_query('''SELECT DISTINCT ?p ?o
            WHERE {{
              {{
                ?s ?p ?o.
                VALUES ?s {{{winningEntities}}}. 
                ?s a <{subjectConcept}> .
                FILTER (strstarts(str(?p), str("http://dbpedia.org/ontology/")) || strstarts(str(?p), str("http://www.georss.org/georss/point"))).
                FILTER (!strstarts(str(?p), "http://dbpedia.org/ontology/wikiPageRevisionID")).
                FILTER (!strstarts(str(?p), "http://dbpedia.org/ontology/wikiPageID")).
                FILTER (isURI(?o) || langmatches(lang(?o), "en") || langmatches(lang(?o), ""))
              }} 
            }}
        ''', {
            "winningEntities": winning_entities,
            "subjectConcept": subject_concept,
            #"colDataType": col_data_type       # FILTER ({colDataType}(?o)).
        })

        print(query)
        return self._exec_query(query)

    def test_q(self):
        query = self._sparql.make_query('''PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?label
                WHERE {{ <http://dbpedia.org/resource/Asturias> rdfs:label ?label }} LIMIT 3
                ''', {})
        return self._exec_query(query)


# TODO: Deprecated
class WikiDataSparqlRepository(SparqlRepository):
    def __init__(self, table_id):
        super().__init__(table_id, WikiDataSparqlManager())

    def test_q(self):
        query = self._sparql.make_query('''SELECT ?item ?itemLabel 
            WHERE 
            {{
              ?item wdt:P31 wd:Q146.
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
            }} LIMIT 3
        ''', {})

        return self._exec_query(query)
