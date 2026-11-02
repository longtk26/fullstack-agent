"""Typed `content` of the built-in sections (Story 17.1).

Each catalogue section has a props model for its `content`; list sections also have an item model that applies to
`content.items` and to the records of the content collection the section is bound to (`data.collection`). Unknown
keys are kept (`extra="allow"`) and reported as warnings by the validator, so a typo never breaks rendering and the
editor's JSON Schema does not flag them as errors. Layout nodes (`Columns`, `Stack`, `Grid`, `Tabs`) hold other
sections in `children`; nesting is at most `MAX_DEPTH` section levels (decision Q18).

Variants (Story 17.7) pick a look per section: a background for content sections, a layout for the hero and a card
style for list sections. They only switch between theme tokens, so every look follows the preset and light/dark.
Story 20.2 adds five hero layouts and section forms (`form`: how a list section lays out its items), so directions
differ in structure, not only in colour.
"""

from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, model_validator

from src.modules.shared.domain.backend_spec.schema_v1 import SpecModel

IMAGE = r"^(asset:[a-z][a-z0-9-]*|https://\S+)$"
Image = Annotated[str, Field(pattern=IMAGE)]
LINK = r"^(https?://|mailto:|tel:|/)"
MAX_DEPTH = 3
Columns = Literal[2, 3, 4]
Gap = Literal["sm", "md", "lg"]
Background = Literal["default", "muted", "primary", "image"]
CardStyle = Literal["outline", "filled", "plain"]
HeroVariant = Literal["split", "centered", "banner", "stage", "type", "stacked", "collage", "vertical"]
FeaturesForm = Literal["cards", "list", "ledger", "alternating"]
TestimonialsForm = Literal["cards", "quote", "strip"]
StatsForm = Literal["cards", "figures", "inline"]


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


class Surface(Props):
    """A content section's background: the page, the muted tone, the primary colour, or an image under a scrim."""

    background: Background = "default"
    background_image: str | None = Field(default=None, pattern=IMAGE)

    @model_validator(mode="after")
    def _image_needs_source(self):
        if self.background == "image" and self.background_image is None:
            raise ValueError("background 'image' needs 'backgroundImage'")
        return self


# -- items (content.items or the records of the bound collection) ----------------------------------------------------


class FeatureItem(Props):
    title: str = Field(min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=600)
    image: str | None = Field(default=None, pattern=IMAGE)  # shown by the `alternating` form


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


ActionKind = Literal["link", "mutation"]
ActionVariant = Literal["default", "destructive", "outline", "secondary", "ghost", "link"]


class ActionOnSuccess(Props):
    toast: str | None = None
    navigate: str | None = None


class SectionAction(Props):
    id: str = Field(min_length=1, max_length=63)
    label: str = Field(min_length=1, max_length=60)
    kind: ActionKind = "link"
    page: str | None = None
    params: dict[str, Any] = {}
    operation_id: str | None = Field(default=None, alias="operationId")
    body: dict[str, Any] = {}
    confirm: str | bool | None = None
    variant: ActionVariant | None = None
    on_success: ActionOnSuccess | None = Field(default=None, alias="onSuccess")

    @model_validator(mode="after")
    def _validate_action(self):
        if self.kind == "link" and not self.page:
            raise ValueError("a link action requires 'page'")
        if self.kind == "mutation" and not self.operation_id:
            raise ValueError("a mutation action requires 'operationId'")
        return self


class SectionControls(Props):
    search: bool = False
    filters: list[str] = []
    sort: list[str] = []
    page_size: int | None = Field(default=None, ge=1, le=100, alias="pageSize")


class StatData(Props):
    operation_id: str = Field(alias="operationId")
    value: str = "count"


class StatItem(Props):
    label: str = Field(min_length=1, max_length=60)
    value: str | int | float = ""
    data: StatData | None = None

    @model_validator(mode="after")
    def _check_value_or_data(self):
        if (self.value is None or self.value == "") and self.data is None:
            raise ValueError("StatItem requires either 'value' or 'data'")
        return self


