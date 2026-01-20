import csv
import json
import os
import re
import tarfile
from collections import defaultdict
from pathlib import Path
import pandas as pd


################USELESS################################
def compare_csv_columns(csv1, csv2, col1, col2, ignore_case=False):
    """
    Reads a specified column from each of two CSV files and compares their values.

    This function extracts the column named col1 from the first CSV and col2 from the second CSV,
    and calculates which values exist only in csv1 and which only exist in csv2.

    Parameters:
        csv1 (str): Path to the first CSV file.
        csv2 (str): Path to the second CSV file.
        col1 (str): Name of the column to read from the first CSV.
        col2 (str): Name of the column to read from the second CSV.
        ignore_case (bool): If True, performs a case-insensitive comparison (defaults to True).

    Returns:
        dict: A dictionary with keys 'only_in_csv1' and 'only_in_csv2' containing the unique values.
    """
    # Load the CSV files with error handling
    try:
        df1 = pd.read_csv(csv1)
        df2 = pd.read_csv(csv2)
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return None

    # Check if the specified columns exist
    if col1 not in df1.columns:
        print(f"Column '{col1}' not found in the first CSV. Available columns: {df1.columns.tolist()}")
        return None
    if col2 not in df2.columns:
        print(f"Column '{col2}' not found in the second CSV. Available columns: {df2.columns.tolist()}")
        return None

    # Extract unique non-null values from the columns
    try:
        values1 = df1[col1].dropna().unique()
        values2 = df2[col2].dropna().unique()
    except Exception as e:
        print(f"Error processing the columns: {e}")
        return None

    # Optionally convert the values to lower case for case-insensitive comparison
    if ignore_case:
        set1 = set(str(value).lower() for value in values1)
        set2 = set(str(value).lower() for value in values2)
    else:
        set1 = set(values1)
        set2 = set(values2)

    # Calculate the differences between the sets
    only_in_csv1 = set1 - set2
    only_in_csv2 = set2 - set1

    # Debug output: print the results to the console.
    print(f"Values only in {csv1} (column '{col1}'): {only_in_csv1}")
    print(f"Values only in {csv2} (column '{col2}'): {only_in_csv2}")

    return {"only_in_csv1": only_in_csv1, "only_in_csv2": only_in_csv2}


def print_csv_column_matches(csv1, csv2, col1, col2, ignore_case=True):
    """
    Reads a specified column from each of two CSV files and prints the values that match (i.e. the common values).

    This function:
      - Loads the two CSV files.
      - Verifies that the specified columns exist in each file.
      - Extracts unique, non-null values from the specified columns.
      - Optionally converts the values to lower case for a case-insensitive comparison.
      - Computes the intersection of both sets (common values).
      - Prints the matching values and their total count, then returns the set of matching values.

    Parameters:
        csv1 (str): Path to the first CSV file.
        csv2 (str): Path to the second CSV file.
        col1 (str): Name of the column to read from the first CSV.
        col2 (str): Name of the column to read from the second CSV.
        ignore_case (bool): If True, performs a case-insensitive comparison (defaults to True).

    Returns:
        set: A set containing the common (matching) values from both columns.
    """
    # Load the CSV files
    try:
        df1 = pd.read_csv(csv1)
        df2 = pd.read_csv(csv2)
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return None

    # Verify that the specified columns exist
    if col1 not in df1.columns:
        print(f"Column '{col1}' not found in {csv1}. Available columns: {df1.columns.tolist()}")
        return None
    if col2 not in df2.columns:
        print(f"Column '{col2}' not found in {csv2}. Available columns: {df2.columns.tolist()}")
        return None

    # Extract unique, non-null values from each column
    values1 = df1[col1].dropna().unique()
    values2 = df2[col2].dropna().unique()

    # Optionally convert values to lower case for a case-insensitive comparison
    if ignore_case:
        set1 = set(str(value).lower() for value in values1)
        set2 = set(str(value).lower() for value in values2)
    else:
        set1 = set(values1)
        set2 = set(values2)

    # Calculate the common values between the two sets
    common_values = set1.intersection(set2)

    # Print the matching values and the count
    print(f"Common (matching) values in '{col1}' from {csv1} and '{col2}' from {csv2}:")
    print(common_values)
    print(f"Number of matches: {len(common_values)}")

    return common_values


