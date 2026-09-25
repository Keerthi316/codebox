/** Pages it is safe to return to after signing in. Anything else (old links such
 *  as /verify-email, typos, other sites) falls back to the problem list. */
const RETURNABLE = [/^\/problems(\/[\w-]+)?$/, /^\/playground$/, /^\/submissions(\/\d+)?$/];

export const DEFAULT_PAGE = "/problems";

export function safeRedirect(from: unknown): string {
  if (typeof from !== "string") return DEFAULT_PAGE;
  const [path, query = ""] = from.split("?", 2);
  if (!RETURNABLE.some((pattern) => pattern.test(path))) return DEFAULT_PAGE;
  return query ? `${path}?${query}` : path;
}
