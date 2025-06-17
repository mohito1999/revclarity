from sqlalchemy.orm import Session
from typing import List, Dict

from app.models import MedicalCode

def validate_codes(db: Session, suggested_codes: Dict[str, List[str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Takes a dictionary of suggested CPT and ICD-10 codes, validates them against the database,
    and returns a structured dictionary with their official descriptions.
    """
    validated_output = {
        "cpt_codes": [],
        "icd10_codes": []
    }
    
    # Validate CPT codes
    for code_val in suggested_codes.get("suggested_cpt_codes", []):
        db_code = db.query(MedicalCode).filter(MedicalCode.code_value == code_val, MedicalCode.code_type == 'CPT').first()
        if db_code:
            validated_output["cpt_codes"].append({"code": db_code.code_value, "description": db_code.description})
    
    # Validate ICD-10 codes
    for code_val in suggested_codes.get("suggested_icd10_codes", []):
        db_code = db.query(MedicalCode).filter(MedicalCode.code_value == code_val, MedicalCode.code_type == 'ICD-10').first()
        if db_code:
            validated_output["icd10_codes"].append({"code": db_code.code_value, "description": db_code.description})
            
    return validated_output