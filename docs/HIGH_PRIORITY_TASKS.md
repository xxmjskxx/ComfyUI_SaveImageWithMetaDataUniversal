# High Priority Tasks

Below are 7 interrelated tasks, split into to main categories. Each of the 7 tasks has to do with either generating and saving metadata, verifying metadata, or both. Use this document as a guide to complete all 7 of the tasks outlined below, referring back to it as necessary.

## A. Fix bugs with metadata tracing, generation, recording

### 1. The recent changes you made to 'saveimage_unimeta\defs\ext\efficiency_nodes.py' didn't seem to help with the 'LoRA Stacker' efficiency node. 

Here's some relevant validation log info:

- Validating workflow: flux-eff-LoRA-stack-ClownsharK.json
  - Expected format: png
  - Filename patterns: flux-eff-LoRA-stack-ClownsharK
  - Found 1 matching image(s)
    - ✗ flux-eff-LoRA-stack-ClownsharK_00001_.png
        - Error: Field 'Lora_3 Model hash' contains 'N/A' value: N/A
        - Error: LoRA 'Fluorescentizer FLUX B.safetensors' hash mismatch: metadata has 'a1e0040929' but Hashes summary has '64d3a2aff8'
        - Error: LoRA 'FluxProtectorsOfNature.safetensors' hash mismatch: metadata has 'a1e0040929' but Hashes summary has '7118fb84e6'
        - Error: LoRA '1.0' has metadata but is missing from Hashes summary
        - Error: LoRA hash for Lora_3 is 'N/A' - hash should always be computed

Here's a relevant excerpt from the metadata:

Lora_0 Model name: Fluorescentizer FLUX B.safetensors, Lora_0 Model hash: a1e0040929, Lora_0 Strength model: 1.0, Lora_0 Strength clip: 0.22, Lora_1 Model name: FluxProtectorsOfNature.safetensors, Lora_1 Model hash: a1e0040929, Lora_1 Strength model: 0.3, Lora_1 Strength clip: 1.0, Lora_2 Model name: DND_COLORBOYZ_FG_FLUX_REMUS_Lora.safetensors, Lora_2 Model hash: None, Lora_2 Strength model: 1.0, Lora_2 Strength clip: 1.0, Lora_3 Model name: 1.0, Lora_3 Model hash: N/A, Lora_3 Strength model: 1.0, Lora_3 Strength clip: 0.44, Lora_4 Model name: None, Lora_4 Model hash: None, Lora_4 Strength model: 1.0, Lora_4 Strength clip: 1.0, Hashes: {"model": "47d8dbdc6d", "vae": "afc8e28272", "lora:Fluorescentizer FLUX B": "64d3a2aff8", "lora:FluxProtectorsOfNature": "7118fb84e6", "lora:DND_COLORBOYZ_FG_FLUX_REMUS_Lora": "None", "lora:None": "None"}, Metadata generator version: 1.3.0

Problems:
- 4 loras were recorded, but there were only 3 used. This is possibly because of the 'clp_str_50' value, which is not actually tied to any specific lora and is a general clip strength applied to the final combined clip. The Lora_4 Model name is recorded as 'None', which should never happen because, as I said before, if a lora or model='None'=it is disabled=do not record.
- The hashes are mostly not provided. 
- Hashes in the 'Hashes' section have 'None' recorded. 

I've pushed these files to the repo: 'saveimage_unimeta/defs/ext/generated_user_rules.py', 'saveimage_unimeta/user_rules/user_captures.json', 'saveimage_unimeta/user_rules/user_samplers.json'. I will delete them later because each user has to generate their own rules based on the nodes they have installed, but for now you can use these files to reference how the nodes are creating capture rules during a given commit so you can better understand what changes need to be made. 'generated_user_rules.py' should likely be the most useful.
Note: most samplers have been explicitly defined in the 'saveimage_unimeta\defs\samplers.py' file, so 'saveimage_unimeta/user_rules/user_samplers.json' actually has verry little useful information. So, 'user_captures.json' and especially 'generated_user_rules.py' will be the most helpful.

As you'll see, when you analyze the above files, the capture rules for the 'LoRA Stacker' node are completely wrong and a mess after your recent edits.

- Note: lora stack loaders have separate inputs for every lora model's strength. Some give strength as a single value, which is both the lora strength and the clip strength, but others will have lora strength and clip strength as separate inputs. Most, though not all, also number the inputs. For example, in advanced mode the LoRA Stacker node has these inputs:
  - lora_name_1
  - model_str_1
  - clip_str_l
  - lora_name_2
  - model_str_2
  - clip_str_2
  - lora_name_3
  - model_str_3
  - clip_str_3
  - clip_str_50

