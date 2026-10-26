import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

type MarkdownReportProps = {
  markdown: string;
};

/** The generated report.md; elements are styled here because the app has no typography plugin. */
export function MarkdownReport({ markdown }: MarkdownReportProps) {
  return (
    <div className="flex flex-col gap-3 text-sm">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h3 className="text-base font-semibold">{children}</h3>,
          h2: ({ children }) => <h4 className="pt-2 text-sm font-semibold">{children}</h4>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-5">{children}</ul>,
          code: ({ children }) => <code className="rounded bg-muted px-1 font-mono text-xs">{children}</code>,
          table: ({ children }) => (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-xs">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border-b bg-muted/50 px-2 py-1.5 text-left font-medium">{children}</th>,
          td: ({ children }) => <td className="border-b px-2 py-1.5 align-top">{children}</td>,
        }}
      >
        {markdown}
      </Markdown>
    </div>
  );
}
