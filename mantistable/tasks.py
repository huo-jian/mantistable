from datetime import datetime, timedelta

import traceback

from app.celery import app
from mantistable.models import ServerState, Table, GlobalStatusEnum, PhasesEnum
from mantistable.process.columns_analysis.columns_classification import info_tables
from mantistable.process.columns_analysis.subject_column_detection.sub_detection import SubDetection
from mantistable.process.concept_datatype_annotation.entities import get_entities
from mantistable.process.data_preparation.normalization.normalize import normalize
from mantistable.process.entity_linking.linking import get_entity_linking
from mantistable.process.predicate_annotation.relationships import get_NE_relationships
from mantistable.process.utils.publisher.internal import Internal
from mantistable.process.utils.sparql.sparql_manager import NoSparqlEndpointAvailableException
from mantistable.process.utils.sparql.sparql_repository import NoSubjectColumnException


def mantis_task(phase_key):
    def inner(task):
        def wrapper(table_id, *args, **kwargs):
            # PHASE DOING
            table = Table.objects.get(id=table_id)
            table.process["phases"][phase_key]["status"] = GlobalStatusEnum.DOING.value
            table.global_status = GlobalStatusEnum.DOING.value
            table.save()
            Internal.general().notify_table_state_changed(table_id)

            # START COMPUTATION
            start_time = datetime.now()

            task(table_id, *args, **kwargs)

            finish_time = datetime.now()
            elapsed_time = finish_time - start_time

            # EXECUTION TIME
            table.process["phases"][phase_key]["execution_time"] = str(elapsed_time).split('.', 2)[0][3:]

            # PHASE DONE
            table.process["phases"][phase_key]["status"] = GlobalStatusEnum.DONE.value

            # TOTAL EXECUTION TIME
            total_exec_time = timedelta(0)
            all_completed = True
            for phase in table.process["phases"].keys():
                all_completed = all_completed and table.process["phases"][phase]["status"] == GlobalStatusEnum.DONE.value
                t = datetime.strptime(table.process["phases"][phase]["execution_time"], "%M:%S")
                total_exec_time += timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
            table.process["execution_time"] = str(total_exec_time).split('.', 2)[0][3:]

            # GLOBAL STATE
            if all_completed:
                table.global_status = GlobalStatusEnum.DONE.value
            else:
                table.global_status = GlobalStatusEnum.DOING.value

            # EDIT DATE
            table.last_edit_date = datetime.now()

            # NEXT BUTTON
            set_next_button = False
            for phase_name in table.process["phases"].keys():
                if set_next_button:
                    if table.process["phases"][phase_name]["status"] == GlobalStatusEnum.DONE.value:
                        continue
                    table.process["phases"][phase_name]["next"] = True
                    break

                if phase_name == phase_key:
                    table.process["phases"][phase_name]["next"] = False
                    set_next_button = True

            table.save()
            Internal.general().notify_table_state_changed(table_id)
            Internal.table(table_id).notify_completed_phase(phase_key)

        return wrapper

    return inner


def mantis_task_complete():
    def inner(task):
        def wrapper(table_id, challenge, *args, **kwargs):
            start_time = datetime.now()

            # TODO: Error checking here???
            task(table_id, challenge, *args, **kwargs)

            finish_time = datetime.now()
            elapsed_time = finish_time - start_time
            print(elapsed_time)

            table = Table.objects.get(id=table_id)

            hms = str(elapsed_time).split('.', 2)[0].split(":")
            table.process["execution_time"] = f"{hms[1]}:{hms[2]}"
            table.save()

            Internal.general().notify_completed_table(table_id, table.process["execution_time"])

        return wrapper

    return inner


@app.task(name="normalization_task")
@mantis_task(PhasesEnum.DATA_PREPARATION.value["key"])
def normalization_task(table_id):
    try:
        normalize(table_id)
    except Exception as e:
        print("Task raised error (normalization)", str(e))
        traceback.print_exc()
        return


@app.task(name="column_analysis_task")
@mantis_task(PhasesEnum.COLUMN_ANALYSIS.value["key"])
def columns_analysis_task(table_id):
    try:
        info_tables.set_info_table(table_id)
        SubDetection().get_sub_col(table_id)
    except Exception as e:
        print("Task raised error (columns analysis)", str(e))
        traceback.print_exc()
        return


# @app.task(name="concept_datatype_annotation_task", autoretry_for=(NoSparqlEndpointAvailableException,), exponential_backoff=2,
#           retry_kwargs={'max_retries': 5}, retry_jitter=False)
# @mantis_task(PhasesEnum.CONCEPT_ANNOTATION.value["key"])
# def concept_datatype_annotation_task(table_id, challenge=False):
#     try:
#         get_entities(table_id, challenge)
#     except Exception as e:
#         print("Task raised error (concept datatype annotation)", str(e))
#         traceback.print_exc()
#         return


# @app.task(name="relationships_task", autoretry_for=(NoSparqlEndpointAvailableException,), exponential_backoff=2,
#           retry_kwargs={'max_retries': 5}, retry_jitter=False)
# @mantis_task(PhasesEnum.PREDICATE_ANNOTATION.value["key"])
# def relationships_task(table_id, challenge=False):
#     try:
#         get_NE_relationships(table_id, challenge)
#     except (NoSubjectColumnException, Exception) as e:
#         # TODO: Logging
#         print("Task raised error (relationship)", str(e))
#         traceback.print_exc()
#         return


# @app.task(name="linking_task", autoretry_for=(NoSparqlEndpointAvailableException,), exponential_backoff=2,
#           retry_kwargs={'max_retries': 5}, retry_jitter=False)
# @mantis_task(PhasesEnum.ENTITY_LINKING.value["key"])
# def linking_task(table_id, challenge=False):
#     try:
#         get_entity_linking(table_id, challenge)
#     except Exception as e:
#         print("Task raised error (linking)", str(e))
#         traceback.print_exc()
#         return


@app.task(name="complete_table_task", autoretry_for=(NoSparqlEndpointAvailableException,), exponential_backoff=2,
          retry_kwargs={'max_retries': 5}, retry_jitter=False)
@mantis_task_complete()
def complete_table_task(table_id, challenge):
    normalization_task(table_id)
    columns_analysis_task(table_id)
    # concept_datatype_annotation_task(table_id, challenge)
    # relationships_task(table_id, challenge)
    # linking_task(table_id, challenge)


@app.task(name="notify_table_process_end")
def notify_table_process_end():
    state = ServerState.objects.first()
    state.current_process_all_task_id = ""
    state.current_tables_in_progress = 0
    state.save()

    Internal.general().notify_task_end(state.current_process_all_task_id)


@app.task(name="delete_all_tables")
def delete_all_tables():
    total_tables = Table.objects.all().count()

    Table.objects.all().delete()

    state = ServerState.objects.first()
    state.reset_loaded_gs()
    state.save()

    Internal.general().notify_delete_all_finished(total_tables)
