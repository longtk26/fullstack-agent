import re

_IRREGULAR_PLURALS = {"person": "people", "child": "children", "man": "men", "woman": "women"}
_IRREGULAR_SINGULARS = {plural: singular for singular, plural in _IRREGULAR_PLURALS.items()}


def to_snake(name: str) -> str:
    value = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    value = re.sub(r"(?<=[A-Z])([A-Z][a-z])", r"_\1", value)
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def to_kebab(name: str) -> str:
    return to_snake(name).replace("_", "-")


def to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in to_snake(name).split("_") if part)


def to_camel(name: str) -> str:
    pascal = to_pascal(name)
    return pascal[:1].lower() + pascal[1:]


def pluralize(word: str) -> str:
    lower = word.lower()
    if lower in _IRREGULAR_PLURALS:
        return _IRREGULAR_PLURALS[lower]
    if re.search(r"[^aeiou]y$", lower):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", lower):
        return word + "es"
    return word + "s"


def singularize(word: str) -> str:
    lower = word.lower()
    if lower in _IRREGULAR_SINGULARS:
        return _IRREGULAR_SINGULARS[lower]
    if lower.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    if re.search(r"(ses|xes|zes|ches|shes)$", lower):
        return word[:-2]
    if lower.endswith("s") and not lower.endswith("ss"):
        return word[:-1]
    return word


def table_name(entity_name: str) -> str:
    snake = to_snake(entity_name)
    head, _, last = snake.rpartition("_")
    return f"{head}_{pluralize(last)}" if head else pluralize(last)
