import datetime
import json
import os
import random

from celery.result import AsyncResult

from app.celery import app
from mantistable.models import Table, TableData, ServerState, GlobalStatusEnum, PhasesEnum, GoldStandardsEnum
from mantistable.process.utils.assets.assets import Assets
from mantistable.process.utils.publisher.internal import Internal


process = {
    "phases": {
        tag.value["key"]: {
            'name': tag.value["name"],
            'routeName': tag.value["key"],
            'status': GlobalStatusEnum.TODO.value,
            'next': idx == 0,
            'execution_time': str(datetime.timedelta(0)).split('.', 2)[0][3:]
        }
        for idx, tag in enumerate(PhasesEnum)
    },
    "execution_time": str(datetime.timedelta(0)).split('.', 2)[0][3:]
}


# TODO: Refactoring needed
def _create_table(table_name, file_name, gs_type, content):
    assert (len(table_name) > 0)
    assert (len(file_name) > 0)
    assert (len(content) > 0)

    print(file_name)
    json_data = json.loads(content)
    header = list(json_data[0].keys())

    table = Table(
        name=table_name,
        gs_type=gs_type,
        file_name=file_name,
        header=header,
        num_cols=len(list(json_data[0].keys())),
        num_rows=len(json_data),
        process=process
    )

    def table_datas_builder(tab):
        datas = []
        for col_index in range(0, len(header)):
            data = []
            for i in range(0, len(json_data)):
                col_name = header[col_index]
                if col_name in json_data[i]:
                    data.append({
                        "value": json_data[i][col_name]
                    })
                else:
                    data.append({
                        "value": ""
                    })

            datas.append(data)

        return TableData(
            table=tab,
            header=header,
            data_original=datas,
            data=datas,
        )

    return table, table_datas_builder


def load_table(table_name, file_name, gs_type, content):
    assert (len(table_name) > 0)
    assert (len(file_name) > 0)
    assert (len(content) > 0)

    print(file_name)
    json_data = json.loads(content)
    header = list(json_data[0].keys())

    table = Table(
        name=table_name,
        gs_type=gs_type,
        file_name=file_name,
        header=header,
        num_cols=len(list(json_data[0].keys())),
        num_rows=len(json_data),
        process=process
    )
    table.save()

    datas = []
    for col_index in range(0, len(header)):
        data = []
        for i in range(0, len(json_data)):
            col_name = header[col_index]
            if col_name in json_data[i]:
                data.append({
                    "value": json_data[i][col_name]
                })
            else:
                data.append({
                    "value": ""
                })

        datas.append(data)

    TableData(
        table=table,
        header=header,
        data_original=datas,
        data=datas,
    ).save()