Since the inputs are numbered, there should never be any mixup between which strength belongs to which lora. You can also see strange notation used here, the 'clp_str_50' value I mentioned earlier. However, this shouldn't throw us off because all the lora_name_, model_str_, and clip_str_ keys are numbered sets, each with three items. This makes it obvious the 'clip_str_50' could not pertain to any of the loras because it does not occur in a set like the others and, especially, has no corresponding lora, and so 'clip_str_50' is extraneous.

- You've also seen the CR LoRA Stack node before. Some stacker nodes like this one have switches for on/off / enable/disable.
  - switch_1
  - lora_name_1
  - model_weight_1
  - clip_weight_1
  - switch_2
  - lora_name_2
  - model_weight_2
  - clip_weight_2
  - switch_3
  - lora_name_3
  - model_weight_3
  - clip_weight_3

Again, here the inputs are all numbered, so you know which properties belong to which lora, and they should be traced appropriately and never mixed up with one another.

- While less common, there are some stack loaders that don't number all the inputs, so you may get something like:
  - lora_name_1
  - str
  - lora_name_2
  - str
  - lora_name_3
  - str

The strength values here aren't numbered but, just like the previous stack nodes we looked at which did have all inputs numbered, they are ordered sequentially, which firmly establishes which lora the str value is associated with. And again, they come in sets, though this time they are pairs, i.e. sets of two.

I'm not sure which file(s) will have to be edited, but sets of lora and strength metadata must never lose their association with one another - one lora's strength can never be recorded under another lora's name. 

Also, the data should never change. If you initially find lora and strength values like (lora_name_1=xxx, str=0.7, lora_name_2=zzz, str=1.1), or (xxx, zzz, 0.7, 1.1) if it's just the values, and then you later record values of (xxx, xxx, 0.7, 1.0) or (xxx, zzz, 1.0, 1.1), something has gone wrong during the assignment of values to keys. The values that were initially traced should never change.

And no two hashes should be identical - such an occurrence suggests something has gone wrong. Hashes are not technically mathematically unique, but they are designed to make collisions very unlikely, and encountering collisions in the context of this custom node pack is improbable.

Note 1: The exact naming conventions used for inputs can vary significantly, and the examples provided above are not anywhere near exhaustive. This is why the heuristics in 'saveimage_unimeta\nodes\scanner.py' are designed to be able to match with a very diverse range of nodes and input names (over 1000 custom nodes were referenced when designing the heuristics in order to align with the diverse naming conventions currently in use).

Note 2: if a switch on a lora loader is set to off/disabled, neither that lora nor any corresponding strength values or hash should be recorded. Similarly, if the value of a lora's name is 'None', neither that lora nor any corresponding strength values or hash should be recorded. If any or all of a lora's strength values are set to 0, that lora and its strength(s) should still be recorded.

Additionally, here is validation from the CR Lora stack workflow:

- Validating workflow: flux-CR-LoRA-stack-ClownsharK.json
  - Expected format: png
  - Filename patterns: flux-CR-LoRA-stack-ClownsharK
  - Found 1 matching image(s)
    - ✗ flux-CR-LoRA-stack-ClownsharK_00001_.png
        - Error: LoRA '80sFantasyMovieMJ7Flux.safetensors' hash mismatch: metadata has '67a9c045d0' but Hashes summary has '30f425fe15'
        - Error: LoRA 'closeupfilm.safetensors' hash mismatch: metadata has '67a9c045d0' but Hashes summary has 'f5481e1d05'

### IMPORTANT:
#### If, at any point, after making some changes to how metadata is traced, generated, captured, and recorded, you would like to stop and check the results of your changes, just stop, make a PR, and let me know. I will generate new 'saveimage_unimeta/defs/ext/generated_user_rules.py', 'saveimage_unimeta/user_rules/user_captures.json', and 'saveimage_unimeta/user_rules/user_samplers.json' files for you in my ComfyUI testing environment and push them to the branch you are working on. 
#### Once I've given you access to the new files, I will let you know to resume, and then you can analyze the updated files to see if your recent changes had the desired effect regarding how metadata is traced, generated, captured, and correcting existing bugs with these functionalities. 
#### It will likely be important to stop and check like this every so often, since you don't have access to a ComfyUI environment in which to perform these actions yourself. Your task is to only work on the 7 tasks laid out in this document until you reach a point where you need the 'user_rules' documents to be refreshed. At that time, your task will be completed. At that time, you can push your results to your working branch.

