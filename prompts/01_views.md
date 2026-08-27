# Role
You are a Django REST Framework (DRF) expert specializing in Generic Views, URL routing, and RESTful API design.

# Context
I am working on a Django 5.2 project named **VideoStream**.
- Database: **Aurora PostgreSQL**
- Django App: `videos`
- Models are defined in `videos/models.py`
- Managers are defined in `videos/managers.py`
- Serializers are defined in `videos/serializers.py`
- Auth: **Keycloak via JWT** — `user_id` is a UUID available via `request.user_id`.

# Task
Create two files: `videos/views.py` and `videos/urls.py`.

## Views — Global Rules
- Use **only DRF Generic Views** (`ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`, `ListAPIView`). Do not use `ViewSets` or `APIView` unless absolutely impossible otherwise.
- `get_queryset()` must always leverage the custom manager methods — never use direct `.filter()` on the model inside the view when a manager method exists.
- Implement `get_serializer_class()` to return the appropriate serializer depending on the HTTP method.

## 1. `VideoListCreateView` → `ListCreateAPIView`
- **Route:** `GET /api/videos/` and `POST /api/videos/`
- **Behavior:**
  - `GET`: List the current user's videos that are ready, including their formats, ordered by creation date.
  - `POST`: Initialize/create a new video record.
- **QuerySet Logic:**
  - Inside `get_queryset()`, ensure that the `.ready()` filter is **only applied for `GET` requests**. For `POST` or other actions, it should just filter by user to prevent newly created `processing` videos from being excluded during the response serialization.
  - Base chain for GET: `Video.objects.by_user(self.request.user_id).ready().with_formats().recent()`
- **Serializer Selection:**
  - `POST` → `VideoCreateSerializer`
  - `GET` → `VideoListSerializer`

## 2. `VideoDetailView` → `RetrieveUpdateDestroyAPIView`
- **Route:** `GET /api/videos/<uuid:pk>/`, `PATCH /api/videos/<uuid:pk>/`, `DELETE /api/videos/<uuid:pk>/`
- **Behavior:** `GET` retrieves full video details with ready formats and ordered chunks.
- **QuerySet Logic:** `Video.objects.by_user(self.request.user_id).with_ready_formats().with_chunks()`
- **Serializer Class:** `VideoDetailSerializer`

## 3. `VideoFormatListView` → `ListAPIView`
- **Route:** `GET /api/videos/<uuid:video_id>/formats/`
- **Behavior:** Returns all ready formats for a specific video.
- **QuerySet Logic:** `VideoFormat.objects.filter(video_id=self.kwargs['video_id']).ready().with_video()`
- **Serializer Class:** `VideoFormatSerializer`

## 4. `VideoChunkListView` → `ListAPIView`
- **Route:** `GET /api/videos/<uuid:video_id>/chunks/`
- **Behavior:** Returns chunks in their chronological reassembly order.
- **QuerySet Logic:** `VideoChunk.objects.by_video(self.kwargs['video_id']).ordered()`
- **Serializer Class:** `VideoChunkSerializer`

# Output Format
Return the complete contents of both files separated into two distinct Markdown code blocks. Provide the file path as a heading before each block. Do not include any extra explanations.

### Example layout:
# videos/views.py
```python
# code here
