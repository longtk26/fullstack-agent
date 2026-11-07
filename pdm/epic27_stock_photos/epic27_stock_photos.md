# Epic 27 — Stock photos from Unsplash

## Overview

Proposed 2026-11-08 for the user's review. Generated sites and apps need sample photos (a hero, product and record
images, people). Today they come from AI image generation (`IMAGE_PROVIDER=gemini`, billed per image and off without
`GEMINI_IMAGE_API_KEY`) or are placeholders. The user has an Unsplash application (`UNSPLASH_ACCESS_KEY` in `.env`)
and wants real photos from it.

The LLM engines cannot fetch them: one-turn JSON has no tools, agy denies `read_url`, Claude Code runs with web fetch
off. The model only writes **what** each photo shows (a short search phrase); the agent's code calls the Unsplash API.

Unsplash's API guidelines decide the design:

- **Hotlink**: use the `urls.*` the API returns (images.unsplash.com); do not download and re-host the image.
- **Track downloads**: call the photo's `links.download_location` when the photo is used.
- **Credit**: show "Photo by <name> on Unsplash" with links to the photographer and Unsplash.
- **Rate limit**: demo applications get 50 requests per hour (checked 2026-11-07: 50/50); production 5,000 after
  Unsplash's review.

So an Unsplash photo is a **remote image with a credit**, not a file: the asset pipeline already renders `https://`
sources as remote images (sites) and keeps outside photo URLs in app seeds (Story 10.5).

## Decisions (proposed)

| # | Decision | Instead of |
|---|---|---|
| D1 | `IMAGE_PROVIDER=unsplash`, next to `gemini`, `fake` and `none` | A separate switch |
| D2 | A photo resolves to the Unsplash URL (hotlinked, sized with its `w` / `h` / `fit` parameters) and its credit; nothing is downloaded | Copying the image into the generated project |
| D3 | One search per distinct phrase, cached (phrase + orientation → photo), so a draft costs a handful of requests and repeated runs cost none | One request per image |
| D4 | The credit is rendered next to (or over) each photo by the site renderer and the app kit, and listed in the project README | A credits page only |

## Stories

| Story | What |
|---|---|
| [27.1](story27.1_unsplash_provider.md) | The provider: search, orientation, URL, credit, download tracking, cache, rate limit |
| [27.2](story27.2_photos_in_sites_and_apps.md) | Sites' photo assets and apps' seeded photos use it; credits rendered |
| [27.3](story27.3_final_check.md) | Real drafts with Unsplash photos, within the hourly limit |

**Requirements:** FR-41 (new, proposed: stock photos with attribution).
