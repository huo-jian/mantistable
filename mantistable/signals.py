from django.dispatch import receiver
from django.db.models.signals import post_migrate
from mantistable.models import ServerState, SparqlEndpoint
import pymongo
from pymongo import MongoClient
from app import settings

@receiver(post_migrate)
def on_init_db(**kwargs):
    def _init_server_state():
        count = ServerState.objects.count()
        if count == 0:
            ServerState().save()

    def _init_sparql_endpoints():
        count = SparqlEndpoint.objects.count()
        if count == 0:
            SparqlEndpoint(
                name="dbpedia-default",
                url="https://dbpedia.org/sparql",
                priority=10,  # Low priority
                error=False,
            ).save()

            SparqlEndpoint(
                name="titan-default",
                url="http://149.132.176.50:8890/sparql",
                priority=1,
                error=False,
            ).save()

            if not settings.DEBUG:
                SparqlEndpoint(
                    name="local-sparql",
                    url=f"http://{settings.EXTERNAL_IP}:8890/sparql",
                    priority=0,
                    error=False,
                ).save()
            
    def _init_indexes():
        mongo_client = MongoClient(settings.DATABASES["default"]["HOST"], settings.DATABASES["default"]["PORT"])
        db = mongo_client['mantistable']
        annotation = db["mantistable_annotation"]
        info_table = db["mantistable_infotable"]
        
        annotation.create_index([("table_id", pymongo.DESCENDING)], background=False)
        info_table.create_index([("table_id", pymongo.DESCENDING)], background=False)
        annotation.create_index([("id", pymongo.DESCENDING)], background=False)
        info_table.create_index([("id", pymongo.DESCENDING)], background=False)

    _init_server_state()
    _init_sparql_endpoints()
    _init_indexes()

    post_migrate.disconnect(on_init_db)
