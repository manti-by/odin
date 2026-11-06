---
title: 'CH-1: Update video enrichment flow'
date: '2026-11-06'
type: implementation
status: resolved
session_id: ses_e4f24949effelbqfcg9VZ7SQMm
services: [__init__, serializers, admin, video_scan, 0002_video_title_en_video_title_omdb_and_more, models, metadata, scanner, translation, base, test_video, test_video_scan, factories, test_video_metadata, test_video_scanner, test_video_translation]
branch: ch-1-update-video-enrichment-flow
tickets: [CH-1]
tags: [wiki, feature, backend]
related: []
---

# CH-1: Update video enrichment flow

## TL;DR

This session implemented updates to the video enrichment flow to better handle Russian video titles. Key changes include adding `title_en` and `title_omdb` fields, translating titles from Russian to English, and querying OMDb with the translated title. The implementation follows a structured plan across model, migration, parser, translation service, and metadata service updates.

## Overview

The video metadata retrieval system was updated to handle Russian video titles more effectively. The new flow:
1. Parses filenames into title and year components
2. Translates titles from Russian to English
3. Stores translated titles in a new `title_en` field
4. Queries OMDb using `title_en` instead of the original title

Key technical decisions:
- Added `title_en` and `title_omdb` fields to the Video model
- Created a MyMemory translation service for Russian-to-English translation
- Updated the metadata service to use `title_en` for OMDb queries
- Maintained the original title in the `title` field

## Step 1 — Extend Video model

**File:** odin/apps/video/models.py

Added new fields to store translated and OMDb titles:
```python
title_en = models.CharField(max_length=255, blank=True)
title_omdb = models.CharField(max_length=255, blank=True)
translation_status = models.CharField(max_length=20, choices=FetchStatus.choices, default=FetchStatus.PENDING)
translation_attempts = models.PositiveSmallIntegerField(default=0)
```

## Step 2 — Update filename parser

**File:** odin/apps/video/services/scanner.py

Modified the parser to handle canonical filename formats:
```python
# Supports formats:
# <title> - <year>.mkv
# <title> - <year> - 4K.mkv
```

## Step 3 — Implement translation service

**File:** odin/apps/video/services/translation.py

Created MyMemory translation service:
```python
def fetch_translation(title: str) -> str:
    """Translate Russian titles to English using MyMemory API"""
    if not contains_cyrillic(title):
        return title
    response = requests.get(API_URL, params={"q": title, "langpair": "ru|en"})
    return response.json()["responseData"]["translatedText"]
```

## Step 4 — Update metadata service

**File:** odin/apps/video/services/metadata.py

Modified to use `title_en` for OMDb queries:
```python
def apply_metadata(video: Video, payload: dict) -> None:
    """Apply OMDb metadata without overwriting original title"""
    video.title_omdb = str(payload["Title"])
    # Keep original title intact
```

## Step 5 — Update admin interface

**File:** odin/apps/video/admin.py

Added new fields to admin:
```python
list_display = (
    "title",
    "title_en",
    "year",
    "imdb_rating",
    "metadata_status",
    "trailer_status",
    "is_available",
    "updated_at",
)
```

## Test Results

All tests passed successfully:
```
============================= 913 passed in 14.45s =============================
```

## Follow-ups

- None

## References
- External: <linear ticket URL>
