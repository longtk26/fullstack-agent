import pytest

from src.modules.shared.domain.backend_spec.naming import pluralize, singularize, table_name, to_camel, to_snake


@pytest.mark.parametrize(
    ("name", "snake"),
    [
        ("projectId", "project_id"),
        ("createdAt", "created_at"),
        ("HTTPServer", "http_server"),
        ("Order Item", "order_item"),
    ],
)
def test_to_snake(name, snake):
    assert to_snake(name) == snake


@pytest.mark.parametrize(
    ("entity", "table"),
    [
        ("Task", "tasks"),
        ("Category", "categories"),
        ("Box", "boxes"),
        ("OrderItem", "order_items"),
        ("Person", "people"),
    ],
)
def test_table_name(entity, table):
    assert table_name(entity) == table


@pytest.mark.parametrize("word", ["post", "category", "box", "match", "person", "status"])
def test_singularize_inverts_pluralize(word):
    assert singularize(pluralize(word)) == word


def test_to_camel():
    assert to_camel("blog-posts") == "blogPosts"
