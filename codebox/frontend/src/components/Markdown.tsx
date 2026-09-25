import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders Markdown safely (react-markdown never injects raw HTML). GFM adds tables,
 *  strikethrough and task lists, which AI answers use often. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-cb">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
