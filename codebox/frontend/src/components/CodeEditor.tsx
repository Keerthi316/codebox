import Editor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/editor/editor.worker?worker";
import tsWorker from "monaco-editor/language/typescript/ts.worker?worker";
import { Spinner } from "./ui";

// Bundle Monaco locally instead of loading it from a CDN (works offline and under CSP).
self.MonacoEnvironment = {
  getWorker(_workerId: string, label: string) {
    return label === "typescript" || label === "javascript" ? new tsWorker() : new editorWorker();
  },
};
loader.config({ monaco });

monaco.editor.defineTheme("codebox", {
  base: "vs-dark",
  inherit: true,
  rules: [],
  colors: {
    "editor.background": "#0b0d10",
    "editor.lineHighlightBackground": "#12151a",
    "editorLineNumber.foreground": "#4b5563",
    "editorLineNumber.activeForeground": "#b4bcc8",
    "editorGutter.background": "#0b0d10",
    "editor.selectionBackground": "#10b98140",
  },
});

const MONACO_LANGUAGE: Record<string, string> = { python: "python", javascript: "javascript", java: "java", cpp: "cpp" };

export function CodeEditor({
  language,
  value,
  onChange,
  readOnly = false,
  onRun,
}: {
  language: string;
  value: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  onRun?: () => void;
}) {
  return (
    <Editor
      height="100%"
      theme="codebox"
      language={MONACO_LANGUAGE[language] ?? "plaintext"}
      value={value}
      onChange={(v) => onChange?.(v ?? "")}
      loading={<Spinner className="size-5 text-muted" />}
      onMount={(editor) => {
        if (onRun) {
          editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => onRun());
        }
      }}
      options={{
        readOnly,
        fontSize: 14,
        fontFamily: "ui-monospace, 'JetBrains Mono', 'Cascadia Code', Menlo, Consolas, monospace",
        fontLigatures: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        smoothScrolling: true,
        tabSize: 4,
        automaticLayout: true,
        padding: { top: 12, bottom: 12 },
        renderLineHighlight: readOnly ? "none" : "all",
        bracketPairColorization: { enabled: true },
        stickyScroll: { enabled: false },
      }}
    />
  );
}
