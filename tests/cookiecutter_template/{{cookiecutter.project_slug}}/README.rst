{{ cookiecutter.project_name }}
=============================

{{ cookiecutter.project_short_description }}

* Free software: {% if cookiecutter.open_source_license != 'Not open source' %}{{ cookiecutter.open_source_license }}{% else %}Proprietary{% endif %}
* Documentation: https://example.com/docs

Features
--------

* TODO: Add features

{% if cookiecutter.open_source_license != 'Not open source' %}
License
-------

Distributed under the {{ cookiecutter.open_source_license }}. See ``LICENSE`` for more information.
{% endif %}
