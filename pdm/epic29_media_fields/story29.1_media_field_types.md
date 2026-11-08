# Story 29.1 — `video`, `audio` and `subtitles` field types

**Epic:** [29 — Media fields](epic29_media_fields.md) · **Requirements:** FR-43, FR-34 · **Depends on:** 10.5

## User story

As a user describing an app with recordings or videos, I want media fields that the backend accepts and checks like
images, with sensible types and sizes, so that uploads of media work without me listing MIME types.

## Context

- `FieldType` (`backend_spec/schema_v1.py`) and the validator's file rules (`accept`, `maxSize` only on `file` and
  `image`, `backend_spec/validator.py`).
- `backend/planner.py` builds `column.file` (`kind`, `accept`, `maxSize`, `prefix`); the `storage` plugin
  (`plugins/storage.py`) writes presign checks, upload checks in use cases, `<field>Url`, tests and seeds, and picks a
  content type per kind for its scenarios (`image/png`, else the first `accept`).

## Steps

1. **Schema:** `FieldType` gains `video`, `audio`, `subtitles`; `accept` and `maxSize` apply to them; the validator
   refuses an `accept` entry outside the kind's playable set (D2) with the allowed list as the suggestion.
2. **Planner:** defaults per kind in one table (`MEDIA_KINDS` next to `IMAGE_TYPES`): types and `maxSize` (D7);
   `column.file.kind` is the field type.
3. **Storage plugin:** presign and upload checks per kind; scenarios and test cases use a content type of the kind
   (`video/mp4`, `audio/mpeg`, `text/vtt`), a too-large size from the kind's limit, a refused type from another kind;
   `x-bga.storage.fields` carries `kind`. Subtitles accept `.srt` (`application/x-subrip`) and `.vtt`.
4. **Reads:** the signed read URL of a media field allows range requests (the S3-compatible store answers them; a test
   checks `Range` on the sandbox store) and sets `ResponseContentType` from the stored key's type.
5. **Subtitle shapes (D3), code only:** the contract marks the tracks of a media field:
   `x-bga.storage.tracks[<Entity>.<mediaField>]` = the same record's `subtitles` fields, or a child entity (a reference
   to the media record) with a `subtitles` field and a language-like field (`language`, `lang`, `locale`, an enum of
   language codes), plus an optional label field.
6. Tests: schema and validator cases; planner defaults; plugin scenarios per kind; the tracks finder on synthetic
   specs (same-record track, child tracks with a language enum, a child without a language: one track, no language);
   contract snapshot updates.

## Acceptance criteria

- [ ] A BackendSpec with `video`, `audio` and `subtitles` fields validates, generates and passes the smoke check.
- [ ] Uploads of a refused type or a too-large file get the plugin's 422 codes, per kind.
- [ ] The contract lists the subtitle tracks of each media field in both shapes.
- [ ] Specs without the new types generate byte-identical code (backend golden tests).

## Verify

`make lint`, `make test`, `make up` with a synthetic media spec (backend only).

## Status

Proposed 2026-11-08.
