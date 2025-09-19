import { app } from "../../scripts/app.js";

// Simple test extension to verify loading
app.registerExtension({
    name: "SaveImageWithMetaDataUniversal.TestWidget",
    
    async setup() {
        console.log("SaveImageWithMetaDataUniversal test widget loaded successfully!");
    }
});