"""Story 19.7 tests: operation coverage, Manage area generation, sign-in exclusion, idempotence."""

from typing import Any

from src.modules.shared.domain.backend_spec import Severity, validate_spec_data
from src.modules.shared.domain.frontend_spec import (
    add_manage_area,
    remove_manage_area,
    uncovered_operations,
    validate_frontend_spec_data,
)
from src.orchestrator.checks.consistency import check_spec_pair
from src.orchestrator.contract import build_contract


def _make_measured_case_backend() -> dict[str, Any]:
    """Rebuild the measured case: Deck, Card, ReviewLog, ContactMessage with 13+ operations."""
    return {
        "specVersion": "1.0",
        "project": {"name": "Flashcards App"},
        "stack": {
            "framework": "fastapi",
            "database": "postgresql",
            "orm": "sqlalchemy",
            "migration": "alembic",
        },
        "auth": {"type": "jwt"},
        "entities": [
            {
                "name": "Deck",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": True},
                    {"name": "name", "type": "string", "required": True},
                    {"name": "description", "type": "text"},
                ],
            },
            {
                "name": "Card",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": True},
                    {"name": "deckId", "type": "uuid", "required": True},
                    {"name": "front", "type": "string", "required": True},
                    {"name": "back", "type": "string", "required": True},
                ],
            },
            {
                "name": "ReviewLog",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": True},
                    {"name": "cardId", "type": "uuid", "required": True},
                    {"name": "rating", "type": "integer", "required": True},
                ],
            },
            {
                "name": "ContactMessage",
                "fields": [
                    {"name": "id", "type": "uuid", "primary": True},
                    {"name": "email", "type": "string", "required": True},
                    {"name": "message", "type": "text", "required": True},
                ],
            },
        ],
        "relationships": [
            {"name": "deckCards", "type": "one-to-many", "from": "Deck", "to": "Card"},
            {"name": "cardReviews", "type": "one-to-many", "from": "Card", "to": "ReviewLog"},
        ],
        "operations": [
            # Deck CRUD (5)
            {
                "operationId": "deck.list",
                "type": "crud",
                "method": "GET",
                "path": "/decks",
                "entity": "Deck",
                "action": "list",
            },
            {
                "operationId": "deck.create",
                "type": "crud",
                "method": "POST",
                "path": "/decks",
                "entity": "Deck",
                "action": "create",
            },
            {
                "operationId": "deck.get",
                "type": "crud",
                "method": "GET",
                "path": "/decks/{id}",
                "entity": "Deck",
                "action": "get",
            },
            {
                "operationId": "deck.update",
                "type": "crud",
                "method": "PATCH",
                "path": "/decks/{id}",
                "entity": "Deck",
                "action": "update",
            },
            {
                "operationId": "deck.delete",
                "type": "crud",
                "method": "DELETE",
                "path": "/decks/{id}",
                "entity": "Deck",
                "action": "delete",
            },
            # Card CRUD (5)
            {
                "operationId": "card.list",
                "type": "crud",
                "method": "GET",
                "path": "/cards",
                "entity": "Card",
                "action": "list",
            },
            {
                "operationId": "card.create",
                "type": "crud",
                "method": "POST",
                "path": "/cards",
                "entity": "Card",
                "action": "create",
            },
            {
                "operationId": "card.get",
                "type": "crud",
                "method": "GET",
                "path": "/cards/{id}",
                "entity": "Card",
                "action": "get",
            },
            {
                "operationId": "card.update",
                "type": "crud",
                "method": "PATCH",
                "path": "/cards/{id}",
                "entity": "Card",
                "action": "update",
            },
            {
                "operationId": "card.delete",
                "type": "crud",
                "method": "DELETE",
                "path": "/cards/{id}",
                "entity": "Card",
                "action": "delete",
            },
            # ReviewLog: only list and create (2)
            {
                "operationId": "reviewLog.list",
                "type": "crud",
                "method": "GET",
                "path": "/review-logs",
                "entity": "ReviewLog",
                "action": "list",
            },
            {
                "operationId": "reviewLog.create",
                "type": "crud",
                "method": "POST",
                "path": "/review-logs",
                "entity": "ReviewLog",
                "action": "create",
            },
            # ContactMessage: only create (1)
            {
                "operationId": "contactMessage.create",
                "type": "crud",
                "method": "POST",
                "path": "/contact-messages",
                "entity": "ContactMessage",
                "action": "create",
            },
            # Custom op by id on Deck
            {
                "operationId": "deck.archive",
                "type": "custom",
                "method": "POST",
                "path": "/decks/{id}/archive",
                "entity": "Deck",
            },
            # Custom op without id on Deck
            {
                "operationId": "deck.resetAll",
                "type": "custom",
                "method": "POST",
                "path": "/decks/reset",
                "entity": "Deck",
            },
            # Sign-in operation on Deck
            {
                "operationId": "deck.purge",
                "type": "custom",
                "method": "DELETE",
                "path": "/decks/{id}/purge",
                "entity": "Deck",
                "auth": "jwt",
            },
        ],
    }


