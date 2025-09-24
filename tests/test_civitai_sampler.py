import importlib
import sys
import os
import pytest

# Add parent directory (containing the package folder) to sys.path so that
# 'saveimage_unimeta.capture' can be imported when running tests in isolation.
PKG_PARENT = os.path.dirname(os.path.dirname(__file__))
if PKG_PARENT not in sys.path:
    sys.path.insert(0, PKG_PARENT)

Capture = importlib.import_module("saveimage_unimeta.capture").Capture


def _wrap(name):
    class Obj:
        def __init__(self, name):
            self.name = name
        def __repr__(self):  # helpful if an assertion fails
            return f"<SamplerObj {self.name}>"
    return Obj(name)


@pytest.mark.parametrize(
    "sampler,scheduler,expected",
    [
        ("dpmpp_2m", "karras", "DPM++ 2M Karras"),
        ("dpmpp_2m", "exponential", "DPM++ 2M"),
        ("ipndm", "normal", "ipndm"),
        ("ipndm", "karras", "ipndm_karras"),
    ],
)
def test_sampler_mappings_parametrized(sampler, scheduler, expected):
    out = Capture.get_sampler_for_civitai([("id", sampler)], [("id", scheduler)])
    assert out == expected


def test_object_sampler_and_scheduler_are_coerced():
    out = Capture.get_sampler_for_civitai([("id", _wrap("dpmpp_2m"))], [("id", _wrap("karras"))])
    assert out == "DPM++ 2M Karras"


def test_object_sampler_without_scheduler():
    out = Capture.get_sampler_for_civitai([("id", _wrap("euler"))], [])
    assert out == "Euler"


def test_empty_inputs_return_empty_string():
    out = Capture.get_sampler_for_civitai([], [])
    assert out == ""


def test_passthrough_spacing_and_case_trim():
    out = Capture.get_sampler_for_civitai([("id", "  ipNDM ")], [("id", "  KARRAS  ")])
    assert out == "ipNDM_karras"  # retains original sampler case but normalized scheduler suffix

