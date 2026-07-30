import { sql, MySQL, PostgreSQL, SQLite } from "@codemirror/lang-sql";
import { Compartment, EditorState, Prec } from "@codemirror/state";
import { EditorView, keymap, type KeyBinding } from "@codemirror/view";
import { basicSetup } from "codemirror";

import type { SqlDialect } from "./types";

export interface SqlEditorOptions {
  parent: HTMLElement;
  initialValue: string;
  dialect: SqlDialect;
  onChange: (value: string) => void;
  onRun: () => void;
}

export interface SqlEditorAdapter {
  setValue(value: string): void;
  setDialect(dialect: SqlDialect): void;
  focus(): void;
  destroy(): void;
}

function dialectExtension(dialect: SqlDialect) {
  if (dialect === "postgresql") {
    return sql({ dialect: PostgreSQL });
  }
  if (dialect === "mysql") {
    return sql({ dialect: MySQL });
  }
  return sql({ dialect: SQLite });
}

export function createSqlEditor(options: SqlEditorOptions): SqlEditorAdapter {
  const language = new Compartment();
  const runBinding: KeyBinding = {
    key: "Mod-Enter",
    run: () => {
      options.onRun();
      return true;
    },
  };
  const state = EditorState.create({
    doc: options.initialValue,
    extensions: [
      basicSetup,
      language.of(dialectExtension(options.dialect)),
      Prec.high(keymap.of([runBinding])),
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          options.onChange(update.state.doc.toString());
        }
      }),
      EditorView.theme({
        "&": {
          height: "100%",
          backgroundColor: "#fff",
          color: "#37352f",
          fontSize: "13px",
        },
        ".cm-content": {
          padding: "14px 0",
          fontFamily:
            '"SFMono-Regular", Consolas, "Liberation Mono", monospace',
        },
        ".cm-gutters": {
          backgroundColor: "#fbfbfa",
          borderRight: "1px solid #e9e9e7",
          color: "#aaa9a6",
        },
        ".cm-activeLine, .cm-activeLineGutter": {
          backgroundColor: "rgba(55, 53, 47, 0.035)",
        },
        "&.cm-focused": { outline: "none" },
      }),
    ],
  });
  const view = new EditorView({ state, parent: options.parent });

  return {
    setValue(value) {
      const current = view.state.doc.toString();
      if (current !== value) {
        view.dispatch({
          changes: { from: 0, to: current.length, insert: value },
        });
      }
    },
    setDialect(dialect) {
      view.dispatch({
        effects: language.reconfigure(dialectExtension(dialect)),
      });
    },
    focus() {
      view.focus();
    },
    destroy() {
      view.destroy();
    },
  };
}