### 2. The other result of the recent changes you made to 'saveimage_unimeta\defs\ext\efficiency_nodes.py' is broken metadata recording in workflows that used to work. Two of the save nodes in the 'efficiency-nodes.json' workflow now fail, when they used to pass.

- Validating workflow: efficiency-nodes.json
  - Expected format: png
  - Filename patterns: eff_basic, eff_adv, eff_xl, eff-without-meta
  - Found 4 matching image(s)
    - ✗ eff_adv_00001_.png
        - Error: Field 'Lora_0 Model hash' contains 'N/A' value: N/A
        - Error: LoRA '1.0' has metadata but is missing from Hashes summary
        - Error: LoRA hash for Lora_0 is 'N/A' - hash should always be computed
    - ✗ eff_basic_00001_.png
        - Error: Field 'Lora_0 Model hash' contains 'N/A' value: N/A
        - Error: LoRA '1.0' has metadata but is missing from Hashes summary
        - Error: LoRA hash for Lora_0 is 'N/A' - hash should always be computed

The loader used in both cases is the 'Efficient Loader' node. This node has a lora loader widget, but no lora was loaded (was set to 'None'), yet both of the above images have a lora recorded to their metadata.

One of the other images was made using the 'Eff. Loader SDXL' node, which has no lora loader widget which is why that image's metadata was correct. And the final image was a control image, saved using the default ComfyUI 'Save Image' node, so it was obviously fine.

### 3. Ensure the version is always the very last entry in the metadata

e.g.:

... Hashes: {"model": "5519e566e6", "vae": "2fc39d3135", "lora:lightx2v_T2V_14B_cfg_step_distill_v2_lora_rank64_bf16_": "37d4921854"}, Metadata generator version: 1.3.0

I think this is already the case, but just double check to be sure the version is always the very last entry in the metadata, as in the above example.

## B. Validation script 'tests\comfyui_cli_tests\validate_metadata.py'

The below issues are likely bugs in the validation script.

### 4. This workflow still fails validation, likely due to failing to resolve the correct path

Unmatched Workflows (1):
  - filename_format_denoise.json
Unmatched Images (1):
  - 123-512x512_20251111-145036_00001_.png
  
This workflow has a linked filename_prefix value of 'Test\\siwm-%model:10%/%pprompt:20%-%nprompt:20%/%seed%-%width%x%height%_%date:yyyyMMdd-hhmmss%'.
- Legend for filename tokens:
  - %model:10% = model name trunc'd to 10 characters
  - %pprompt:20% = positive prompt trunc'd to 20 chars
  - %nprompt:20% = negative prompt trunc'd to 20 characters
  - %seed% = seed
  - %width% = width
  - %height% = height

I expect that once the path and filename are correctly resolved, the image and workflow will match.

I also changed the filename_prefix value in the workflow to 'Test\\%model:10%/%pprompt:20%-%nprompt:20%/%seed%-%width%x%height%_%date:yyyyMMdd-hhmmss%-siwm'. 
Moving '-siwm' to the end of the filename_prefix makes it part of the filename, rather than the path (as it previously was), which will be easier for matching.


### 5. Possible false positive?

- Validating workflow: extra_metadata_clip_skip.json
  - Expected format: png
  - Sampler nodes found: 1
  - Filename patterns: extra_metadata_clip_skip
  - Found 1 matching image(s)
    - ✗ extra_metadata_clip_skip_00001_.png
        - Error: Hashes field is not valid JSON

I think this validation error may be incorrect. Here is a snippet of the metadata:

... Size: 832x1216, Model: cyberrealistic_v33.safetensors, Model hash: 7a4dbba12f, Clip skip: 2, Hashes: {"model": "7a4dbba12f"}, custom_h: 1216, custom_key: custom_value, custom_w: 832, hello: world, Metadata generator version: 1.3.0

This looks fine to me, but I could be mistaken. Perhaps it's because the Hashes section only has one key value pair? I'm not sure.

### 6. Hash validation against .sha256 sidecar files

I would like to add an additional step to to the validation script 'tests\comfyui_cli_tests\validate_metadata.py' to verify all hashes (loras, unet/ckpt, vae, embedding) which are read/found in the metadata of all images being validated. The hashes in the metadata should be validated against their sidecar '.sha256' files. Additionally, verify the sidecar files contain the full hash and that the hashes in metadata have always been truncated to the first 10 characters.

### 7. Exception

Every time I run the validation script 'tests\comfyui_cli_tests\validate_metadata.py' the last two lines printed to the console are:

```
======================================================================
Exception ignored in: Exception ignored in sys.unraisablehook
```

I'm not sure if this exception is something that should be addressed, or irrelevant.


