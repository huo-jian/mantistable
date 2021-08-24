from enum import Enum

from celery.result import GroupResult
from django.db import models
from django.utils.timezone import now
from djongo.models.json import JSONField

import json


# NOTE: MongoDB does not allow '.' character in the document's keys (to avoid nasty NoSQL injection attacks). PyMongo
# enforce this rule by checking keys prior to insertion. To circumvent this limitation/security I propose a classic
# encode/decode solution. Prior to insertion dot character '.' is substituted with "\u002e" (the string,
# not the character). Any time the field is requested the string "\u002e" is substituted with the '.' character.
# NOTE: It should work seamlessly (you can use the '.' character) with any query operation like Model.objects.filter(
# ), but I haven't tested it yet...
class SafeJSONField(JSONField):
    translation_map = {
        "\\": "\\u005C",
        ".": "\\u002e",
        "$": "\\u0024",
    }
    reversed_translation_map = {v: k for k, v in translation_map.items()}

    def from_db_value(self, value, expr, conn):
        if value is None:
            return value

        return self.__decode(value)

    def to_python(self, value):
        if value is None:
            return value

        return self.__decode(value)

    def get_prep_value(self, value):
        return self.__encode(value)

    def __update_keys(self, json_data, func):
        if isinstance(json_data, list):
            array = []
            for item in json_data:
                array.append(self.__update_keys(item, func))

            return array

        if isinstance(json_data, dict):
            d = {}
            for k in json_data.keys():
                d[func(k)] = self.__update_keys(json_data[k], func)

            return d

        return json_data

    def __encode(self, json_data):
        return self.__update_keys(json_data, lambda k: self.__translate(k, SafeJSONField.translation_map))

    def __decode(self, json_data):
        return self.__update_keys(json_data, lambda k: self.__translate(k, SafeJSONField.reversed_translation_map))

    def __translate(self, key, translation_map):
        for mongo_chr in translation_map:
            key = str(key).replace(mongo_chr, translation_map[mongo_chr])

        return key

    # Json pretty print
    def __str__(self):
        return json.dumps(super.__str__(), indent=4)


class GoldStandardsEnum(Enum):
    NONE = 'NONE'
    CHALLENGE = 'CHALLENGE'
    Limaye200 = 'Limaye200'
    T2D = 'T2D'
    limaye = 'limaye'
    semantification = 'semantification'
    semr1 = 'semr1'
    semr2 = 'semr2'
    semr3 = 'semr3'
    semr4 = 'semr4'
    t2 = 't2'
    wiki = 'wiki'


class GlobalStatusEnum(Enum):
    TODO = 'TODO'
    DOING = 'DOING'
    DONE = 'DONE'


class PhasesEnum(Enum):
    DATA_PREPARATION = {'key': 'dataPreparation', 'name': 'Data Preparation'}
    COLUMN_ANALYSIS = {'key': 'columnsAnalysis', 'name': 'Column Analysis'}
    # CONCEPT_ANNOTATION = {'key': 'conceptDatatypeAnnotation', 'name': 'Concept and Datatype Annotation'}
    # PREDICATE_ANNOTATION = {'key': 'relationshipsAnnotation', 'name': 'Predicate Annotation'}
    # ENTITY_LINKING = {'key': 'entityLinking', 'name': 'Entity Linking'}


