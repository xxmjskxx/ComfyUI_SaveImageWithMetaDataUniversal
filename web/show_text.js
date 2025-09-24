// Local Show Text node frontend extension.
// Attribution: Based on the original Show Text implementation from
// pythongosssss / ComfyUI-Custom-Scripts (MIT License). Reimplemented here
// to avoid requiring users to install another custom pack just to view
// arbitrary text outputs in workflows.

import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "SaveImageWithMetaDataUniversal.ShowText",
    async beforeRegisterNodeDef(nodeType, nodeData) {
    // Only handle the base ShowText node here; UniMeta variants are handled in show_text_unimeta.js
    const supported = new Set(["ShowText"]);
        if (!supported.has(nodeData.name)) return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const r = origOnNodeCreated?.apply(this, arguments);
            // Helper to resize the textarea and recompute node size
            this._resizeShowText = () => {
                const el = this._showTextDisplay;
                if (!el) return;
                // Auto-size the textarea height to content, with a sane cap
                el.style.height = "auto";
                const maxPx = 600; // cap to reduce oversized nodes
                const next = Math.min(maxPx, Math.max(80, el.scrollHeight));
                el.style.height = `${next}px`;
                // Recompute node size so widgets don't overflow the node
                if (typeof this.computeSize === "function") {
                    this.size = this.computeSize();
                }
                this.setDirtyCanvas?.(true, true);
            };
            // Style the source text widget if present (ShowText variants)
            const textWidget = this.widgets?.find(w => w.name === "text");
            if (textWidget?.inputEl) {
                Object.assign(textWidget.inputEl.style, {
                    fontFamily: "monospace",
                    whiteSpace: "pre-wrap",
                    overflowWrap: "anywhere",
                    resize: "vertical",
                });
                // Prefer rows over fixed min-height so ComfyWidgets can compute layout
                if (textWidget.inputEl.tagName === "TEXTAREA") {
                    textWidget.inputEl.rows = Math.max(3, textWidget.inputEl.rows || 6);
                }
            }

            // Ensure a passive read-only mirror widget named "display" exists and is styled.
            let displayWidget = this.widgets?.find(w => w.name === "display");
            if (!displayWidget) {
                const wDef = ComfyWidgets.STRING(this, "display", ["STRING", { multiline: true }], app);
                displayWidget = wDef.widget;
            } else {
                // If created server-side, ensure we have a reference to the widget object
                displayWidget = displayWidget;
            }
            if (displayWidget?.inputEl) {
                displayWidget.inputEl.readOnly = true;
                displayWidget.inputEl.placeholder = "(Displayed text will appear here after execution)";
                Object.assign(displayWidget.inputEl.style, {
                    fontFamily: "monospace",
                    background: "#202020",
                    color: "#ddd",
                    whiteSpace: "pre-wrap",
                    overflowWrap: "anywhere",
                    resize: "vertical",
                });
                // Prefer rows over fixed min-height so ComfyWidgets can compute layout
                if (displayWidget.inputEl.tagName === "TEXTAREA") {
                    displayWidget.inputEl.rows = Math.max(4, displayWidget.inputEl.rows || 8);
                }
                this._showTextDisplay = displayWidget.inputEl;
                // Initial resize pass
                this._resizeShowText();
            }
            return r;
        };

        const origExec = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(message) {
            const r = origExec?.apply(this, arguments);
            const display = this._showTextDisplay;
            if (!display) return r;
            // Attempt common payload shapes and join arrays into a single block
            let val = null;
            if (typeof message?.text === "string") val = message.text;
            else if (Array.isArray(message?.text) && message.text.length) val = message.text;
            else if (message?.ui?.text && Array.isArray(message.ui.text) && message.ui.text.length) val = message.ui.text;
            else if (Array.isArray(message?.output) && message.output.length) val = message.output;

            if (val != null) {
                const text = Array.isArray(val) ? val.map(v => (v == null ? "" : String(v))).join("\n") : String(val);
                display.value = text;
                // Resize after content update
                this._resizeShowText?.();
            }
            return r;
        };
    }
});
