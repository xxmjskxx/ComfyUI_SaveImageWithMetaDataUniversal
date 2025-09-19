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
                        const top = nodeRef.widgets.find(w => w.name === "exclude_keywords");
                        // Force the top widget (exclude_keywords) to a compact logical layout height
                        if (top && top.inputEl) {
                            const TOP_TEXTAREA_H = 52; // px (visible textarea height target)
                            // Force the DOM element to the target height
                            top.inputEl.style.height = TOP_TEXTAREA_H + "px";
                            top.inputEl.style.minHeight = TOP_TEXTAREA_H + "px";
                            top.inputEl.style.maxHeight = (TOP_TEXTAREA_H + 12) + "px"; // a tiny bit of headroom
                            top.inputEl.style.overflowY = "auto";
                            top.inputEl.style.resize = "vertical"; // allow user expansion if really needed

                            // Make sure LiteGraph's layout engine also believes this widget is short.
                            // Some internal ComfyUI widgets cache a larger height on creation; overriding
                            // computeSize ensures future draws use our compact value (height + label + margin).
                            const LAYOUT_H = TOP_TEXTAREA_H + 18; // label + padding allowance
                            if (!top._forceCompactApplied) {
                                const origCompute = top.computeSize ? top.computeSize.bind(top) : null;
                                top.computeSize = function(w) {
                                    // Preserve width logic if original existed
                                    let width = w;
                                    if (origCompute) {
                                        try { width = origCompute(w)[0]; } catch(_) {}
                                    }
                                    return [width, LAYOUT_H];
                                };
                                // Store logical layout height for later calculations
                                top._logicalHeight = LAYOUT_H;
                                top._forceCompactApplied = true;
                            }
                        }
                        // Helper to obtain a widget's effective layout height
                        const getWidgetHeight = (w) => {
                            if (!w) return 0;
                            return w._logicalHeight || w.height || (typeof w.computeSize === "function" ? (w.computeSize(nodeRef.size[0])||[0,20])[1] : 20);
                        }

                        // Calculate space for bottom widget
                        // Sum heights of all other widgets (excluding bottom results)
                        let otherHeights = 0;
                        for (const w of nodeRef.widgets) {
                            if (w === widget) continue;
                            otherHeights += getWidgetHeight(w) || 40;
                        }

                        const CHROME = 40; // title + padding
                        const MIN_BOTTOM = 120; // minimal reasonable editing area

                        // Raw space currently available inside node for bottom widget
                        const rawAvailable = nodeRef.size[1] - (otherHeights + CHROME);
                        let available;
                        if (rawAvailable < MIN_BOTTOM) {
                            // Not enough space: clamp to raw (could even be negative) so we don't force node to resize larger.
                            // We'll give the textarea a minimal height and rely on scrolling.
                            available = Math.max(60, rawAvailable); // allow very small but usable
                        } else {
                            available = rawAvailable;
                        }

                        // Apply to bottom widget using logical height (cannot assign to widget.height; getter only in some builds)
                        const bottomLogical = Math.max(60, available);
                        widget._logicalHeight = bottomLogical;
                        if (!widget._computeOverridden) {
                            const origCompute = widget.computeSize ? widget.computeSize.bind(widget) : null;
                            widget.computeSize = function(w) {
                                let width = w;
                                if (origCompute) {
                                    try { width = origCompute(w)[0]; } catch(_) {}
                                }
                                return [width, widget._logicalHeight || 120];
                            };
                            widget._computeOverridden = true;
                        }
                        // Inner textarea height (leave a small label/padding allowance ~14px)
                        const innerH = Math.max(40, bottomLogical - 14);
                        widget.inputEl.style.height = innerH + "px";
                        widget.inputEl.style.maxHeight = innerH + "px";
                        widget.inputEl.style.overflow = "auto";

                        // Recompute true required node height (what we *could* be) using preferred bottom min if we have slack
                        const preferredBottom = Math.max(MIN_BOTTOM, widget._logicalHeight || bottomLogical);
                        const idealNodeH = otherHeights + preferredBottom + CHROME + 8;

                        // If current node is larger than ideal (e.g. after shrinking top widget), shrink it.
                        if (nodeRef.size[1] > idealNodeH + 4) {
                            nodeRef.size[1] = idealNodeH;
                        }

                        // Recalculate widget y positions to eliminate stale spacing from earlier heights.
                        const startY = nodeRef.widgets_start_y || 4;
                        // Ensure results widget is last in ordering so gap doesn't appear above toggles.
                        const currentIdx = nodeRef.widgets.indexOf(widget);
                        if (currentIdx !== -1 && currentIdx !== nodeRef.widgets.length - 1) {
                            nodeRef.widgets.splice(currentIdx, 1);
                            nodeRef.widgets.push(widget);
                        }
                        let yCursor = startY;
                        for (const w of nodeRef.widgets) {
                            const effH = (w === widget) ? (widget._logicalHeight || 120) : (getWidgetHeight(w) || 20);
                            const h = Math.max(effH, 8);
                            w.y = yCursor;
                            yCursor += h + 4;
                        }

                        // Detect excessive vertical gap between first (top) and second widget.
                        if (nodeRef.widgets.length > 2) {
                            const first = nodeRef.widgets[0];
                            const second = nodeRef.widgets[1];
                            const firstH = getWidgetHeight(first) || first.height || 20;
                            const gap = second.y - (first.y + firstH + 4);
                            if (gap > 40) { // large unexpected gap
                                const shift = gap - 4;
                                for (let i = 1; i < nodeRef.widgets.length; i++) {
                                    nodeRef.widgets[i].y -= shift;
                                }
                                nodeRef.size[1] -= shift; // shrink node accordingly
                            }
                        }

                        // Debug dump (remove later)
                        if (!nodeRef._scannerLayoutLoggedOnce) {
                            try {
                                console.log("[MetadataRuleScanner layout] widgets:");
                                nodeRef.widgets.forEach((w,i)=>{
                                    console.log(`#${i}`, w.name, 'y=', w.y, 'h=', w.height);
                                });
                            } catch(_) {}
                            nodeRef._scannerLayoutLoggedOnce = true;
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