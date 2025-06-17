import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Text
from typing import List, Dict
from app.models import MedicalCode
import logging

logger = logging.getLogger(__name__)

def validate_codes(db: Session, suggested_codes: Dict[str, List[str]]) -> Dict[str, List[Dict[str, str]]]:
    """
    Takes a dictionary of suggested codes. Validates them against the DB.
    For CPT codes, if not found, it will trust the AI's suggestion for the demo.
    """
    validated_output = { "cpt_codes": [], "icd10_codes": [] }
    
    all_suggested_codes = suggested_codes.get("suggested_cpt_codes", []) + suggested_codes.get("suggested_icd10_codes", [])
    if not all_suggested_codes:
        return validated_output

    db_results = db.query(MedicalCode).filter(MedicalCode.code_value.in_(all_suggested_codes)).all()
    code_map = {code.code_value: code for code in db_results}
    logger.info(f"Found {len(db_results)} matching codes in the database out of {len(all_suggested_codes)} suggestions.")

    # --- UPDATED CPT LOGIC ---
    for code_val in suggested_codes.get("suggested_cpt_codes", []):
        if code_val in code_map:
            # Found in DB, use official description
            db_code = code_map[code_val]
            validated_output["cpt_codes"].append({"code": db_code.code_value, "description": db_code.description})
        else:
            # Not found in DB, trust the AI for now and add it with a placeholder description
            logger.warning(f"CPT code {code_val} not found in DB. Using AI suggestion directly for demo.")
            validated_output["cpt_codes"].append({"code": code_val, "description": "AI Suggested Code (Unverified)"})

    # --- ICD-10 logic remains strict ---
    for code_val in suggested_codes.get("suggested_icd10_codes", []):
        if code_val in code_map:
            db_code = code_map[code_val]
            validated_output["icd10_codes"].append({"code": db_code.code_value, "description": db_code.description})
        else:
            # We have the full ICD-10 list, so if it's not here, it's an error.
            logger.error(f"ICD-10 code {code_val} suggested by AI but not found in DB. Discarding.")
            
    return validated_output

def search_icd10_codes_by_description(db: Session, search_terms: List[str]) -> List[Dict[str, str]]:
    """
    Searches for ICD-10 codes in the database using descriptive terms.
    """
    if not search_terms:
        return []
    
    # This creates a query like: SELECT * FROM medical_codes WHERE description ILIKE '%term1%' OR description ILIKE '%term2%'
    # It's a simplified but effective search for the demo.
    from sqlalchemy import or_
    
    search_filters = [MedicalCode.description.ilike(f"%{term}%") for term in search_terms]
    
    results = db.query(MedicalCode).filter(
        MedicalCode.code_type == 'ICD-10',
        or_(*search_filters)
    ).limit(5).all() # Limit to 5 to avoid too many results

    return [{"code": code.code_value, "description": code.description} for code in results]