import ast
import csv
import json
import os
import re
import shutil
from collections import defaultdict, Counter
from pathlib import Path
import tarfile

import pandas as pd


def clean_folder(folder_path):
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a valid folder.")
        return

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            print(f"Error while deleting {item_path}: {e}")

    print(f"Contents of folder '{folder_path}' successfully deleted.")


def sample_by_operator(input_file: str, output_file: str, extracted_rows: int = 500):
    """
    Legge un file CSV, filtra al massimo `max_righe_per_operatore` righe per ciascun valore
    unico della colonna 'operator', e salva il risultato in un nuovo file CSV.

    :param input_file: Percorso del file CSV di input
    :param output_file: Percorso del file CSV di output
    :param extracted_rows: Numero massimo di righe per ogni operatore (default: 500)
    """
    df = pd.read_csv(input_file)

    if 'operator' not in df.columns:
        raise ValueError("La colonna 'operator' non esiste nel file CSV.")

    filtered_df = df.groupby('operator').head(extracted_rows)
    filtered_df.to_csv(output_file, index=False)

    print(f"File filtrato salvato come '{output_file}'.")

def count_rows_per_operator(input_file: str):
    """
    Conta il numero di righe per ciascun valore unico della colonna 'operator'.

    :param input_file: Percorso del file CSV di input
    :return: DataFrame con operatori e conteggio righe
    """
    df = pd.read_csv(input_file, usecols=['operator'])

    conteggi = df['operator'].value_counts()

    for operatore, count in conteggi.items():
        print(f"{operatore}: {count}")

# Ritorna un csv che abbia per ogni contratto un'unica mutazione
def unique_contract_mutation_mapper(input_file: str, output_file: str):
    """
    Legge la colonna 'fullname_y' e, se esistono duplicati, restituisce un nuovo CSV
    con solo la prima occorrenza per ogni valore duplicato.

    :param input_file: Percorso del file CSV di input
    :param output_file: Percorso del file CSV di output
    """
    df = pd.read_csv(input_file)

    if 'fullname_y' not in df.columns:
        raise ValueError("La colonna 'fullname_y' non esiste nel file CSV.")

    unique_df = df.drop_duplicates(subset='fullname_y', keep='first')
    unique_df.to_csv(output_file, index=False)


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

    print(f"Filtered CSV saved to '{output_file}' with {len(filtered_df)} rows for operator '{operator_value}'.")


def extract_files_from_csv(csv_path, source_folder, destination_folder, column_name = "fullname_y"):
    # Read the CSV file
    df = pd.read_csv(csv_path)

    # Create the destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)

    # Get the list of filenames to copy
    filenames = df[column_name].dropna().unique()

    # Walk through the source folder recursively and build a lookup of file paths
    file_lookup = {}
    for root, _, files in os.walk(source_folder):
        for name in files:
            file_lookup[name] = os.path.join(root, name)

    # Copy each file if found
    for filename in filenames:
        source_path = file_lookup.get(filename)
        if source_path and os.path.isfile(source_path):
            destination_path = os.path.join(destination_folder, filename)
            shutil.copy2(source_path, destination_path)
        else:
            print(f"File not found: {filename}")


def extract_findings(json_dir_path, output_csv_path):
    base_path = Path(json_dir_path)
    file_findings = {}

    for contract_folder in base_path.iterdir():
        if not contract_folder.is_dir():
            continue

        result_tar_path = contract_folder / "result.tar"
        if not result_tar_path.exists():
            print(f"❌ Nessun result.tar in {contract_folder.name}")
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


def count_findings(csv_path, column_name="findings"):
    # Read the CSV
    df = pd.read_csv(csv_path)

    # Initialize a dictionary to store sums per check
    check_sums = defaultdict(int)

    # Regex to extract: "check-name": value
    pattern = r'"([^"]+)":\s*(\d+)'

    for entry in df[column_name].dropna():
        matches = re.findall(pattern, str(entry))
        for check, value in matches:
            check_sums[check] += int(value)

    # Print results
    print("Total sum per check:")
    for check, total in check_sums.items():
        print(f'"{check}": {total}')


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