def _make_measured_case_frontend() -> dict[str, Any]:
    """Frontend covering only 7 operations, leaving others uncovered."""
    return {
        "specVersion": "1.0",
        "project": {"name": "Flashcards App", "mode": "dynamic"},
        "theme": {"style": "minimal"},
        "layout": {
            "header": {
                "navigation": [
                    {"label": "Home", "page": "home"},
                    {"label": "Decks", "page": "decks"},
                ]
            }
        },
        "pages": [
            {
                "id": "home",
                "route": "/",
                "title": "Home",
                "sections": [
                    {
                        "id": "hero",
                        "component": "Hero",
                        "content": {"heading": "Learn with Flashcards", "body": "Practice every day."},
                    }
                ],
            },
            {
                "id": "decks",
                "route": "/decks",
                "title": "Decks",
                "sections": [
                    {
                        "id": "decks-table",
                        "component": "DataTable",
                        "data": {"operationId": "deck.list", "fields": ["name", "description"]},
                    }
                ],
            },
            {
                "id": "decks-new",
                "route": "/decks/new",
                "title": "New Deck",
                "sections": [{"id": "new-deck-form-section", "component": "Form", "form": "newDeckForm"}],
            },
            {
                "id": "cards-list",
                "route": "/cards",
                "title": "Cards",
                "sections": [
                    {
                        "id": "cards-grid",
                        "component": "CardGrid",
                        "data": {"operationId": "card.list", "fields": ["front", "back"]},
                    }
                ],
            },
            {
                "id": "cards-new",
                "route": "/cards/new",
                "title": "New Card",
                "sections": [{"id": "new-card-form-section", "component": "Form", "form": "newCardForm"}],
            },
        ],
        "forms": [
            {
                "id": "newDeckForm",
                "operationId": "deck.create",
                "fields": [
                    {"name": "name", "type": "string", "label": "Deck Name", "required": True},
                    {"name": "description", "type": "string", "label": "Description"},
                ],
            },
            {
                "id": "newCardForm",
                "operationId": "card.create",
                "fields": [
                    {"name": "deckId", "type": "string", "label": "Deck ID", "required": True},
                    {"name": "front", "type": "string", "label": "Front", "required": True},
                    {"name": "back", "type": "string", "label": "Back", "required": True},
                ],
            },
        ],
    }


