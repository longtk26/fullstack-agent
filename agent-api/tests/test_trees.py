"""Epic 21: tree pages (element trees as Frontend-Agent's site JSON): the rules, the code fixes and the schema."""

import copy
import json

from generation_helpers import EXAMPLES

from src.modules.shared.domain.frontend_spec import autofix_frontend_spec, validate_frontend_spec_data
from src.modules.shared.domain.frontend_spec.trees import (
    PRIMITIVES,
    check_tree,
    class_problems,
    classify,
    count_nodes,
    fix_trees,
    scope_css,
    used_primitives,
)

LANDING = json.loads((EXAMPLES / "frontend-specs" / "static-landing.json").read_text())

TREE = {
    "type": "main",
    "props": {"className": "relative bg-background text-foreground"},
    "children": [
        {
            "type": "section",
            "props": {"className": "grid gap-8 md:grid-cols-12 py-24", "animate": {"on": "view", "type": "fade-up"}},
            "children": [
                {
                    "type": "div",
                    "props": {"className": "md:col-span-7"},
                    "children": [
                        {
                            "type": "span",
                            "props": {"className": "inline-flex items-center gap-2 text-primary font-mono text-xs"},
                            "children": [{"type": "Sparkles", "props": {"className": "size-4"}}, "Est. 1924"],
                        },
                        {
                            "type": "h1",
                            "props": {"className": "font-heading text-6xl"},
                            "children": ["A studio of two"],
                        },
                        {
                            "type": "Link",
                            "props": {"to": "page:work", "className": "underline"},
                            "children": ["See the work"],
                        },
                    ],
                },
                {
                    "type": "figure",
                    "props": {"className": "md:col-span-5 lg:-mt-14"},
                    "children": [
                        {"type": "img", "props": {"src": "asset:hero", "alt": "The studio", "className": "rounded-3xl"}}
                    ],
                },
            ],
        },
        {
            "type": "Tabs",
            "props": {"defaultValue": "a"},
            "children": [
                {"type": "TabsList", "children": [{"type": "TabsTrigger", "props": {"value": "a"}, "children": ["A"]}]},
                {"type": "TabsContent", "props": {"value": "a"}, "children": [{"type": "p", "children": ["Tab A"]}]},
            ],
        },
        {"type": "Faq", "props": {"title": "Questions", "items": [{"question": "When?", "answer": "Now."}]}},
    ],
}


def tree_spec(tree: dict, css: str | None = None) -> dict:
    spec = copy.deepcopy(LANDING)
    spec["pages"][0] = {"route": "/", "title": "Home", "tree": tree, **({"css": css} if css else {})}
    return spec


def test_node_types_are_classified():
    assert classify("div") == "element" and classify("Tabs") == "primitive" and classify("Faq") == "section"
    assert classify("CollectionBrowser") == "data" and classify("Metric") == "data"
    assert classify("Sparkles") == "icon" and classify("ArrowUpRight") == "icon"
    assert classify("Link") == "primitive", "a primitive wins over the icon of the same name"
    assert classify("script") == "removed" and classify("OpeningSequence") == "unknown"
    assert count_nodes(TREE) == (15, 5), "object nodes only; text children are not nodes"


def test_a_tree_page_validates_and_normalizes():
    result = validate_frontend_spec_data(tree_spec(TREE, ".hero { background: var(--primary) }"))
    assert result.report.valid, result.report.errors
    assert result.normalized["pages"][0]["tree"]["type"] == "main" and result.normalized["pages"][0]["sections"] == []
    assert used_primitives(result.normalized) == {"tabs"} and set(PRIMITIVES["Tabs"]) == set("tabs")

    neither = tree_spec(TREE)
    del neither["pages"][0]["tree"]
    assert not validate_frontend_spec_data(neither).report.valid, "a page needs sections or a tree"


