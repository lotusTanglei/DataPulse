import { describe, expect, it } from "vitest";
import { applyCommand } from "../screens/editor/commands";
import { EditorHistory } from "../screens/editor/history";
import type { DashboardDocument } from "../../contracts";

const document: DashboardDocument = {
  canvas: { width: 1000, height: 800 },
  components: [],
};
const component = {
  id: "plugin-one",
  type: "org.example.metric",
  frame: { x: 0, y: 0, width: 320, height: 180 },
  props: { label: "Total" },
};
describe("plugin editor dependencies", () => {
  it("adds the component and exact dependency in one undoable command", () => {
    const history = new EditorHistory(document);
    const added = history.execute({
      type: "add_plugin_component",
      component,
      dependency: { id: "org.example.metrics", version: "1.0.0" },
    });
    expect(added.plugin_dependencies).toEqual([
      { id: "org.example.metrics", version: "1.0.0" },
    ]);
    expect(added.components).toEqual([component]);
    expect(history.undo()).toEqual(document);
    expect(history.redo()).toEqual(added);
  });
  it("refuses to silently replace a pinned version", () => {
    const pinned = {
      ...document,
      plugin_dependencies: [{ id: "org.example.metrics", version: "1.0.0" }],
    };
    expect(() =>
      applyCommand(pinned, {
        type: "add_plugin_component",
        component,
        dependency: { id: "org.example.metrics", version: "2.0.0" },
      }),
    ).toThrow(/version/i);
    expect(pinned.plugin_dependencies[0]?.version).toBe("1.0.0");
  });
});
