import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Text
from typing import List, Dict
from app.models.medical_code import MedicalCode
import logging
from sqlalchemy import or_, and_
from app.services.embedding_service import get_embeddings

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

def find_similar_icd10_codes(db: Session, search_terms: List[str]) -> List[Dict[str, str]]:
    """
    Finds the most semantically similar ICD-10 codes using vector search.
    """
    if not search_terms:
        return []

    query_text = " ".join(search_terms)
    
    try:
        query_vector = get_embeddings([query_text])[0]
    except Exception as e:
        logger.error(f"Could not get embedding for query text: {e}")
        return []

    if not query_vector:
        logger.warning("Embedding service returned no vector for the query text.")
        return []

    # --- THE FIX IS HERE ---
    # We access the distance function directly from the model's Vector column.
    results = db.query(MedicalCode).filter(
        MedicalCode.code_type == 'ICD-10'
    ).order_by(
        MedicalCode.vector.l2_distance(query_vector) # <-- This is the new, correct way
    ).limit(50).all()

    logger.info(f"Found {len(results)} similar ICD-10 candidates via vector search.")
    
    return [{"code": code.code_value, "description": code.description} for code in results]
