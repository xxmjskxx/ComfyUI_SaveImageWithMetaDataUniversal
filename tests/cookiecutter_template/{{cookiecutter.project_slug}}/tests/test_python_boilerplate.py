{% if cookiecutter.use_pytest == "y" %}
import pytest


@pytest.fixture()
def response():
    return "success"


def test_response(response):
    assert response == "success"
{% else %}
import unittest


class TestPythonBoilerplate(unittest.TestCase):
    def test_sanity(self):
        self.assertEqual(2 * 2, 4)


if __name__ == "__main__":
    unittest.main()
{% endif %}
