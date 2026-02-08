import os
import shutil
import re
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.repositories.org_application_file_repo import create_org_application_file
from app.schemas.org_application_file_schema import OrgApplicationFileCreate


def save_application_file(db: Session, application_id: int, upload: UploadFile):
    settings = get_settings()
    root = settings.upload_dir
    os.makedirs(root, exist_ok=True)

    original_name = upload.filename or "file"
    safe_name = os.path.basename(original_name)
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    storage_key = f"{application_id}/{ts}_{safe_name}"
    full_path = os.path.join(root, storage_key)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    total = 0
    try:
        with open(full_path, "wb") as f:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds max size {settings.max_upload_bytes} bytes",
                    )
                f.write(chunk)
    except Exception:
        if os.path.exists(full_path):
            os.remove(full_path)
        raise

    data = OrgApplicationFileCreate(
        application_id=application_id,
        file_name=safe_name,
        mime_type=upload.content_type,
        storage_key=storage_key,
        file_size_bytes=os.path.getsize(full_path),
    )
    return create_org_application_file(db, data)
