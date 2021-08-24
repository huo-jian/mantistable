import datetime
import json

from celery import chain, group
from django.core.paginator import Paginator
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe

from mantistable import tasks
from mantistable.process.utils.assets import importer
from mantistable.process.utils.publisher.internal import Internal
from mantistable.process.utils.export import cpa, cea
from mantistable.process.utils.export import cta
from mantistable.process.utils.export import rdf
from mantistable.process.utils.sparql.sparql_repository import DbpediaSparqlRepository, WikiDataSparqlRepository
from mantistable.process.utils.export.format_exporters.csv_exporter import CSVExporter
from mantistable.process.utils.data_type import DataTypeEnum
from .forms import TableFromJSONForm
from .models import Table, TableData, InfoTable, ServerState, Log, Annotation, GlobalStatusEnum, GoldStandardsEnum, \
    PhasesEnum


def index(request):
    context = {}
    return render(request, 'mantistable/index.html', context)


def changelog(request):
    tables_completed_count = Table.objects.filter(global_status=GlobalStatusEnum.DONE.value).count()
    tables_in_progress_count = Table.objects.filter(global_status=GlobalStatusEnum.DOING.value).count()

    return render(request, 'mantistable/changelog.html', {
        'tables_count': Table.objects.count(),
        'tables_completed': tables_completed_count,
        'tables_in_progress': tables_in_progress_count,
        'current_process_all_task_id': ServerState.objects.get().current_process_all_task_id
    })


def home(request):
    table_list = Table.objects.order_by('pub_date')
    searching = False

    search_filter_param = request.GET.get("search", "")
    gs_filter_param = request.GET.get("gs", "")
    status_filter_param = request.GET.get("status", "")

    gs = {
        "none": GoldStandardsEnum.NONE.value,
        "T2D": GoldStandardsEnum.T2D.value,
        "Limaye200": GoldStandardsEnum.Limaye200.value,
        "limaye": GoldStandardsEnum.limaye.value,
        "semantification": GoldStandardsEnum.semantification.value,
        "semr1": GoldStandardsEnum.semr1.value,
        "semr2": GoldStandardsEnum.semr2.value,
        "semr3": GoldStandardsEnum.semr3.value,
        "semr4": GoldStandardsEnum.semr4.value,
        "wiki": GoldStandardsEnum.wiki.value,
        "t2": GoldStandardsEnum.t2.value,
        "Challenge": GoldStandardsEnum.CHALLENGE.value
    }.get(gs_filter_param, None)

    status = {
        "TODO": GlobalStatusEnum.TODO.value,
        "DOING": GlobalStatusEnum.DOING.value,
        "DONE": GlobalStatusEnum.DONE.value,
    }.get(status_filter_param, None)

    # NOTE: Very fast/easy way to do filtering: one list, no paginator
    if search_filter_param != "" or gs is not None or status is not None:
        if search_filter_param != "":
            table_list = table_list.filter(name__icontains=search_filter_param)

        if gs is not None:
            table_list = table_list.filter(gs_type=gs)

        if status is not None:
            table_list = table_list.filter(global_status=status)

        tables_count = max(len(table_list), 1)
        paginator = Paginator(table_list, tables_count)
        page = 1
        searching = True
    else:
        tables_count = Table.objects.count()

        num_elem = 25
        paginator = Paginator(table_list, num_elem)
        page = request.GET.get('page')

    tables = paginator.get_page(page)
    print(page)
    tables_completed_count = Table.objects.filter(global_status=GlobalStatusEnum.DONE.value).count()
    tables_in_progress_count = Table.objects.filter(global_status=GlobalStatusEnum.DOING.value).count()

    context = {
        'tables': tables,
        'tables_count': tables_count,
        'tables_completed': tables_completed_count,
        'tables_in_progress': tables_in_progress_count,
        'current_process_all_task_id': ServerState.objects.get().current_process_all_task_id,
        'searching': searching
    }

    if request.is_ajax():
        table_list_html = render_to_string(
            template_name="mantistable/table-list.html",
            context=context
        )

        data = {
            "table_list_html": table_list_html,
        }

        return JsonResponse(data=data, safe=False)

    return render(request, 'mantistable/home.html', context)


