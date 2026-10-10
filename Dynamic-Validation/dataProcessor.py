"""
dataProcessor.py - Dynamic Data Validation Pipeline using Pydantic V2

This module reads source-to-target mapping (STM) configurations at runtime,
dynamically builds Pydantic validation models on the fly, validates input data
from CSV/delimited files, and segregates valid and error records into target directories.

Workflow:
1. Load Schema Configuration from Config/stm_config.txt
2. Dynamically Generate Pydantic Models for each source file using create_model()
3. Read raw data records from Data/input/
4. Validate each record against the runtime-generated model
5. Write valid records to Data/processed/valid/ and invalid records to Data/processed/error/
"""

import csv
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, Field, ValidationError, create_model

# ---------------------------------------------------------------------------
# Setup Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DataProcessor")

# ---------------------------------------------------------------------------
# Directory Paths Setup (Resolving relative to script location)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "Config" / "stm_config.txt"
INPUT_DIR = BASE_DIR / "Data" / "input"
PROCESSED_DIR = BASE_DIR / "Data" / "processed"
VALID_DIR = PROCESSED_DIR / "valid"
ERROR_DIR = PROCESSED_DIR / "error"

# Mapping string type names from configuration to actual Python data types
DATA_TYPE_MAP: Dict[str, Type] = {
    "int": int,
    "integer": int,
    "str": str,
    "string": str,
    "float": float,
    "double": float,
    "bool": bool,
    "boolean": bool,
}


