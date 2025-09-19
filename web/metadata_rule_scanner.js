import { app } from "../../scripts/app.js";

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
                
                // Add the results display widget
                const widget = this.addWidget("text", "scan_results_display", "", function(v) {
                    // Callback when value changes
                }, {
                    multiline: true,
                    placeholder: "After running Metadata Rule Scanner, the results will populate here.\nYou can edit these rules before copying them for use.",
                    serialize: false  // Don't save this in the workflow
                });
                
                console.log("SaveImageWithMetaDataUniversal: Widget added:", widget);
                
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