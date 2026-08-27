# Role
You are a Django REST Framework (DRF) expert specializing in serialization and data validation.

# Context
I am working on a Django 5.2 project named **VideoStream**.
- Database: **Aurora PostgreSQL**
- Django App: `videos`
- The models `Video`, `VideoChunk`, and `VideoFormat` are already defined in `videos/models.py`.
- Auth: Keycloak via JWT — `user_id` is a UUID extracted from the token and attached to the request object as `request.user_id`.

# Task
Create the file `videos/serializers.py` containing the following five serializers.

## 1. VideoChunkSerializer
- **Type:** `ModelSerializer`
- **Model:** `VideoChunk`
- **Fields:** `id`, `chunk_index`, `s3_key`, `sha256`, `size_bytes`
- **Behavior:** All fields should be read-only by default unless explicitly written to.

## 2. VideoFormatSerializer
- **Type:** `ModelSerializer`
- **Model:** `VideoFormat`
- **Fields:** `id`, `resolution`, `s3_key`, `codec`, `bitrate_kbps`, `ready`
- **Behavior:** All fields are read-only.

## 3. VideoListSerializer
- **Type:** Lightweight `ModelSerializer` optimized for listing endpoints.
- **Model:** `Video`
- **Fields:** `id`, `title`, `status`, `duration_s`, `size_bytes`, `created_at`

## 4. VideoDetailSerializer
- **Type:** Full `ModelSerializer` for detailed single-video view.
- **Model:** `Video`
- **Fields:** `id`, `upload_id`, `owner_id`, `title`, `description`, `total_chunks`, `size_bytes`, `duration_s`, `status`, `is_ready`, `formats`, `chunks`, `created_at`
- **Nested Relationships:**
  - `formats` → `VideoFormatSerializer(many=True, read_only=True)`
  - `chunks` → `VideoChunkSerializer(many=True, read_only=True)`
- **Custom Fields:**
  - `is_ready` → `SerializerMethodField` that returns `True` if `status == 'ready'`, else `False`.
  - `owner_id` → `UUIDField(source='user_id', read_only=True)`

## 5. VideoCreateSerializer
- **Type:** `ModelSerializer` dedicated exclusively to video initialization.
- **Model:** `Video`
- **Fields:** `upload_id`, `title`, `description`, `total_chunks`, `size_bytes`
- **Validation:** - Field-level validation on `total_chunks` using `validate_total_chunks`. It must be strictly greater than 0, otherwise raise `serializers.ValidationError`.
- **Creation Logic:**
  - In the `create(self, validated_data)` method, extract `user_id` from `self.context['request'].user_id` and inject it into `validated_data` before calling `super().create()`.

# Important Rules
- Single responsibility: Separate serializers for List, Detail, and Creation to optimize payloads.
- No heavy business logic inside serializers—only validation and field mapping.
- Properly import `serializers` from `rest_framework` and the necessary models from `.models`.

# Output Format
Return only the complete content of the `videos/serializers.py` file, without any explanation.