class Table(models.Model):
    # TODO: I would like to remove these, but templates use them...
    DATA_PREPARATION = 'Data Preparation'
    DATA_PREPARATION_KEY = 'dataPreparation'
    COLUMN_ANALYSIS = 'Column Analysis'
    COLUMN_ANALYSIS_KEY = 'columnsAnalysis'
    # CONCEPT_ANNOTATION = 'Concept and Datatype Annotation'
    # CONCEPT_ANNOTATION_KEY = 'conceptDatatypeAnnotation'
    # PREDICATE_ANNOTATION = 'Predicate Annotation'
    # PREDICATE_ANNOTATION_KEY = 'relationshipsAnnotation'
    # ENTITY_LINKING = 'Entity Linking'
    # ENTITY_LINKING_KEY = 'entityLinking'

    name = models.CharField(max_length=200)
    gs_type = models.CharField(max_length=10, choices=[(tag.name, tag.value) for tag in GoldStandardsEnum],
                               default=GoldStandardsEnum.NONE.value)
    file_name = models.TextField()
    global_status = models.CharField(max_length=10, choices=[(tag.name, tag.value) for tag in GlobalStatusEnum],
                                     default=GlobalStatusEnum.TODO.value)
    process = JSONField()
    pub_date = models.DateTimeField(default=now)
    last_edit_date = models.DateTimeField(default=now)
    header = JSONField()
    num_cols = models.PositiveIntegerField(default=0)
    num_rows = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class TableData(models.Model):
    table = models.OneToOneField(Table, on_delete=models.CASCADE)
    header = SafeJSONField()
    data_original = SafeJSONField()
    data = JSONField()


class InfoTable(models.Model):
    table = models.OneToOneField(Table, on_delete=models.CASCADE)
    table_name = models.CharField(max_length=200)
    lit_cols = JSONField()
    ne_cols = JSONField()
    no_ann_cols = JSONField()
    subject_col = models.PositiveIntegerField(default=0)
    subject_cols_paper = JSONField(default=[])


class Linking(models.Model):
    table = models.OneToOneField(Table, on_delete=models.CASCADE)
    table_name = models.CharField(max_length=200)
    data = JSONField()
    """
    [
        0: [        # column
            0: {    # row
                "value_for_query": "" 
                "linking_entities": [] 
            }
        ]
    ]    
    """


class Annotation(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    cols_we = SafeJSONField()


class SparqlEndpoint(models.Model):
    name = models.CharField(max_length=200)
    url = models.CharField(max_length=200)
    priority = models.PositiveIntegerField(default=0)
    error = models.BooleanField()
    checked_date = models.DateTimeField(default=now)

    @classmethod
    def reset(cls):
        SparqlEndpoint.objects.all().update(error=False)


class ServerState(models.Model):
    current_process_all_task_id = models.CharField(max_length=200, default="", blank=True)
    current_tables_in_progress = models.PositiveIntegerField(default=0)
    loaded_t2d = models.BooleanField(default=False)
    loaded_limaye200 = models.BooleanField(default=False)
    loaded_challenge = models.BooleanField(default=False)
    loaded_limaye = models.BooleanField(default=False)
    loaded_semantification = models.BooleanField(default=False)
    loaded_semr1 = models.BooleanField(default=False)
    loaded_semr2 = models.BooleanField(default=False)
    loaded_semr3 = models.BooleanField(default=False)
    loaded_semr4 = models.BooleanField(default=False)
    loaded_wiki = models.BooleanField(default=False)
    loaded_t2 = models.BooleanField(default=False)

    def reset_loaded_gs(self):
        self.loaded_t2d = False
        self.loaded_limaye200 = False
        self.loaded_challenge = False
        self.loaded_limaye = False
        self.loaded_semantification = False
        self.loaded_semr1 = False
        self.loaded_semr2 = False
        self.loaded_semr3 = False
        self.loaded_semr4 = False
        self.loaded_wiki = False
        self.loaded_t2 = False

    def save(self, *args, **kwargs):
        states = ServerState.objects.order_by('id')
        if ServerState.objects.count() == 2:
            states[0].delete()

        super(ServerState, self).save(*args, **kwargs)


class Log(models.Model):
    process_started = models.DateTimeField()
    task_id = models.CharField(max_length=200)
    sparql_endpoint = models.CharField(max_length=200, blank=True, default="")
    warnings = JSONField(default=[])
    errors = JSONField(default=[])

    def save(self, *args, **kwargs):
        if len(self.sparql_endpoint) == 0:
            endpoints = SparqlEndpoint.objects.order_by('priority').filter(error=False)
            if len(endpoints) > 0:
                self.sparql_endpoint = endpoints[0].url

        super(Log, self).save(*args, **kwargs)
