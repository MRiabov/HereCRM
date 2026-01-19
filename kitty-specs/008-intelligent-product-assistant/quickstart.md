# Quickstart: Intelligent Product Assistant

## 1. Configuration

Ensure `src/assets/channels.yaml` is populated:

```yaml
channels:
  whatsapp:
    max_length: 500
    style: "concise"
  email:
    max_length: 2000
    style: "detailed"
```

## 2. Usage

Trigger the assistant via WhatsApp:

- **How-To**: "How do I add a lead?"
- **Troubleshooting**: "Why did my last message fail?"
- **Discovery**: "What can I do to use you better?"

## 3. Development

- The assistant logic resides in `src/services/help_service.py`.
- Prompts are defined in `src/assets/prompts.yaml`.
- The product manual is injected from `src/assets/manual.md`.