class GalleryItem(Props):
    image: str = Field(pattern=IMAGE)
    title: str | None = Field(default=None, max_length=120)
    caption: str | None = Field(default=None, max_length=300)


# -- sections ----------------------------------------------------------------------------------------------------------


class HeroProps(Surface):
    # split: text beside the image; centered: one sentence in wide space; banner: full width, image behind; stage:
    # the image is the first screen, the text on its lower edge; type: an oversized headline, no image; stacked: a
    # full-width headline over a wide image; collage: headline and 3-4 images in a grid; vertical: a rotated label.
    variant: HeroVariant = "split"
    heading: str = Field(min_length=1, max_length=160)
    eyebrow: str | None = Field(default=None, max_length=60)
    body: str | None = Field(default=None, max_length=600)
    image: str | None = Field(default=None, pattern=IMAGE)
    images: list[Image] | None = Field(default=None, max_length=4)  # the `collage` layout (with `image` first)
    cta: Cta | None = None
    secondary_cta: Cta | None = None


class FeaturesProps(Surface):
    title: str | None = None
    description: str | None = None
    items: list[FeatureItem] | None = Field(default=None, max_length=24)
    columns: Columns | None = None
    card_style: CardStyle = "outline"
    # cards: a grid of cards; list: numbered rows; ledger: hairline rows, title left, text right; alternating: rows of
    # image and text on alternating sides (items need `image`, otherwise `list`).
    form: FeaturesForm = "cards"


class CallToActionProps(Surface):
    background: Background = "primary"  # the panel's colour
    heading: str = Field(min_length=1, max_length=160)
    body: str | None = Field(default=None, max_length=600)
    cta: Cta


class TestimonialsProps(Surface):
    title: str | None = None
    items: list[TestimonialItem] | None = Field(default=None, max_length=24)
    card_style: CardStyle = "outline"
    form: TestimonialsForm = "cards"  # cards; quote: the first as one large quote, the rest below; strip: one row


class FaqProps(Surface):
    title: str | None = None
    items: list[FaqItem] | None = Field(default=None, max_length=50)


class PricingProps(Surface):
    title: str | None = None
    description: str | None = None
    items: list[PlanItem] | None = Field(default=None, max_length=6)
    card_style: CardStyle = "outline"


class StatsProps(Surface):
    title: str | None = None
    items: list[StatItem] | None = Field(default=None, max_length=12)
    card_style: CardStyle = "outline"
    form: StatsForm = "cards"  # cards; figures: large numbers without boxes; inline: one line with dividers


class GalleryProps(Surface):
    title: str | None = None
    items: list[GalleryItem] | None = Field(default=None, max_length=48)
    columns: Columns | None = None


class RichTextProps(Surface):
    heading: str | None = Field(default=None, max_length=160)
    body: str = Field(min_length=1, max_length=20000)  # paragraphs separated by a blank line


class ContactInfoProps(Surface):
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


# -- content sections of Story 20.8: what businesses really have (steps, history, people, prices, a place) ----------


class StepItem(Props):
    title: str = Field(min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=600)


class StepsProps(Surface):
    """How booking, ordering or a service works, step by step."""

    title: str | None = None
    description: str | None = None
    items: list[StepItem] | None = Field(default=None, max_length=8)
    form: Literal["numbered", "horizontal", "connected"] = "numbered"


class TimelineItem(Props):
    date: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=600)
    image: str | None = Field(default=None, pattern=IMAGE)


class TimelineProps(Surface):
    """A story over time: history, milestones, an event programme."""

    title: str | None = None
    description: str | None = None
    items: list[TimelineItem] | None = Field(default=None, max_length=24)
    form: Literal["vertical", "alternating"] = "vertical"


class TeamMember(Props):
    name: str = Field(min_length=1, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=400)
    image: str | None = Field(default=None, pattern=IMAGE)


