"""Stories 20.5 and 20.6: icon references and intents resolved per set, the per-site icon registry, direction icons
and motion from the tone, the signature moment, the motion presets and their CSS."""

import copy
import json

import pytest

from src.engines.fake_design import with_icon_intents
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.icons import closest_icon, icon_index, kebab, resolve_icon
from src.orchestrator.drafting.design_cards import Card, fill_card, home_pool, signature
from src.orchestrator.drafting.design_direction import directions
from src.orchestrator.drafting.design_tone import icon_style, motion_feel
from src.orchestrator.frontend.custom_components import ICON_PACKAGE
from src.orchestrator.frontend.motion import (
    FEELS,
    MARK_OVERSHOOT,
    SURFACE_OVERSHOOT,
    damping_for,
    linear_easing,
    motion_css,
)
from src.orchestrator.frontend.planner import plan_frontend
from src.orchestrator.frontend.renderer import ICONS_FILE, SITE_FILE, renderer_files
from src.orchestrator.frontend.theme import build_theme, globals_css
from tests.generation_helpers import EXAMPLES

LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())

# -- icons -----------------------------------------------------------------------------------------------------------

# Intents from the golden requirements (examples/requirements/diversity) and what each may resolve to, per set.
INTENTS = [
    ("fast delivery", {"Truck"}, {"Truck"}),
    ("secure payment", {"CreditCard", "Lock"}, {"CreditCard", "Lock", "Shield"}),
    ("opening hours", {"Clock"}, {"Clock"}),
    ("location", {"MapPin"}, {"MapPin"}),
    ("phone", {"Phone"}, {"Phone"}),
    ("email", {"Mail"}, {"Envelope"}),
    ("haircut", {"Scissors"}, {"Scissors"}),
    ("massage", {"Hand", "HandHeart"}, {"Hand", "HandHeart"}),
    ("coffee", {"Coffee"}, {"Coffee"}),
    ("cake", {"Cake"}, {"Cake"}),
    ("sourdough", {"Wheat", "Croissant"}, {"Bread"}),
    ("doctor", {"Stethoscope"}, {"Stethoscope"}),
    ("vaccination", {"Syringe"}, {"Syringe"}),
    ("children", {"Baby"}, {"Baby"}),
    ("repeat prescriptions", {"Pill"}, {"Pill"}),
    ("appointment", {"Calendar"}, {"Calendar"}),
    ("check-ups", {"Stethoscope"}, {"Stethoscope"}),
    ("contract", {"Signature", "FilePen"}, {"Signature"}),
    ("team", {"Users"}, {"Users"}),
    ("support", {"Headset"}, {"Headset"}),
    ("gift", {"Gift"}, {"Gift"}),
    ("organic", {"Leaf"}, {"Leaf"}),
    ("award", {"Trophy", "Medal", "Award"}, {"Trophy", "Medal"}),
    ("growth", {"TrendingUp"}, {"TrendUp"}),
    ("personal training", {"Dumbbell"}, {"Barbell"}),
    ("printer", {"Printer"}, {"Printer"}),
]


def test_the_icon_index_covers_both_pinned_sets():
    index = icon_index()
    assert index["lucide"]["version"] == "1.62.0" and len(index["lucide"]["icons"]) > 1500
    assert index["phosphor"]["version"] == "2.1.10" and len(index["phosphor"]["icons"]) > 1200
    assert "delivery" in index["lucide"]["icons"]["truck"] and "delivery" in index["phosphor"]["icons"]["Truck"]
    assert kebab("ArrowUp01") == "arrow-up-0-1" and kebab("MapPin") == "map-pin"


@pytest.mark.parametrize(("intent", "lucide", "phosphor"), INTENTS)
def test_intents_resolve_to_an_icon_that_means_it(intent, lucide, phosphor):
    assert resolve_icon(f"intent:{intent}", "lucide").removeprefix("lucide:") in lucide
    assert resolve_icon(f"intent:{intent}", "phosphor").removeprefix("phosphor:") in phosphor


def test_references_follow_the_sites_set():
    assert resolve_icon("lucide:Truck", "lucide") == "lucide:Truck"
    assert resolve_icon("lucide:Truck", "phosphor") == "phosphor:Truck"
    assert resolve_icon("lucide:Mail", "phosphor") == "phosphor:Envelope"
    assert resolve_icon("phosphor:Envelope", "lucide") == "lucide:Mail"
    assert resolve_icon("intent:truck", "none") is None and resolve_icon("intent:zzqx", "lucide") is None
    assert resolve_icon("truck", "lucide") is None, "a bare word is not a reference"
    assert closest_icon("Truk", "lucide") == "Truck"


