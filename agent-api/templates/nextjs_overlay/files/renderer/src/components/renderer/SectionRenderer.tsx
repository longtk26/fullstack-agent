import { site, type TSiteSection } from "./site";
import { sections } from "./registry";

type SectionRendererProps = {
  pageId: string;
  section: TSiteSection;
};

function childTitle(section: TSiteSection): string {
  const content = section.content ?? {};
  const title = content.title ?? content.heading;
  return typeof title === "string" ? title : section.id;
}

/**
 * One FrontendSpec section: the registered component with the section's content, the records of its content
 * collection as `items`, and — for layout nodes — its children rendered by this same component. The markers
 * name the section for inspect mode (16.4).
 */
export function SectionRenderer({ pageId, section }: SectionRendererProps) {
  const Component = sections[section.component];
  if (!Component) return null;
  const props: Record<string, unknown> = { ...section.content };
  if (section.data?.collection) props.items = site.collections[section.data.collection] ?? [];
  if (section.data?.fields?.length) props.fields = section.data.fields;
  const children = section.children?.map((child) => (
    <SectionRenderer key={child.id} pageId={pageId} section={child} />
  ));
  if (section.children) props.childTitles = section.children.map(childTitle);
  return (
    <div data-bga-section={`${pageId}/${section.id}`} data-bga-component={section.component}>
      <Component {...props}>{children}</Component>
    </div>
  );
}
