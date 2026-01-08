"""Jinja2 template engine for generating steering documents."""

from pathlib import Path
from typing import Any, Optional
from datetime import datetime
import jinja2
from rich.console import Console

from ..models.questionnaire_schema import QuestionnaireSchema


class TemplateEngineError(Exception):
    """Base exception for template engine errors."""
    pass


class TemplateEngine:
    """Jinja2-based template engine for generating steering documents."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the template engine."""
        self.console = console or Console()
        self.env = None

    def setup_environment(self, template_dirs: list[Path]) -> None:
        """
        Set up Jinja2 environment with template directories.
        
        Args:
            template_dirs: List of directories to search for templates.
        """
        # Convert Path objects to strings for Jinja2
        template_paths = [str(path) for path in template_dirs if path.exists()]
        
        if not template_paths:
            raise TemplateEngineError("No valid template directories found")
            
        # Create Jinja2 environment
        loader = jinja2.FileSystemLoader(template_paths)
        self.env = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['datetime'] = self._format_datetime
        self.env.filters['yesno'] = self._format_boolean

    def render_template(
        self, 
        template_name: str, 
        answers: dict[str, Any],
        schema: QuestionnaireSchema,
        project_path: Path
    ) -> str:
        """
        Render a template with the given answers.
        
        Args:
            template_name: Name of the template file.
            answers: Dictionary of questionnaire answers.
            schema: The questionnaire schema.
            project_path: Path to the project directory.
            
        Returns:
            Rendered template content.
            
        Raises:
            TemplateEngineError: If rendering fails.
        """
        if not self.env:
            raise TemplateEngineError("Template environment not set up. Call setup_environment() first.")
            
        try:
            template = self.env.get_template(template_name)
        except jinja2.TemplateNotFound:
            raise TemplateEngineError(f"Template not found: {template_name}")
        except jinja2.TemplateSyntaxError as e:
            raise TemplateEngineError(f"Template syntax error in {template_name}: {e}")
            
        # Prepare template context
        context = {
            'answers': answers,
            'metadata': schema.metadata,
            'project_path': project_path,
            'creation_date': datetime.now().strftime('%Y-%m-%d'),
            'creation_datetime': datetime.now(),
        }
        
        # Add helper functions to context
        context.update({
            'get_answer': lambda key, default=None: answers.get(key, default),
            'has_answer': lambda key: key in answers and answers[key],
            'is_true': lambda key: answers.get(key, False) is True,
            'is_false': lambda key: answers.get(key, True) is False,
        })
        
        try:
            return template.render(**context)
        except jinja2.TemplateRuntimeError as e:
            raise TemplateEngineError(f"Template rendering error in {template_name}: {e}")
        except Exception as e:
            raise TemplateEngineError(f"Unexpected error rendering {template_name}: {e}")

    def render_to_file(
        self,
        template_name: str,
        output_path: Path,
        answers: dict[str, Any],
        schema: QuestionnaireSchema,
        project_path: Path
    ) -> None:
        """
        Render a template and write it to a file.
        
        Args:
            template_name: Name of the template file.
            output_path: Path to write the rendered content.
            answers: Dictionary of questionnaire answers.
            schema: The questionnaire schema.
            project_path: Path to the project directory.
            
        Raises:
            TemplateEngineError: If rendering or writing fails.
        """
        content = self.render_template(template_name, answers, schema, project_path)
        
        try:
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.console.print(f"[green]✓ Generated {output_path.name}[/green]")
            
        except OSError as e:
            raise TemplateEngineError(f"Failed to write file {output_path}: {e}")

    def list_available_templates(self, template_dirs: list[Path]) -> list[str]:
        """
        List all available template files.
        
        Args:
            template_dirs: List of directories to search for templates.
            
        Returns:
            List of template file names.
        """
        templates = []
        
        for template_dir in template_dirs:
            if not template_dir.exists():
                continue
                
            for template_file in template_dir.glob("*.j2"):
                templates.append(template_file.name)
                
        return sorted(set(templates))

    def validate_template(self, template_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate a template file for syntax errors.
        
        Args:
            template_path: Path to the template file.
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                
            # Create a temporary environment to test parsing
            env = jinja2.Environment()
            env.parse(template_content)
            
            return True, None
            
        except jinja2.TemplateSyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Error reading template: {e}"

    def _format_datetime(self, dt: datetime, format_string: str = '%Y-%m-%d %H:%M:%S') -> str:
        """Jinja2 filter to format datetime objects."""
        if isinstance(dt, datetime):
            return dt.strftime(format_string)
        return str(dt)

    def _format_boolean(self, value: Any, true_text: str = 'Yes', false_text: str = 'No') -> str:
        """Jinja2 filter to format boolean values as Yes/No."""
        return true_text if value else false_text