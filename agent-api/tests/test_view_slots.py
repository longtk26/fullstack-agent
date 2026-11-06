"""Engine-written view slots (Story 23.11), an opt-in experiment: off by default; with it on, the shell and the main
records' cards are written against fixed props, and code refuses a slot that loads data, renders a form or has no
default export (the kit's view is used). Runs on the fake engine only."""

import json
from pathlib import Path

from src.engines.fake_engine import write_view_slot
from src.orchestrator.frontend.app.slots import (
    REGISTRY,
    SLOT_INPUT,
    enabled,
    planned_slots,
    refusal,
    registry_ts,
    slot_input,
)

KIT = (
    Path(__file__).parents[1]
    / "templates"
    / "nextjs_overlay"
    / "files"
    / "dynamic"
    / "app"
    / "src"
    / "components"
    / "app"
)
SPEC = {
    "project": {"locale": "en"},
    "app": {
        "name": "StudioTube",
        "entities": {"Video": {"label": "Video", "plural": "Videos"}},
        "design": {
            "archetype": "catalogue",
            "shell": "topbar",
            "mainEntity": "Video",
            "entities": {
                "Video": {"view": "media-grid", "roles": {"media": "thumbnail"}},
                "Channel": {"view": "cards", "roles": {}},
                "PlaylistItem": {"view": "table", "roles": {}},
            },
        },
    },
}


def test_slots_are_off_unless_asked():
    assert enabled({}) is False and enabled({"viewSlots": "off"}) is False
    assert enabled({"viewSlots": "engine"}) is True


def test_the_shell_and_the_card_views_get_slots_the_main_entity_first():
    slots = planned_slots(SPEC)
    assert [slot.name for slot in slots] == ["Shell", "VideoCard", "ChannelCard"]
    assert slots[1].file == "src/components/app/slots/VideoCard.tsx" and slots[1].brief["view"] == "media-grid"
    asked = slot_input(slots[1], SPEC)
    assert asked["props"] == "TCardProps" and asked["labels"]["plural"] == "Videos"


def test_code_refuses_a_slot_that_does_what_tested_code_does():
    good = "export default function Card() { return <div />; }"
    assert refusal(good) is None
    assert refusal("function Card() { return null; }") == "has no default export"
    for bad, why in (
        ('import { request } from "@/lib/api/client";\nexport default function C() {}', "imports the API client"),
        ("export default function C() { fetch('/x'); }", "calls fetch"),
        ("export default function C() { useOperationQuery('x', {}); }", "loads or changes data"),
        ("export default function C() { return <form />; }", "renders a form"),
        ("export default function C() { localStorage.x = 1; }", "reads storage"),
    ):
        assert refusal(bad) == why


def test_the_registry_names_the_accepted_slots():
    slots = planned_slots(SPEC)
    text = registry_ts([slots[0], slots[1]])
    assert 'import Shell from "./slots/Shell";' in text and 'import VideoCard from "./slots/VideoCard";' in text
    assert 'export const slots: TSlots = { shell: Shell, cards: { "Video": VideoCard } };' in text
    assert "shell: undefined, cards: {  }" in registry_ts([])


def test_the_fake_engine_writes_slots_and_a_planted_fetch_is_refused(tmp_path):
    (tmp_path / ".bga").mkdir()
    for slot in planned_slots(SPEC)[:2]:
        (tmp_path / SLOT_INPUT).write_text(json.dumps(slot_input(slot, SPEC)))
        written = write_view_slot(tmp_path, defect=False)
        assert written == slot.file and refusal((tmp_path / written).read_text()) is None
    (tmp_path / SLOT_INPUT).write_text(json.dumps(slot_input(planned_slots(SPEC)[1], SPEC)))
    written = write_view_slot(tmp_path, defect=True)
    assert refusal((tmp_path / written).read_text()) == "calls fetch"


def test_the_kit_uses_a_slot_only_when_registered():
    assert (
        (KIT / "slots.ts").read_text().strip().endswith("export const slots: TSlots = { shell: undefined, cards: {} };")
    )
    views = (KIT / "views.tsx").read_text()
    assert "slots.cards[props.section.content?.entity" in views
    assert "if (slots.shell)" in (KIT / "AppShell.tsx").read_text()
    assert REGISTRY == "src/components/app/slots.ts"
