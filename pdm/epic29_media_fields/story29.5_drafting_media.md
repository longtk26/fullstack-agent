# Story 29.5 — Drafting picks media fields

**Epic:** [29 — Media fields](epic29_media_fields.md) · **Requirements:** FR-43, FR-38 · **Depends on:** 29.1, 29.4

## User story

As a user writing a requirement in plain words, I want recordings, clips, episodes or captions in my requirement to
become media fields with the right roles, so that I never have to name field types.

## Context

- The app draft is one structured call (`draft_app@v5`, `drafting/answer_schema.py`); `drafting/app.fix_backend_defaults`
  fixes mechanical mistakes before any check.

## Steps

1. **Prompt and schema:** the field type list in the answer schema gains the three types (generated from `FieldType`);
   the prompt's field guidance says when to use each (a file people watch, listen to, or read as captions) and that
   subtitles in several languages are a child entity with a language field.
2. **Code fixes (no model call):** a `file` field whose `accept` is only video, audio or subtitle types, or whose name
   says so (`video`, `clip`, `recording`, `audio`, `episode`, `subtitles`, `captions`), becomes the matching type, with
   one note; a media field without an image field on its entity gets no poster and the note says so.
3. **Design brief:** an entity whose `media` role is a video defaults to the `media` detail view and a media-first list
   view (as images do today).
4. Tests: the fixes on synthetic drafts; the schema snapshot.

## Acceptance criteria

- [ ] Drafts of requirements that mention recordings, videos or captions get media field types, roles and views,
      without the user naming them.
- [ ] Drafts without media are unchanged.

## Verify

`make test`; one real draft in 29.6.

## Status

Proposed 2026-11-08.