def _spec(**theme) -> dict:
    spec = copy.deepcopy(LANDING)
    spec["theme"] |= theme
    spec["content"][0]["records"][0]["icon"] = "intent:brand identity"
    spec["content"][0]["records"][1]["icon"] = "lucide:Globe"
    return spec


def test_the_validator_warns_on_icons_it_cannot_draw():
    spec = _spec(icons={"set": "lucide", "weight": "duotone"})
    spec["content"][0]["records"][2]["icon"] = "lucide:Truk"
    warnings = {(w.code, w.path): w for w in validate_frontend_spec_data(spec).report.warnings}
    assert warnings[("FE_UNKNOWN_ICON", "/content/0/records/2/icon")].hint == "Closest icon: lucide:Truck"
    assert ("FE_DESIGN_RULE", "/theme/icons/weight") in warnings
    assert not validate_frontend_spec_data(_spec()).report.warnings, "resolvable icons are fine"


def _files(spec: dict) -> dict[str, str]:
    normalized = validate_frontend_spec_data(spec).normalized
    return renderer_files(plan_frontend(normalized), normalized, None)


def test_a_site_imports_only_the_icons_it_uses_in_its_set():
    files = _files(_spec(icons={"set": "phosphor", "weight": "duotone", "treatment": "tile"}))
    services = json.loads(files[SITE_FILE])["collections"]["services"]
    assert [item.get("icon") for item in services] == ["phosphor:Fingerprint", "phosphor:Globe", None]
    icons = files[ICONS_FILE]
    assert 'import { Fingerprint as PhosphorFingerprint } from "@phosphor-icons/react/dist/ssr/Fingerprint";' in icons
    assert '"phosphor:Globe": PhosphorGlobe' in icons and "lucide-react" not in icons
    assert (
        'export const iconStyle: TIconStyle = {"set": "phosphor", "weight": "duotone", "treatment": "tile"};' in icons
    )
    assert icons.count("@phosphor-icons/react/dist/ssr/") == 2 + 6, "two content icons and the six marks"


def test_lucide_by_default_and_no_content_icons_with_none():
    lucide = _files(_spec())[ICONS_FILE]
    assert 'import LucideFingerprintPattern from "lucide-react/icons/fingerprint-pattern";' in lucide
    assert 'export const glyphSet: "lucide" | "phosphor" = "lucide";' in lucide
    none = _files(_spec(icons={"set": "none"}))
    assert "icon" not in json.dumps(json.loads(none[SITE_FILE])["collections"])
    assert "export const icons: Record<string, TIconComponent> = {\n};" in none[ICONS_FILE]
    assert "LucideCheck" in none[ICONS_FILE], "marks that carry meaning (checks) are still drawn"


def test_the_fake_engine_writes_icon_intents_from_titles():
    spec = with_icon_intents(copy.deepcopy(LANDING))
    records = {c["collection"]: c["records"] for c in spec["content"]}
    assert [r["icon"] for r in records["services"]] == ["intent:Brand identity", "intent:Websites", "intent:Print"]
    assert records["plans"][0]["icon"] == "intent:Starter", "Pricing plans by name"
    assert "icon" not in records["testimonials"][0], "testimonials take no icon"


def test_custom_components_may_not_import_an_icon_package():
    assert ICON_PACKAGE.search('import { Truck } from "lucide-react";')
    assert ICON_PACKAGE.search("import { Truck } from '@phosphor-icons/react/dist/ssr';")
    assert not ICON_PACKAGE.search('import { Icon } from "@/components/sections/Icon";')


# -- tone → icons and motion -----------------------------------------------------------------------------------------


def tone(energy=3, finish=3, density=3, weight=3, seriousness=3) -> dict[str, int]:
    return {"energy": energy, "finish": finish, "density": density, "weight": weight, "seriousness": seriousness}


