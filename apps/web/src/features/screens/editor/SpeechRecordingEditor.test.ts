import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, expect, test, vi } from "vitest";
import SpeechRecordingEditor from "./SpeechRecordingEditor.vue";
import AssetLibraryDialog from "../assets/AssetLibraryDialog.vue";
import type { ScreenAsset } from "../assets/api";

const media: ScreenAsset = {
  id: "voice", name: "Recording", original_name: "voice.wav", asset_type: "audio", mime_type: "audio/wav",
  sha256: "a".repeat(64), size_bytes: 100, family_id: "voice", version: 1, created_at: "2026-09-09T00:00:00Z",
  media: { validated: true, duration_seconds: 4, audio_codec: "pcm_s16le" },
};
afterEach(() => vi.restoreAllMocks());

test("confirmation is explicit and includes immutable media identity", async () => {
  const pause = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  const load = vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  const wrapper = mount(SpeechRecordingEditor, { props: { media, recording: null, inUseIds: [] } });
  const button = wrapper.findAll("button").find((item) => item.text().includes("确认录制内容"))!;
  await wrapper.get("textarea").setValue("Hello");
  expect(button.attributes("disabled")).toBeDefined();
  await wrapper.get('input[type="checkbox"]').setValue(true);
  await button.trigger("click");
  expect(wrapper.emitted("confirm")![0]![0]).toMatchObject({ asset_id: "voice", sha256: media.sha256, duration_seconds: 4, transcript: "Hello", cues: [] });
  const audio = wrapper.get("audio").element;
  wrapper.unmount();
  expect(pause).toHaveBeenCalled();
  expect(load).toHaveBeenCalled();
  expect(audio.getAttribute("src")).toBeNull();
});

test("import uses validated subtitle cues; manual edits detach the asset snapshot and require renewed review", async () => {
  vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => {});
  vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => {});
  const wrapper = mount(SpeechRecordingEditor, {
    props: { media, recording: null, inUseIds: [] }, global: { stubs: { AssetLibraryDialog: true } },
  });
  try {
    await wrapper.findAll("button").find((item) => item.text().includes("导入字幕"))!.trigger("click");
    wrapper.findComponent(AssetLibraryDialog).vm.$emit("select", {
      ...media, id: "subtitle", asset_type: "subtitle", sha256: "b".repeat(64),
      media: { validated: true, cues: [{ start: 0.1, end: 2, text: "Hello" }] },
    });
    await flushPromises();
    expect(wrapper.get("textarea").element.value).toBe("Hello");
    const button = wrapper.findAll("button").find((item) => item.text().includes("确认录制内容"))!;
    await wrapper.get('input[type="checkbox"]').setValue(true);
    await button.trigger("click");
    expect(wrapper.emitted("confirm")![0]![0]).toMatchObject({ subtitle_asset_id: "subtitle", subtitle_sha256: "b".repeat(64) });
    await wrapper.get('[aria-label="字幕 1 结束秒数"]').setValue(5);
    expect(wrapper.text()).toContain("字幕时间必须递增");
    expect(button.attributes("disabled")).toBeDefined();
    await wrapper.get('[aria-label="字幕 1 结束秒数"]').setValue(3);
    await wrapper.get('input[type="checkbox"]').setValue(true);
    await button.trigger("click");
    expect(wrapper.emitted("confirm")![1]![0]).toMatchObject({ subtitle_asset_id: "", subtitle_sha256: "", cues: [{ start: 0.1, end: 3, text: "Hello" }] });
    await wrapper.get("textarea").setValue("Different");
    expect(wrapper.text()).toContain("字幕文字与录制文案不一致");
  } finally { wrapper.unmount(); }
});
