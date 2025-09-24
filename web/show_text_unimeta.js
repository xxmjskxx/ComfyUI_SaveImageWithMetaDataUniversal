// Frontend extension for ShowText|unimeta (local variant)
// Attribution: derived from pythongosssss ShowText (MIT). Key change: different node key
// to avoid collisions with other custom packs.

// Use absolute paths to avoid incorrect relative resolution when ComfyUI serves
// extension JS from a flattened URL (prevents 404 on widgets.js/app.js).
import { app } from "/scripts/app.js";
import { ComfyWidgets } from "/scripts/widgets.js";

app.registerExtension({
    name: "SaveImageWithMetaDataUniversal.ShowTextUniMeta",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "ShowText|unimeta" && nodeData.name !== "ShowAny|unimeta") return;

        function populate(text) {
            if (this.widgets) {
                const isConvertedWidget = +!!this.inputs?.[0]?.widget;
                for (let i = isConvertedWidget; i < this.widgets.length; i++) {
                    this.widgets[i].onRemove?.();
                }
                this.widgets.length = isConvertedWidget;
            }
            const v = [...text];
            if (!v[0]) v.shift();
            for (let list of v) {
                if (!(list instanceof Array)) list = [list];
                for (const l of list) {
                    const w = ComfyWidgets.STRING(this, "text_" + (this.widgets?.length ?? 0), ["STRING", { multiline: true }], app).widget;
                    w.inputEl.readOnly = true;
                    w.inputEl.style.opacity = 0.65;
                    w.value = l;
                }
            }
            requestAnimationFrame(() => {
                const sz = this.computeSize();
                if (sz[0] < this.size[0]) sz[0] = this.size[0];
                if (sz[1] < this.size[1]) sz[1] = this.size[1];
                this.onResize?.(sz);
                app.graph.setDirtyCanvas(true, false);
            });
        }

        const origExec = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(message) {
            origExec?.apply(this, arguments);
            let payload = message?.text;
            if (!payload && message?.ui?.text) payload = message.ui.text;
            populate.call(this, payload);
        };

        const VALUES = Symbol("values");
        const configure = nodeType.prototype.configure;
        nodeType.prototype.configure = function() {
            this[VALUES] = arguments[0]?.widgets_values;
            return configure?.apply(this, arguments);
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function() {
            onConfigure?.apply(this, arguments);
            const widgets_values = this[VALUES];
            if (widgets_values?.length) {
                requestAnimationFrame(() => {
                    populate.call(this, widgets_values.slice(+(widgets_values.length > 1 && this.inputs?.[0]?.widget)));
                });
            }
        };
    }
});