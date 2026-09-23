import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ApiError } from "../../../lib/api";
import AssetLibraryDialog from "./AssetLibraryDialog.vue";
import * as api from "./api";

vi.mock("./api", async (original) => ({
  ...await original<typeof import("./api")>(),
  listAssets: vi.fn(), getAsset: vi.fn(), getAssetUsage: vi.fn(),
  listExpiringAssets: vi.fn(),
  getAssetReferences: vi.fn(), patchAsset: vi.fn(), uploadAsset: vi.fn(), deleteAsset: vi.fn(),
}));

const first: api.ScreenAsset = {
  id: "avatar", name: "Avatar", original_name: "avatar.png", family_id: "avatar", version: 1,
  asset_type: "image", mime_type: "image/png", size_bytes: 120, sha256: "a".repeat(64),
  created_at: "2026-09-09T00:00:00Z", has_thumbnail: true, media: { width: 32, height: 24 },
};
const second: api.ScreenAsset = { ...first, id: "avatar-v2", version: 2 };
let wrapper: VueWrapper | undefined;
beforeEach(() => {
  vi.mocked(api.listAssets).mockResolvedValue([first, second]);
  vi.mocked(api.getAsset).mockResolvedValue(first);
  vi.mocked(api.listExpiringAssets).mockResolvedValue([]);
  vi.mocked(api.getAssetReferences).mockResolvedValue([]);
  vi.mocked(api.getAssetUsage).mockResolvedValue({ asset_count: 2, size_bytes: 240, duration_seconds: 0, max_total_bytes: 1000, max_total_duration_seconds: 3600, max_image_bytes: 1000, max_media_bytes: 1000, max_duration_seconds: 300 });
  vi.mocked(api.uploadAsset).mockResolvedValue(second);
  vi.mocked(api.patchAsset).mockImplementation(async (id, patch) => ({ ...first, id, ...patch, name: patch.name ?? first.name, license_note: patch.license_note ?? first.license_note }));
  vi.mocked(api.deleteAsset).mockResolvedValue(undefined);
});
afterEach(() => {
  wrapper?.unmount(); wrapper = undefined;
  document.body.innerHTML = "";
  vi.resetAllMocks(); vi.restoreAllMocks();
});

async function open(props: Record<string, unknown> = {}) {
  wrapper = mount(AssetLibraryDialog, { attachTo: document.body, props, global: { stubs: { teleport: true } } });
  await flushPromises();
  return wrapper;
}

test("search, filtering and pagination are sent to the asset API", async () => {
  const view = await open();
  await view.get('[aria-label="搜索资源"]').setValue("Avatar & 100%");
  await view.get(".asset-library__toolbar").trigger("submit");
  await flushPromises();
  expect(api.listAssets).toHaveBeenLastCalledWith(expect.objectContaining({ search: "Avatar & 100%", offset: 0 }), expect.any(AbortSignal));
  await view.get('[aria-label="资源类型"]').setValue("audio");
  await flushPromises();
  expect(api.listAssets).toHaveBeenLastCalledWith(expect.objectContaining({ assetType: "audio", offset: 0 }), expect.any(AbortSignal));
  vi.mocked(api.listAssets).mockResolvedValue(Array.from({ length: 25 }, (_, i) => ({ ...first, id: String(i) })));
  await view.get(".asset-library__toolbar").trigger("submit");
  await flushPromises();
  expect(view.findAll(".asset-library__item")).toHaveLength(24);
  await view.get('[aria-label="下一页资源"]').trigger("click");
  expect(api.listAssets).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 24 }), expect.any(AbortSignal));
});

test("shows a proactive authorization expiry reminder", async () => {
  vi.mocked(api.listExpiringAssets).mockResolvedValue([{ ...first, license_expires_at: "2026-09-20T00:00:00Z" }]);
  const view = await open();
  expect(view.text()).toContain("1 个资源将在 30 天内到期");
  expect(view.get(".inline-notice .secondary-button").text()).toContain("查看资源");
});

test("replacement stays unselected until the administrator explicitly uses its new version", async () => {
  const view = await open({ selectedId: first.id, allowedTypes: ["image"] });
  const input = view.get<HTMLInputElement>('[aria-label="替换资源文件"]');
  const file = new File(["image"], "new.png", { type: "image/png" });
  Object.defineProperty(input.element, "files", { value: [file] });
  await input.trigger("change");
  await flushPromises();
  expect(api.uploadAsset).toHaveBeenCalledWith(file, first.id, expect.any(AbortSignal));
  expect(view.emitted("select")).toBeUndefined();
  expect(view.get(".asset-library__preview img").attributes("src")).toBe("/api/admin/assets/avatar-v2");
  await view.get(".asset-library__footer .primary-button").trigger("click");
  expect(view.emitted("select")).toEqual([[second]]);
});

