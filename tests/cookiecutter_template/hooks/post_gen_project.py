import shutil
from pathlib import Path

PROJECT_DIR = Path.cwd()


def _remove_if_exists(relative_path: str) -> None:
    target = PROJECT_DIR / relative_path
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()


if "{{ cookiecutter.create_author_file }}" != "y":
    _remove_if_exists("AUTHORS.rst")
    _remove_if_exists("docs/authors.rst")

if "{{ cookiecutter.open_source_license }}" == "Not open source":
    _remove_if_exists("LICENSE")

if "{{ cookiecutter.command_line_interface }}" != "Click":
    _remove_if_exists("{{ cookiecutter.project_slug }}/cli.py")
