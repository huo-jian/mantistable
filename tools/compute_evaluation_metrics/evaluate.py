import json

target = json.loads(open("./target.json", "r").read())
gt = json.loads(open("./groundtruth.json", "r").read())

def main():
    eval()

def eval():
    tables = read_annotation_from_mongo_export("infotable_data.json")
    table_type = {}
    subject = {}
    for table in tables:
        if table["table_name"] not in target:
            continue
        table_type[table["table_name"]] = {}
        for ne_col in table["ne_cols"]:
            key_index = str(ne_col["index"])
            if key_index not in gt[table["table_name"]]:
                continue 
            subject[table["table_name"]] = table["subject_col"]    
            gc = ne_col["global_concepts"]
            table_type[table["table_name"]][key_index] = ne_col["type"][28:]      
    P, R, F1, subject_accuracy, error, error2 = get_metrics(table_type, gt, subject, target)
    print("METRCIS:")
    print(f'P: {P} R: {R} F1: {F1}') 
    print(f'Subject Accuracy: {subject_accuracy}')
    return P, R

def write_file(file_name, result, is_json=False):
    if is_json:
        result = json.dumps(result, indent=4)
    with open(file_name, mode='w') as out:
        out.write(result)    

def read_annotation_from_mongo_export(filename):        
    file = open(filename, "r")
    contents = file.read()
    lines = contents.split('\n')
    lines.pop()
    return [json.loads(line) for line in lines]    

def get_metrics(annotations, groundtruth, subject, target):
    perfect_annotations, subject_accuracy, error, error2 = evaluate_cta(annotations, groundtruth, subject, target)
    precision = perfect_annotations / len(annotations)
    recall = perfect_annotations / len(groundtruth)
    try:
        f1 = (2 * precision * recall) / (precision + recall)
    except:
        f1 = 0
    return round(precision, 4), round(recall, 4), round(f1, 4), subject_accuracy, error, error2

def evaluate_cta(annotations, groundtruth, subject, target):
    error = []
    error2 = []
    perfect_annotations = 0
    subject_accuracy = 0
    for table_name in annotations:
        if subject[table_name] == target[table_name]:
            subject_accuracy += 1
        else:
            error2.append({
                "tableID":table_name,
                "mantis_index": subject[table_name],
                "groundtruth": target[table_name]
            }
            )    
        for col in annotations[table_name]:
            if annotations[table_name][col] == groundtruth[table_name][col] or groundtruth[table_name][col] == "Country":
                perfect_annotations += 1
            else:
                error.append({
                    "tableID":table_name,
                    "mantis_annotations": annotations[table_name][col],
                    "groundtruth": groundtruth[table_name][col]
                })
          
    subject_accuracy = subject_accuracy/len(target)              
    return perfect_annotations, subject_accuracy, error, error2    

if __name__ == '__main__':
    main()