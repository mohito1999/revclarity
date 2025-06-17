import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os
import logging

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Add project root to path to allow imports from `app` ---
# This is a bit of a hack to make the script runnable from the command line
# It assumes the script is in backend/scripts and the app is in backend/app
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.core.config import settings
from app.models.medical_code import MedicalCode
from app.db.session import SessionLocal

# --- Configuration ---
# UPDATE THESE FILENAMES to match the names of your Excel files
CPT_FILE_NAME = "cpt_codes.xlsx"  # <--- CHANGE THIS IF YOUR CPT FILE IS NAMED DIFFERENTLY
ICD10_FILE_NAME = "icd10_codes.xlsx" # <--- CHANGE THIS IF YOUR ICD-10 FILE IS NAMED DIFFERENTLY

def import_cpt_codes(db_session):
    """Reads the CPT Excel file and loads data into the database."""
    file_path = os.path.join(project_root, CPT_FILE_NAME)
    if not os.path.exists(file_path):
        logging.error(f"CPT file not found at: {file_path}")
        return 0

    logging.info(f"Reading CPT codes from {file_path}...")
    df = pd.read_excel(file_path)
    
    # Based on your screenshot, the columns are: 'CPT Codes', 'Procedure Code Descriptions'
    # We rename them for consistency
    df.rename(columns={'CPT Codes': 'code_value', 'Procedure Code Descriptions': 'description'}, inplace=True)
    df['code_type'] = 'CPT'
    
    codes_to_add = []
    for _, row in df.iterrows():
        # Ensure code_value is treated as a string to avoid scientific notation
        code_value_str = str(row['code_value']).strip()
        if not code_value_str:
            continue
            
        code = MedicalCode(
            code_value=code_value_str,
            description=str(row['description']).strip(),
            code_type='CPT'
        )
        codes_to_add.append(code)
    
    logging.info(f"Adding {len(codes_to_add)} CPT codes to the session...")
    db_session.bulk_save_objects(codes_to_add)
    db_session.commit()
    logging.info("Successfully committed CPT codes to the database.")
    return len(codes_to_add)

def import_icd10_codes(db_session):
    """Reads the ICD-10 Excel file and loads data into the database."""
    file_path = os.path.join(project_root, ICD10_FILE_NAME)
    if not os.path.exists(file_path):
        logging.error(f"ICD-10 file not found at: {file_path}")
        return 0
        
    logging.info(f"Reading ICD-10 codes from {file_path}...")
    df = pd.read_excel(file_path)
    
    # Based on your screenshot, the columns are: 'CODE', 'LONG DESCRIPTION (VALID ICD-10 FY2025)'
    # We rename them for consistency
    df.rename(columns={'CODE': 'code_value', 'LONG DESCRIPTION (VALID ICD-10 FY2025)': 'description'}, inplace=True)
    df['code_type'] = 'ICD-10'
    
    codes_to_add = []
    for _, row in df.iterrows():
        code_value_str = str(row['code_value']).strip()
        if not code_value_str:
            continue

        code = MedicalCode(
            code_value=code_value_str,
            description=str(row['description']).strip(),
            code_type='ICD-10'
        )
        codes_to_add.append(code)
        
    logging.info(f"Adding {len(codes_to_add)} ICD-10 codes to the session...")
    db_session.bulk_save_objects(codes_to_add)
    db_session.commit()
    logging.info("Successfully committed ICD-10 codes to the database.")
    return len(codes_to_add)


if __name__ == "__main__":
    logging.info("Starting medical code database seeding process...")
    db = SessionLocal()
    
    # Optional: Clear the table first to prevent duplicates on re-runs
    logging.info("Clearing existing data from medical_codes table...")
    db.query(MedicalCode).delete()
    db.commit()
    
    try:
        num_cpt = import_cpt_codes(db)
        num_icd10 = import_icd10_codes(db)
        logging.info("--- Seeding Complete ---")
        logging.info(f"Total CPT codes loaded: {num_cpt}")
        logging.info(f"Total ICD-10 codes loaded: {num_icd10}")
        logging.info(f"Grand Total: {num_cpt + num_icd10}")
    except Exception as e:
        logging.error(f"An error occurred during the seeding process: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()