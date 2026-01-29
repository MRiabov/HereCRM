import pytest
import os
import yaml
from src.services.template_service import TemplateService


@pytest.fixture
def mock_jinja(tmp_path):
    d = tmp_path / "assets"
    d.mkdir()
    f = d / "messages.jinja"
    content = """
{% macro simple() -%}
Hello World
{%- endmacro %}

{% macro with_var(name) -%}
Hello {{ name }}
{%- endmacro %}

{% macro mixed(name, role) -%}
Hello {{ name }} as {{ role }}
{%- endmacro %}
"""
    f.write_text(content)
    return str(f)


def test_template_render_simple(mock_jinja):
    ts = TemplateService(mock_jinja)
    assert ts.render("simple") == "Hello World"


def test_template_render_var(mock_jinja):
    ts = TemplateService(mock_jinja)
    assert ts.render("with_var", name="Alice") == "Hello Alice"


def test_template_render_mixed(mock_jinja):
    ts = TemplateService(mock_jinja)
    assert ts.render("mixed", name="Alice", role="Admin") == "Hello Alice as Admin"


def test_template_render_missing_key(mock_jinja):
    ts = TemplateService(mock_jinja)
    assert ts.render("nonexistent") == "[nonexistent]"


def test_template_render_missing_var(mock_jinja):
    ts = TemplateService(mock_jinja)
    # Jinja Undefined renders as empty string by default
    assert ts.render("with_var") == "Hello "

def test_template_load_fallback_yaml_path(tmp_path):
    # Test that if .yaml path is provided but only .jinja exists, it works (migration logic)
    d = tmp_path / "assets"
    d.mkdir()
    f = d / "messages.jinja"
    f.write_text("{% macro foo() %}bar{% endmacro %}")

    yaml_path = str(d / "messages.yaml")
    ts = TemplateService(yaml_path)
    assert ts.render("foo") == "bar"

def test_yaml_compatibility(tmp_path):
    # Test backward compatibility with YAML files (like prompts.yaml)
    d = tmp_path / "assets"
    d.mkdir() # mkdir ok if exists? tmp_path/assets might be same as above test? tmp_path is unique per test function.
    f = d / "prompts.yaml"
    content = {
        "legacy": "Hello {name}",
        "struct": {"key": "value"}
    }
    f.write_text(yaml.dump(content))

    ts = TemplateService(str(f))
    assert ts.render("legacy", name="Bob") == "Hello Bob"
    assert ts.templates["struct"] == {"key": "value"}


def test_template_render_extra_args(mock_jinja):
    ts = TemplateService(mock_jinja)
    # "simple" macro takes no args. Passing extra args should not crash.
    assert ts.render("simple", extra="ignored") == "Hello World"
    # "with_var" takes "name".
    assert ts.render("with_var", name="Alice", extra="ignored") == "Hello Alice"
