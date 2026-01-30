import pytest
from pydantic import ValidationError
from src.schemas.pwa import WhatsAppTemplateComponentSchema, WhatsAppTemplateCreate

def test_template_component_validation_success():
    # Valid variables should pass
    valid_text = "Hi {{customer.first_name}}, your job {{job.type}} is set for {{job.date}}."
    component = WhatsAppTemplateComponentSchema(type="BODY", text=valid_text)
    assert component.text == valid_text

def test_template_component_validation_failure():
    # Invalid variables should raise ValidationError
    invalid_text = "Hi {{customer.nickname}}, thanks for the {{money}}."
    with pytest.raises(ValidationError) as excinfo:
        WhatsAppTemplateComponentSchema(type="BODY", text=invalid_text)
    
    assert "Unsupported variables: customer.nickname, money" in str(excinfo.value)

def test_template_create_validation():
    # Test through the main Create schema
    data = {
        "name": "test_template",
        "category": "UTILITY",
        "language": "en_US",
        "components": [
            {
                "type": "BODY",
                "text": "Correct: {{business.name}}, Incorrect: {{wrong.var}}"
            }
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        WhatsAppTemplateCreate(**data)
    
    assert "Unsupported variables: wrong.var" in str(excinfo.value)
