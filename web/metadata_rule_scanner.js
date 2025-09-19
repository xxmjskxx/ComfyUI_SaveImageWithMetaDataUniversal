import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Add a custom widget to MetadataRuleScanner for displaying results
app.registerExtension({
    name: "SaveImageWithMetaDataUniversal.MetadataRuleScanner",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Debug logging
        console.log("SaveImageWithMetaDataUniversal: Checking node:", nodeData.name, "Display name:", nodeData.display_name);
        
        // Match by either class name or display name
        if (nodeData.name === "MetadataRuleScanner" || 
            nodeData.display_name === "Metadata Rule Scanner") {
            
            console.log("SaveImageWithMetaDataUniversal: Found MetadataRuleScanner, adding widget");
            
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                console.log("SaveImageWithMetaDataUniversal: Creating MetadataRuleScanner node, adding widget");
                
                // Add the results display widget using ComfyWidgets for true multiline behavior
                const wDef = ComfyWidgets["STRING"](
                    this,
                    "scan_results_display",
                    ["STRING", { multiline: true }],
                    app
                );
                const widget = wDef.widget;
                widget.serialize = false;
                widget.inputEl.placeholder = "After running Metadata Rule Scanner, the results will populate here.\nYou can edit these rules before saving with the Save Custom Metadata Rules node.";
                widget.inputEl.style.whiteSpace = "pre";
                widget.inputEl.style.fontFamily = "monospace";
                widget.inputEl.style.minHeight = "220px";
                widget.inputEl.style.resize = "vertical";
                widget.inputEl.style.boxSizing = "border-box";

                // Ensure base node size baseline
                if (this.size && this.size[0] < 440) this.size[0] = 440;
                if (this.size && this.size[1] < 360) this.size[1] = 360;

                const nodeRef = this;

                function adjustHeights() {
                    try {
                        if (!nodeRef.widgets || !nodeRef.widgets.length) return;
                        const top = nodeRef.widgets.find(w => w.name === "exclude_keywords");
                        // Force the top widget (exclude_keywords) to a compact logical layout height
                        if (top && top.inputEl) {
                            const TOP_TEXTAREA_H = 52; // px
                            top.inputEl.style.height = TOP_TEXTAREA_H + "px";
                            top.inputEl.style.maxHeight = "72px";
                            top.inputEl.style.overflowY = "auto";
                            top.inputEl.style.resize = "vertical"; // still allow minimal manual expansion
                            // Synchronize widget.height so LiteGraph layout uses the compact height
                            top.height = TOP_TEXTAREA_H + 10; // small padding for label margin
                        }

                        // Calculate space for bottom widget
                        // Sum heights of all other widgets (excluding bottom results)
                        let otherHeights = 0;
                        for (const w of nodeRef.widgets) {
                            if (w === widget) continue;
                            // Prefer explicit height; fallback to computeSize if available
                            let h = w.height;
                            if (!h && typeof w.computeSize === "function") {
                                try { h = w.computeSize(nodeRef.size[0])[1]; } catch(_) {}
                            }
                            otherHeights += (h || 40);
                        }

                        // Title + internal padding allowance
                        const CHROME = 40; // node title bar + internal spacing
                        const minBottom = 160; // minimal practical editing area
                        const available = Math.max(minBottom, nodeRef.size[1] - (otherHeights + CHROME));

                        // Apply to bottom widget
                        widget.height = available; // layout height used by graph
                        const innerH = Math.max(available - 8, 120); // inner textarea height
                        widget.inputEl.style.height = innerH + "px";
                        widget.inputEl.style.maxHeight = innerH + "px"; // prevent stretching beyond node bounds
                        widget.inputEl.style.overflow = "auto";

                        // Ensure node container at least fits summed widgets
                        const requiredNodeH = otherHeights + widget.height + CHROME + 8; // small pad
                        if (requiredNodeH > nodeRef.size[1]) {
                            nodeRef.size[1] = requiredNodeH;
                        }
                    } catch (e) {
                        console.warn("MetadataRuleScanner layout adjust failed", e);
                    }
                }

                // Wrap onResize so only bottom grows with node while top stays capped
                const origResize = this.onResize;
                this.onResize = function(sz) {
                    const r = origResize ? origResize.apply(this, arguments) : undefined;
                    adjustHeights();
                    return r;
                };

                requestAnimationFrame(() => {
                    adjustHeights();
                    nodeRef.setDirtyCanvas?.(true);
                });

                console.log("SaveImageWithMetaDataUniversal: Widget added & layout adjusted:", widget);
                
                return r;
            };
            
            // Hook into the node execution to update the widget
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                console.log("SaveImageWithMetaDataUniversal: MetadataRuleScanner executed with message:", message);
                const r = onExecuted ? onExecuted.apply(this, arguments) : undefined;
                
                // Find the results widget early
                const resultsWidget = this.widgets?.find(w => w.name === "scan_results_display");
                if (!resultsWidget) {
                    return r;
                }

                let payload = null;
                // 1) New direct top-level key (string)
                if (typeof message?.scan_results === "string" && message.scan_results.trim()) {
                    payload = message.scan_results;
                    console.log("SaveImageWithMetaDataUniversal: Using top-level scan_results string");
                }
                // 2) New top-level list variant (defensive)
                else if (Array.isArray(message?.scan_results) && message.scan_results.length) {
                    payload = message.scan_results[0];
                    console.log("SaveImageWithMetaDataUniversal: Using top-level scan_results array");
                }
                // 3) UI payload list
                else if (message?.ui?.scan_results && Array.isArray(message.ui.scan_results) && message.ui.scan_results.length) {
                    payload = message.ui.scan_results[0];
                    console.log("SaveImageWithMetaDataUniversal: Using ui.scan_results payload");
                }
                // 4) Legacy tuple result
                else if (message?.output?.length > 0) {
                    payload = message.output[0];
                    console.log("SaveImageWithMetaDataUniversal: Using legacy output payload");
                }

                if (payload) {
                    try {
                        const parsed = JSON.parse(payload);
                        resultsWidget.value = JSON.stringify(parsed, null, 2);
                    } catch (e) {
                        resultsWidget.value = payload;
                    }
                    if (resultsWidget.callback) {
                        resultsWidget.callback(resultsWidget.value);
                    }
                    if (this.setDirtyCanvas) {
                        this.setDirtyCanvas(true);
                    }
                }
                
                return r;
            };
        }
    },
    
    // Also try the async setup method as an alternative
    async setup() {
        console.log("SaveImageWithMetaDataUniversal: MetadataRuleScanner extension setup called");
    }
});