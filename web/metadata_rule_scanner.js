import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Add a custom widget to MetadataRuleScanner for displaying results
app.registerExtension({
    name: "SaveImageWithMetaDataUniversal.MetadataRuleScanner",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
    // Only minimal logging (remove noisy per-node enumeration)
        
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
                // Use wrapping so long lines don't force horizontal scrolling
                widget.inputEl.style.whiteSpace = "pre-wrap"; // preserve newlines, allow wrap
                widget.inputEl.style.wordBreak = "break-word";
                widget.inputEl.style.overflowWrap = "anywhere";
                widget.inputEl.style.fontFamily = "monospace";
                widget.inputEl.style.minHeight = "220px";
                widget.inputEl.style.resize = "vertical";
                widget.inputEl.style.boxSizing = "border-box";
                widget.inputEl.style.width = "100%"; // avoid horizontal clipping
                widget.inputEl.style.overflowX = "hidden"; // hide horizontal scrollbar
                widget.inputEl.wrap = "soft";

                // Ensure base node size baseline
                if (this.size && this.size[0] < 440) this.size[0] = 440;
                if (this.size && this.size[1] < 360) this.size[1] = 360;

                const nodeRef = this;

                function adjustHeights() {
                    try {
                        if (!nodeRef.widgets || !nodeRef.widgets.length) return;
                        const TOP_H = 52; // visible top textarea
                        const TOP_LAYOUT = TOP_H + 18; // label + padding
                        const CHROME = 34; // node title + inner top padding approximation
                        const MIN_BOTTOM = 140;
                        const MAX_BOTTOM = 500; // don't let it balloon
                        const PADDING = 6; // bottom padding

                        // Identify widgets
                        const top = nodeRef.widgets.find(w => w.name === "exclude_keywords");
                        const bottom = widget; // results

                        // Style top (idempotent)
                        if (top?.inputEl) {
                            Object.assign(top.inputEl.style, {
                                height: TOP_H + "px",
                                minHeight: TOP_H + "px",
                                maxHeight: TOP_H + 12 + "px",
                                overflowY: "auto",
                                resize: "vertical"
                            });
                            if (!top._forced) {
                                const orig = top.computeSize ? top.computeSize.bind(top) : null;
                                top.computeSize = w => {
                                    let width = w;
                                    if (orig) { try { width = orig(w)[0]; } catch(_){} }
                                    return [width, TOP_LAYOUT];
                                };
                                top._logicalHeight = TOP_LAYOUT;
                                top._forced = true;
                            }
                        }

                        // Collect middle widgets (everything except top & bottom)
                        const middle = nodeRef.widgets.filter(w => w !== top && w !== bottom);
                        // Estimate middle total height
                        let middleTotal = 0;
                        middle.forEach(w => {
                            let h = w._logicalHeight || w.height || (typeof w.computeSize === "function" ? (w.computeSize(nodeRef.size[0])||[0,20])[1] : 20);
                            if (!h || h < 20) h = 20;
                            middleTotal += h + 4; // include spacing
                        });

                        // Desired node height -> if user resized, honor up to MAX_BOTTOM
                        let desiredNodeH = nodeRef.size[1];
                        if (!desiredNodeH || desiredNodeH < 240) desiredNodeH = 240;

                        // Compute available for bottom based on current node size
                        let availableForBottom = desiredNodeH - (CHROME + TOP_LAYOUT + middleTotal + PADDING);
                        // Clamp
                        if (availableForBottom < MIN_BOTTOM) availableForBottom = MIN_BOTTOM;
                        if (availableForBottom > MAX_BOTTOM) availableForBottom = MAX_BOTTOM;
                        bottom._logicalHeight = availableForBottom;

                        // Update bottom textarea element heights
                        const innerBottom = Math.max(40, availableForBottom - 14);
                        Object.assign(bottom.inputEl.style, {
                            height: innerBottom + "px",
                            maxHeight: innerBottom + "px",
                            overflow: "auto"
                        });

                        // Now recompute node height exactly to fit stacked widgets
                        const finalNodeH = CHROME + TOP_LAYOUT + middleTotal + availableForBottom + PADDING;
                        nodeRef.size[1] = finalNodeH;

                        // Assign y positions
                        let y = nodeRef.widgets_start_y || 4;
                        if (top) { top.y = y; y += TOP_LAYOUT + 4; }
                        for (const w of middle) {
                            let mH = w._logicalHeight || w.height || 20;
                            if (mH < 20) mH = 20;
                            w.y = y;
                            y += mH + 4;
                        }
                        bottom.y = y;
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
                    // Re-run sizing in case content length affects scrollbars etc.
                    if (typeof this.onResize === "function") {
                        try { this.onResize(this.size); } catch(_) {}
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