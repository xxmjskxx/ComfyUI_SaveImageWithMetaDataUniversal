import datetime
import importlib
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

try:  # Optional dependency for template baking tests
    from click.testing import CliRunner
except (ImportError, ModuleNotFoundError):  # pragma: no cover - skip entire module when missing
    pytest.skip("Click not installed; skipping template bake tests", allow_module_level=True)

pytest.importorskip("pytest_cookies", reason="pytest-cookies not installed; skipping cookiecutter template tests")

try:  # Optional dependency for template baking tests
    from cookiecutter.utils import rmtree
except (ImportError, ModuleNotFoundError, AttributeError):  # pragma: no cover - skip entire module when missing
    pytest.skip("cookiecutter not installed; skipping template bake tests", allow_module_level=True)


def _project_path(result) -> Path:
    """Return the pathlib.Path to the baked project root."""

    project_path = getattr(result, "project_path", None)
    if project_path is not None:
        return Path(project_path)
    return Path(str(result.project))


@contextmanager
def inside_dir(dirpath):
    """
    Execute code from inside the given directory
    :param dirpath: String, path of the directory the command is being run.
    """
    old_path = os.getcwd()
    try:
        os.chdir(dirpath)
        yield
    finally:
        os.chdir(old_path)


@contextmanager
def bake_in_temp_dir(cookies, *args, **kwargs):
    """
    Delete the temporal directory that is created when executing the tests
    :param cookies: pytest_cookies.Cookies,
        cookie to be baked and its temporal files will be removed
    """
    user_context = kwargs.pop("extra_context", {}) or {}
    default_context = {"year": str(datetime.datetime.now().year)}
    default_context.update(user_context)
    result = cookies.bake(*args, extra_context=default_context, **kwargs)
    try:
        yield result
    finally:
        rmtree(str(_project_path(result)))


def run_inside_dir(command, dirpath):
    """
    Run a command from inside a given directory, returning the exit status
    :param command: Command that will be executed
    :param dirpath: String, path of the directory the command is being run.
    """
    with inside_dir(dirpath):
        return subprocess.check_call(shlex.split(command))


def check_output_inside_dir(command, dirpath):
    "Run a command from inside a given directory, returning the command output"
    with inside_dir(dirpath):
        return subprocess.check_output(shlex.split(command))


def test_year_compute_in_license_file(cookies):
    with bake_in_temp_dir(cookies) as result:
        project_root = _project_path(result)
        license_file_path = project_root / "LICENSE"
        now = datetime.datetime.now()
        assert str(now.year) in license_file_path.read_text()


def project_info(result):
    """Get toplevel dir, project_slug, and project dir from baked cookies"""
    assert result.exception is None
    project_root = _project_path(result)
    assert project_root.is_dir()

    project_path = str(project_root)
    project_slug = os.path.split(project_path)[-1]
    project_dir = os.path.join(project_path, project_slug)
    return project_path, project_slug, project_dir


def test_bake_with_defaults(cookies):
    with bake_in_temp_dir(cookies) as result:
        project_root = _project_path(result)
        assert project_root.is_dir()
        assert result.exit_code == 0
        assert result.exception is None

        found_toplevel_files = [entry.name for entry in project_root.iterdir()]
        assert "setup.py" in found_toplevel_files
        assert "python_boilerplate" in found_toplevel_files
        assert "tox.ini" in found_toplevel_files
        assert "tests" in found_toplevel_files


def test_bake_and_run_tests(cookies):
    with bake_in_temp_dir(cookies) as result:
        project_root = _project_path(result)
        assert project_root.is_dir()
        project_root_str = str(project_root)
        run_inside_dir("python setup.py test", project_root_str) == 0
        print("test_bake_and_run_tests path", project_root_str)


def test_bake_withspecialchars_and_run_tests(cookies):
    """Ensure that a `full_name` with double quotes does not break setup.py"""
    with bake_in_temp_dir(cookies, extra_context={"full_name": 'name "quote" name'}) as result:
        project_root = _project_path(result)
        assert project_root.is_dir()
        run_inside_dir("python setup.py test", str(project_root)) == 0


def test_bake_with_apostrophe_and_run_tests(cookies):
    """Ensure that a `full_name` with apostrophes does not break setup.py"""
    with bake_in_temp_dir(cookies, extra_context={"full_name": "O'connor"}) as result:
        project_root = _project_path(result)
        assert project_root.is_dir()
        run_inside_dir("python setup.py test", str(project_root)) == 0


# def test_bake_and_run_travis_pypi_setup(cookies):
#     # given:
#     with bake_in_temp_dir(cookies) as result:
#         project_path = str(result.project)
#
#         # when:
#         travis_setup_cmd = ('python travis_pypi_setup.py'
#                             ' --repo audreyr/cookiecutter-pypackage'
#                             ' --password invalidpass')
#         run_inside_dir(travis_setup_cmd, project_path)
#         # then:
#         result_travis_config = yaml.load(
#             result.project.join(".travis.yml").open()
#         )
#         min_size_of_encrypted_password = 50
#         assert len(
#             result_travis_config["deploy"]["password"]["secure"]
#         ) > min_size_of_encrypted_password


