import math

from mantistable.models import Table, InfoTable
from mantistable.process.columns_analysis.subject_column_detection.metric import EMCMetric, UCMetric, AWMetric, \
    DFMetric


class SubDetection:
    def __init__(self):
        self.sub_col_score = []

    def get_sub_col(self, table_id):
        table = Table.objects.get(id=table_id)
        score_list = []
        first_ne = 0
        info_table = InfoTable.objects.get(table=table)
        ne_cols = info_table.ne_cols

        metrics = {}
        for i, necol in enumerate(ne_cols):
            element = {}
            col_idx = necol["index"]

            if i == 0:
                first_ne = col_idx

            metric_map = {
                "emc": EMCMetric(table, col_idx),
                "uc": UCMetric(table, col_idx),
                "aw": AWMetric(table, col_idx),
                "df": DFMetric(col_idx, first_ne),
            }

            for metric_key in metric_map:
                if metric_key not in metrics:
                    metrics[metric_key] = []

                score = metric_map[metric_key].compute()
                metrics[metric_key].append(score)
                element[metric_key] = score
                
            score_list.append(element)

        for i, necol in enumerate(ne_cols):
            for metric_key in metric_map:
                key_norm = f"{metric_key}Norm"
                score_norm = metric_map[metric_key].normalized(metrics[metric_key][i], metrics[metric_key])
                metrics[key_norm] = score_norm
                element[key_norm] = score_norm
                
            score_list[i].update(element)

        ne_cols_count = len(ne_cols)

        sub_col_score_paper = []
        for i in range(0, ne_cols_count):
            self.sub_col_score.append((2 * score_list[i]["ucNorm"] + score_list[i]["awNorm"] - score_list[i]["emcNorm"]) / math.sqrt(score_list[i]["dfNorm"]))
            score_list[i]["finalScore"] = self.sub_col_score[i]

            # no emc, no uc, no df, no aw
            sub_col_score_paper.append([
                (2 * score_list[i]["ucNorm"] + score_list[i]["awNorm"]) / math.sqrt(score_list[i]["dfNorm"]),
                (score_list[i]["awNorm"] - score_list[i]["emcNorm"]) / math.sqrt(score_list[i]["dfNorm"]),
                (2 * score_list[i]["ucNorm"] + score_list[i]["awNorm"] - score_list[i]["emcNorm"]),
                (2 * score_list[i]["ucNorm"] - score_list[i]["emcNorm"]) / math.sqrt(score_list[i]["dfNorm"])
            ])
            score_list[i]["finalScore_paper"] = sub_col_score_paper[i]

        for i in range(0, len(ne_cols)):
            ne_cols[i]["score"] = score_list[i]

        if len(self.sub_col_score) > 0:
            final_score_max = max(self.sub_col_score)
            tmp = list(filter(lambda item: item["score"]["finalScore"] == final_score_max, ne_cols))
            if len(tmp) > 0:
                index_sub_col = tmp[0]["index"]
            else:
                index_sub_col = None
        else:
            index_sub_col = None

        index_sub_cols = []
        if len(sub_col_score_paper) > 0:
            for score_idx in range(0, 4):
                final_score_max = max([score[score_idx] for score in sub_col_score_paper])
                tmp = list(filter(lambda item: item["score"]["finalScore_paper"][score_idx] == final_score_max, ne_cols))
                if len(tmp) > 0:
                    index_sub_col_paper = tmp[0]["index"]
                else:
                    index_sub_col_paper = None

                index_sub_cols.append(index_sub_col_paper)
        else:
            index_sub_cols = [None, None, None, None]

        info_table.ne_cols = ne_cols
        info_table.subject_col = index_sub_col
        info_table.subject_cols_paper = index_sub_cols
        info_table.save()
