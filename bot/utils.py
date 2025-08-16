import os
from uuid import uuid4
from bot.config import UPLOAD_FOLDER

def save_uploaded_file(file_bytes, extension="pdf"):
    filename = f"{uuid4().hex}.{extension}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(file_bytes)
    return filepath
