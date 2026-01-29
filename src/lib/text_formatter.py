import os
from jinja2 import Environment, FileSystemLoader

def render_schedule_report(context: dict) -> str:
    """
    Renders the employee schedule report using a Jinja2 template.
    
    Args:
        context: A dictionary containing 'employees', 'UNSCHEDULED', and 'date_str'.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_src_dir = os.path.dirname(current_dir) # src/
    template_dir = os.path.join(project_src_dir, 'templates')
    
    # Ensure template_dir exists, though it should
    if not os.path.exists(template_dir):
         return "Error: Template directory not found."

    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    
    try:
        template = env.get_template('schedule_report.j2')
        return template.render(context)
    except Exception as e:
        return f"Error rendering schedule report: {str(e)}"
