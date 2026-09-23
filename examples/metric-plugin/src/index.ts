import {
  definePlugin,
  type PluginContext,
  type JsonValue,
} from "../../../packages/plugin-sdk/src/index";

export default definePlugin({
  apiVersion: 1,
  components: {
    "org.datapulse.example.metric": {
      mount(element: HTMLElement, initial: PluginContext) {
        const label = document.createElement("div"),
          value = document.createElement("strong"),
          note = document.createElement("small");
        element.style.cssText =
          "box-sizing:border-box;height:100%;padding:24px;display:flex;flex-direction:column;justify-content:center;gap:10px;background:#0b1b2b;border-radius:12px;color:#edf7ff;font-family:system-ui,sans-serif";
        label.style.cssText = "font-size:14px;opacity:.7";
        value.style.cssText =
          "font-size:42px;font-variant-numeric:tabular-nums";
        note.style.cssText = "opacity:.6;font-size:11px";
        element.replaceChildren(label, value, note);
        function update(context: PluginContext) {
          if (context.signal.aborted) return;
          label.textContent = String(context.props.label ?? "示例指标");
          value.style.color = String(
            context.props.color ?? context.theme.accent ?? "#26d9c1",
          );
          const precision =
            typeof context.props.precision === "number"
              ? Math.max(0, Math.min(8, context.props.precision))
              : 0;
          const field = context.props.field;
          const index =
            typeof field === "string" && field
              ? (context.result?.columns.findIndex(
                  (column) => column.name === field,
                ) ?? -1)
              : (context.result?.rows[0]?.findIndex(
                  (cell) => typeof cell === "number",
                ) ?? -1);
          const number =
            index >= 0 ? context.result?.rows[0]?.[index] : undefined;
          value.textContent = context.loading
            ? "…"
            : context.error
              ? "数据暂不可用"
              : typeof number === "number"
                ? number.toFixed(precision)
                : "—";
          note.textContent = context.result
            ? `${context.result.row_count} 行 · 受控查询结果`
            : "绑定数据后显示指标";
        }
        update(initial);
        return {
          update,
          destroy() {
            element.replaceChildren();
          },
        };
      },
      migrate(props: Record<string, JsonValue>) {
        return { ...props };
      },
    },
  },
});
