# Role
You are a Django expert specializing in service layer architecture, the Registry Pattern, and cloud storage abstraction.

# Context
I am working on a Django 5.2 project named **VideoStream**.
- Database: **Aurora PostgreSQL**
- Django App: `videos`
- Models: `Video`, `VideoChunk`, `VideoFormat` defined in `videos/models.py`
- Auth: Keycloak via JWT — `user_id` is a UUID extracted from the token via `request.user_id`
- `upload_id` from the frontend equals `video_id` — Lambda already generated it as a UUIDv7
- Storage: local filesystem in development, AWS S3 in staging and production
- We store the **S3 key** in the database (not the full URL). The full URL is generated on demand via pre-signed URLs.

# Task
Create the `videos/services/` package with the following structure:

```
videos/
└── services/
    ├── __init__.py
    ├── chunk_upload_service.py
    ├── chunk_hash_service.py
    └── storage/
        ├── __init__.py          ← Registry
        ├── base_storage.py      ← Abstract interface
        ├── local_storage.py     ← Local filesystem
        └── s3_storage.py        ← AWS S3
```

---

## Step 1 — `videos/services/storage/base_storage.py`

Abstract base class defining the storage interface:

```python
from abc import ABC, abstractmethod

class BaseStorage(ABC):

    @abstractmethod
    def upload(self, chunk: bytes, video_id: str, chunk_index: int) -> str:
        """
        Upload a chunk and return the storage key.
        - Local: returns the absolute file path
        - S3: returns the S3 key (e.g. chunks/{video_id}/{chunk_index})
        """
        pass
```

---

## Step 2 — `videos/services/storage/local_storage.py`
- Implements `BaseStorage`.
- Uploads chunk data to the local filesystem.
- Base storage directory: `/tmp/videostream/chunks`
- Key/Path format: `/tmp/videostream/chunks/{video_id}/{chunk_index}`
- Ensure intermediate directories are created safely using `os.makedirs(..., exist_ok=True)`.
- Open the file in binary write mode (`"wb"`) to properly persist the raw `bytes`.
- Returns the full file path string.

## Step 3 — `videos/services/storage/s3_storage.py`
- Implements `BaseStorage`.
- Uploads chunk data to AWS S3 using `boto3`.
- Initialize the `boto3.client('s3')` inside the `__init__` method for client reusability.
- Bucket name target: `settings.AWS_S3_BUCKET`
- Key format: `chunks/{video_id}/{chunk_index}`
- Use `s3_client.put_object(Bucket=..., Key=..., Body=...)` to upload the raw bytes.
- Returns the S3 key string (not the full URL).

## Step 4 — `videos/services/storage/__init__.py` — Registry Pattern

- Define a `STORAGE_REGISTRY` dictionary mapping environment names to storage classes:
  ```python
  STORAGE_REGISTRY = {
      'local':      LocalStorage,
      'test':       LocalStorage,
      'stage':      S3Storage,
      'production': S3Storage,
  }
  ```
- Define `get_storage() -> BaseStorage` that reads `settings.ENVIRONMENT` and returns the correct storage instance
- Raise `ValueError` if the environment is not found in the registry
- No `if/elif` chains — only dictionary lookup

---

## Step 5 — `videos/services/chunk_upload_service.py`
Handles receiving a single video chunk from the controller layer and persisting it.

### Input parameters
- `video_id: str` (UUIDv7 string matching the upload workflow)
- `chunk_index: int`
- `chunk_hash: str` (SHA-256 string)
- `chunk_data: bytes`
- `size_bytes: int`

### Logic
1. Execute `get_storage().upload(chunk_data, video_id, chunk_index)` to retrieve the `storage_key`.
2. Persist or update the entry in PostgreSQL using `VideoChunk.objects.update_or_create()`.
   - **Crucial Optimization:** Use `video_id=video_id` (using the `_id` suffix property of the ForeignKey field) directly in the lookups/defaults. This links the record using the raw ID string and prevents Django from running an extra SQL `SELECT` to fetch a `Video` instance.
3. Return the `storage_key`.

---
## Step 6 — `videos/services/chunk_hash_service.py`

This service updates the `s3_key` of a chunk identified by its hash, after finalization confirms the S3 URL.

### Method: `update_s3_key(video_id: str, chunk_hash: str, s3_key: str) -> None`
- Filter `VideoChunk` by `video_id` and `sha256=chunk_hash`
- Update its `s3_key` field
- Use `.update()` for efficiency (no object load)

---

## Important Rules

- No business logic in views — all logic goes in services
- Services are pure Python classes, no inheritance from Django classes
- `get_storage()` is the only entry point for storage — never instantiate storage classes directly outside the registry
- Never store full S3 URLs in the database — only keys
- `boto3` import in `s3_storage.py` only — do not import it elsewhere

# Output Format
Return each file separately with its path as a heading before each code block.

### Example layout:
## videos/services/storage/base_storage.py
```python
# code here
```
