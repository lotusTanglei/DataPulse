import { DataPulseEmbed } from "../../../packages/embed-sdk/src/index";

const query = new URLSearchParams(window.location.search);
const screenId = query.get("screen");
const ticket = query.get("ticket");
const status = document.querySelector<HTMLElement>("#host-status");
const mountPoint = document.querySelector<HTMLElement>("#embed-root");

if (!screenId || !ticket || !status || !mountPoint) {
  throw new Error("Embed host bootstrap parameters are missing.");
}

const embedded = DataPulseEmbed.mount(mountPoint, {
  url: `${window.location.origin}/embed/${encodeURIComponent(screenId)}`,
  ticket,
  className: "embedded-screen",
});

embedded.onError((error) => {
  status.textContent = `error:${error.code}`;
});

const readyTimer = window.setInterval(() => {
  if (embedded.ready) {
    window.clearInterval(readyTimer);
    status.textContent = "ready";
  }
}, 20);

document
  .querySelector<HTMLButtonElement>("#set-region")
  ?.addEventListener("click", async () => {
    await embedded.setParameters({ region: "华南" });
    const parameters = await embedded.getParameters();
    status.textContent = `region:${String(parameters.region)}`;
  });

document
  .querySelector<HTMLButtonElement>("#refresh")
  ?.addEventListener("click", () => {
    embedded.refresh();
    status.textContent = "refreshed";
  });

document
  .querySelector<HTMLButtonElement>("#fullscreen")
  ?.addEventListener("click", async () => {
    await embedded.fullscreen(false);
    status.textContent = "fullscreen-requested";
  });

document
  .querySelector<HTMLButtonElement>("#forbidden")
  ?.addEventListener("click", async () => {
    try {
      await embedded.setParameters({ year: 2027 });
    } catch (error) {
      status.textContent =
        error instanceof Error && "code" in error
          ? `error:${String(error.code)}`
          : "error:UNKNOWN";
    }
  });

window.addEventListener("beforeunload", () => embedded.destroy());
