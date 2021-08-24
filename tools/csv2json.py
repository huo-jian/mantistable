import os
import sys
import json
import signal

from csv_parsing import generate_json

filepaths = []
detected_errors = 0
written_files = 0

def on_exit_signal(sig, frame):
    print("")
    print("Operation interrupted by user")
    print_logs()
    sys.exit(0)
    
def print_logs():
    print("")
    print("-" * 20)
    print(f"Succeded: {written_files}/{len(filepaths)}. Errors: {detected_errors}")

def convert_csv(input_dir, output_dir):
    global filepaths
    global detected_errors
    global written_files
    
    filepaths = sorted(list(filter(lambda path: path.endswith(".csv"), os.listdir(input_dir))))
    #filepaths = ["List_of_teams_and_cyclists_in_the_2005_Tour_de_France#9.csv"]
    for idx, filepath in enumerate(filepaths):
        print(" " * (len(filepaths[idx - 1]) + 4), end="\r")
        print(f"{int(100 * (idx + 1) / len(filepaths))}%", filepath, end='\r', flush=True)
        json_result = generate_json.csv_to_json(input_dir + filepath)

        #print(json_result)

        try:
            json.loads(json_result)

            with open(output_dir + filepath[0:-3] + "json", "w") as json_file:
                json_file.write(json_result)

            written_files += 1
        except json.JSONDecodeError as e:
            print("")
            print("-" * 20)
            print("Error", filepath)
            print(json_result)
            print("-" * 20)
            print("")
            detected_errors += 1

def get_usage():
    return f"""Usage: {sys.argv[0]} CSV_INPUT_DIRECTORY JSON_OUTPUT_DIRECTORY
Convert csv Challenge dataset into json mantistable format and sanitize content."""


def main():    
    def is_valid_dir(dir_path):
        return os.path.isdir(dir_path) and os.path.exists(dir_path)

    signal.signal(signal.SIGINT, on_exit_signal)

    if len(sys.argv) == 2 and sys.argv[1] == "--help" or sys.argv[1] == "-h":
        print(get_usage())
        sys.exit(0)
    elif len(sys.argv) != 3:
        print(f"{sys.argv[0]}: wrong input")
        print(f"{sys.argv[0]}: Use \"{sys.argv[0]} --help\" for more informations")
        sys.exit(-1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if is_valid_dir(input_dir) and is_valid_dir(output_dir):
        convert_csv(input_dir, output_dir)
        print_logs()
    else:
        print(f"{sys.argv[0]}: wrong directory path")


if __name__ == '__main__':
    main()
