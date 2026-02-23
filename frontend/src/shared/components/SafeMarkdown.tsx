import Markdown from "react-markdown";
import type { Components, Options } from "react-markdown";

const components: Components = {
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline text-blue-link transition-colors hover:text-blue-dark rounded"
    >
      {children}
    </a>
  ),
  p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc ml-4 mb-3">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal ml-4 mb-3">{children}</ol>,
  li: ({ children }) => <li className="mb-1">{children}</li>,
};

interface Props {
  children: string;
  remarkPlugins?: Options["remarkPlugins"];
  components?: Options["components"];
}

/** Renders markdown with links forced to open in a new tab safely. */
export default function SafeMarkdown({
  children,
  remarkPlugins,
  components: componentOverrides,
}: Props) {
  return (
    <Markdown
      components={{ ...components, ...componentOverrides }}
      remarkPlugins={remarkPlugins}
    >
      {children}
    </Markdown>
  );
}