class TeamProps(Surface):
    """The people of a studio, clinic, firm or school."""

    title: str | None = None
    description: str | None = None
    items: list[TeamMember] | None = Field(default=None, max_length=24)
    form: Literal["grid", "list", "portraits"] = "grid"


class PriceItem(Props):
    name: str = Field(min_length=1, max_length=120)
    price: str | int | float | None = None
    description: str | None = Field(default=None, max_length=300)
    tags: list[str] = Field(default=[], max_length=4)


class PriceGroup(Props):
    title: str | None = Field(default=None, max_length=120)
    items: list[PriceItem] = Field(min_length=1, max_length=40)


class PriceListProps(Surface):
    """A menu or a price list, in groups (breads, pastries; cuts, colour)."""

    title: str | None = None
    description: str | None = None
    groups: list[PriceGroup] = Field(min_length=1, max_length=12)
    form: Literal["menu", "columns", "cards"] = "menu"


class OpeningHours(Props):
    days: str = Field(min_length=1, max_length=40)  # "Mon–Fri", "Sat, Sun", "Daily"
    opens: str | None = Field(default=None, max_length=20)
    closes: str | None = Field(default=None, max_length=20)
    note: str | None = Field(default=None, max_length=60)  # "closed", "by appointment"


class LocationProps(Surface):
    """Where to find a place and when it is open; a link to a map, never an embedded one."""

    title: str | None = None
    address: str = Field(min_length=1, max_length=300)
    hours: list[OpeningHours] = Field(default=[], max_length=10)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    map_link: str | None = Field(default=None, pattern=r"^https://")
    image: str | None = Field(default=None, pattern=IMAGE)
    form: Literal["split", "card", "band"] = "split"


class ComparisonRow(Props):
    label: str = Field(min_length=1, max_length=120)
    values: list[str | bool] = Field(min_length=2, max_length=4)


class ComparisonProps(Surface):
    """Options side by side: plans, packages, before and after."""

    title: str | None = None
    description: str | None = None
    columns: list[str] = Field(min_length=2, max_length=4)
    rows: list[ComparisonRow] = Field(min_length=1, max_length=30)
    form: Literal["table", "cards"] = "table"

    @model_validator(mode="after")
    def _one_value_per_column(self):
        for index, row in enumerate(self.rows):
            if len(row.values) != len(self.columns):
                raise ValueError(
                    f"row {index} ('{row.label}') has {len(row.values)} values for {len(self.columns)} columns"
                )
        return self


class StatementProps(Surface):
    """What the business stands for, or one real quote, set large."""

    text: str = Field(min_length=1, max_length=280)
    attribution: str | None = Field(default=None, max_length=120)
    image: str | None = Field(default=None, pattern=IMAGE)
    form: Literal["large", "quote", "band"] = "large"


class DataSectionProps(Props):
    """CardGrid, DataTable, DetailView, List: the records come from `data`; content only titles the section."""

    title: str | None = None
    description: str | None = None
    actions: list[SectionAction] = []
    controls: SectionControls | None = None


class CardGridProps(DataSectionProps):
    card_style: CardStyle = "outline"
    featured: bool = False  # the first record spans two columns


class ActionBarProps(Props):
    title: str | None = None
    description: str | None = None
    actions: list[SectionAction] = []


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
    "ActionBar": ActionBarProps,
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
    "Steps": StepsProps,
    "Timeline": TimelineProps,
    "Team": TeamProps,
    "PriceList": PriceListProps,
    "Location": LocationProps,
    "Comparison": ComparisonProps,
    "Statement": StatementProps,
    "Form": FormProps,
    "CardGrid": CardGridProps,
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
    "Steps": StepItem,
    "Timeline": TimelineItem,
    "Team": TeamMember,
}
LAYOUT_SECTIONS = frozenset({"Columns", "Stack", "Grid", "Tabs"})
