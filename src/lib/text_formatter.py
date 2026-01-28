import os
from jinja2 import Environment, FileSystemLoader

def render_employee_dashboard(context: dict) -> str:
    """
    Renders the employee dashboard text message using a Jinja2 template.
    
    Args:
        context: A dictionary containing 'employees' and 'UNSCHEDULED' jobs.
                 Expected structure:
                 {
                     'employees': [
                         {
                             'name': str,
                             'jobs': [
                                 {
                                     'scheduled_at': datetime,
                                     'description': str,
                                     'id': int,
                                     'location': str
                                 }, ...
                             ]
                         }, ...
                     ],
                     'UNSCHEDULED': [
                         {
                             'description': str,
                             'id': int
                         }, ...
                     ]
                 }
                 
    Returns:
        str: The rendered text message.
    """
    # src/lib/text_formatter.py -> src/templates
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_src_dir = os.path.dirname(current_dir) # src/
    template_dir = os.path.join(project_src_dir, 'templates')
    
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=False)
    template = env.get_template('dashboard.j2')
    
    return template.render(context)
