from django.urls import path

from mantistable.models import PhasesEnum
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('changelog/', views.changelog, name='changelog'),

    # Tables
    path('tables/', views.home, name='home'),
    path('tables/create/', views.create_tables, name='createTables'),
    path('tables/<int:table_id>', views.edit_table, name='editTable'),

    path('load-gs-table/', views.load_gs_tables, name='load_gs_table'),
    path('delete-gs-table/', views.delete_gs_tables, name='delete_gs_table'),

    # Process
    path('process/start/<int:table_id>', views.start, name='start'),
    path('process/data-preparation/<int:table_id>', views.data_preparation,
         name=PhasesEnum.DATA_PREPARATION.value["key"]),
    path('process/columns-analysis/<int:table_id>', views.columns_analysis,
         name=PhasesEnum.COLUMN_ANALYSIS.value["key"]),
    # path('process/concept-datatype-annotation/<int:table_id>', views.concept_datatype_annotation,
    #      name=PhasesEnum.CONCEPT_ANNOTATION.value["key"]),
    # path('process/relationships-annotation/<int:table_id>', views.relationships_annotation,
    #      name=PhasesEnum.PREDICATE_ANNOTATION.value["key"]),
    # path('process/entity-linking/<int:table_id>', views.entity_linking, name=PhasesEnum.ENTITY_LINKING.value["key"]),
    path('process/edit-annotations/<int:table_id>', views.edit_annotations, name='editAnnotations'),

    path('process/<int:table_id>', views.process_step, name='process_step'),

    # utils
    path('ajax_calls/process_all/', views.process_all, name='process_all'),
    path('ajax_calls/delete_all/', views.delete_all, name='delete_all'),
    path('ajax_calls/update_process_nav/<int:table_id>', views.update_process_nav, name='update_process_nav'),
    path('ajax_calls/reset_process/<int:table_id>', views.reset_process, name='resetProcess'),
    path('ajax_calls/run_again_phase/<int:table_id>', views.run_again_phase, name='runAgainPhase'),
    path('ajax_calls/update_annotation/<int:table_id>', views.update_annotation, name='update_annotation'),

    # console
    path('console/<int:table_id>', views.console, name='console'),

    # export
    path('export/', views.export, name='export'),

    # Download
    path('process/download_csv/<int:table_id>', views.download_csv, name='download_table_csv'),
    path('process/download_raw/<int:table_id>', views.download_raw, name='download_table_raw'),

]