# NOTE: gs_type is one of Table.LIMAYE200, Table.T2D, ecc...
@app.task(bind=True)
def load_gs_tables(self, gs_type):
    print(gs_type," TIPO GS")
    try:
        print("NAMES")
        file_names = {
            GoldStandardsEnum.T2D.value: json.loads(Assets().get_asset("tables/T2Dv2/t2dTables.json")),
            GoldStandardsEnum.Limaye200.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/Limaye200/converted/"))
            ),
            GoldStandardsEnum.limaye.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/limayeoutput/converted/"))
            ),
            GoldStandardsEnum.semantification.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/semantification/converted/"))
            ),
            GoldStandardsEnum.semr1.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/semr1output/converted/"))
            ),
            GoldStandardsEnum.semr2.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/semr2output/converted/"))
            ),
            GoldStandardsEnum.semr3.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/semr3output/converted/"))
            ),
            GoldStandardsEnum.semr4.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/semr4output/converted/"))
            ),
            GoldStandardsEnum.wiki.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/wikioutput/converted/"))
            ),
            GoldStandardsEnum.t2.value: list(map(
                lambda path: os.path.splitext(os.path.basename(path))[0],
                Assets().list_files("tables/t2output/converted/"))
            ),
            GoldStandardsEnum.CHALLENGE.value: json.loads(Assets().get_asset("tables/Round2/round2Tables.json")),
        }.get(gs_type, [])
        print(file_names)
        if len(file_names) > 0:
            __load_gs_tables({  # Type,           "directory"
                                 GoldStandardsEnum.T2D.value: (GoldStandardsEnum.T2D, "T2Dv2"),
                                 GoldStandardsEnum.Limaye200.value: (GoldStandardsEnum.Limaye200, "Limaye200"),
                                 GoldStandardsEnum.CHALLENGE.value: (GoldStandardsEnum.CHALLENGE, "Round2"),
                                 GoldStandardsEnum.limaye.value: (GoldStandardsEnum.limaye, "limayeoutput"),
                                 GoldStandardsEnum.semantification.value: (GoldStandardsEnum.semantification, "semantificationoutput"),
                                 GoldStandardsEnum.semr1.value: (GoldStandardsEnum.semr1, "semr1output"),
                                 GoldStandardsEnum.semr2.value: (GoldStandardsEnum.semr2, "semr2output"),
                                 GoldStandardsEnum.semr3.value: (GoldStandardsEnum.semr3, "semr3output"),
                                 GoldStandardsEnum.semr4.value: (GoldStandardsEnum.semr4, "semr4output"),
                                 GoldStandardsEnum.t2.value: (GoldStandardsEnum.t2, "t2output"),
                                 GoldStandardsEnum.wiki.value: (GoldStandardsEnum.wiki, "wikioutput")
                             }.get(gs_type, None), file_names)

            state = ServerState.objects.get()
            if gs_type == GoldStandardsEnum.T2D.value:
                state.loaded_t2d = True
            elif gs_type == GoldStandardsEnum.Limaye200.value:
                state.loaded_limaye200 = True
            elif gs_type == GoldStandardsEnum.CHALLENGE.value:
                state.loaded_challenge = True
            elif gs_type == GoldStandardsEnum.semantification.value:
                state.loaded_semantification = True    
            elif gs_type == GoldStandardsEnum.limaye.value:
                state.loaded_limaye = True
            elif gs_type == GoldStandardsEnum.semr1.value:
                state.loaded_semr1 = True
            elif gs_type == GoldStandardsEnum.semr2.value:
                state.loaded_semr2 = True
            elif gs_type == GoldStandardsEnum.semr3.value:
                state.loaded_semr3 = True
            elif gs_type == GoldStandardsEnum.semr4.value:
                state.loaded_semr4 = True  
            elif gs_type == GoldStandardsEnum.wiki.value:
                state.loaded_wiki = True
            elif gs_type == GoldStandardsEnum.t2.value:
                state.loaded_t2 = True               

            state.save()

            state = AsyncResult(self.request.id).state
            if state == "PENDING":
                state = "SUCCESS"
            Internal.general().notify_import_status(state)
        else:
            print("ELSE FAIL")
            Internal.general().notify_import_status("FAILURE")
            return None
    except FileNotFoundError as e:
        print(e)
        Internal.general().notify_import_status("FAILURE")


def __load_gs_tables(gs_type, file_names):
    assert (gs_type is not None)
    assert (len(file_names) > 0)
    tables = []
    table_data_builders = []
    for i in range(0, len(file_names)):
        content = Assets().get_asset("tables/{gs}/converted/{file}.json".format(
            gs=gs_type[1],
            file=file_names[i],
        ))

        # load_table(file_names[i], "{file}.json".format(file=file_names[i]), gs_type[0], content)
        table, table_data_builder = _create_table(file_names[i], "{file}.json".format(file=file_names[i]), gs_type[0].value,
                                                  content)
        tables.append(table)
        table_data_builders.append(table_data_builder)

    curr_table_count = Table.objects.count()
    total_table_count = curr_table_count + len(tables)
    for i, table in enumerate(tables):
        table.save()
        table_data_builders[i](table).save()

        Internal.general().notify_import_progress(curr_table_count + i, table.gs_type, total_table_count)
        # Table.objects.bulk_create(tables)


# NOTE: gs_type is one of Table.LIMAYE200, Table.T2D, ecc...
@app.task(bind=True)
def delete_gs_tables(self, gs_type):
    Table.objects.filter(gs_type=gs_type).delete()

    state = ServerState.objects.get()
    if gs_type == GoldStandardsEnum.T2D.value:
        state.loaded_t2d = False
    elif gs_type == GoldStandardsEnum.Limaye200.value:
        state.loaded_limaye200 = False
    elif gs_type == GoldStandardsEnum.CHALLENGE.value:
        state.loaded_challenge = False
    elif gs_type == GoldStandardsEnum.semantification.value:
        state.loaded_semantification = False    
    elif gs_type == GoldStandardsEnum.limaye.value:
        state.loaded_limaye = False
    elif gs_type == GoldStandardsEnum.semr1.value:
        state.loaded_semr1 = False
    elif gs_type == GoldStandardsEnum.semr2.value:
        state.loaded_semr2 = False
    elif gs_type == GoldStandardsEnum.semr3.value:
        state.loaded_semr3 = False
    elif gs_type == GoldStandardsEnum.semr4.value:
        state.loaded_semr4 = False  
    elif gs_type == GoldStandardsEnum.wiki.value:
        state.loaded_wiki = False
    elif gs_type == GoldStandardsEnum.t2.value:
        state.loaded_t2 = False    

    state.save()

    state = AsyncResult(self.request.id).state
    if state == "PENDING":
        state = "SUCCESS"
    Internal.general().notify_import_status(state)
