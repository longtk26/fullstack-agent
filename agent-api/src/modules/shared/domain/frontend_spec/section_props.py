"""Typed `content` of the built-in sections (Story 17.1).

Each catalogue section has a props model for its `content`; list sections also have an item model that applies to
`content.items` and to the records of the content collection the section is bound to (`data.collection`). Unknown
keys are kept (`extra="allow"`) and reported as warnings by the validator, so a typo never breaks rendering and the
editor's JSON Schema does not flag them as errors. Layout nodes (`Columns`, `Stack`, `Grid`, `Tabs`) hold other
sections in `children`; nesting is at most `MAX_DEPTH` section levels (decision Q18).
"""

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from src.modules.shared.domain.backend_spec.schema_v1 import SpecModel

IMAGE = r"^(asset:[a-z][a-z0-9-]*|https://\S+)$"
LINK = r"^(https?://|mailto:|tel:|/)"
MAX_DEPTH = 3
Columns = Literal[2, 3, 4]
Gap = Literal["sm", "md", "lg"]


class Props(SpecModel):
    model_config = ConfigDict(extra="allow")


class Cta(Props):
    label: str = Field(min_length=1, max_length=60)
    page: str | None = None
    href: str | None = Field(default=None, pattern=LINK)

    @model_validator(mode="after")
    def _one_target(self):
        if (self.page is None) == (self.href is None):
            raise ValueError("a call to action needs exactly one of 'page' or 'href'")
        return self


# -- items (content.items or the records of the bound collection) ----------------------------------------------------


class FeatureItem(Props):
    title: str = Field(min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=600)


class TestimonialItem(Props):
    quote: str = Field(min_length=1, max_length=600)
    author: str = Field(min_length=1, max_length=120)
    role: str | None = Field(default=None, max_length=120)


class FaqItem(Props):
    question: str = Field(min_length=1, max_length=300)
    answer: str = Field(min_length=1, max_length=2000)


class PlanItem(Props):
    name: str = Field(min_length=1, max_length=60)
    price: str | int | float
    description: str | None = Field(default=None, max_length=300)
    features: list[str] = []
    cta: Cta | None = None
    highlighted: bool = False


class StatItem(Props):
    label: str = Field(min_length=1, max_length=60)
    value: str | int | float


class GalleryItem(Props):
    image: str = Field(pattern=IMAGE)
    title: str | None = Field(default=None, max_length=120)
    caption: str | None = Field(default=None, max_length=300)


# -- sections ----------------------------------------------------------------------------------------------------------


class HeroProps(Props):
    heading: str = Field(min_length=1, max_length=160)
    eyebrow: str | None = Field(default=None, max_length=60)
    body: str | None = Field(default=None, max_length=600)
    image: str | None = Field(default=None, pattern=IMAGE)
    cta: Cta | None = None
    secondary_cta: Cta | None = None


class FeaturesProps(Props):
    title: str | None = None
    description: str | None = None
    items: list[FeatureItem] | None = Field(default=None, max_length=24)
    columns: Columns | None = None


class CallToActionProps(Props):
    heading: str = Field(min_length=1, max_length=160)
    body: str | None = Field(default=None, max_length=600)
    cta: Cta


class TestimonialsProps(Props):
    title: str | None = None
    items: list[TestimonialItem] | None = Field(default=None, max_length=24)


class FaqProps(Props):
    title: str | None = None
    items: list[FaqItem] | None = Field(default=None, max_length=50)


class PricingProps(Props):
    title: str | None = None
    description: str | None = None
    items: list[PlanItem] | None = Field(default=None, max_length=6)


class StatsProps(Props):
    title: str | None = None
    items: list[StatItem] | None = Field(default=None, max_length=12)


class GalleryProps(Props):
    title: str | None = None
    items: list[GalleryItem] | None = Field(default=None, max_length=48)
    columns: Columns | None = None


class RichTextProps(Props):
    heading: str | None = Field(default=None, max_length=160)
    body: str = Field(min_length=1, max_length=20000)  # paragraphs separated by a blank line


class ContactInfoProps(Props):
    title: str | None = None
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=300)
    map_url: str | None = Field(default=None, pattern=r"^https://")

    @model_validator(mode="after")
    def _something(self):
        if not (self.email or self.phone or self.address):
            raise ValueError("contact info needs at least one of 'email', 'phone' or 'address'")
        return self


class DataSectionProps(Props):
    """CardGrid, DataTable, DetailView, List: the records come from `data`; content only titles the section."""

    title: str | None = None
    description: str | None = None


class FormProps(Props):
    title: str | None = None
    description: str | None = None


# -- layout nodes ------------------------------------------------------------------------------------------------------


class ColumnsProps(Props):
    title: str | None = None
    columns: Columns | None = None  # default: one column per child, at most 4
    gap: Gap = "md"


class StackProps(Props):
    title: str | None = None
    gap: Gap = "md"


class GridProps(Props):
    title: str | None = None
    columns: Columns = 2
    gap: Gap = "md"


class TabsProps(Props):
    labels: list[str] | None = None  # one per child; default: each child's title / heading / id


SECTION_PROPS: dict[str, type[Props]] = {
    "Hero": HeroProps,
    "Features": FeaturesProps,
    "CallToAction": CallToActionProps,
    "Testimonials": TestimonialsProps,
    "Faq": FaqProps,
    "Pricing": PricingProps,
    "Stats": StatsProps,
    "Gallery": GalleryProps,
    "RichText": RichTextProps,
    "ContactInfo": ContactInfoProps,
    "Form": FormProps,
    "CardGrid": DataSectionProps,
    "DataTable": DataSectionProps,
    "DetailView": DataSectionProps,
    "List": DataSectionProps,
    "Columns": ColumnsProps,
    "Stack": StackProps,
    "Grid": GridProps,
    "Tabs": TabsProps,
}
# List sections: the item model for `content.items` and for the records of `data.collection`.
SECTION_ITEMS: dict[str, type[Props]] = {
    "Features": FeatureItem,
    "Testimonials": TestimonialItem,
    "Faq": FaqItem,
    "Pricing": PlanItem,
    "Stats": StatItem,
    "Gallery": GalleryItem,
}
LAYOUT_SECTIONS = frozenset({"Columns", "Stack", "Grid", "Tabs"})