def test_the_rules_find_what_breaks_them():
    broken = copy.deepcopy(TREE)
    broken["children"].append({"type": "script", "children": ["alert(1)"]})
    broken["children"].append({"type": "Wobble", "children": [{"type": "h1", "children": ["Second"]}]})
    broken["children"][0]["props"]["className"] = "bg-emerald-500 text-[#fff] fixed grid"
    broken["children"][0]["children"][1]["children"][0]["props"]["src"] = "https://example.com/x.jpg"
    broken["children"][0]["children"][0]["children"][2]["props"]["to"] = "page:nowhere"
    found = check_tree(broken, "/pages/0/tree", {"home", "work"}, {"hero"}, {"products": {"name"}})
    codes = {(issue["code"], issue["warning"]) for issue in found}
    assert ("FE_UNSUPPORTED_FEATURE", True) in codes and ("FE_UNKNOWN_PAGE", False) in codes
    assert ("FE_DESIGN_RULE", True) in codes and ("FE_UNKNOWN_ASSET", True) in codes
    assert any("2 h1" in issue["message"] for issue in found)
    assert class_problems("bg-emerald-500 text-[#fff] fixed grid md:fixed bg-primary/10") == [
        "bg-emerald-500",
        "text-[#fff]",
        "fixed",
        "md:fixed",
    ]

    report = validate_frontend_spec_data(tree_spec(broken)).report
    assert not report.valid and any(i.code == "FE_UNKNOWN_PAGE" for i in report.errors)


def test_the_fixes_repair_what_the_rules_can_decide():
    broken = copy.deepcopy(TREE)
    broken["children"].append({"type": "script", "children": ["alert(1)"]})
    broken["children"].append(
        {"type": "Wobble", "props": {"className": "p-4"}, "children": [{"type": "p", "children": ["kept"]}]}
    )
    broken["children"][0]["props"]["className"] = "bg-emerald-500 fixed grid"
    broken["children"][0]["children"][1]["children"][0]["props"] = {"src": "images/x.jpg"}
    spec, notes = fix_trees(tree_spec(broken, ".a { position: fixed; color: #fff } @import url(x);"))
    tree = spec["pages"][0]["tree"]
    assert [child["type"] for child in tree["children"]] == ["section", "Tabs", "Faq", "div"], (
        "script dropped, Wobble unwrapped"
    )
    assert tree["children"][3]["children"][0]["children"] == ["kept"]
    assert tree["children"][0]["props"]["className"] == "grid"
    image = tree["children"][0]["children"][1]["children"][0]["props"]
    placeholder = f"tree-image-{len(LANDING['assets']) + 1}"
    assert image["src"] == f"asset:{placeholder}" and image["alt"] == ""
    assert spec["assets"][-1] == {
        "id": placeholder,
        "kind": "image",
        "alt": None,
        "source": "placeholder",
        "decorative": True,
    }
    assert spec["pages"][0]["css"] == '[data-page="home"] .a {  color: #fff }'
    messages = " | ".join(note["message"] for note in notes)
    assert "not rendered; removed" in messages and "unwrapped" in messages and "theme tokens only" in messages
    assert "placeholder asset" in messages and "Page CSS cleaned" in messages and "raw colours" in messages
    assert validate_frontend_spec_data(spec).report.valid

    fixed, auto_notes = autofix_frontend_spec(tree_spec(broken))
    assert fixed["pages"][0]["tree"]["children"][0]["props"]["className"] == "grid" and len(auto_notes) >= 4


