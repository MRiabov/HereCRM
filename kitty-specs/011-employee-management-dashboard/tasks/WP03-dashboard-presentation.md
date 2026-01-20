---
work_package_id: WP03
title: Dashboard Presentation
lane: "for_review"
dependencies: []
subtasks: [T008, T009, T010]
agent: "Antigravity"
shell_pid: "3779362"
---

# Work Package 03: Dashboard Presentation

## Objective

Implement the View layer. Create the text template and rendering logic that transforms the raw data from `DashboardService` into the user-facing text message.

## Files

- `src/templates/dashboard.txt` (New)
- `src/lib/text_formatter.py` (New/Modify) or `src/services/dashboard_service.py`
- `tests/unit/test_presentation.py` (New)

## Detailed Guidance

### T008: Create Template

**Purpose**: Define the visual layout.

1. Create `src/templates/dashboard.txt` (or `.j2`).
2. Content should iterate over employees:

   ```jinja2
   Employees management:
   {% for emp in employees %}
   {{ emp.name }}'s schedule:
   {% for job in emp.jobs %}
   {{ job.scheduled_at.strftime('%H:%M') }} - {{ job.description }} #{{ job.id }} ({{ job.location }})
   {% endfor %}
   {% endfor %}

   Unscheduled jobs:
   {% for job in unscheduled %}
   {{ job.description }} #{{ job.id }}
   {% endfor %}
   ```

3. Use Jinja2 syntax.

### T009: Implement Renderer

**Purpose**: Bind data to template.

1. In `src/lib/text_formatter.py` (or similar utility), add `render_employee_dashboard(context: dict) -> str`.
2. Ensure it loads the template environment using `jinja2.Environment`.
3. The context should match what the template expects.

### T010: Presentation Tests

**Purpose**: Ensure the output looks exactly as specified.

1. Create `tests/unit/test_presentation.py`.
2. Mock up a list of employees and jobs.
3. Call the renderer.
4. Assert the string output contains specific lines (e.g., "John's schedule:", "#123").
5. Verify line breaks and spacing are readable.

## Acceptance Criteria

- Dashboard renders correctly with valid data.
- Dashboard handles empty lists gracefully (e.g., "No unscheduled jobs").

## Implementation Command

`spec-kitty implement WP03 --base WP01`

## Activity Log

- 2026-01-20T18:12:33Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T18:17:21Z – Antigravity – shell_pid=3779362 – lane=for_review – Ready for review: Implemented dashboard template and renderer with unit tests.
