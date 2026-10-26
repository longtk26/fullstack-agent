# Story 12.1 — FrontendSpec 1.0 schema & validation

**Epic:** [12 — Modes, FrontendSpec & contract](epic12_contract_and_frontend_spec.md) · **Requirements:** FR-22 · **Depends on:** 2.1, 2.3

## User story

As a user, I want the frontend I am about to generate described in one JSON (how many pages, which theme, which
components, which data each page shows), so that I can review and edit it before any code is written.

## FrontendSpec 1.0 — shape

```jsonc
{
  "specVersion": "1.0",
  "project": { "name": "Corner Shop", "description": "…", "mode": "dynamic", "locale": "en", "locales": ["en"] },
  "theme": {
    "style": "minimal",                         // preset: minimal | editorial | playful | corporate | dashboard
    "colorScheme": "light-dark",                // light | dark | light-dark
    "colors": { "primary": "#1d4ed8", "secondary": "#64748b", "accent": "#f59e0b",
                "background": "#ffffff", "foreground": "#0f172a", "destructive": "#dc2626" },
    "typography": { "headingFont": "Inter", "bodyFont": "Inter", "scale": "default" },
    "radius": "md",                             // none | sm | md | lg | full
    "density": "comfortable"                    // compact | comfortable
  },
  "layout": {
    "shell": "header-footer",                   // header-footer | sidebar | blank
    "header": { "logoText": "Corner Shop", "navigation": [{ "label": "Shop", "page": "products" }] },
    "footer": { "text": "© Corner Shop", "links": [{ "label": "Contact", "page": "contact" }] }
  },
  "pages": [
    {
      "id": "products", "route": "/products", "title": "Products", "purpose": "browse the catalogue",
      "seo": { "title": "Shop all products", "description": "…" },
      "sections": [
        { "id": "grid", "component": "ProductGrid",
          "data": { "operationId": "product.list", "params": { "limit": 12, "sort": "-createdAt" } },
          "states": { "empty": "No products yet", "error": "Could not load products" } }
      ]
    },
    {
      "id": "product-detail", "route": "/products/[id]", "title": "Product",
      "sections": [
        { "id": "detail", "component": "ProductDetail", "data": { "operationId": "product.get", "params": { "id": "$route.id" } } },
        { "id": "add", "component": "Form", "form": "addToCart" }
      ]
    },
    { "id": "about", "route": "/about", "title": "About", "sections": [
        { "id": "hero", "component": "Hero", "content": { "heading": "Our story", "body": "…", "image": "asset:hero" } } ] }
  ],
  "components": [                               // the catalogue the pages may use (derived + declared)
    { "name": "ProductGrid", "kind": "composite", "uses": ["card", "badge", "pagination"], "description": "…" },
    { "name": "Form", "kind": "composite", "uses": ["form", "input", "button"] },
    { "name": "Hero", "kind": "section" }
  ],
  "forms": [
    { "id": "addToCart", "operationId": "cartItem.create", "fields": [
        { "name": "quantity", "type": "integer", "required": true, "min": 1 } ],
      "onSuccess": { "toast": "Added to cart", "navigate": "/cart" } }
  ],
  "content": [                                  // static data: always for `static`, optional seed text for `dynamic`
    { "collection": "testimonials", "records": [{ "author": "…", "quote": "…" }] }
  ],
  "assets": [{ "id": "hero", "kind": "image", "alt": "Shop front", "source": "placeholder" }],
  "auth": null,                                 // reserved for Epic 10 (login page, protected routes)
  "x-backendSpec": "…"                          // dynamic mode: reference to the BackendSpec drafted with it
}
```

Why these fields: `pages` + `route` fix the page count and URL map; `theme` maps 1:1 onto design tokens
(nextjs-skills `globals.css` variables, so no hard-coded colours); `layout` gives the outside-in shell the skill
builds first; `sections[].component` + `components[]` list exactly which components exist (shadcn primitives
they use are listed in `uses`, so the planner can `shadcn add` them); `data.operationId` / `forms[].operationId`
are the **only** link to the backend (checked against the contract in 12.5); `states` makes loading/empty/error
explicit; `content` and `assets` let `static` mode work without any backend.

## Acceptance criteria

- [ ] Pydantic models + exported JSON Schema (`GET /api/v1/frontend-specs/schema`), same conventions as
      BackendSpec (camelCase, `extra="forbid"`, versioned `specVersion`).
- [ ] Semantic validation with stable error codes (`FE_DUPLICATE_ROUTE`, `FE_UNKNOWN_COMPONENT`,
      `FE_UNKNOWN_PAGE` in navigation, `FE_UNKNOWN_FORM`, `FE_STATIC_HAS_BINDING` (static mode must not reference
      operations), `FE_ROUTE_PARAM_UNBOUND` (`$route.x` must be a route segment), invalid colour/token values).
- [ ] `POST /api/v1/frontend-specs/validate` and `POST /api/v1/frontend-specs` (stored like BackendSpecs, owner-scoped).
- [ ] Normalizer fills defaults (theme preset values, component catalogue derived from sections, page ids).
- [ ] Example specs in `examples/frontend-specs/` (`static-landing.json`, `shop-dynamic.json`), loadable in the UI.