def test_old_lucide_names_are_renamed_not_unwrapped():
    """gen_01M6J88EY82D746ZG01MB7WE77: the engine wrote AlertTriangle, CheckCircle2, History; they were dropped."""
    tree = {
        "type": "main",
        "children": [
            {"type": "AlertTriangle", "props": {"className": "size-4"}},
            {"type": "CheckCircle2", "props": {"className": "size-4"}},
            {"type": "History"},
            {"type": "Sparkles"},
        ],
    }
    spec, notes = fix_trees(tree_spec(tree))
    types = [child["type"] for child in spec["pages"][0]["tree"]["children"]]
    assert types == ["TriangleAlert", "CircleCheck", "RotateCcwClock", "Sparkles"]
    assert all(classify(name) == "icon" for name in types)
    assert spec["pages"][0]["tree"]["children"][0]["props"] == {"className": "size-4"}
    assert sum("Lucide's current name" in note["message"] for note in notes) == 3
    assert not any("unwrapped" in note["message"] for note in notes)


def test_metric_and_chart_words_are_mapped_and_an_unclear_metric_goes_alone():
    """gen_01M6J88EY82D746ZG01MB7WE77: one Metric with a wrong `fn` cost the home page its whole tree."""
    metric = lambda **props: {"type": "Metric", "props": {"collection": "products", **props}}  # noqa: E731
    tree = {
        "type": "main",
        "children": [
            metric(fn="average", field="price"),
            metric(fn="Total", field="price"),
            metric(fn="total"),
            metric(fn="latest"),
            metric(fn="median", field="price"),
            metric(fn="max"),
            {"type": "Chart", "props": {"collection": "products", "kind": "pie", "groupBy": "category"}},
            {"type": "h1", "children": ["Stock"]},
        ],
    }
    spec, notes = fix_trees(tree_spec(tree))
    children = spec["pages"][0]["tree"]["children"]
    assert [child["props"].get("fn") for child in children if child["type"] == "Metric"] == [
        "avg",
        "sum",
        "count",
        "count",
    ], "'total' without a field counts; an unknown fn without a field counts; median and max without field go"
    assert children[-2]["props"]["kind"] == "donut" and children[-1]["type"] == "h1"
    assert sum("Metric dropped" in note["message"] for note in notes) == 2
    found = check_tree(spec["pages"][0]["tree"], "/pages/0/tree", set(), set(), {"products": {"price", "category"}})
    assert not [issue for issue in found if not issue["warning"]]


def test_css_is_scoped_to_the_page():
    css = ".a{color:red} @media (min-width:600px){.b, .c{x:1}} @keyframes k{from{opacity:0}} @supports (x:y){.d{y:1}}"
    assert scope_css(css, "home").splitlines() == [
        '[data-page="home"] .a {color:red}',
        "@media (min-width:600px) {",
        '[data-page="home"] .b, [data-page="home"] .c {x:1}',
        "}",
        "@keyframes k {from{opacity:0}}",
        "@supports (x:y) {",
        '[data-page="home"] .d {y:1}',
        "}",
    ]


def test_data_components_check_their_collections_on_static_sites():
    tree = {
        "type": "main",
        "children": [
            {
                "type": "CollectionStrip",
                "props": {"limit": 3, "sortBy": "rank"},
                "children": [{"type": "ItemList", "children": [{"type": "RecordField", "props": {"field": "name"}}]}],
            },
            {"type": "Metric", "props": {"collection": "products", "fn": "sum"}},
            {"type": "Chart", "props": {"collection": "nope", "kind": "pie", "groupBy": "category"}},
        ],
    }
    one = {"products": {"name", "rank"}}
    found = check_tree(tree, "/pages/0/tree", set(), set(), one)
    messages = [issue["message"] for issue in found]
    assert not any("needs 'collection'" in m for m in messages), "one collection: the components need no name"
    assert any("needs 'field'" in m for m in messages) and any("Unknown collection 'nope'" in m for m in messages)
    assert any("'kind' is one of" in m for m in messages)
    two = one | {"news": {"title"}}
    assert any("needs 'collection'" in i["message"] for i in check_tree(tree, "/pages/0/tree", set(), set(), two))
    assert not any("needs 'collection'" in i["message"] for i in check_tree(tree, "/pages/0/tree", set(), set(), None))
