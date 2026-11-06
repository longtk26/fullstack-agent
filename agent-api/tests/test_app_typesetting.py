"""Japanese and English typesetting for apps (Story 23.8): the locale from the requirement, a bundled Japanese face
after the Latin one, `:lang(ja)` rules, the kit's and the planner's words in Japanese; English apps unchanged."""

import json
from pathlib import Path

from src.modules.shared.domain.backend_spec import validate_spec_data
from src.modules.shared.domain.frontend_spec import validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.fonts import FONTS, JA_FONTS, closest_font
from src.orchestrator.backend.planner import build_plan
from src.orchestrator.frontend.app.files import app_files
from src.orchestrator.frontend.app.outline import complete_outline
from src.orchestrator.frontend.app.screens import app_frontend_spec, ensure_aggregates
from src.orchestrator.frontend.app.typesetting import ja_css, ja_face, locale_of
from src.orchestrator.frontend.planner import plan_frontend
from src.orchestrator.integration.contract import build_contract

EXAMPLES = Path(__file__).parents[2] / "examples"
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


def test_the_locale_comes_from_the_requirements_script():
    assert locale_of("歯科クリニックの予約アプリ。患者は予約し、受付が確認します。") == "ja"
    assert locale_of("A dental clinic booking app with an お知らせ page") is None, "a few Japanese words: English"
    assert locale_of("牙科诊所预约") is None, "Chinese without kana is not Japanese"
    assert locale_of("") is None


def test_each_look_has_its_japanese_face():
    assert ja_face("editorial") == "Shippori Mincho" and ja_face("enterprise") == "BIZ UDPGothic"
    assert ja_face("glass") == "Noto Sans JP" and ja_face(None, "Newsreader") == "Noto Serif JP"
    assert set(JA_FONTS) & set(FONTS) == set(), "static sites never pair a Japanese face"
    assert closest_font("Noto Sans JP") != "Noto Sans JP"


def test_japanese_css_stacks_the_face_after_the_latin_one():
    css = ja_css(
        {"fonts": {"body": '"Inter", ui-sans-serif, sans-serif', "heading": '"Syne", sans-serif'}}, "Noto Sans JP"
    )
    assert '--font-body: "Inter", "Noto Sans JP", "Hiragino Sans"' in css
    assert ":root:lang(ja) body { line-height: 1.8;" in css and "text-transform: none" in css
    assert "font-weight: min(var(--heading-weight, 600), 700)" in css


def _app(name: str, locale: str | None):
    backend = validate_spec_data(json.loads((EXAMPLES / "specs" / f"{name}.json").read_text())).normalized
    raw = json.loads((EXAMPLES / "app-outlines" / f"{name}.json").read_text())
    if locale:
        raw["locale"] = locale
    outline, _ = complete_outline(raw, backend, build_contract(backend, build_plan(backend)))
    backend, outline, _ = ensure_aggregates(backend, outline)
    contract = build_contract(backend, build_plan(backend))
    spec = validate_frontend_spec_data(
        app_frontend_spec(backend, outline, {"colorScheme": "light-dark"}, contract).spec
    ).normalized
    return spec, app_files(plan_frontend(spec, contract), spec, contract)


def test_a_japanese_app_gets_its_face_its_rules_and_japanese_words():
    spec, files = _app("clinic-bookings", "ja")
    assert spec["project"]["locale"] == "ja"
    assert "@fontsource/" in files["src/app/fonts.ts"] and "Story 23.8" in files["src/app/fonts.ts"]
    assert ":root:lang(ja)" in files["src/app/globals.css"]
    data = json.loads(files["src/content/app.json"])
    labels = [
        action["label"]
        for page in data["pages"].values()
        for s in page["sections"]
        for action in (s.get("content") or {}).get("actions") or []
    ]
    assert "編集" in labels and "Edit" not in labels
    assert any(item["label"] == "ダッシュボード" for item in data["nav"]) or data["design"]["homeView"] != "dashboard"


def test_an_english_app_has_no_japanese_typesetting():
    spec, files = _app("news-feed", None)
    assert "locale" not in spec["project"] or spec["project"]["locale"] == "en"
    assert ":lang(ja)" not in files.get("src/app/globals.css", "") and "src/app/fonts.ts" not in files


def test_every_kit_string_has_a_japanese_text():
    text = (KIT / "messages.ts").read_text()
    english = text.split("const en = {", 1)[1].split("} as const;", 1)[0]
    japanese = text.split("const ja: Record<TKey, string> = {", 1)[1].split("};", 1)[0]
    keys = lambda block: {line.split(":", 1)[0].strip() for line in block.splitlines() if ":" in line}  # noqa: E731
    assert keys(english) == keys(japanese) and len(keys(english)) > 30
