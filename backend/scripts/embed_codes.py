import sys
import os
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# --- Setup Logging & Path ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.core.config import settings
from app.models.medical_code import MedicalCode
from app.services.embedding_service import get_embeddings

# --- Configuration ---
BATCH_SIZE = 100 # Process 100 codes at a time

def main():
    logging.info("Starting database vectorization process...")
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        codes_to_process = db.query(MedicalCode).filter(MedicalCode.vector == None).all()
        total_codes = len(codes_to_process)
        logging.info(f"Found {total_codes} medical codes to vectorize.")

        if total_codes == 0:
            logging.info("No new codes to vectorize. Exiting.")
            return

        for i in range(0, total_codes, BATCH_SIZE):
            batch = codes_to_process[i:i + BATCH_SIZE]
            # Filter out any descriptions that are empty or just whitespace
            valid_descriptions = [code.description for code in batch if code.description and code.description.strip()]
            
            if not valid_descriptions:
                logging.warning(f"Skipping batch {i//BATCH_SIZE + 1} as it contains no valid descriptions.")
                continue

            logging.info(f"Processing batch {i//BATCH_SIZE + 1}/{(total_codes + BATCH_SIZE - 1)//BATCH_SIZE}...")
            
            embeddings = get_embeddings(valid_descriptions)
            
            # Map embeddings back to the correct codes
            desc_to_code_map = {code.description: code for code in batch if code.description and code.description.strip()}
            for desc, vector in zip(valid_descriptions, embeddings):
                if vector:
                    desc_to_code_map[desc].vector = vector
            
            db.commit()
            logging.info(f"Committed vectors for {len(valid_descriptions)} codes.")

        logging.info("--- Vectorization Complete ---")

    except Exception as e:
        logging.error(f"An error occurred during vectorization: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()