def process_findings_diff(baseline_csv, result_csv, output_csv):
    # Load CSVs
    df_base = pd.read_csv(baseline_csv)
    df_res = pd.read_csv(result_csv)

    # Normalize column names
    df_base.columns = df_base.columns.str.strip().str.lower()
    df_res.columns = df_res.columns.str.strip().str.lower()

    output_rows = []

    for _, base_row in df_base.iterrows():
        fullname_x = base_row["nome"]
        findings_x = str(base_row.get("findings", "")).strip()
        base_findings = parse_findings(findings_x)

        # Match by "contains"
        matching_rows = df_res[df_res["nome"].str.contains(re.escape(fullname_x.strip()), na=False, case=False)]

        if matching_rows.empty:
            print(f"[!] No match found for file: {fullname_x}")
            continue

        for _, res_row in matching_rows.iterrows():
            fullname_y = res_row["nome"]
            findings_y = str(res_row.get("findings", "")).strip()
            result_findings = parse_findings(findings_y)

            diff = compute_diff(base_findings, result_findings)

            output_rows.append({
                "fullname_y": fullname_x,
                "fullname_x": fullname_y,
                "findings_y": findings_x,
                "findings_x": findings_y,
                "differences": json.dumps(diff, ensure_ascii=False)
            })

    if output_rows:
        df_output = pd.DataFrame(output_rows)
        df_output.to_csv(output_csv, index=False)
        print(f"✅ Diff saved to: {output_csv}")
    else:
        print("⚠️ No matching data found. Output CSV will not be created.")


def filter_sample(difference_csv, target_csv, output_csv):
    # Carica i due CSV
    df_diff = pd.read_csv(difference_csv)
    df_target = pd.read_csv(target_csv)

    # Pulizia nomi colonna
    df_diff.columns = df_diff.columns.str.strip().str.lower()
    df_target.columns = df_target.columns.str.strip().str.lower()

    # Ottieni lista dei nomi originali da cercare
    original_names = df_diff["fullname_y"].dropna().unique()

    # Crea un filtro per righe che contengono almeno uno dei nomi
    pattern = "|".join(re.escape(name.strip()) for name in original_names)
    filtered_df = df_target[df_target["fullname_y"].str.contains(pattern, na=False, case=False)]

    # Salva su file
    filtered_df.to_csv(output_csv, index=False)
    print(f"✅ Filtered CSV saved to: {output_csv}")


def drop_empty_findings_x(csv_path):
    df = pd.read_csv(csv_path)
    original_len = len(df)
    df = df[df['findings_x'].str.strip() != '{}'].copy()
    new_len = len(df)
    removed = original_len - new_len
    df.to_csv(csv_path, index=False)
    print(f"Removed {removed} rows with compilation errors.")


def convert_column_to_json(csv_path, column_name="differences"):
    # Leggi il CSV
    df = pd.read_csv(csv_path)

    # Funzione di conversione per ogni riga
    def convert_entry(entry):
        try:
            python_dict = ast.literal_eval(entry)
            return json.dumps(python_dict, ensure_ascii=False)
        except Exception as e:
            print(f"[!] Errore nella conversione: {entry} - {e}")
            return ""

    # Applica la conversione
    df[column_name] = df[column_name].apply(convert_entry)

    # Sovrascrive il file originale
    df.to_csv(csv_path, index=False)
    print(f"✅ Colonna '{column_name}' convertita in JSON e salvata in: {csv_path}")


def count_rows(csv_path):
    df = pd.read_csv(csv_path)
    row_count = len(df)
    print(f"Number of rows: {row_count}")
    return row_count


