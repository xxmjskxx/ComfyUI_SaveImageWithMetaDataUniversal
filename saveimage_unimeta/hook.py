"""Hooks into the ComfyUI execution process to capture workflow data.

This module provides functions that are monkeypatched into the ComfyUI
`execution` module. These hooks allow the `saveimage_unimeta` package to
capture the current prompt, extra data, and the ID of the save image node,
which are essential for the metadata capture process.
"""
from .nodes.node import SaveImageWithMetaDataUniversal

current_prompt = {}
current_extra_data = {}
prompt_executer = None
current_save_image_node_id = -1


def pre_execute(self, prompt, prompt_id, extra_data, execute_outputs):
    """A hook that runs before the execution of a prompt.

    This function is called before a prompt is executed, and it captures the
    current prompt, extra data, and the prompt executer instance for later use
    in the metadata capture process.

    Args:
        self: The `PromptExecutor` instance.
        prompt (dict): The prompt to be executed.
        prompt_id (str): The ID of the prompt.
        extra_data (dict): Extra data associated with the prompt.
        execute_outputs: The outputs of the execution.
    """
    global current_prompt
    global current_extra_data
    global prompt_executer

    current_prompt = prompt
    current_extra_data = extra_data
    prompt_executer = self


def pre_get_input_data(inputs, class_def, unique_id, *args):
    """A hook that runs before getting the input data for a node.

    This function is called before the input data for a node is retrieved. It
    checks if the current node is a `SaveImageWithMetaDataUniversal` node and,
        if so, captures its unique ID.

    Args:
        inputs (dict): The inputs to the node.
        class_def (type): The class of the node.
        unique_id (str): The unique ID of the node.
        *args: Additional arguments.
    """
    global current_save_image_node_id

    if class_def == SaveImageWithMetaDataUniversal:
        current_save_image_node_id = unique_id
