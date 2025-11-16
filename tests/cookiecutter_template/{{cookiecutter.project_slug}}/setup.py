import sys
from pathlib import Path

from setuptools import Command, find_packages, setup

here = Path(__file__).parent


class PyTestCommand(Command):
    """Run pytest via ``python setup.py test`` for backwards-compatible tests."""

    description = "run tests with pytest"
    user_options = []

    def initialize_options(self):  # type: ignore[override]
        self.test_args = []
        self.test_suite = True

    def finalize_options(self):  # type: ignore[override]
        pass

    def run(self):  # type: ignore[override]
        import pytest

        raise SystemExit(pytest.main(self.test_args))

setup(
    name={{ cookiecutter.project_slug | tojson }},
    version={{ cookiecutter.version | tojson }},
    description={{ cookiecutter.project_short_description | tojson }},
    author={{ cookiecutter.full_name | tojson }},
    author_email={{ cookiecutter.email | tojson }},
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        {% if cookiecutter.command_line_interface == "Click" %}"click>=8.1.0"{% endif %}
    ],
    license=(
        {{ cookiecutter.open_source_license | tojson }}
        if {{ cookiecutter.open_source_license | tojson }} != "Not open source"
        else "Proprietary"
    ),
    {% if cookiecutter.command_line_interface == "Click" %}
    entry_points={
        "console_scripts": [
            "{{ cookiecutter.project_slug }}={{ cookiecutter.project_slug }}.cli:main",
        ],
    },
    {% endif %}
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.9",
    tests_require=["pytest"],
    cmdclass={"test": PyTestCommand},
)