def test_coverage_and_manage_area_measured_case():
    raw_be = _make_measured_case_backend()
    be_val = validate_spec_data(raw_be)
    assert be_val.report.valid, be_val.report.errors
    backend = be_val.normalized

    contract = build_contract(backend)
    frontend = _make_measured_case_frontend()

    fe_val = validate_frontend_spec_data(frontend)
    assert fe_val.report.valid, fe_val.report.errors

    # 1. Check uncovered operations
    uncovered = uncovered_operations(frontend, contract)
    assert "card.get" in uncovered
    assert "card.update" in uncovered
    assert "card.delete" in uncovered
    assert "deck.get" in uncovered
    assert "deck.update" in uncovered
    assert "deck.delete" in uncovered
    assert "deck.archive" in uncovered
    assert "deck.resetAll" in uncovered
    assert "deck.purge" in uncovered
    assert "reviewLog.list" in uncovered
    assert "reviewLog.create" in uncovered
    assert "contactMessage.create" in uncovered

    # Covered operations are not in uncovered
    assert "deck.list" not in uncovered
    assert "deck.create" not in uncovered
    assert "card.list" not in uncovered
    assert "card.create" not in uncovered

    # Pair check emits FE_OPERATION_UNUSED warning for each uncovered op
    initial_issues = check_spec_pair(frontend, backend)
    warnings = [i for i in initial_issues if i.code == "FE_OPERATION_UNUSED"]
    warning_messages = " ".join(w.message for w in warnings)
    for op_id in uncovered:
        assert op_id in warning_messages

    # 2. Add Manage area
    managed, notes = add_manage_area(frontend, contract)

    # 3. Sign-in operations are reported with notes
    assert any("deck.purge" in note and "sign-in" in note for note in notes)

    # 4. Verify Manage area structure
    managed_routes = {p["route"]: p for p in managed["pages"]}
    assert "/manage" in managed_routes
    assert "/manage/decks" in managed_routes
    assert "/manage/decks/[id]" in managed_routes
    assert "/manage/decks/[id]/edit" in managed_routes
    assert "/manage/cards" in managed_routes
    assert "/manage/cards/[id]" in managed_routes
    assert "/manage/cards/[id]/edit" in managed_routes
    assert "/manage/review-logs" in managed_routes
    assert "/manage/review-logs/new" in managed_routes

    # Check ReviewLog has no detail or edit page (since it only has list + create)
    assert "/manage/review-logs/[id]" not in managed_routes
    assert "/manage/review-logs/[id]/edit" not in managed_routes

    # Check custom operation on deck: deck.archive (takes id) appears in DetailView actions
    deck_detail_page = managed_routes[
        "manage-decks-detail" if "manage-decks-detail" in managed_routes else "/manage/decks/[id]"
    ]
    detail_section = next(s for s in deck_detail_page["sections"] if s["component"] == "DetailView")
    action_ids = [a["id"] for a in detail_section["content"]["actions"]]
    assert "deck_archive" in action_ids

    # Check custom operation on deck: deck.resetAll (no id) appears in list page
    deck_list_page = managed_routes["/manage/decks"]
    list_action_bars = [s for s in deck_list_page["sections"] if s["component"] == "ActionBar"]
    all_bar_actions = [a["id"] for bar in list_action_bars for a in bar["content"].get("actions", [])]
    assert "deck_reset_all" in all_bar_actions

    # Check header navigation has Manage link
    nav_labels = [n.get("label") for n in managed["layout"]["header"]["navigation"]]
    assert "Manage" in nav_labels

    # 5. Managed spec validates and passes consistency check
    managed_fe_val = validate_frontend_spec_data(managed)
    assert managed_fe_val.report.valid, managed_fe_val.report.errors

    managed_issues = check_spec_pair(managed, backend)
    # The only issue remaining should be the FE_OPERATION_UNUSED warning for deck.purge (needs sign-in)
    assert len(managed_issues) == 1
    assert managed_issues[0].code == "FE_OPERATION_UNUSED"
    assert "deck.purge" in managed_issues[0].message
    assert managed_issues[0].severity == Severity.WARNING

    # 6. Idempotence: calling add_manage_area again produces identical spec
    managed_twice, notes_twice = add_manage_area(managed, contract)
    assert managed_twice == managed
    assert notes_twice == notes

    # 7. remove_manage_area restores original pages
    removed = remove_manage_area(managed)
    assert not any(p["route"].startswith("/manage") for p in removed["pages"])
    assert not any(f["id"].startswith("manage_") or f["id"].startswith("manage-") for f in removed.get("forms", []))
    assert not any(
        n.get("page") == "manage-index" for n in removed.get("layout", {}).get("header", {}).get("navigation", [])
    )
