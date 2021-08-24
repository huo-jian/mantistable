# /bin/python

import copy
import json
import os

from utils import utils


bad_tables = [
    "2015%E2%80%9316_Liga_Leumit#2",
    "Hong_Kong_Island_(constituency)#0",
    "Irish_House_of_Commons#0",
    "Kinniku_Banzuke#0",
    "List_of_Algerian_records_in_athletics#1",
    "List_of_European_tornadoes_in_2014#5",
    "List_of_Game_of_Thrones_characters#18",
    "List_of_Grand_National_first_four_placings#0",
    "List_of_James_Bond_allies#0",
    "List_of_James_Bond_allies#Ling#0",
    "List_of_Lost_characters#Dharma_Initiative_members#6",
    "List_of_Lost_characters#Leslie_Arzt#1",
    "List_of_Lost_characters#List_of_recurring_flashback_characters#3",
    "List_of_Lost_characters#Widmore_and_employees#6",
    "List_of_Montserrat_records_in_athletics#0",
    "List_of_My_Little_Pony_characters#Flutter_Ponies#3",
    "List_of_My_Little_Pony_characters#Gilda#3",
    "List_of_NFL_franchise_post-season_droughts#6",
    "List_of_NFL_franchise_post-season_streaks#12",
    "List_of_North,_Central_American_and_Caribbean_records_in_athletics#3",
    "List_of_Paramount_Pictures_films#10",
    "List_of_Rhode_Island_Public_Transit_Authority_routes#35#0",
    "List_of_Rome_characters#Levi#0",
    "List_of_Ryder_Cup_matches#0",
    "List_of_S%C3%BCper_Lig_top_scorers#0",
    "List_of_Saudi_Arabian_records_in_athletics#1",
    "List_of_Seychellois_records_in_athletics#3",
    "List_of_Star_Trek_characters_(A%E2%80%93F)#Chaotica#4",
    "List_of_Star_Trek_characters_(A%E2%80%93F)#Duras.2C_son_of_Ja.27rod#1",
    "List_of_Star_Trek_characters_(N%E2%80%93S)#Norah_Satie#5",
    "List_of_Teen_Wolf_characters#Jackson_Whittemore#3",
    "List_of_The_Walking_Dead_(TV_series)_characters#Main_Characters#7",
    "List_of_The_Walking_Dead_(TV_series)_characters#The_Claimers#7",
    "List_of_UK_R%26B_Albums_Chart_number_ones_of_1999#0",
    "List_of_United_States_federal_executive_orders#0",
    "List_of_United_States_tornadoes_from_July_to_September_2012#46",
    "List_of_WBA_world_champions#6",
    "List_of_Weber_State_University_people#0",
    "List_of_Your_Song_episodes#0",
    "List_of_administrators,_archbishops,_bishops,_and_prince-archbishops_of_Bremen#2",
    "List_of_archive_formats#1",
    "List_of_awards_and_nominations_received_by_Anah%C3%AD#14",
    "List_of_awards_and_nominations_received_by_Cate_Blanchett#23",
    "List_of_awards_and_nominations_received_by_Justin_Bieber#0",
    "List_of_best-selling_albums_by_country#23",
    "Tributaries_of_the_Murrumbidgee_River#0",
]


def csv_to_json(filepath):
    rows = utils.get_csv_content_alt(filepath)

    # Custom fix
    if os.path.basename(filepath)[0:-4] in bad_tables:
        rows = list(filter(lambda item: len(item) > 1, rows))

    cols_len = [len(col) for col in rows]
    col_count = utils.get_max_freq_column_count(cols_len)
    if len(rows) == 1:
        header = [f"NO-HEADER{i}" for i in range(0, len(rows[0]))]
        content = rows[0]
    else:
        # print(col_count, freq, freq_map)

        header = rows[0]
        # Empty header
        for i, h in enumerate(header):
            if h == "" or h == r'""':
                header[i] = f"NO-HEADER{i}"

        # Repeated keys
        tmp_header = []
        for i, h in enumerate(header):
            if h in tmp_header:
                header[i] = f"{h} {i}"
            else:
                tmp_header.append(h)

        if len(header) <= 1:
            header = rows[1]
        
        """
        for i, h in enumerate(header):
            if h == "" or h == r'""':
                header[i] = f"NO-HEADER{i}"
        """

        if len(header) < col_count:
            tmp = copy.deepcopy(header)
            tmp.extend([f"NO-HEADER{i}" for i in range(len(header), col_count)])
            header = tmp
            content = rows
        else:
            content = rows[1:]

        copy_content = copy.deepcopy(content)
        for i, row in enumerate(content):
            for j in range(0, col_count):
                if j >= len(row):
                    copy_content[i].append("")

        content = copy_content
        
    json_list = [
        {
            utils.sanitize(header[col_idx]): utils.sanitize(row[col_idx])
            for col_idx in range(0, col_count)
        }
        for row_idx, row in enumerate(content)
    ]
    json_str = json.dumps(json_list, indent=4, ensure_ascii=True)
    return json_str
