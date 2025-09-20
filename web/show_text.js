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
        if (nodeData.name !== "ShowText") return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            const r = origOnNodeCreated?.apply(this, arguments);
            // Ensure we have a multiline widget for the input text (first required input)
            // Comfy will already create one because we declared multiline in Python, but
            // we enforce styling & add a label widget if provided.
            const textWidget = this.widgets?.find(w => w.name === "text");
            if (textWidget && textWidget.inputEl) {
                Object.assign(textWidget.inputEl.style, {
                    fontFamily: "monospace",
                    whiteSpace: "pre-wrap",
                    overflowWrap: "anywhere",
                    resize: "vertical",
                    minHeight: "120px",
                });
            }
            // Add a passive read-only mirror widget (optional) for clarity — many ShowText
            // variants present a separate display area. We'll skip if already present.
            if (!this.widgets?.some(w => w.name === "display")) {
                const wDef = ComfyWidgets.STRING(this, "display", ["STRING", { multiline: true }], app);
                const w = wDef.widget;
                w.inputEl.readOnly = true;
                w.inputEl.placeholder = "(Displayed text will appear here after execution)";
                Object.assign(w.inputEl.style, {
                    fontFamily: "monospace",
                    background: "#202020",
                    color: "#ddd",
                    whiteSpace: "pre-wrap",
                    overflowWrap: "anywhere",
                    resize: "vertical",
                    minHeight: "140px",
                });
                this._showTextDisplay = w.inputEl;
            }
            return r;
        };

        const origExec = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(message) {
            const r = origExec?.apply(this, arguments);
            const display = this._showTextDisplay;
            if (!display) return r;
            // Attempt common payload shapes (string directly, array, ui wrapper, output tuple)
            let payload = null;
            if (typeof message?.text === "string") payload = message.text;
            else if (Array.isArray(message?.text) && message.text.length) payload = message.text[0];
            else if (message?.ui?.text && Array.isArray(message.ui.text) && message.ui.text.length) payload = message.ui.text[0];
            else if (Array.isArray(message?.output) && message.output.length) payload = message.output[0];
            if (payload != null) {
                display.value = String(payload);
            }
            return r;
        };
    }
});