# ---------------------------------------------------------------------------
# Step 1: Configuration Reader
# ---------------------------------------------------------------------------
def load_stm_config(config_file: Path) -> Dict[str, Dict[str, Any]]:
    """
    Parses the source-to-target mapping (STM) configuration file.

    Expected columns in config:
    source_file_name,taget_table_name,source_col_Name,source_col_type,source_col_length

    Returns:
        dict: A nested dictionary grouped by source_file_name:
        {
            "emp.txt": {
                "target_table": "emp",
                "columns": [
                    {"name": "empid", "type": "int", "length": None},
                    {"name": "ename", "type": "string", "length": 500},
                    ...
                ]
            },
            ...
        }
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    config_map: Dict[str, Dict[str, Any]] = {}

    logger.info(f"Loading STM configuration from: {config_file}")
    with open(config_file, mode="r", encoding="utf-8") as f:
        # Using csv.reader to handle variable column lengths and trailing commas
        reader = csv.reader(f)
        header = [col.strip() for col in next(reader, [])]

        for line_num, row in enumerate(reader, start=2):
            # Clean and strip row values
            cleaned_row = [item.strip() for item in row]
            if not cleaned_row or not cleaned_row[0]:
                continue  # Skip empty lines

            # Extract fields with safe defaults for missing length columns
            src_file = cleaned_row[0]
            target_table = cleaned_row[1] if len(cleaned_row) > 1 else src_file.split(".")[0]
            col_name = cleaned_row[2] if len(cleaned_row) > 2 else ""
            col_type = cleaned_row[3].lower() if len(cleaned_row) > 3 else "string"
            col_length = None

            if len(cleaned_row) > 4 and cleaned_row[4]:
                try:
                    col_length = int(cleaned_row[4])
                except ValueError:
                    logger.warning(
                        f"Line {line_num}: Invalid column length '{cleaned_row[4]}' for {col_name}. Ignored."
                    )

            if src_file not in config_map:
                config_map[src_file] = {
                    "target_table": target_table,
                    "columns": [],
                }

            config_map[src_file]["columns"].append({
                "name": col_name,
                "type": col_type,
                "length": col_length,
            })

    logger.info(f"Successfully loaded configuration for {len(config_map)} source file(s): {list(config_map.keys())}")
    return config_map


# ---------------------------------------------------------------------------
# Step 2: Dynamic Model Generator (Runtime Pydantic Model)
# ---------------------------------------------------------------------------
def build_dynamic_model(model_name: str, column_specs: List[Dict[str, Any]]) -> Type[BaseModel]:
    """
    Dynamically generates a Pydantic V2 BaseModel class at runtime.

    Uses `pydantic.create_model`:
    Syntax: create_model(model_name, field_name=(field_type, field_default_or_Field_info), ...)

    Args:
        model_name: Name of the generated model class (e.g. 'EmpModel')
        column_specs: List of column definitions with 'name', 'type', 'length'

    Returns:
        Type[BaseModel]: Dynamically constructed Pydantic model class
    """
    field_definitions: Dict[str, Any] = {}

    for spec in column_specs:
        field_name = spec["name"]
        raw_type = spec["type"]
        length = spec["length"]

        # Resolve Python type from mapping (default to str if unknown)
        py_type = DATA_TYPE_MAP.get(raw_type, str)

        # Build Field constraints (e.g. max_length for string columns)
        # Note: '...' (Ellipsis) signifies that the field is mandatory/required
        if py_type is str and length is not None and length > 0:
            field_definitions[field_name] = (py_type, Field(..., max_length=length))
        else:
            field_definitions[field_name] = (py_type, Field(...))

    # create_model dynamically creates a subclass of BaseModel with the specified fields
    dynamic_model = create_model(model_name, **field_definitions)
    logger.debug(f"Created dynamic model '{model_name}' with fields: {list(field_definitions.keys())}")
    return dynamic_model


# ---------------------------------------------------------------------------
# Step 3: Input Data Reader
# ---------------------------------------------------------------------------
def read_input_data(file_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Reads delimited data from an input file.

    Returns:
        Tuple of (headers: list of column names, records: list of row dicts)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    records: List[Dict[str, str]] = []
    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in (reader.fieldnames or [])]

        for row in reader:
            # Clean leading/trailing whitespaces in keys and values
            cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k is not None}
            records.append(cleaned_row)

    return headers, records


# ---------------------------------------------------------------------------
# Step 4: Data Validation Engine
# ---------------------------------------------------------------------------
def validate_dataset(
    model: Type[BaseModel], records: List[Dict[str, str]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validates each record against the dynamically generated Pydantic model.

    Separates rows into:
    - valid_records: Rows that passed all schema and type validations.
    - error_records: Rows that failed, augmented with a 'validation_error' description.

    Returns:
        Tuple of (valid_records, error_records)
    """
    valid_records: List[Dict[str, Any]] = []
    error_records: List[Dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        try:
            # Pydantic validates types, casts compatible types (e.g., '100' -> 100),
            # and checks constraints (e.g. max_length).
            validated_instance = model.model_validate(record)
            # Store validated record as standard dictionary
            valid_records.append(validated_instance.model_dump())
        except ValidationError as err:
            # Extract clean, human-readable error messages for each failing field
            error_details = []
            for e in err.errors():
                loc = ".".join(str(item) for item in e.get("loc", []))
                msg = e.get("msg", "Invalid value")
                error_details.append(f"{loc}: {msg}")

            # Keep original row data and attach validation failure details
            error_row = dict(record)
            error_row["validation_error"] = "; ".join(error_details)
            error_records.append(error_row)

    return valid_records, error_records


# ---------------------------------------------------------------------------
# Step 5: Data Output Writer
# ---------------------------------------------------------------------------
def write_csv_data(file_path: Path, records: List[Dict[str, Any]], headers: List[str]) -> None:
    """
    Writes a list of dictionary records to a CSV file.
    Ensures parent directory exists before writing.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


# ---------------------------------------------------------------------------
# Step 6: Single File Pipeline Coordinator
# ---------------------------------------------------------------------------
def process_single_file(
    file_name: str, file_config: Dict[str, Any], input_dir: Path
) -> None:
    """
    Executes the end-to-end dynamic validation pipeline for a given file.
    """
    logger.info("=" * 60)
    logger.info(f"Processing File: {file_name}")

    input_file = input_dir / file_name
    if not input_file.exists():
        logger.error(f"Input file {file_name} does not exist in {input_dir}. Skipping.")
        return

    # 1. Read input data
    headers, raw_records = read_input_data(input_file)
    logger.info(f"Read {len(raw_records)} record(s) from {file_name}")

    # 2. Build dynamic Pydantic model at runtime
    table_name = file_config.get("target_table", file_name.split(".")[0])
    model_class_name = f"{table_name.capitalize()}DynamicModel"
    dynamic_model = build_dynamic_model(model_class_name, file_config["columns"])

    logger.info(f"Constructed runtime model '{model_class_name}' with fields: {list(dynamic_model.model_fields.keys())}")

    # 3. Validate data records
    valid_records, error_records = validate_dataset(dynamic_model, raw_records)

    logger.info(f"Validation completed: {len(valid_records)} VALID, {len(error_records)} ERROR")

    # 4. Write valid records
    valid_file = VALID_DIR / file_name
    write_csv_data(valid_file, valid_records, headers)
    logger.info(f"Written valid records to: {valid_file}")

    # 5. Write error records to both error/ and invalid/ directories
    error_headers = headers + ["validation_error"]
    error_file = ERROR_DIR / file_name
    write_csv_data(error_file, error_records, error_headers)
    logger.info(f"Written error records to: {error_file}")


# ---------------------------------------------------------------------------
# Step 7: Main Pipeline Orchestrator
# ---------------------------------------------------------------------------
def run_pipeline() -> None:
    """
    Driver function to orchestrate the dynamic validation across all configured files.
    """
    logger.info("Starting Dynamic Validation Data Pipeline")
    logger.info(f"Base Directory: {BASE_DIR}")

    # Ensure output directories exist
    VALID_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load STM Config
    stm_configs = load_stm_config(CONFIG_PATH)

    # 2. Process each source file specified in the configuration
    for src_file, file_config in stm_configs.items():
        try:
            process_single_file(src_file, file_config, INPUT_DIR)
        except Exception as exc:
            logger.exception(f"Unexpected error processing file {src_file}: {exc}")

    logger.info("=" * 60)
    logger.info("Dynamic Validation Pipeline Completed Successfully!")


if __name__ == "__main__":
    run_pipeline()