def find_duplicate_groups(csv_path, ignore_columns=None, add_one=False):
    """
    Reads a CSV file and groups rows that are duplicates based on all columns
    except those specified in ignore_columns. This function returns a dictionary where
    each key is a tuple of values from the columns used for grouping, and each value
    is a list of row numbers that share that combination (i.e., are duplicates).

    Parameters:
        csv_path (str): Path to the CSV file.
        ignore_columns (list or None): A list of columns to ignore when checking for duplicates.
                                       Default is None (which means all columns are checked).
        add_one (bool): If True, converts 0-based index to 1-based numbering (like Excel).
                        Default is False.

    Returns:
        dict: A dictionary where each key is a tuple containing the group values and each value
              is a list of row indices (or row numbers if add_one=True) that share those values.
              Only groups with more than one row are included.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading CSV file '{csv_path}': {e}")
        return None

    # Set ignored columns to an empty list if not provided.
    if ignore_columns is None:
        ignore_columns = []

    # Columns to check for duplicates.
    columns_to_check = [col for col in df.columns if col not in ignore_columns]

    duplicate_groups = {}
    # Group the DataFrame based on the selected columns.
    grouped = df.groupby(columns_to_check, dropna=False)

    # Iterate over each group; if a group contains more than 1 row, it's a duplicate group.
    for group_key, group_df in grouped:
        if len(group_df) > 1:
            indices = group_df.index.tolist()
            if add_one:
                indices = [i + 1 for i in indices]
            duplicate_groups[group_key] = indices

    # Print the duplicate groups so you can see which rows are paired together.
    if duplicate_groups:
        print("Found duplicate groups:")
        for key, indices in duplicate_groups.items():
            print(f"Group {key}: rows {indices}")
    else:
        print("No duplicates found based on the specified columns.")

    return duplicate_groups
#############################################

def count_rows(csv_path):
    df = pd.read_csv(csv_path)
    row_count = len(df)
    return row_count


def count_operator_occurrences(csv_path: str, output_path: str = None):
    """
    Reads a CSV file and prints how many times each unique value appears
    in the 'operator' column. Optionally saves the result to a new CSV file.

    Args:
        csv_path (str): Path to the input CSV file.
        output_path (str, optional): Path to save the result as a CSV file.
    """
    # Read the CSV file
    df = pd.read_csv(csv_path)

    # Count occurrences of each value in 'operator' column
    operator_counts = df['Operator'].value_counts()

    # Print the result
    print("Operator occurrences:\n")
    print(operator_counts)


def extract_findings(json_dir_path, output_csv_path):
    base_path = Path(json_dir_path)
    file_findings = {}

    for contract_folder in base_path.iterdir():
        if not contract_folder.is_dir():
            continue

        result_tar_path = contract_folder / "result.tar"
        if not result_tar_path.exists():
            # print(f"❌ Nessun result.tar in {contract_folder.name}")
            continue

        try:
            # Estrai il file "output.json" da result.tar
            with tarfile.open(result_tar_path, "r") as tar:
                output_json_file = None
                for member in tar.getmembers():
                    if member.name.endswith("output.json"):
                        output_json_file = member
                        break

                if not output_json_file:
                    print(f"⚠️  Nessun output.json trovato in {result_tar_path}")
                    file_findings[contract_folder.name] = {}
                    continue

                extracted = tar.extractfile(output_json_file)
                data = json.load(extracted)

            # Processa il JSON
            detectors = data.get("results", {}).get("detectors", [])
            if not detectors:
                print(f"⚠️  Nessun detector nel file output.json per {contract_folder.name}")
                file_findings[contract_folder.name] = {}
                continue

            findings_counter = defaultdict(int)

            for detector in detectors:
                check_type = detector.get("check")
                if check_type:
                    findings_counter[check_type] += 1
                else:
                    print(f"⚠️  Detector senza 'check' in {contract_folder.name}")

            file_findings[contract_folder.name] = findings_counter

        except Exception as e:
            print(f"❌ Errore nel file {result_tar_path}: {e}")
            file_findings[contract_folder.name] = {}

    # Scrittura CSV
    with open(output_csv_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["nome", "findings"])

        for contract_name, checks in file_findings.items():
            findings_json = json.dumps(checks) if checks else "{}"
            writer.writerow([contract_name, findings_json])

    print(f"\n✅ CSV generato con successo: {output_csv_path}")


def parse_findings(findings_str):
    """Parses a findings string like '"check": 2, "other": 1' into a dict."""
    findings = defaultdict(int)
    if pd.isna(findings_str) or not str(findings_str).strip():
        return findings
    pattern = r'"([^"]+)":\s*(-?\d+)'
    for check, value in re.findall(pattern, findings_str):
        findings[check] += int(value)
    return findings


def compute_diff(baseline, result):
    """Returns dict of differences between baseline and result findings."""
    diff = {}
    all_keys = set(baseline) | set(result)
    for key in all_keys:
        base_val = baseline.get(key, 0)
        res_val = result.get(key, 0)
        delta = res_val - base_val
        if delta != 0:
            diff[key] = delta
    return diff


def _canonical_name(raw):
    """
    Restituisce il nome file in forma canonica:
        - basename (niente path)
        - tagliato al primo '-'
        - tutto lower‑case
        - termina con '.sol'
        - niente spazi esterni
    """
    if pd.isna(raw):
        return ""

    name = os.path.basename(str(raw).strip())
    name = name.split("-", 1)[0]
    name = name.lower()
    if not name.endswith(".sol"):
        name += ".sol"

    return name


def process_findings_diff(baseline_csv, result_csv, output_csv):
    """
    Confronta baseline e result in modo robusto:
        - normalizza le colonne
        - usa _canonical_name per i confronti
        - salva le differenze in output_csv
        - stampa quanti file del baseline non hanno match
    """
    # Carica i CSV
    df_base = pd.read_csv(baseline_csv)
    df_res  = pd.read_csv(result_csv)

    # Normalizza i nomi colonna
    df_base.columns = df_base.columns.str.strip().str.lower()
    df_res.columns  = df_res.columns.str.strip().str.lower()

    # Crea la colonna “canon” in entrambi i dataframe
    df_base["canon"] = df_base["nome"].apply(_canonical_name)
    df_res["canon"]  = df_res["nome"].apply(_canonical_name)

    # (Opzionale) indicizza il result su canon per lookup O(1)
    res_groups = df_res.groupby("canon")

    output_rows  = []
    no_match_cnt = 0

    for _, base_row in df_base.iterrows():
        canon_key   = base_row["canon"]
        fullname_x  = base_row["nome"].strip()
        findings_x  = str(base_row.get("findings", "")).strip()
        base_findings = parse_findings(findings_x)

        # Recupera (se esistono) tutti i result con lo stesso canon
        if canon_key in res_groups.groups:
            matching_rows = res_groups.get_group(canon_key)
        else:
            matching_rows = pd.DataFrame()   # vuoto

        if matching_rows.empty:
            print(f"[!] No match found for file: {fullname_x}")
            no_match_cnt += 1
            continue

        # Per ogni riga matchata calcola la diff
        for _, res_row in matching_rows.iterrows():
            fullname_y      = res_row["nome"]
            findings_y      = str(res_row.get("findings", "")).strip()
            result_findings = parse_findings(findings_y)

            diff = compute_diff(base_findings, result_findings)

            output_rows.append({
                "fullname_y": fullname_x,
                "fullname_x": fullname_y,
                "findings_y": findings_x,
                "findings_x": findings_y,
                "operator":   res_row.get("operator", ""),
                "differences": json.dumps(diff, ensure_ascii=False)
            })

    # Scrittura output
    if output_rows:
        pd.DataFrame(output_rows).to_csv(output_csv, index=False)
        print(f"✅ Diff salvato in: {output_csv}")
    else:
        print("⚠️ Nessun dato corrispondente. Output CSV non creato.")

    # Riepilogo finale
    print(f"📄 Contratti senza match: {no_match_cnt}")


def update_operator_column_inplace(hash_operator_csv, target_csv):
    """
    Updates the target CSV in place by adding a new column 'Operator'.

    The hash_operator CSV is expected to have at least two columns:
        - 'Hash'
        - 'Operator'
    The target CSV is expected to have at least one column:
        - 'name'

    For each unique 'Hash' in the hash_operator CSV, the function checks if that hash (as a substring)
    exists in the 'name' field of each row in the target CSV. When a match is found, the corresponding
    'Operator' from the hash_operator CSV is appended to the new 'Operator' column in the target CSV.

    Finally, the target CSV is overwritten with the updated data, so it now includes the 'Operator' column.

    Parameters:
        hash_operator_csv (str): Path to the CSV file with 'Hash' and 'Operator' columns.
        target_csv (str): Path to the target CSV file with the 'name' column.

    Returns:
        None
    """
    # Read the CSV files into DataFrames.
    df_hash = pd.read_csv(hash_operator_csv)
    df_target = pd.read_csv(target_csv)

    # Create a dictionary mapping for each unique 'Hash' to its corresponding 'Operator' value(s).
    # If multiple entries exist for the same Hash, unique operators are concatenated by commas.
    hash_operator_dict = df_hash.groupby('Hash')['Operator'].agg(
        lambda x: ','.join(x.astype(str).unique())
    ).to_dict()

    # Function to find matching operators for a given 'name' value.
    def find_operator(name_value):
        matches = []
        for hash_val, operator in hash_operator_dict.items():
            # Check if the hash value appears as a substring in the name_value.
            if str(hash_val) in str(name_value):
                matches.append(operator)
        return ','.join(matches) if matches else ''

    # Apply the matching function to every row in the 'name' column.
    df_target['Operator'] = df_target['nome'].apply(find_operator)

    # Overwrite the target CSV with the updated DataFrame (i.e., with the new 'Operator' column).
    df_target.to_csv(target_csv, index=False)
    print(f"Processing complete. The file '{target_csv}' has been updated with the 'Operator' column.")


def analyze_differences_column(csv_path, column="differences"):
    df = pd.read_csv(csv_path)

    summary = defaultdict(lambda: {"positive": 0, "negative": 0})

    for _, row in df.iterrows():
        cell = row.get(column)
        if not isinstance(cell, str) or cell.strip() == "":
            continue
        try:
            json_data = json.loads(cell)
            for key, value in json_data.items():
                if isinstance(value, (int, float)):
                    if value >= 0:
                        summary[key]["positive"] += value
                    else:
                        summary[key]["negative"] += value
        except json.JSONDecodeError:
            continue

    # Prepare and sort final output
    formatted_output = {}
    combined = []

    for key, values in summary.items():
        if values["negative"] != 0:
            combined.append((f"{key}_", values["negative"]))
        if values["positive"] != 0:
            combined.append((key, values["positive"]))

    # Sort by value
    combined.sort(key=lambda x: x[1])

    # Build ordered dict
    for k, v in combined:
        formatted_output[k] = v

    print("Removed/Added Patterns:", formatted_output)
    return formatted_output


def filter_by_operator(input_file: str, output_file: str, operator_value: str):
    """
    Filters rows by a specific value in the 'operator' column
    and writes the result to a new CSV file.

    :param input_file: Path to the input CSV file
    :param output_file: Path to the output CSV file
    :param operator_value: The operator value to filter by
    """
    df = pd.read_csv(input_file)

    if 'operator' not in df.columns:
        raise ValueError("Column 'operator' not found in the CSV file.")

    filtered_df = df[df['operator'] == operator_value]
    filtered_df.to_csv(output_file, index=False)
    #print(f"Filtered CSV saved to '{output_file}' with {len(filtered_df)} rows for operator '{operator_value}'.")


def count_tp_fn(csv_path, keyword):
    df = pd.read_csv(csv_path)
    true_positives = 0
    false_negatives = 0
    fn_rows = []

    for index, cell in df['differences'].dropna().items():
        try:
            differences = json.loads(cell)
            if any(keyword in key for key in differences.keys()):
                true_positives += 1
            else:
                false_negatives += 1
                fn_rows.append(index)
        except json.JSONDecodeError:
            false_negatives += 1
            fn_rows.append(index)

    print(f"TP: {true_positives}")
    print(f"FN: {false_negatives}")
    # print(f"Total: {true_positives + false_negatives}")
    # print(f"False Negative rows: {fn_rows}")









sumo_mutation_results = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/sumo/results/sumo_results.csv'

json_folder_original = '/Users/matteocicalese/results/slither-0.10.4/slither_original'
result_original = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/analysis/resultOriginal.csv'
json_folder_mutated = '/Users/matteocicalese/results/slither-0.10.4/slither_mutated'
result_mutated = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/analysis/resultMutated.csv'

diffs = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/analysis/differences.csv'
diffs_filtered_by_operator = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/analysis/differences_filtered.csv'

"""
# Mutation types count
count_operator_occurrences(sumo_mutation_results)

# Findings extraction
extract_findings(json_folder_original, result_original)
extract_findings(json_folder_mutated, result_mutated)

# Operator columns appending
update_operator_column_inplace(sumo_mutation_results, result_mutated)

# Diffs calculation (Errors: "No match found for file" means that some baseline contracts do not have a mutated version)
process_findings_diff(result_original, result_mutated, diffs)


# Results analysis
print(f"Baseline Contracts: {count_rows(result_original)}")
print(f"Mutated Contracts: {count_rows(result_mutated)}")

# Analysis by operator
# filter_by_operator(diffs, diffs_filtered_by_operator, operator_value="TD")
# analyze_differences_column(diffs_filtered_by_operator)
# count_tp_fn(diffs_filtered_by_operator, "timestamp")
"""