@pytest.mark.parametrize(
    ("levels", "icons", "feel"),
    [
        (tone(finish=1, energy=5), ("none", "regular", "plain"), "cut"),
        (tone(seriousness=5, energy=2), ("none", "regular", "plain"), "slide"),
        (tone(weight=1, finish=4, energy=1), ("lucide", "thin", "plain"), "none"),
        (tone(weight=2, finish=5), ("lucide", "light", "plain"), "flow"),
        (tone(weight=4, seriousness=2, energy=4), ("phosphor", "duotone", "tile"), "bounce"),
        (tone(weight=5, energy=4), ("phosphor", "fill", "plain"), "click"),
        (tone(weight=4), ("phosphor", "bold", "plain"), "drop"),
        (tone(seriousness=2), ("phosphor", "regular", "tile"), "slide"),
        (tone(weight=2, energy=2), ("lucide", "regular", "plain"), "float"),
        (tone(), ("lucide", "regular", "plain"), "slide"),
    ],
)
def test_the_tone_decides_icons_and_motion(levels, icons, feel):
    assert tuple(icon_style(levels).values()) == icons
    assert motion_feel(levels) == feel


FLOOR = directions("A family bakery with sourdough and cakes")[0]


def test_a_card_gets_icons_motion_and_a_signature_its_page_can_show():
    pool = home_pool(LANDING)
    card = Card.model_validate({"name": "A", "tone": tone(weight=4), "heroLayout": "split", "keyVisual": "photo"})
    theme = fill_card(card, FLOOR, pool, [], 1)[0]["theme"]
    assert theme["icons"] == {"set": "phosphor", "weight": "bold", "treatment": "plain"}
    assert theme["motion"] == {"feel": "drop", "signature": "imageUnmask"}
    chosen = Card.model_validate(
        {"name": "B", "icons": {"set": "lucide", "weight": "fill"}, "motion": "float", "signature": "countUp"}
    )
    direction, notes = fill_card(chosen, FLOOR, pool, [], 1)
    assert direction["theme"]["icons"]["set"] == "phosphor" and "icons: fill needs the phosphor set" in notes
    assert direction["theme"]["motion"] == {"feel": "float", "signature": "imageUnmask"}, "no figures: no count-up"
    stats = [*pool, {"id": "n", "component": "Stats", "content": {"items": [{"label": "Years", "value": "12"}]}}]
    assert signature("", "split", stats) == "countUp"
    assert signature("", "type", pool) == "headlineRise" and signature("indicator", "split", pool) == "indicator"
    quiet = Card.model_validate({"name": "C", "tone": tone(energy=1, weight=1)})
    assert fill_card(quiet, FLOOR, pool, [], 1)[0]["theme"]["motion"] == {"feel": "none", "signature": "none"}


# -- motion presets --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("feel", [name for name in FEELS if name != "cut"])
def test_spring_easings_end_at_one_and_keep_their_overshoot(feel):
    stiffness, ratio, *_ = FEELS[feel]
    surface = linear_easing(stiffness, max(ratio, damping_for(SURFACE_OVERSHOOT)))
    mark = linear_easing(stiffness, max(ratio, damping_for(MARK_OVERSHOOT)))
    for points, limit in ((surface, SURFACE_OVERSHOOT), (mark, MARK_OVERSHOOT)):
        assert points[0] == 0 and points[-1] == 1 and abs(points[-2] - 1) <= 0.008
        assert max(points) <= 1 + limit + 0.001


def test_a_still_site_has_no_motion_and_a_moving_one_its_feel_and_signature():
    still = validate_frontend_spec_data(LANDING).normalized
    built = build_theme(still["theme"])
    assert "motion" not in built and "data-motion" not in globals_css(built) and motion_css(None) == ""
    assert "motion" not in json.loads(_files(LANDING)[SITE_FILE])
    moving = copy.deepcopy(LANDING)
    moving["theme"]["motion"] = {"feel": "drop", "signature": "headlineRise"}
    normalized = validate_frontend_spec_data(moving).normalized
    css = globals_css(build_theme(normalized["theme"]))
    assert "--motion-duration: 480ms;" in css and "--motion-enter: 420ms;" in css and "--motion-y: -24px;" in css
    assert "--motion-ease: linear(0," in css
    assert "@keyframes bga-rise" in css and "@keyframes bga-unmask" not in css
    assert "html[data-motion='on'] [data-slot='button']:active" in css
    assert json.loads(_files(moving)[SITE_FILE])["motion"] == {"feel": "drop", "signature": "headlineRise"}
    cut = globals_css(build_theme({**normalized["theme"], "motion": {"feel": "cut", "signature": "countUp"}}))
    assert "steps(2, jump-end)" in cut and "--motion-count: 1600ms;" in cut
