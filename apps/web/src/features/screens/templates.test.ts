import { expect, test } from "vitest";

import { createTemplateDocument, screenTemplates } from "./templates";

test("provides five independent dashboard templates", () => {
  expect(screenTemplates).toHaveLength(5);
  expect(new Set(screenTemplates.map((template) => template.id)).size).toBe(5);

  for (const template of screenTemplates) {
    const document = createTemplateDocument(template.id);
    expect(document.canvas).toEqual({
      width: 1920,
      height: 1080,
      background: { color: "#08111f" },
    });
    const components = document.components ?? [];
    expect(components.length).toBeGreaterThanOrEqual(7);
    expect(new Set(components.map((component) => component.id)).size).toBe(
      components.length,
    );
    for (const component of components) {
      expect(component.frame.x).toBeGreaterThanOrEqual(0);
      expect(component.frame.y).toBeGreaterThanOrEqual(0);
      expect(component.frame.x + component.frame.width).toBeLessThanOrEqual(1920);
      expect(component.frame.y + component.frame.height).toBeLessThanOrEqual(1080);
    }
  }
});

test("returns a fresh document for each template creation", () => {
  const first = createTemplateDocument(screenTemplates[0].id);
  const second = createTemplateDocument(screenTemplates[0].id);
  const firstComponent = first.components?.[0];
  const secondComponent = second.components?.[0];
  if (!firstComponent || !secondComponent) {
    throw new Error("Template must contain components");
  }
  firstComponent.props = { ...(firstComponent.props ?? {}), text: "changed" };

  expect(secondComponent.props?.text).not.toBe("changed");
});