def create_tables(request):
    invalid_file = False
    valid_file = False

    state = ServerState.objects.get()

    if request.method == 'POST':
        form = TableFromJSONForm(request.POST, request.FILES)
        if form.is_valid():
            assert ('json_file' in request.FILES)

            # NOTE: Huge file could be bad for server performance
            # NOTE: What about chuncking the input?
            data = request.FILES['json_file'].file.read()
            file_name = request.FILES['json_file'].name
            table_name = request.POST.get('table_name')
            gs_type = request.POST.get('gs_type')

            # Bad post request
            if gs_type not in (gs.name for gs in GoldStandardsEnum):
                return HttpResponseRedirect(reverse('home'))

            try:
                importer.load_table(table_name, file_name, gs_type, data)
                valid_file = True
            except ValueError as e:
                print(e)
                invalid_file = True
    else:
        form = TableFromJSONForm()

    tables_completed_count = Table.objects.filter(global_status=GlobalStatusEnum.DONE.value).count()
    tables_in_progress_count = Table.objects.filter(global_status=GlobalStatusEnum.DOING.value).count()

    context = {
        'invalidfile': invalid_file,
        'validfile': valid_file,
        'form': form,
        'tables_count': Table.objects.count(),
        'tables_completed': tables_completed_count,
        'tables_in_progress': tables_in_progress_count,
        'standard_loaded': {
            "t2d": state.loaded_t2d,
            "limaye200": state.loaded_limaye200,
            "limaye": state.loaded_limaye,
            "semantification": state.loaded_semantification,
            "semr1": state.loaded_semr1,
            "semr2": state.loaded_semr2,
            "semr3": state.loaded_semr3,
            "semr4": state.loaded_semr4,
            "wiki": state.loaded_wiki,
            "t2": state.loaded_t2,
            "challenge": state.loaded_challenge
        }
    }
    return render(request, 'mantistable/tables/create_tables.html', context)


def edit_table(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    context = {
        'uploadingTable': False,
        'table': table,
        'tables_count': Table.objects.count()
    }
    return render(request, 'mantistable/tables/edit_table.html', context)


def load_gs_tables(request):
    table_type = request.GET.get('type', None)

    # TODO: Could use enum for automatic mapping...
    if table_type == 't2d':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.T2D.value)
    elif table_type == 'limaye200':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.Limaye200.value)
    elif table_type == 'limaye':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.limaye.value)   
    elif table_type == 'semantification':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.semantification.value) 
    elif table_type == 'semr1':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.semr1.value) 
    elif table_type == 'semr2':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.semr2.value) 
    elif table_type == 'semr3':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.semr3.value) 
    elif table_type == 'semr4':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.semr4.value) 
    elif table_type == 't2':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.t2.value) 
    elif table_type == 'wiki':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.wiki.value)                              
    elif table_type == 'challenge':
        task = importer.load_gs_tables.delay(GoldStandardsEnum.CHALLENGE.value)
    else:
        return {'error': 'wrong gs type'}

    response_data = {'task_id': task.id}
    return JsonResponse(response_data)


def delete_gs_tables(request):
    table_type = request.GET.get('type', None)

    # TODO: Could use enum for automatic mapping...
    if table_type == 't2d':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.T2D.value)
    elif table_type == 'limaye200':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.Limaye200.value)
    elif table_type == 'limaye':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.limaye.value)   
    elif table_type == 'semantification':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.semantification.value) 
    elif table_type == 'semr1':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.semr1.value) 
    elif table_type == 'semr2':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.semr2.value) 
    elif table_type == 'semr3':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.semr3.value) 
    elif table_type == 'semr4':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.semr4.value) 
    elif table_type == 't2':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.t2.value) 
    elif table_type == 'wiki':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.wiki.value)    
    elif table_type == 'challenge':
        task = importer.delete_gs_tables.delay(GoldStandardsEnum.CHALLENGE.value)
    else:
        return {'error': 'wrong gs type'}

    response_data = {'task_id': task.id}
    return JsonResponse(response_data)