def compute_total_diffs(csv_file: str, column_before: str, column_after: str) -> dict:
    grouped_additions = defaultdict(int)
    grouped_removals = defaultdict(int)

    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader, start=1):
            try:
                json_before = json.loads(row[column_before])
                json_after = json.loads(row[column_after])
            except json.JSONDecodeError as e:
                print(f"JSON parsing error at row {i}: {e}")
                continue

            def extract_named_values(data):
                values = []
                def recurse(obj):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if not isinstance(v, (dict, list)):
                                values.append(f"{k}:{v}")
                            else:
                                recurse(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            recurse(item)
                recurse(data)
                return values

            values_before = extract_named_values(json_before)
            values_after = extract_named_values(json_after)

            counter_before = Counter(values_before)
            counter_after = Counter(values_after)

            all_keys = set(counter_before.keys()) | set(counter_after.keys())
            for key in all_keys:
                before_count = counter_before.get(key, 0)
                after_count = counter_after.get(key, 0)
                delta = after_count - before_count

                match = re.match(r"^(.*?):[^:]+$", key)
                group_key = match.group(1) if match else key

                if delta > 0:
                    grouped_additions[group_key] += delta
                elif delta < 0:
                    grouped_removals[group_key] += abs(delta)

    final_diffs = {}
    for key in sorted(set(grouped_additions.keys()) | set(grouped_removals.keys())):
        added = grouped_additions.get(key, 0)
        removed = grouped_removals.get(key, 0)
        if added:
            final_diffs[key] = added
        if removed:
            final_diffs[f"{key}_"] = -removed

    # Sort final_diffs by value (ascending)
    sorted_diffs = dict(sorted(final_diffs.items(), key=lambda item: item[1]))

    print(sorted_diffs)

    return sorted_diffs


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

    print("Output:", formatted_output)
    return formatted_output


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





contracts_folder = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/contracts'
original_folder = '/Users/matteocicalese/PycharmProjects/smartbugs-wild/contracts'
mutation_results_folder = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/sumo/results'

json_folder_original = '/Users/matteocicalese/results/slither-0.10.4/UR_ORIGINAL'
result_original = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/experiment/resultOriginal.csv'
json_folder_mutated = '/Users/matteocicalese/results/slither-0.10.4/UR1_MUTATED'
result_mutated = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/experiment/resultMutated.csv'

new_experiment_diffs = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/experiment/newExperiment.csv'


dataset = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/data/final_results_analyzed_.csv'
sampled = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/data/sampled.csv'
sampled_filtered_by_operator = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/data/filtered_by_operator.csv'
original_experiment_diffs = '/Users/matteocicalese/PycharmProjects/SuMo-SOlidity-MUtator/experiment/originalExperiment.csv'



class FirstStep:
    def __init__(self):
        # clean_folder(contracts_folder)
        clean_folder(mutation_results_folder)
        # Sampling del csv originale per considerare un numero di contratti gestibile
        sample_by_operator(dataset, sampled, 1500)
        # count_rows_per_operator(dataset)
        # count_rows_per_operator(sampled)

        # Filtro il CSV in base all'operatore che sto analizzando
        filter_by_operator(sampled, sampled_filtered_by_operator, "UR")

        # Estraggo i contratti originali relative alle entry del csv samplato e le copio in contracts per effettuare le mutazione e runnare Slither
        extract_files_from_csv(sampled_filtered_by_operator, original_folder, contracts_folder)

# FirstStep()


# Vengono mutati i contratti estratti e si runna Slither sui contratti originali e quelli mutati
# I contratti originali vengono rianalizzati perchè servono i json affinchè si possa fare il confronto


class SecondStep:
    def __init__(self):
        # Estraggo i findings per fare il confronto con la vecchia run dell'esperimento
        extract_findings(json_folder_original, result_original)
        extract_findings(json_folder_mutated, result_mutated)
        # count_rows(result_original)
        # count_rows(result_mutated)

        # Leggo le colonne dei check rilevati e creo un csv che mappa le differences (diff calcolate con nuova scan slither)
        process_findings_diff(result_original, result_mutated, new_experiment_diffs)
        # count_rows(new_experiment_diffs)

        # Filtro il csv prodotto per avere solo le entry necessarie al confronto (perchè non tutti i contratti originali vengono mutati)
        filter_sample(new_experiment_diffs, sampled_filtered_by_operator, original_experiment_diffs)
        # count_rows(original_experiment_diffs)

        convert_column_to_json(original_experiment_diffs)

        print("***MUTATION STATUS***")
        print("--Old Mutation Run--")
        drop_empty_findings_x(original_experiment_diffs)
        count_rows(original_experiment_diffs)
        count_tp_fn(original_experiment_diffs, "unused-return")
        # print("")
        # count_findings(original_experiment_diffs, "differences")

        print("\n--New Mutation Run--")
        drop_empty_findings_x(new_experiment_diffs)
        count_rows(new_experiment_diffs)
        count_tp_fn(new_experiment_diffs, "unused-return")
        # print("")
        # count_findings(new_experiment_diffs, "differences")

        print("\n")

        print("***CHECK COUNT***")
        print("--Old Mutation Run--")
        analyze_differences_column(original_experiment_diffs)

        print("\n--New Mutation Run--")
        analyze_differences_column(new_experiment_diffs)

SecondStep()