def test_bake_without_travis_pypi_setup(cookies):
    # Lazy import to avoid hard test dependency when cookiecutter suite is skipped.
    try:
        import yaml
    except Exception:
        pytest.skip("PyYAML not installed; skipping travis config bake test")

    with bake_in_temp_dir(cookies, extra_context={"use_pypi_deployment_with_travis": "n"}) as result:
        project_root = _project_path(result)
        travis_config_path = project_root / ".travis.yml"
        result_travis_config = yaml.load(travis_config_path.read_text(), Loader=yaml.FullLoader)
        assert "deploy" not in result_travis_config
        assert "python" == result_travis_config["language"]
        # found_toplevel_files = [f.basename for f in result.project.listdir()]


def test_bake_without_author_file(cookies):
    with bake_in_temp_dir(cookies, extra_context={"create_author_file": "n"}) as result:
        project_root = _project_path(result)
        found_toplevel_files = [entry.name for entry in project_root.iterdir()]
        assert "AUTHORS.rst" not in found_toplevel_files
        doc_files = [entry.name for entry in (project_root / "docs").iterdir()]
        assert "authors.rst" not in doc_files

        # Assert there are no spaces in the toc tree
        docs_index_path = project_root / "docs" / "index.rst"
        with docs_index_path.open() as index_file:
            assert "contributing\n   history" in index_file.read()

        # Check that
        manifest_path = project_root / "MANIFEST.in"
        with manifest_path.open() as manifest_file:
            assert "AUTHORS.rst" not in manifest_file.read()


def test_make_help(cookies):
    with bake_in_temp_dir(cookies) as result:
        # The supplied Makefile does not support win32
        if sys.platform != "win32":
            project_root = _project_path(result)
            output = check_output_inside_dir("make help", str(project_root))
            assert b"check code coverage quickly with the default Python" in output


def test_bake_selecting_license(cookies):
    license_strings = {
        "MIT license": "MIT ",
        "BSD license": "Redistributions of source code must retain the " + "above copyright notice, this",
        "ISC license": "ISC License",
        "Apache Software License 2.0": "Licensed under the Apache License, Version 2.0",
        "GNU General Public License v3": "GNU GENERAL PUBLIC LICENSE",
    }
    for license, target_string in license_strings.items():
        with bake_in_temp_dir(cookies, extra_context={"open_source_license": license}) as result:
            project_root = _project_path(result)
            assert target_string in (project_root / "LICENSE").read_text()
            assert license in (project_root / "setup.py").read_text()


def test_bake_not_open_source(cookies):
    with bake_in_temp_dir(cookies, extra_context={"open_source_license": "Not open source"}) as result:
        project_root = _project_path(result)
        found_toplevel_files = [entry.name for entry in project_root.iterdir()]
        assert "setup.py" in found_toplevel_files
        assert "LICENSE" not in found_toplevel_files
        assert "License" not in (project_root / "README.rst").read_text()


def test_using_pytest(cookies):
    with bake_in_temp_dir(cookies, extra_context={"use_pytest": "y"}) as result:
        project_root = _project_path(result)
        assert project_root.is_dir()
        test_file_path = project_root / "tests" / "test_python_boilerplate.py"
        file_contents = test_file_path.read_text()
        assert "import pytest" in file_contents
        # Test the new pytest target
        run_inside_dir("pytest", str(project_root)) == 0


def test_not_using_pytest(cookies):
    with bake_in_temp_dir(cookies) as result:
        project_root = _project_path(result)
        assert project_root.is_dir()
        test_file_path = project_root / "tests" / "test_python_boilerplate.py"
        file_contents = test_file_path.read_text()
        assert "import unittest" in file_contents
        assert "import pytest" not in file_contents


# def test_project_with_hyphen_in_module_name(cookies):
#     result = cookies.bake(
#         extra_context={'project_name': 'something-with-a-dash'}
#     )
#     assert result.project is not None
#     project_path = str(result.project)
#
#     # when:
#     travis_setup_cmd = ('python travis_pypi_setup.py'
#                         ' --repo audreyr/cookiecutter-pypackage'
#                         ' --password invalidpass')
#     run_inside_dir(travis_setup_cmd, project_path)
#
#     # then:
#     result_travis_config = yaml.load(
#         open(os.path.join(project_path, ".travis.yml"))
#     )
#     assert "secure" in result_travis_config["deploy"]["password"],\
#         "missing password config in .travis.yml"


def test_bake_with_no_console_script(cookies):
    context = {"command_line_interface": "No command-line interface"}
    result = cookies.bake(extra_context=context)
    project_path, project_slug, project_dir = project_info(result)
    found_project_files = os.listdir(project_dir)
    assert "cli.py" not in found_project_files

    setup_path = os.path.join(project_path, "setup.py")
    with open(setup_path) as setup_file:
        assert "entry_points" not in setup_file.read()


def test_bake_with_console_script_files(cookies):
    context = {"command_line_interface": "Click"}
    result = cookies.bake(extra_context=context)
    project_path, project_slug, project_dir = project_info(result)
    found_project_files = os.listdir(project_dir)
    assert "cli.py" in found_project_files

    setup_path = os.path.join(project_path, "setup.py")
    with open(setup_path) as setup_file:
        assert "entry_points" in setup_file.read()


def test_bake_with_console_script_cli(cookies):
    context = {"command_line_interface": "Click"}
    result = cookies.bake(extra_context=context)
    project_path, project_slug, project_dir = project_info(result)
    module_path = os.path.join(project_dir, "cli.py")
    module_name = ".".join([project_slug, "cli"])
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    runner = CliRunner()
    noarg_result = runner.invoke(cli.main)
    assert noarg_result.exit_code == 0
    noarg_output = " ".join(["Replace this message by putting your code into", project_slug])
    assert noarg_output in noarg_result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "Show this message" in help_result.output