# PROCESS
def start(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    table_data = TableData.objects.get(table=table)

    data = []
    for row_idx in range(0, table.num_rows):
        row = []
        for col_idx, col in enumerate(table_data.data_original):
            row.append(col[row_idx]["value"])

        data.append(row)

    context = {
        'table': table,
        'table_datas': json.dumps(data),
        'tables_count': Table.objects.count()
    }
    return render(request, 'mantistable/tables/process/00-start.html', context)


def process_all(request):
    tables = Table.objects.all()

    table_jobs = []
    for table in tables:
        process_job = tasks.complete_table_task.si(table.id, table.gs_type == GoldStandardsEnum.CHALLENGE.value)
        """
        if table.gs_type == GoldStandardsEnum.ROUND2.value:
            #process_job = chain(tasks.complete_table_task.s(table.id, True),
            #                    link=tasks.notify_table_process_end.s(table.id))
            process_job = tasks.complete_table_task.si(table.id, table.gs_type == GoldStandardsEnum.ROUND2.value)
        else:
            process_job = tasks.complete_table_task.si(table.id, False)
        """

        table_jobs.append(process_job)

    group_job = group(table_jobs)
    group_job = group_job | tasks.notify_table_process_end.si()
    task = group_job.apply_async()

    state = ServerState.objects.first()
    state.current_process_all_task_id = task.id
    state.current_tables_in_progress = len(tables)
    state.save()

    Log(
        process_started=datetime.datetime.now(),
        task_id=task.id,
    ).save()

    #task.save()

    Internal.general().notify_started_process_all()
    return JsonResponse({"status": "ok"})


def delete_all(request):
    tasks.delete_all_tables.delay()
    return JsonResponse({"status": "ok"})


# TODO: We must discriminate between Round2 challenges and non-challenges tables
def process_step(request, table_id):
    if request.is_ajax():
        table = get_object_or_404(Table, id=table_id)
        step_name = request.GET.get('step_name')
        current_path = request.GET.get('current_path')
        prev_step_path = reverse('start', args=(table_id,))

        if step_name in (phase.value["key"] for phase in PhasesEnum):
            prev_index = [phase.value["key"] for phase in PhasesEnum].index(step_name) - 1
            if prev_index < 0:
                prev_step_path = reverse('start', args=(table_id,))
            else:
                prev_step_path = reverse(list(PhasesEnum)[prev_index].value["key"], args=(table_id,))

            print(prev_step_path)

            if table.process['phases'][step_name]['status'] == GlobalStatusEnum.TODO.value:
                challenge = table.gs_type == GoldStandardsEnum.CHALLENGE.value
                task_runnable = {
                    PhasesEnum.DATA_PREPARATION.value["key"]: lambda tid: tasks.normalization_task.delay(tid),
                    PhasesEnum.COLUMN_ANALYSIS.value["key"]: lambda tid: tasks.columns_analysis_task.delay(tid),
                    # PhasesEnum.CONCEPT_ANNOTATION.value["key"]: lambda tid: tasks.concept_datatype_annotation_task.delay(tid, challenge),
                    # PhasesEnum.PREDICATE_ANNOTATION.value["key"]: lambda tid: tasks.relationships_task.delay(tid, challenge),
                    # PhasesEnum.ENTITY_LINKING.value["key"]: lambda tid: tasks.linking_task.delay(tid, challenge),
                }.get(step_name, None)
                assert task_runnable is not None  # NOTE: Impossible

                task_runnable(table_id)

        data = {
            "redirect": current_path == prev_step_path,
            "redirect_url": reverse(step_name, args=(table_id,))
        }

        return JsonResponse(data)


def update_process_nav(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    context = {
        'table': table,
    }
    return render(request, 'mantistable/tables/process/multistep.html', context)


def data_preparation(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    context = {
        'table': table,
        'tables_count': Table.objects.count(),
        'loading': True,  # TODO: Just making a very fast solution
        'phase_name': PhasesEnum.DATA_PREPARATION.value["key"],
        'process_time': table.process['phases'][PhasesEnum.DATA_PREPARATION.value["key"]]['execution_time'],
    }
    if table.process['phases'][PhasesEnum.DATA_PREPARATION.value["key"]]['status'] == GlobalStatusEnum.DONE.value:
        table = get_object_or_404(Table, id=table_id)
        table_data = TableData.objects.get(table=table)

        # NOTE: Ok this is a bit complex... but it just make a list of dictionaries => header: label, type{i}: type
        data = []
        for row_idx in range(0, table.num_rows):
            row = []
            for col_idx, col in enumerate(table_data.data):
                for header, value in zip((table_data.header[col_idx], f"type{col_idx}"),
                                         (col[row_idx]["value"], col[row_idx]["data_preparation"]["type"])):
                    row.append(value)

            data.append(row)

        comments = []
        right_sidebar = {}

        for col_idx, col in enumerate(table_data.data):
            for row_idx, transformed in enumerate(col):
                if transformed['data_preparation']['comment']:
                    comments.append({
                        "row": row_idx,
                        "col": 2 * col_idx,
                        "comment": {"value": transformed['data_preparation']['comment']}
                    })

                key_coords = "row" + str(row_idx) + "col" + str(2 * col_idx)
                right_sidebar[key_coords] = {
                    "cell_title": transformed['value'],
                    "cell_header": table.header[col_idx],
                    "cell_row_coord": row_idx,
                    "cell_col_coord": col_idx,
                    "step_name": table.process['phases'][PhasesEnum.DATA_PREPARATION.value["key"]]['name'],
                    "cell_value_before": transformed['value_original'],
                    # TODO  db transformations
                    "cell_transformation": ["Turned text into lowercase"]

                }

        context = {
            'table': table,
            'table_datas': json.dumps(data),
            'tables_count': Table.objects.count(),
            'loading': False,
            'table_comments': json.dumps(comments),
            'process_time': table.process['phases'][PhasesEnum.DATA_PREPARATION.value["key"]]['execution_time'],
            'phase_name': PhasesEnum.DATA_PREPARATION.value["key"],
            'right_sidebar': right_sidebar
        }

    return render(request, 'mantistable/tables/process/01-data_preparation.html', context)


def columns_analysis(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    context = {
        'table': table,
        'tables_count': Table.objects.count(),
        'loading': True,
        'phase_name': PhasesEnum.COLUMN_ANALYSIS.value["key"],
        'process_time': table.process['phases'][PhasesEnum.COLUMN_ANALYSIS.value["key"]]['execution_time'],
    }
    if table.process['phases'][PhasesEnum.COLUMN_ANALYSIS.value["key"]]['status'] == GlobalStatusEnum.DONE.value:
        table = get_object_or_404(Table, id=table_id)
        table_data = TableData.objects.get(table=table)
        info_table = InfoTable.objects.get(table=table)

        lit_cols = info_table.lit_cols
        ne_cols = info_table.ne_cols

        ne_cols_scores = {ne["index"]: ne["score"] for ne in ne_cols}
        lit_cols_regex_types = {lit["index"]: lit["regex_type"] for lit in lit_cols}
        lit_cols_freq_types = {lit["index"]: lit["type_freq_table"] for lit in lit_cols}

        right_sidebar = {}
        for col_idx, col in enumerate(table_data.data):
            key_coords = "col" + str(col_idx)
            right_sidebar[key_coords] = {
                "header": table.header[col_idx],
                "step_name": table.process['phases'][PhasesEnum.COLUMN_ANALYSIS.value["key"]]['name']
            }

        data = [
            [
                col[row_idx]["value"]
                for col_idx, col in enumerate(table_data.data)
            ] for row_idx in range(0, table.num_rows)
        ]

        context = {
            'table': table,
            'table_datas': json.dumps(data),
            'loading': False,
            'lit_cols': json.dumps(lit_cols),
            'ne_cols': json.dumps(ne_cols),
            'subject_col': info_table.subject_col,
            'ne_cols_scores': json.dumps(ne_cols_scores),
            'lit_cols_regex_types': json.dumps(lit_cols_regex_types),
            "lit_cols_freq_types": json.dumps(lit_cols_freq_types),
            'tables_count': Table.objects.count(),
            'process_time': table.process['phases'][PhasesEnum.COLUMN_ANALYSIS.value["key"]]['execution_time'],
            'phase_name': PhasesEnum.COLUMN_ANALYSIS.value["key"],
            'right_sidebar': right_sidebar,
        }
    return render(request, 'mantistable/tables/process/02-column_analysis.html', context)


# def concept_datatype_annotation(request, table_id):
#     table = get_object_or_404(Table, id=table_id)
#
#     context = {
#         'table': table,
#         'tables_count': Table.objects.count(),
#         'loading': True,
#         'phase_name': PhasesEnum.CONCEPT_ANNOTATION.value["key"],
#         'process_time': table.process['phases'][PhasesEnum.CONCEPT_ANNOTATION.value["key"]]['execution_time'],
#     }
#     if table.process['phases'][PhasesEnum.CONCEPT_ANNOTATION.value["key"]]['status'] == GlobalStatusEnum.DONE.value:
#         table_data = TableData.objects.get(table=table)
#         info_table = InfoTable.objects.get(table=table)
#         annotations = Annotation.objects.get(table=table)
#
#         lit_cols = info_table.lit_cols
#         ne_cols = info_table.ne_cols
#
#         ne_cols_scores = {ne["index"]: ne["score"] for ne in ne_cols}
#         lit_cols_regex_types = {lit["index"]: lit["regex_type"] for lit in lit_cols}
#         lit_cols_data_types = {lit["index"]: lit["data_type"] for lit in lit_cols}
#
#         winning_concepts = {ne_col["index"]: ne_col["type"] for ne_col in ne_cols}
#         candidate_concepts = {ne_col["index"]: ne_col["winning_concepts"] for ne_col in ne_cols}
#
#         data = [
#             [
#                 col[row_idx]["value"]
#                 for col_idx, col in enumerate(table_data.data)
#             ] for row_idx in range(0, table.num_rows)
#         ]
#
#         right_sidebar = {}
#         comments = []
#
#         for col_idx, col in enumerate(table_data.data):
#             # header
#             key_coords = "col" + str(col_idx)
#             right_sidebar[key_coords] = {
#                 "header": table.header[col_idx],
#                 "step_name": table.process['phases'][PhasesEnum.CONCEPT_ANNOTATION.value["key"]]['name'],
#             }
#             if str(col_idx) in annotations.cols_we:
#                 ann_row_idx = 0
#                 for row_idx, _ in enumerate(table_data.data[col_idx]):
#                     if "result_entities" in table_data.data[col_idx][row_idx] and ann_row_idx < len(annotations.cols_we[str(col_idx)]):
#                         annotation = annotations.cols_we[str(col_idx)][ann_row_idx]
#                         ann_row_idx += 1
#
#                     # cell
#                     key_coords = "row" + str(row_idx) + "col" + str(col_idx)
#                     right_sidebar[key_coords] = {
#                         "cell_title": table_data.data[col_idx][row_idx]['value'],
#                         "cell_header": table.header[col_idx],
#                         "cell_row_coord": row_idx,
#                         "cell_col_coord": col_idx,
#                         "step_name": table.process['phases'][PhasesEnum.CONCEPT_ANNOTATION.value["key"]]['name'],
#                         # "entities" : annotation['entity'],
#                         # "concepts" : annotation['type'],
#                         "annotations": table_data.data[col_idx][row_idx].get('result_entities', [])
#                     }
#
#                     if "result_entities" in table_data.data[col_idx][row_idx] and ann_row_idx < len(annotations.cols_we[str(col_idx)]):
#                         comments.append({
#                             "row": row_idx,
#                             "col": col_idx,
#                             "comment": {
#                                 # TODO: need all entities, not just the winning ones
#                                 "num_entities": len(table_data.data[col_idx][row_idx].get('result_entities', [])),
#                                 "num_concepts": len(annotation['type']),
#                                 "value": ""
#                             }
#                         })
#
#         context = {
#             'table': table,
#             'table_datas': json.dumps(data),
#             'loading': False,
#             'lit_cols': json.dumps(lit_cols),
#             'ne_cols': json.dumps(ne_cols),
#             'subject_col': info_table.subject_col,
#             'winning_concepts': winning_concepts,
#             'candidate_concepts': json.dumps(candidate_concepts),
#             'ne_cols_scores': json.dumps(ne_cols_scores),
#             'lit_cols_regex_types': json.dumps(lit_cols_regex_types),
#             'lit_cols_data_types': json.dumps(lit_cols_data_types),
#             'tables_count': Table.objects.count(),
#             'table_comments': json.dumps(comments),
#             'process_time': table.process['phases'][PhasesEnum.CONCEPT_ANNOTATION.value["key"]]['execution_time'],
#             'phase_name': PhasesEnum.CONCEPT_ANNOTATION.value["key"],
#             'right_sidebar': json.dumps(right_sidebar)
#         }
#     return render(request, 'mantistable/tables/process/03-concept_datatype_annotation.html', context)


# def relationships_annotation(request, table_id):
#     table = get_object_or_404(Table, id=table_id)
#
#     context = {
#         'table': table,
#         'tables_count': Table.objects.count(),
#         'loading': True,
#         'phase_name': PhasesEnum.PREDICATE_ANNOTATION.value["key"],
#         'process_time': table.process['phases'][PhasesEnum.PREDICATE_ANNOTATION.value["key"]]['execution_time'],
#     }
#     if table.process['phases'][PhasesEnum.PREDICATE_ANNOTATION.value["key"]]['status'] == GlobalStatusEnum.DONE.value:
#         table_data = TableData.objects.get(table=table)
#         info_table = InfoTable.objects.get(table=table)
#
#         lit_cols = info_table.lit_cols
#         ne_cols = info_table.ne_cols
#
#         ne_cols_scores = {ne["index"]: ne["score"] for ne in ne_cols}
#         lit_cols_regex_types = {lit["index"]: lit["regex_type"] for lit in lit_cols}
#         lit_cols_data_types = {lit["index"]: lit["data_type"] for lit in lit_cols}
#
#         ne_cols_rel = {ne["index"]: ne["rel"] for ne in ne_cols if "rel" in ne}
#         lit_cols_rel = {lit["index"]: lit["rel"] for lit in lit_cols if "rel" in lit}
#
#         cols_rel = {}
#         cols_rel.update(ne_cols_rel)
#         cols_rel.update(lit_cols_rel)
#
#         winning_concepts = {ne_col["index"]: ne_col["type"] for ne_col in ne_cols}
#
#         data = [
#             [
#                 col[row_idx]["value"]
#                 for col_idx, col in enumerate(table_data.data)
#             ] for row_idx in range(0, table.num_rows)
#         ]
#
#         right_sidebar = {}
#         for col_idx, col in enumerate(table_data.data):
#             key_coords = "col" + str(col_idx)
#             right_sidebar[key_coords] = {
#                 "header": table.header[col_idx],
#                 "step_name": table.process['phases'][PhasesEnum.PREDICATE_ANNOTATION.value["key"]]['name'],
#             }
#
#         context = {
#             'table': table,
#             'table_datas': json.dumps(data),
#             'loading': False,
#             'lit_cols': json.dumps(lit_cols),
#             'ne_cols': json.dumps(ne_cols),
#             'subject_col': info_table.subject_col,
#             'ne_cols_scores': json.dumps(ne_cols_scores),
#             'cols_rel': json.dumps(cols_rel),
#             'winning_concepts': winning_concepts,
#             'lit_cols_regex_types': json.dumps(lit_cols_regex_types),
#             'lit_cols_data_types': json.dumps(lit_cols_data_types),
#             'tables_count': Table.objects.count(),
#             'process_time': table.process['phases'][PhasesEnum.PREDICATE_ANNOTATION.value["key"]]['execution_time'],
#             'phase_name': PhasesEnum.PREDICATE_ANNOTATION.value["key"],
#             'right_sidebar': right_sidebar
#         }
#     return render(request, 'mantistable/tables/process/04-relationships_annotation.html', context)
#
#
# def entity_linking(request, table_id):
#     table = get_object_or_404(Table, id=table_id)
#
#     context = {
#         'table': table,
#         'tables_count': Table.objects.count(),
#         'loading': True,
#         'phase_name': PhasesEnum.ENTITY_LINKING.value["key"],
#         'process_time': table.process['phases'][PhasesEnum.ENTITY_LINKING.value["key"]]['execution_time'],
#     }
#     if table.process['phases'][PhasesEnum.ENTITY_LINKING.value["key"]]['status'] == GlobalStatusEnum.DONE.value:
#         table_data = TableData.objects.get(table=table)
#         info_table = InfoTable.objects.get(table=table)
#
#         lit_cols = info_table.lit_cols
#         ne_cols = info_table.ne_cols
#
#         ne_cols_scores = {ne["index"]: ne["score"] for ne in ne_cols}
#         lit_cols_regex_types = {lit["index"]: lit["regex_type"] for lit in lit_cols}
#         lit_cols_data_types = {lit["index"]: lit["data_type"] for lit in lit_cols}
#
#         ne_cols_rel = {ne["index"]: ne["rel"] for ne in ne_cols if "rel" in ne}
#         lit_cols_rel = {lit["index"]: lit["rel"] for lit in lit_cols if "rel" in lit}
#
#         winning_concepts = {ne_col["index"]: ne_col["type"] for ne_col in ne_cols}
#
#         cols_rel = {}
#         cols_rel.update(ne_cols_rel)
#         cols_rel.update(lit_cols_rel)
#
#         data = []
#         for row_idx in range(0, table.num_rows):
#             row_data = []
#             for col_idx, col in enumerate(table_data.data):
#                 row_data.append([col[row_idx]["value"], col[row_idx].get("linked_entity", None)])
#
#             data.append(row_data)
#
#         right_sidebar = {}
#         for col_idx, col in enumerate(table_data.data):
#             key_coords = "col" + str(col_idx)
#             right_sidebar[key_coords] = {
#                 "header": table.header[col_idx],
#                 "step_name": table.process['phases'][PhasesEnum.ENTITY_LINKING.value["key"]]['name'],
#             }
#
#         context = {
#             'table': table,
#             'table_datas': json.dumps(data),
#             'loading': False,
#             'lit_cols': json.dumps(lit_cols),
#             'ne_cols': json.dumps(ne_cols),
#             'subject_col': info_table.subject_col,
#             'ne_cols_scores': json.dumps(ne_cols_scores),
#             'cols_rel': json.dumps(cols_rel),
#             'winning_concepts': winning_concepts,
#             'lit_cols_regex_types': json.dumps(lit_cols_regex_types),
#             'lit_cols_data_types': json.dumps(lit_cols_data_types),
#             'tables_count': Table.objects.count(),
#             'process_time': table.process['phases'][PhasesEnum.ENTITY_LINKING.value["key"]]['execution_time'],
#             'phase_name': PhasesEnum.ENTITY_LINKING.value["key"],
#             'right_sidebar': right_sidebar
#         }
#     return render(request, 'mantistable/tables/process/05-entity_linking.html', context)


def edit_annotations(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    table_data = TableData.objects.get(table=table)
    info_table = InfoTable.objects.get(table=table)

    lit_cols = info_table.lit_cols
    ne_cols = info_table.ne_cols

    ne_cols_scores = {ne["index"]: ne["score"] for ne in ne_cols}
    lit_cols_regex_types = {lit["index"]: lit["regex_type"] for lit in lit_cols}
    lit_cols_data_types = {lit["index"]: lit["data_type"] for lit in lit_cols}

    ne_cols_rel = {ne["index"]: ne["rel"] for ne in ne_cols if "rel" in ne}
    lit_cols_rel = {lit["index"]: lit["rel"] for lit in lit_cols if "rel" in lit}

    cols_rel = {}
    cols_rel.update(ne_cols_rel)
    cols_rel.update(lit_cols_rel)

    winning_concepts = {ne_col["index"]: ne_col["type"] for ne_col in ne_cols}
    candidate_concepts = {ne_col["index"]: ne_col["winning_concepts"] for ne_col in ne_cols}

    data = [
        [
            col[row_idx]["value"]
            for col_idx, col in enumerate(table_data.data)
        ] for row_idx in range(0, table.num_rows)
    ]

    right_sidebar = {
        "step_name": 'Edit Annotations',
        "rdf": [],
        "hint_mantis": [],
        "hint_abstat": [],
    }

    context = {
        'table': table,
        'table_datas': json.dumps(data),
        'subject_col': info_table.subject_col,
        'lit_cols': json.dumps(lit_cols),
        'ne_cols': json.dumps(ne_cols),
        'ne_cols_scores': json.dumps(ne_cols_scores),
        'cols_rel': json.dumps(cols_rel),
        'winning_concepts': winning_concepts,
        'candidate_concepts': json.dumps(candidate_concepts),
        'lit_cols_regex_types': json.dumps(lit_cols_regex_types),
        'lit_cols_data_types': json.dumps(lit_cols_data_types),
        'tables_count': Table.objects.count(),
        'right_sidebar': json.dumps(right_sidebar)

    }

    return render(request, 'mantistable/tables/process/06-edit_annotations.html', context)


def update_annotation(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    info_table = InfoTable.objects.get(table=table)

    lit_cols = info_table.lit_cols
    ne_cols = info_table.ne_cols

    data = {
        'is_valid': False,
    }

    if request.is_ajax():
        col_idx = int(request.GET.get("col_idx"))
        annotation_type = request.GET.get("annotation_type")
        annotation = request.GET.get("annotation")

        new_annotation_data = annotation

        for ne in ne_cols:
            if col_idx == ne["index"]:
                if annotation_type == "predicate":
                    ne["rel"] = annotation
                else:
                    ne["type"] = annotation

        for lit in lit_cols:
            if col_idx == lit["index"]:
                if annotation_type == "predicate":
                    lit["rel"] = annotation
                else:
                    lit["data_type"] = [
                        DataTypeEnum.get_datatype_uri(annotation)
                    ]
                    new_annotation_data = DataTypeEnum.get_datatype_uri(annotation)

        info_table.save()

        data = {
            'is_valid': True,
            'new_annotation': new_annotation_data
        }

    return JsonResponse(data)


def reset_process(request, table_id):
    table = get_object_or_404(Table, id=table_id)

    for phase_key in table.process["phases"].keys():
        table.process["phases"][phase_key]["status"] = GlobalStatusEnum.TODO.value
        table.process["phases"][phase_key]["next"] = False

    table.process["phases"][PhasesEnum.DATA_PREPARATION.value["key"]]["next"] = True
    table.global_status = GlobalStatusEnum.TODO.value

    table.save()

    Internal.general().notify_table_state_changed(table_id)

    return HttpResponseRedirect(reverse("start", args=[table_id]))


def run_again_phase(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    phase_name = request.GET.get('phaseName', None)

    if phase_name in (tag.value["key"] for tag in PhasesEnum):
        table.process['phases'][phase_name]['status'] = GlobalStatusEnum.TODO.value
        table.global_status = GlobalStatusEnum.TODO.value
        table.save()
    else:
        return HttpResponseRedirect(reverse('home'))

    return HttpResponseRedirect(reverse(phase_name, args=[table_id]))


# TODO: Is this thing used anywhere?
def console(request, table_id):
    return render(request, 'mantistable/chat.html', {
        'table_id': mark_safe(json.dumps(table_id))
    })


def search(request):
    data = {
        'is_valid': False,
        'response': ''
    }
    if request.is_ajax():
        message = request.GET.get('message')
        input = request.GET.get('input')
        if message == 'search':
            data.update(is_valid=True)
            data.update(response='This is the response' + input)

    return JsonResponse(data)


def export(request):
    def build_file_response(name_prefix, data, ext):
        format_type_map = {
            'xml': ('text/xml', 'xml'),
            'nt': ('text/nt', 'nt'),
            'turtle': ('text/turtle', 'ttl'),
            'jsonld': ('application/ld+json', 'json')
        }

        format_type = format_type_map.get(ext, ('text/csv', 'csv'))

        date = datetime.datetime.now().strftime("%d_%m_%Y")

        response = HttpResponse(data, content_type=format_type[0])
        response['Content-Disposition'] = f'attachment; filename="{name_prefix}_{date}.{format_type[1]}"'

        return response

    type_list = ['CTA', 'CEA', 'CPA', 'RDF']
    format_list = ['xml', 'nt', 'turtle', 'jsonld']

    export_gs = request.GET.get('export_gs', None)
    export_type = request.GET.get('export_type', None)
    export_format = request.GET.get('export_format', 'csv')

    print(export_gs)

    if export_type is None and export_gs is None:
        tables_completed_count = Table.objects.filter(global_status=GlobalStatusEnum.DONE.value).count()
        tables_in_progress_count = Table.objects.filter(global_status=GlobalStatusEnum.DOING.value).count()

        return render(request, 'mantistable/export.html', {
            'tables_count': Table.objects.count(),
            'tables_completed': tables_completed_count,
            'tables_in_progress': tables_in_progress_count,
            'current_process_all_task_id': ServerState.objects.get().current_process_all_task_id
        })

    if export_gs is not None:
        if export_gs in (gs.value for gs in GoldStandardsEnum):
            gs_tables = Table.objects.filter(gs_type=export_gs)
            # TODO: use gs_type to get result
            if export_type in type_list:
                result = ""
                if export_type == 'CTA':
                    result = cta.export(gs_tables)
                elif export_type == 'CPA':
                    result = cpa.export(gs_tables)
                elif export_type == 'CEA':
                    # TODO: implement cea export
                    result = cea.export(gs_tables)
                elif export_type == 'RDF':
                    # TODO: Mattia
                    if export_format in format_list:
                        if export_format == 'xml':
                            result = rdf.exportRdf('xml')
                        elif export_format == 'nt':
                            result = rdf.exportRdf('nt')
                        elif export_format == 'turtle':
                            result = rdf.exportRdf('turtle')
                        elif export_format == 'jsonld':
                            result = rdf.exportRdf('jsonld')

                return build_file_response(f"annotations_{export_type}", result, export_format)

        else:
            return HttpResponseRedirect(reverse('export'))
    else:
        return HttpResponseRedirect(reverse('export'))


#Download

def download_csv(request, table_id):
    def build_file_response_download(name_prefix, data, ext):

        date = datetime.datetime.now().strftime("%d_%m_%Y")

        response = HttpResponse(data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{name_prefix}_{date}.csv"'

        return response

    table = get_object_or_404(Table, id=table_id)

    if table.process['phases'][PhasesEnum.COLUMN_ANALYSIS.value["key"]]['status'] == GlobalStatusEnum.DONE.value:
        table = get_object_or_404(Table, id=table_id)
        table_data = TableData.objects.get(table=table)
        info_table = InfoTable.objects.get(table=table)


    print("HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")

    # Le header n'est pas filtré, on place juste la colonne sujet en premier
    header = table.header
    header.insert(0,header.pop(info_table.subject_col))
    header = [header]
    print(header)

    # Filter data ? TODO
    # On recupère les données de la table
    data = [
         [
             col[row_idx]["value"]
             for col_idx, col in enumerate(table_data.data)
         ] for row_idx in range(0, table.num_rows)
     ]

    #On place la colonne sujet en premier pour chaque ligne de la table
    for row in data:
        row.insert(0,row.pop(info_table.subject_col))


    table = header + data


    print("HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")

    result = CSVExporter(table).export()

    export_format = request.GET.get('export_format', 'csv')

    return build_file_response_download(f"annotations_CSV", result, export_format)



def download_raw(request, table_id):
    def build_file_response_download(name_prefix, data, ext):

        date = datetime.datetime.now().strftime("%d_%m_%Y")

        response = HttpResponse(data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{name_prefix}_{date}.csv"'

        return response

    table = get_object_or_404(Table, id=table_id)
    table_data = TableData.objects.get(table=table)

    header = [table.header]

    data = [
        [
            col[row_idx]["value"]
            for col_idx, col in enumerate(table_data.data)
        ] for row_idx in range(0, table.num_rows)
    ]

    table = header + data

    result = CSVExporter(table).export()
    export_format = request.GET.get('export_format', 'csv')

    return build_file_response_download(f"annotations_CSV", result, export_format)

