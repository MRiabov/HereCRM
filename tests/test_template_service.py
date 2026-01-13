import pytest
import os
import yaml
from src.services.template_service import TemplateService


@pytest.fixture
def mock_yaml(tmp_path):
    d = tmp_path / "assets"
    d.mkdir()
    f = d / "messages.yaml"
    content = {
        "simple": "Hello World",
        "with_var": "Hello {name}",
        "with_double_var": "Hello {{name}}",
        "mixed": "Hello {name} as {{role}}",
    }
    f.write_text(yaml.dump(content))
    return str(f)


def test_template_load(mock_yaml):
    ts = TemplateService(mock_yaml)
    assert ts.templates["simple"] == "Hello World"


def test_template_render_simple(mock_yaml):
    ts = TemplateService(mock_yaml)
    assert ts.render("simple") == "Hello World"


def test_template_render_var(mock_yaml):
    ts = TemplateService(mock_yaml)
    assert ts.render("with_var", name="Alice") == "Hello Alice"


def test_template_render_double_var(mock_yaml):
    ts = TemplateService(mock_yaml)
    assert ts.render("with_double_var", name="Alice") == "Hello Alice"


def test_template_render_mixed(mock_yaml):
    ts = TemplateService(mock_yaml)
    assert ts.render("mixed", name="Alice", role="Admin") == "Hello Alice as Admin"


def test_template_render_missing_key(mock_yaml):
    ts = TemplateService(mock_yaml)
    assert ts.render("nonexistent") == "[nonexistent]"


def test_template_render_missing_var(mock_yaml):
    ts = TemplateService(mock_yaml)
    # Should not crash, returns normalized template
    assert ts.render("with_var") == "Hello {name}"
