import os
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIRECTORY = "./uploads"
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)

def save_upload_file(upload_file: UploadFile) -> str:
    """
    Saves an uploaded file to the UPLOAD_DIRECTORY and returns the full path.
    Sanitizes the filename to prevent security issues.
    """
    # Sanitize filename to prevent directory traversal attacks
    filename = Path(upload_file.filename).name
    if not filename:
        raise ValueError("Filename cannot be empty.")
        
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())
        
    return file_path