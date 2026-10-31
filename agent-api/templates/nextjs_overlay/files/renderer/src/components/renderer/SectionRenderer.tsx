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
 * One FrontendSpec section: the registered component with the section's content; data sections get their content
 * collection (`items`) or their operation binding, columns and states; forms their definition; layout nodes their
 * children, rendered by this same component. The markers name the section for inspect mode (16.4).
 */
export function SectionRenderer({ pageId, section }: SectionRendererProps) {
  const Component = sections[section.component];
  if (!Component) return null;
  const props: Record<string, unknown> = { ...section.content };
  const data = section.data;
  if (data?.collection) props.items = site.collections[data.collection] ?? [];
  if (data?.columns) props.columns = data.columns;
  if (data?.operationId) props.binding = data;
  if (section.states) props.states = section.states;
  if (section.form) {
    props.formId = section.form;
    props.form = site.forms[section.form];
  }
  const children = section.children?.map((child) => (
    <SectionRenderer key={child.id} pageId={pageId} section={child} />
  ));
  if (section.children) props.childTitles = section.children.map(childTitle);
  return (
    <div data-bga-section={`${pageId}/${section.id}`} data-bga-section-id={section.id} data-bga-component={section.component}>
      <Component {...props}>{children}</Component>
    </div>
  );
}