test("published references and unsaved local references disable deletion", async () => {
  vi.mocked(api.getAssetReferences).mockResolvedValue([{ screen_id: "screen", screen_name: "Operations", in_draft: false, in_published: true }]);
  const view = await open({ selectedId: first.id });
  expect(view.get('[aria-label="删除资源版本"]').attributes()).toHaveProperty("disabled");
  expect(view.get(".asset-library__references").text()).toContain("已发布");
  vi.mocked(api.getAssetReferences).mockResolvedValue([]);
  await view.setProps({ inUseIds: [second.id] });
  await view.findAll(".asset-library__item")[1]!.trigger("click");
  await flushPromises();
  expect(view.get('[aria-label="删除资源版本"]').attributes()).toHaveProperty("disabled");
  expect(view.text()).toContain("当前编辑草稿已引用");
  expect(api.deleteAsset).not.toHaveBeenCalled();
});

test("unreferenced deletion requires a separate confirmation", async () => {
  const view = await open({ selectedId: first.id });
  await view.get('[aria-label="删除资源版本"]').trigger("click");
  expect(api.deleteAsset).not.toHaveBeenCalled();
  await view.get(".asset-library__delete .danger-button").trigger("click");
  await flushPromises();
  expect(api.deleteAsset).toHaveBeenCalledWith(first.id, expect.any(AbortSignal));
  expect(view.find(".asset-library__preview").exists()).toBe(false);
});

test("metadata editing preserves the resource ID and blocks selection until saved", async () => {
  const view = await open({ selectedId: first.id });
  await view.get('.asset-library__form input:not([type])').setValue("Renamed");
  await view.get(".asset-library__form textarea").setValue("Licensed for this project");
  expect(view.get(".asset-library__footer .primary-button").attributes()).toHaveProperty("disabled");
  await view.get(".asset-library__form").trigger("submit");
  await flushPromises();
  expect(api.patchAsset).toHaveBeenCalledWith(first.id, { name: "Renamed", license_note: "Licensed for this project", license_expires_at: null }, expect.any(AbortSignal));
  expect(view.get(".asset-library__footer .primary-button").attributes()).not.toHaveProperty("disabled");
});

test("wrong-type assets can be inspected but cannot be selected for a slot", async () => {
  const view = await open({ selectedId: first.id, allowedTypes: ["audio"] });
  expect(view.find(".asset-library__preview img").exists()).toBe(true);
  expect(view.get(".asset-library__footer .primary-button").attributes()).toHaveProperty("disabled");
});

test("failed reference checks cannot silently enable deletion or remain loading", async () => {
  vi.mocked(api.getAssetReferences).mockRejectedValue(new ApiError({ code: "ASSET_NOT_FOUND", message: "Missing", requestId: "request-ref", status: 404 }));
  const view = await open({ selectedId: first.id });
  expect(view.text()).toContain("引用检查失败");
  expect(view.text()).toContain("request-ref");
  expect(view.text()).not.toContain("正在检查引用");
  expect(view.get('[aria-label="删除资源版本"]').attributes()).toHaveProperty("disabled");
});

test("unmount aborts in-flight loads and restores the invoking control's focus", async () => {
  const opener = document.createElement("button"); document.body.append(opener); opener.focus();
  const signals: AbortSignal[] = [];
  vi.mocked(api.listAssets).mockImplementation((_options, signal) => { signals.push(signal!); return new Promise(() => {}); });
  vi.mocked(api.getAssetReferences).mockImplementation((_id, signal) => { signals.push(signal!); return new Promise(() => {}); });
  const view = await open({ selectedId: first.id });
  view.unmount(); wrapper = undefined;
  expect(signals).toHaveLength(2);
  expect(signals.every((signal) => signal.aborted)).toBe(true);
  expect(document.activeElement).toBe(opener);
});

test("switching resources stops and unloads the previous audio preview", async () => {
  const audio: api.ScreenAsset = { ...first, asset_type: "audio", mime_type: "audio/wav", id: "audio" };
  vi.mocked(api.getAsset).mockResolvedValue(audio);
  const view = await open({ selectedId: audio.id });
  const media = view.get<HTMLAudioElement>("audio").element;
  const pause = vi.spyOn(media, "pause");
  const reload = vi.spyOn(media, "load");
  await view.findAll(".asset-library__item")[0]!.trigger("click");
  expect(pause).toHaveBeenCalledOnce();
  expect(reload).toHaveBeenCalledOnce();
  expect(media.hasAttribute("src")).toBe(false);
});

test("audio previews expose transient loudness and silence processing options", async () => {
  const audio: api.ScreenAsset = { ...first, asset_type: "audio", mime_type: "audio/wav", id: "audio" };
  vi.mocked(api.getAsset).mockResolvedValue(audio);
  const view = await open({ selectedId: audio.id });
  expect(view.get("audio").attributes("src")).toBe("/api/admin/assets/audio/preview");
  const options = view.findAll<HTMLInputElement>(".asset-library__preview-options input");
  await options[0]!.setValue(true);
  await options[1]!.setValue(true);
  await flushPromises();
  expect(view.get("audio").attributes("src")).toBe(
    "/api/admin/assets/audio/preview?normalize_loudness=true&trim_silence=true",
  );
});
