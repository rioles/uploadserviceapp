# Role
You are a Django expert specializing in PostgreSQL query optimization and the Manager/QuerySet pattern.

# Context
I am working on a Django 5.2 project named **VideoStream**.
- Database: **Aurora PostgreSQL**
- Django App: `videos`
- The models `Video`, `VideoChunk`, and `VideoFormat` are already defined in `videos/models.py`
- Relations:
  - `Video` → `VideoChunk`: One-to-Many via `related_name='chunks'`
  - `Video` → `VideoFormat`: One-to-Many via `related_name='formats'`

# Task
Create the file `videos/managers.py` containing the following QuerySets and Managers.

## `VideoQuerySet` and `VideoManager`

| Method | Behavior |
|---|---|
| `ready()` | `filter(status='ready')` |
| `processing()` | `filter(status='processing')` |
| `by_user(user_id)` | `filter(user_id=user_id)` |
| `recent()` | `order_by('-created_at')` |
| `with_formats()` | `prefetch_related('formats')` — avoids N+1 queries for Video→VideoFormat |
| `with_chunks()` | `prefetch_related('chunks')` — avoids N+1 queries for Video→VideoChunk |
| `with_ready_formats()` | `Prefetch('formats', queryset=VideoFormat.objects.filter(ready=True), to_attr='ready_formats')` |
| `lightweight()` | `only('id', 'title', 'status', 'user_id', 'created_at')` — reduces selected columns |

## `VideoFormatQuerySet` and `VideoFormatManager`

| Method | Behavior |
|---|---|
| `ready()` | `filter(ready=True)` |
| `by_resolution(resolution)` | `filter(resolution=resolution)` |
| `with_video()` | `select_related('video')` — JOIN Many→One, single SQL query |

## `VideoChunkQuerySet` and `VideoChunkManager`

| Method | Behavior |
|---|---|
| `ordered()` | `order_by('chunk_index')` — order for video reassembly |
| `by_video(video_id)` | `filter(video_id=video_id)` |
| `with_video()` | `select_related('video')` — JOIN Many→One |

# Important Rules
- Each `Manager` must inherit from `models.Manager`.
- Each `Manager` must implement `get_queryset()` returning its associated `QuerySet`.
- Each `Manager` must expose the same methods as its `QuerySet` by delegating them via `get_queryset()`.
- Use `django.db.models.Prefetch` for `with_ready_formats()`.
- **CRITICAL:** Do not import models at the module level to prevent circular imports. Import the required models inside the specific methods when needed (especially `VideoFormat` inside `with_ready_formats`).

# Output Format
Return only the complete content of the `videos/managers.py` file, without any explanation.
