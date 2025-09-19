import { app } from "../../scripts/app.js";

// Add a custom widget to MetadataRuleScanner for displaying results
app.registerExtension({
    name: "SaveImageWithMetaDataUniversal.MetadataRuleScanner",
    
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "MetadataRuleScanner") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // Add the results display widget
                this.addWidget("text", "scan_results_display", "", function(v) {}, {
                    multiline: true,
                    placeholder: "After running Metadata Rule Scanner, the results will populate here.",
                    readonly: false,  // Allow editing so users can modify before copying
                    serialize: false  // Don't save this in the workflow
                });
                
                return r;
            };
            
            // Hook into the node execution to update the widget
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                const r = onExecuted ? onExecuted.apply(this, arguments) : undefined;
                
                if (message && message.output) {
                    // Find the results widget
                    const resultsWidget = this.widgets.find(w => w.name === "scan_results_display");
                    if (resultsWidget && message.output.length > 0) {
                        // Use the JSON output (first return value)
                        const jsonResults = message.output[0];
                        if (jsonResults) {
                            // Pretty format the JSON for better readability
                            try {
                                const parsed = JSON.parse(jsonResults);
                                resultsWidget.value = JSON.stringify(parsed, null, 2);
                            } catch (e) {
                                // Fallback to raw text if JSON parsing fails
                                resultsWidget.value = jsonResults;
                            }
                        }
                    }
                }
                
                return r;
            };
        }
    }
});