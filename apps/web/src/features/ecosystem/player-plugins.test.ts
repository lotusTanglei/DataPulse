import { afterEach, expect, it, vi } from "vitest";
import { fetchPlayerPluginModule } from "../player/api";
vi.mock("./plugins", () => ({
  importPluginResponse: async (response: Response) => response.text(),
}));
afterEach(() => vi.unstubAllGlobals());
it("fetches embed modules using bearer auth without cookies or ticket URLs", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response("export default {}"));
  vi.stubGlobal("fetch", fetcher);
  expect(
    await fetchPlayerPluginModule(
      "embed",
      "screen-1",
      "org.example.plugin",
      "1.0.0",
      "index.mjs",
      "ticket-1",
    ),
  ).toContain("export default");
  expect(fetcher).toHaveBeenCalledWith(
    "/api/embed/screens/screen-1/plugins/org.example.plugin/1.0.0/files/index.mjs",
    expect.objectContaining({
      credentials: "omit",
      headers: { Authorization: "Bearer ticket-1" },
    }),
  );
});
it("fetches standalone modules with its existing display cookie", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response("export default {}"));
  vi.stubGlobal("fetch", fetcher);
  await fetchPlayerPluginModule(
    "standalone",
    "screen-1",
    "org.example.plugin",
    "1.0.0",
    "index.mjs",
    "",
  );
  expect(fetcher).toHaveBeenCalledWith(
    "/api/player/screens/screen-1/plugins/org.example.plugin/1.0.0/files/index.mjs",
    expect.objectContaining({ credentials: "same-origin" }),
  );
});
