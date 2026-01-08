"""Interactive questionnaire engine for collecting user preferences."""

import re
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text

from ..models.config import (
    TestingConfig,
    GitHubConfig,
    FormattingConfig,
    VirtualizationConfig,
    ProjectConfiguration,
)


class QuestionnaireEngine:
    """Manages interactive user prompts and input validation."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the questionnaire engine."""
        self.console = console or Console()

    def collect_configuration(self, project_path: Path) -> ProjectConfiguration:
        """
        Collect complete project configuration through interactive prompts.

        Args:
            project_path: Path to the project directory.

        Returns:
            Complete ProjectConfiguration with all user preferences.

        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
        """
        self.console.print(
            Panel.fit(
                "[bold blue]Steering Docs Wizard[/bold blue]\n"
                "Let's configure your project's development guidelines!",
                border_style="blue",
            )
        )

        # Display project path
        self.console.print(f"\n[bold]Project Path:[/bold] {project_path}")
        self.console.print()

        # Collect each configuration section
        testing = self.prompt_testing_preferences()
        github = self.prompt_github_info()
        formatting = self.prompt_formatting_rules()
        virtualization = self.prompt_virtualization_preferences()

        # Create and return complete configuration
        return ProjectConfiguration.create_with_current_date(
            testing=testing,
            github=github,
            formatting=formatting,
            virtualization=virtualization,
            project_path=project_path,
        )

    def prompt_testing_preferences(self) -> TestingConfig:
        """
        Prompt for local testing preferences.

        Returns:
            TestingConfig with user's testing preferences.

        Requirements: 2.1
        """
        self.console.print("[bold cyan]Testing Configuration[/bold cyan]")

        # Local testing preference
        testing_options = {
            "1": ("docker", "Docker containers"),
            "2": ("pytest", "Pytest only"),
            "3": ("both", "Both Docker and Pytest"),
            "4": ("none", "No specific testing preference"),
        }

        self.console.print("\nLocal testing preferences:")
        for key, (_, description) in testing_options.items():
            self.console.print(f"  {key}. {description}")

        while True:
            choice = Prompt.ask(
                "Select your local testing preference",
                choices=list(testing_options.keys()),
                default="2",
            )
            local_testing = testing_options[choice][0]
            break

        # Docker usage
        use_docker = local_testing in ["docker", "both"]
        if local_testing == "none":
            use_docker = Confirm.ask(
                "Do you want to include Docker support?", default=False
            )

        # Pytest usage
        use_pytest = local_testing in ["pytest", "both"]
        if local_testing == "none":
            use_pytest = Confirm.ask(
                "Do you want to include Pytest support?", default=True
            )

        return TestingConfig(
            local_testing=local_testing, use_docker=use_docker, use_pytest=use_pytest
        )

    def prompt_github_info(self) -> GitHubConfig:
        """
        Prompt for GitHub repository information.

        Returns:
            GitHubConfig with user's GitHub preferences.

        Requirements: 2.2, 2.3
        """
        self.console.print("\n[bold cyan]GitHub Configuration[/bold cyan]")

        # GitHub repository URL
        repository_url = None
        if Confirm.ask(
            "Do you have a GitHub repository for this project?", default=False
        ):
            repository_url = self._prompt_github_url()

        # GitHub Actions
        use_github_actions = False
        if repository_url:
            use_github_actions = Confirm.ask(
                "Do you want to include GitHub Actions testing configuration?",
                default=True,
            )

        return GitHubConfig(
            repository_url=repository_url, use_github_actions=use_github_actions
        )

    def _prompt_github_url(self) -> Optional[str]:
        """
        Prompt for GitHub URL with validation and re-prompting.

        Returns:
            Valid GitHub URL or None if user chooses to skip.

        Requirements: 2.2, 5.2
        """
        github_pattern = r"^https://github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?$"
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                url = Prompt.ask(
                    "Enter your GitHub repository URL (e.g., https://github.com/user/repo)",
                    default="",
                )

                if not url:
                    if Confirm.ask("Skip GitHub repository configuration?", default=True):
                        return None
                    continue

                if re.match(github_pattern, url):
                    return url

                self.console.print(
                    f"[red]Invalid GitHub URL format. Please use: https://github.com/username/repository[/red]"
                )

                if attempt < max_attempts - 1:
                    self.console.print(f"Attempts remaining: {max_attempts - attempt - 1}")
                else:
                    self.console.print(
                        "[yellow]Maximum attempts reached. Skipping GitHub configuration.[/yellow]"
                    )
                    return None
                    
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Input cancelled by user.[/yellow]")
                if Confirm.ask("Skip GitHub repository configuration?", default=True):
                    return None
                continue
            except Exception as e:
                self.console.print(f"[red]Error during input: {e}[/red]")
                if attempt < max_attempts - 1:
                    self.console.print("Please try again.")
                    continue
                else:
                    self.console.print("[yellow]Skipping GitHub configuration due to repeated errors.[/yellow]")
                    return None

        return None

    def prompt_formatting_rules(self) -> FormattingConfig:
        """
        Prompt for code formatting preferences.

        Returns:
            FormattingConfig with user's formatting preferences.

        Requirements: 2.4, 2.5
        """
        self.console.print("\n[bold cyan]Code Formatting Configuration[/bold cyan]")

        # Black formatter
        use_black = Confirm.ask(
            "Do you want to use Black code formatter?", default=True
        )

        # Google style guide
        use_google_style = Confirm.ask(
            "Do you want to follow Google Python style guide?", default=True
        )

        # Custom formatting rules
        custom_rules = None
        if Confirm.ask("Do you have custom formatting rules to add?", default=False):
            custom_rules = self._prompt_custom_formatting_rules()

        return FormattingConfig(
            use_black=use_black,
            use_google_style=use_google_style,
            custom_rules=custom_rules,
        )

    def _prompt_custom_formatting_rules(self) -> Optional[str]:
        """
        Prompt for custom formatting rules with free-form text input.

        Returns:
            Custom formatting rules text or None if empty.

        Requirements: 2.5
        """
        self.console.print(
            "\n[dim]Enter your custom formatting rules (press Enter twice to finish):[/dim]"
        )

        lines = []
        empty_line_count = 0

        try:
            while True:
                try:
                    line = input()
                    if not line.strip():
                        empty_line_count += 1
                        if empty_line_count >= 2:
                            break
                    else:
                        empty_line_count = 0
                    lines.append(line)
                except (EOFError, KeyboardInterrupt):
                    break
        except Exception as e:
            self.console.print(f"[red]Error during input: {e}[/red]")
            self.console.print("[yellow]Skipping custom formatting rules.[/yellow]")
            return None

        # Remove trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()

        if not lines:
            return None

        return "\n".join(lines)

    def prompt_virtualization_preferences(self) -> VirtualizationConfig:
        """
        Prompt for virtualization and environment preferences.

        Returns:
            VirtualizationConfig with user's virtualization preferences.

        Requirements: 2.6
        """
        self.console.print("\n[bold cyan]Virtualization Configuration[/bold cyan]")

        # Virtualization preference
        virt_options = {
            "1": ("venv", "Python venv (built-in virtual environments)"),
            "2": ("poetry", "Poetry (dependency management and packaging)"),
            "3": ("poetry_with_venv_docs", "Poetry with venv documentation"),
        }

        self.console.print("\nVirtualization preferences:")
        for key, (_, description) in virt_options.items():
            self.console.print(f"  {key}. {description}")

        choice = Prompt.ask(
            "Select your virtualization preference",
            choices=list(virt_options.keys()),
            default="2",
        )
        preference = virt_options[choice][0]

        # Include venv documentation
        include_venv_docs = preference == "poetry_with_venv_docs"
        if preference in ["venv", "poetry"]:
            include_venv_docs = Confirm.ask(
                "Do you want to include venv documentation in the guidelines?",
                default=preference == "venv",
            )

        return VirtualizationConfig(
            preference=preference, include_venv_docs=include_venv_docs
        )

    def validate_all_responses(self, config: ProjectConfiguration) -> bool:
        """
        Validate all collected responses before proceeding.

        Args:
            config: Complete project configuration to validate.

        Returns:
            True if all responses are valid, False otherwise.

        Requirements: 2.7
        """
        validation_results = []

        # Validate each configuration section
        if not config.testing.validate():
            validation_results.append("Testing configuration is invalid")

        if not config.github.validate():
            validation_results.append("GitHub configuration is invalid")

        if not config.formatting.validate():
            validation_results.append("Formatting configuration is invalid")

        if not config.virtualization.validate():
            validation_results.append("Virtualization configuration is invalid")

        if not config.validate():
            validation_results.append("Overall project configuration is invalid")

        # Display validation results
        if validation_results:
            self.console.print("\n[red]Validation Errors:[/red]")
            for error in validation_results:
                self.console.print(f"  • {error}")
            return False

        # Display successful validation
        self.console.print("\n[green]✓ All responses validated successfully![/green]")
        return True

    def display_configuration_summary(self, config: ProjectConfiguration) -> None:
        """
        Display a summary of the collected configuration.

        Args:
            config: Complete project configuration to display.
        """
        self.console.print("\n[bold cyan]Configuration Summary[/bold cyan]")

        # Testing configuration
        self.console.print(f"\n[bold]Testing:[/bold]")
        self.console.print(f"  Local testing: {config.testing.local_testing}")
        self.console.print(
            f"  Docker support: {'Yes' if config.testing.use_docker else 'No'}"
        )
        self.console.print(
            f"  Pytest support: {'Yes' if config.testing.use_pytest else 'No'}"
        )

        # GitHub configuration
        self.console.print(f"\n[bold]GitHub:[/bold]")
        if config.github.repository_url:
            self.console.print(f"  Repository: {config.github.repository_url}")
            self.console.print(
                f"  GitHub Actions: {'Yes' if config.github.use_github_actions else 'No'}"
            )
        else:
            self.console.print("  No GitHub repository configured")

        # Formatting configuration
        self.console.print(f"\n[bold]Formatting:[/bold]")
        self.console.print(
            f"  Black formatter: {'Yes' if config.formatting.use_black else 'No'}"
        )
        self.console.print(
            f"  Google style guide: {'Yes' if config.formatting.use_google_style else 'No'}"
        )
        if config.formatting.custom_rules:
            self.console.print(
                f"  Custom rules: Yes ({len(config.formatting.custom_rules)} characters)"
            )
        else:
            self.console.print("  Custom rules: No")

        # Virtualization configuration
        self.console.print(f"\n[bold]Virtualization:[/bold]")
        self.console.print(f"  Preference: {config.virtualization.preference}")
        self.console.print(
            f"  Include venv docs: {'Yes' if config.virtualization.include_venv_docs else 'No'}"
        )

        self.console.print(f"\n[bold]Project Path:[/bold] {config.project_path}")
        self.console.print(f"[bold]Creation Date:[/bold] {config.creation_date}")
