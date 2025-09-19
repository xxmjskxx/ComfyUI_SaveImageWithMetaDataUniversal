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
                
                if (message && message.output) {
                    // Find the results widget
                    const resultsWidget = this.widgets?.find(w => w.name === "scan_results_display");
                    console.log("SaveImageWithMetaDataUniversal: Found results widget:", resultsWidget);
                    
                    if (resultsWidget && message.output.length > 0) {
                        // Use the JSON output (first return value)
                        const jsonResults = message.output[0];
                        if (jsonResults) {
                            console.log("SaveImageWithMetaDataUniversal: Updating widget with results:", jsonResults);
                            // Pretty format the JSON for better readability
                            try {
                                const parsed = JSON.parse(jsonResults);
                                resultsWidget.value = JSON.stringify(parsed, null, 2);
                            } catch (e) {
                                // Fallback to raw text if JSON parsing fails
                                resultsWidget.value = jsonResults;
                            }
                            
                            // Force widget update and redraw
                            if (resultsWidget.callback) {
                                resultsWidget.callback(resultsWidget.value);
                            }
                            if (this.setDirtyCanvas) {
                                this.setDirtyCanvas(true);
                            }
                        }
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