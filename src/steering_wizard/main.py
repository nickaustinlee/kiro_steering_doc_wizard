"""Main CLI interface for the Steering Docs Wizard."""

import sys
from pathlib import Path
from typing import Optional, Any, Dict

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from . import __version__
from .core.project_finder import ProjectFinder, ProjectFinderError, PermissionError
from .core.questionnaire import QuestionnaireEngine
from .core.document_generator import DocumentGenerator, DocumentGeneratorError, FileOverwriteError
from .core.dynamic_questionnaire import DynamicQuestionnaireEngine
from .core.template_engine import TemplateEngine, TemplateEngineError
from .core.yaml_questionnaire import YamlQuestionnaireLoader, YamlQuestionnaireError

# Global console for consistent output formatting
console = Console()


@click.command()
@click.option(
    "--target-dir",
    "-t",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path),
    help="Target project directory (defaults to current directory)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what files would be created without actually creating them",
)
@click.option(
    "--questionnaire",
    "-q",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    help="Path to custom questionnaire YAML file",
)
@click.option(
    "--list-templates",
    is_flag=True,
    help="List available templates and exit",
)
@click.option(
    "--validate-questionnaire",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path),
    help="Validate a questionnaire YAML file and exit",
)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="Show version information and exit",
)
def main(
    target_dir: Optional[Path],
    dry_run: bool,
    questionnaire: Optional[Path],
    list_templates: bool,
    validate_questionnaire: Optional[Path],
    version: bool,
) -> None:
    """
    Create standardized steering documents for Kiro development projects.
    
    This wizard guides you through configuring your project's development
    preferences and generates appropriate steering files in the .kiro/steering
    directory to guide AI development assistants.
    
    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
    """
    # Handle version option
    if version:
        console.print(f"[bold blue]Steering Docs Wizard[/bold blue] version [green]{__version__}[/green]")
        sys.exit(0)
        
    # Handle list templates option
    if list_templates:
        _list_available_templates()
        sys.exit(0)
        
    # Handle validate questionnaire option
    if validate_questionnaire:
        _validate_questionnaire_file(validate_questionnaire)
        sys.exit(0)
        
    # Run the main wizard logic
    run_wizard(target_dir, dry_run, questionnaire)


def run_wizard(target_dir: Optional[Path], dry_run: bool, questionnaire_path: Optional[Path]) -> None:
    """Run the main wizard logic."""
    document_generator = None
    
    try:
        # Display welcome message
        _display_welcome_message()
        
        # Validate target directory if provided
        _validate_target_directory(target_dir)
        
        # Initialize components
        project_finder = ProjectFinder()
        document_generator = DocumentGenerator(console)
        
        # Determine questionnaire mode
        use_yaml_questionnaire = questionnaire_path is not None
        
        if use_yaml_questionnaire:
            # Use new YAML-driven questionnaire system
            dynamic_questionnaire = DynamicQuestionnaireEngine(console)
            template_engine = TemplateEngine(console)
        else:
            # Use legacy hardcoded questionnaire system
            questionnaire = QuestionnaireEngine(console)
        
        # Step 1: Find and validate project
        console.print("\n[bold cyan]Step 1: Project Discovery[/bold cyan]")
        project_path = _find_project_directory(project_finder, target_dir)
        
        if dry_run:
            console.print(f"\n[yellow]DRY RUN MODE: No files will be created[/yellow]")
        
        # Step 2: Ensure steering directory exists
        console.print("\n[bold cyan]Step 2: Preparing Steering Directory[/bold cyan]")
        steering_path = _prepare_steering_directory(project_finder, project_path, dry_run)
        
        # Step 3: Check for existing files
        existing_files = document_generator.check_existing_files(steering_path)
        if existing_files and not dry_run:
            _display_existing_files_warning(existing_files)
        
        # Step 4: Collect configuration
        console.print("\n[bold cyan]Step 3: Configuration Collection[/bold cyan]")
        
        if use_yaml_questionnaire:
            config, schema = _collect_yaml_configuration_with_recovery(
                dynamic_questionnaire, template_engine, questionnaire_path, project_path
            )
        else:
            config = _collect_configuration_with_recovery(questionnaire, project_path)
            schema = None
        
        # Step 5: Validate configuration
        if use_yaml_questionnaire:
            if not dynamic_questionnaire.validate_answers(config, schema):
                console.print("\n[red]Configuration validation failed. Please restart the wizard.[/red]")
                _display_recovery_options()
                sys.exit(1)
        else:
            if not questionnaire.validate_all_responses(config):
                console.print("\n[red]Configuration validation failed. Please restart the wizard.[/red]")
                _display_recovery_options()
                sys.exit(1)
        
        # Step 6: Display configuration summary
        if use_yaml_questionnaire:
            dynamic_questionnaire.display_answers_summary(config, schema)
        else:
            questionnaire.display_configuration_summary(config)
        
        # Step 7: Generate documents
        console.print("\n[bold cyan]Step 4: Document Generation[/bold cyan]")
        if dry_run:
            if use_yaml_questionnaire:
                _display_yaml_dry_run_summary(config, schema, steering_path)
            else:
                _display_dry_run_summary(config, steering_path)
        else:
            if use_yaml_questionnaire:
                _generate_yaml_documents_with_recovery(template_engine, config, schema, steering_path)
            else:
                _generate_documents_with_recovery(document_generator, config, steering_path)
        
        # Step 8: Display success summary
        if use_yaml_questionnaire:
            _display_yaml_success_summary(config, schema, steering_path, dry_run)
        else:
            _display_success_summary(config, steering_path, dry_run)
        
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Wizard interrupted by user.[/yellow]")
        if document_generator:
            document_generator.cleanup_on_interruption()
        console.print("[dim]Partial files have been cleaned up.[/dim]")
        sys.exit(1)
    except (ProjectFinderError, DocumentGeneratorError, FileOverwriteError) as e:
        _handle_known_error(e, document_generator)
        sys.exit(1)
    except OSError as e:
        _handle_filesystem_error(e, document_generator)
        sys.exit(1)
    except Exception as e:
        _handle_unexpected_error(e, document_generator)
        sys.exit(1)


def _display_welcome_message() -> None:
    """
    Display welcome message with tool information.
    
    Requirements: 6.5
    """
    welcome_text = Text()
    welcome_text.append("Steering Docs Wizard", style="bold blue")
    welcome_text.append(f" v{__version__}\n", style="dim")
    welcome_text.append("Create standardized steering documents for Kiro projects", style="dim")
    
    console.print(Panel.fit(welcome_text, border_style="blue"))


def _find_project_directory(project_finder: ProjectFinder, target_dir: Optional[Path]) -> Path:
    """
    Find and validate the project directory.
    
    Args:
        project_finder: ProjectFinder instance.
        target_dir: Optional target directory specified by user.
    
    Returns:
        Path to the validated project directory.
    
    Raises:
        ProjectFinderError: If no valid project is found.
    
    Requirements: 1.1, 1.2, 1.5, 6.3
    """
    if target_dir:
        console.print(f"Searching for Kiro project in: [bold]{target_dir}[/bold]")
        project_path = project_finder.find_kiro_project(target_dir)
    else:
        console.print("Searching for Kiro project in current directory and parents...")
        project_path = project_finder.find_kiro_project()
    
    if project_path is None:
        if target_dir:
            error_msg = f"No .kiro directory found in {target_dir} or its parent directories."
        else:
            error_msg = "No .kiro directory found in current directory or parent directories."
        
        console.print(f"[yellow]{error_msg}[/yellow]")
        
        # Offer to create new project structure
        create_new = click.confirm(
            "Would you like to create a new .kiro/steering directory structure?",
            default=True
        )
        
        if not create_new:
            raise ProjectFinderError("User chose not to create new project structure")
        
        # Use target_dir or current directory for new project
        project_path = target_dir or Path.cwd()
        console.print(f"Will create new .kiro structure in: [bold]{project_path}[/bold]")
    else:
        display_path = project_finder.get_project_display_path(project_path)
        console.print(f"[green]✓ Found Kiro project at: [bold]{display_path}[/bold][/green]")
    
    return project_path


def _prepare_steering_directory(
    project_finder: ProjectFinder, project_path: Path, dry_run: bool
) -> Path:
    """
    Prepare the steering directory for document generation.
    
    Args:
        project_finder: ProjectFinder instance.
        project_path: Path to the project directory.
        dry_run: Whether this is a dry run.
    
    Returns:
        Path to the steering directory.
    
    Requirements: 1.3, 1.4, 5.1, 6.4
    """
    try:
        if dry_run:
            # In dry run mode, just validate or show what would be created
            kiro_path = project_path / ".kiro"
            steering_path = kiro_path / "steering"
            
            if not kiro_path.exists():
                console.print(f"[yellow]Would create: {kiro_path}[/yellow]")
            
            if not steering_path.exists():
                console.print(f"[yellow]Would create: {steering_path}[/yellow]")
            
            console.print(f"[green]✓ Steering directory prepared (dry run)[/green]")
            return steering_path
        else:
            steering_path = project_finder.ensure_steering_directory(project_path)
            console.print(f"[green]✓ Steering directory ready: {steering_path}[/green]")
            return steering_path
            
    except PermissionError as e:
        console.print(f"\n[red]Permission Error:[/red] {e}")
        console.print("\n[dim]Suggested solutions:[/dim]")
        console.print("  • Check directory permissions")
        console.print("  • Run with appropriate user permissions")
        console.print("  • Use sudo if necessary (be careful!)")
        raise ProjectFinderError("Cannot create steering directory due to permissions")


def _display_existing_files_warning(existing_files: list[Path]) -> None:
    """
    Display warning about existing files that might be overwritten.
    
    Args:
        existing_files: List of existing files.
    
    Requirements: 3.4, 4.5, 5.4
    """
    console.print("\n[yellow]Warning: Existing steering files found:[/yellow]")
    for file_path in existing_files:
        console.print(f"  • {file_path.name}")
    console.print("\n[dim]You will be prompted before overwriting any files.[/dim]")


def _generate_documents(
    document_generator: DocumentGenerator, config, steering_path: Path
) -> None:
    """
    Generate the steering documents.
    
    Args:
        document_generator: DocumentGenerator instance.
        config: Project configuration.
        steering_path: Path to steering directory.
    
    Requirements: 3.1, 4.1, 5.3
    """
    try:
        # Generate development guidelines
        dev_guidelines_path = steering_path / "development-guidelines.md"
        document_generator.generate_development_guidelines(config, dev_guidelines_path)
        
        # Generate LLM guidance
        llm_guidance_path = steering_path / "llm-guidance.md"
        document_generator.generate_llm_guidance(config, llm_guidance_path)
        
    except FileOverwriteError:
        console.print("\n[yellow]Document generation cancelled by user.[/yellow]")
        sys.exit(0)


def _display_dry_run_summary(config, steering_path: Path) -> None:
    """
    Display what would be created in dry run mode.
    
    Args:
        config: Project configuration.
        steering_path: Path to steering directory.
    
    Requirements: 6.4
    """
    console.print("\n[bold yellow]Dry Run Summary - Files that would be created:[/bold yellow]")
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("File", style="cyan")
    table.add_column("Description", style="dim")
    
    table.add_row(
        "development-guidelines.md",
        "Project configuration and development preferences"
    )
    table.add_row(
        "llm-guidance.md", 
        "AI assistant guidance with current date and standards"
    )
    
    console.print(table)
    console.print(f"\n[dim]Target directory: {steering_path}[/dim]")
    console.print(f"[dim]Configuration date: {config.creation_date}[/dim]")


def _display_success_summary(config, steering_path: Path, dry_run: bool) -> None:
    """
    Display comprehensive success summary with created files.
    
    Args:
        config: Project configuration.
        steering_path: Path to steering directory.
        dry_run: Whether this was a dry run.
    
    Requirements: 5.4, 5.5
    """
    if dry_run:
        console.print("\n[bold green]✓ Dry run completed successfully![/bold green]")
        console.print("[dim]No files were actually created.[/dim]")
        
        # Show what would have been created
        console.print("\n[bold]Files that would be created:[/bold]")
        potential_files = [
            ("development-guidelines.md", "Project configuration and development preferences"),
            ("llm-guidance.md", "AI assistant guidance with current date and standards")
        ]
        
        for filename, description in potential_files:
            console.print(f"  • [cyan]{filename}[/cyan] - [dim]{description}[/dim]")
            
        console.print(f"\n[bold]Target location:[/bold] {steering_path}")
    else:
        console.print("\n[bold green]✓ Steering documents created successfully![/bold green]")
        
        # Display created files with detailed information
        console.print("\n[bold]Created files:[/bold]")
        created_files = [
            steering_path / "development-guidelines.md",
            steering_path / "llm-guidance.md"
        ]
        
        total_size = 0
        files_created = 0
        
        for file_path in created_files:
            if file_path.exists():
                file_size = file_path.stat().st_size
                total_size += file_size
                files_created += 1
                
                # Format file size nicely
                if file_size < 1024:
                    size_str = f"{file_size} bytes"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                console.print(f"  • [cyan]{file_path.name}[/cyan] ([dim]{size_str}[/dim])")
            else:
                console.print(f"  • [red]{file_path.name}[/red] ([dim]creation failed[/dim])")
        
        # Display summary statistics
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  • Files created: {files_created}")
        console.print(f"  • Total size: {total_size} bytes")
        console.print(f"  • Location: {steering_path}")
        console.print(f"  • Configuration date: {config.creation_date}")
        
        # Display next steps
        console.print(f"\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("  • Review the generated steering documents")
        console.print("  • Commit the files to your version control system")
        console.print("  • Update the documents as your project evolves")
        
        if config.github.repository_url:
            console.print(f"  • Consider adding these files to your GitHub repository")
        
        # Offer to display file contents
        if files_created > 0:
            if click.confirm("\nWould you like to see the contents of the generated files?", default=False):
                _display_file_contents([f for f in created_files if f.exists()])


def _validate_target_directory(target_dir: Optional[Path]) -> None:
    """
    Validate the target directory if provided.
    
    Args:
        target_dir: Optional target directory to validate.
    
    Raises:
        ProjectFinderError: If target directory is invalid.
    
    Requirements: 5.1, 6.3
    """
    if not target_dir:
        return
        
    if not target_dir.exists():
        console.print(f"[red]Error: Target directory does not exist: {target_dir}[/red]")
        console.print("\n[dim]Suggested solutions:[/dim]")
        console.print(f"  • Create the directory: mkdir -p {target_dir}")
        console.print("  • Check the path for typos")
        console.print("  • Use an existing directory")
        raise ProjectFinderError(f"Target directory does not exist: {target_dir}")
    
    if not target_dir.is_dir():
        console.print(f"[red]Error: Target path is not a directory: {target_dir}[/red]")
        console.print("\n[dim]Suggested solutions:[/dim]")
        console.print("  • Specify a directory path, not a file")
        console.print("  • Check the path for correctness")
        raise ProjectFinderError(f"Target path is not a directory: {target_dir}")


def _collect_configuration_with_recovery(
    questionnaire: QuestionnaireEngine, project_path: Path
) -> "ProjectConfiguration":
    """
    Collect configuration with error recovery.
    
    Args:
        questionnaire: QuestionnaireEngine instance.
        project_path: Path to the project directory.
    
    Returns:
        Complete ProjectConfiguration.
    
    Requirements: 5.2
    """
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            return questionnaire.collect_configuration(project_path)
        except KeyboardInterrupt:
            raise  # Re-raise to be handled by main error handler
        except Exception as e:
            console.print(f"\n[red]Error during configuration collection: {e}[/red]")
            
            if attempt < max_attempts - 1:
                console.print(f"[yellow]Retrying... (Attempt {attempt + 2}/{max_attempts})[/yellow]")
                console.print("[dim]Press Ctrl+C to cancel[/dim]")
            else:
                console.print("[red]Maximum retry attempts reached.[/red]")
                _display_recovery_options()
                raise ProjectFinderError("Configuration collection failed after multiple attempts")


def _generate_documents_with_recovery(
    document_generator: DocumentGenerator, config, steering_path: Path
) -> None:
    """
    Generate documents with error recovery.
    
    Args:
        document_generator: DocumentGenerator instance.
        config: Project configuration.
        steering_path: Path to steering directory.
    
    Requirements: 5.3
    """
    try:
        # Generate development guidelines
        dev_guidelines_path = steering_path / "development-guidelines.md"
        document_generator.generate_development_guidelines(config, dev_guidelines_path)
        
        # Generate LLM guidance
        llm_guidance_path = steering_path / "llm-guidance.md"
        document_generator.generate_llm_guidance(config, llm_guidance_path)
        
    except FileOverwriteError:
        console.print("\n[yellow]Document generation cancelled by user.[/yellow]")
        sys.exit(0)
    except OSError as e:
        console.print(f"\n[red]File system error during document generation: {e}[/red]")
        _display_filesystem_recovery_options()
        raise DocumentGeneratorError(f"Document generation failed: {e}")


def _handle_known_error(error: Exception, document_generator: Optional[DocumentGenerator]) -> None:
    """
    Handle known application errors with helpful messages.
    
    Args:
        error: The known error that occurred.
        document_generator: Optional DocumentGenerator for cleanup.
    
    Requirements: 5.1, 5.4
    """
    console.print(f"\n[red]Error: {error}[/red]")
    
    if document_generator:
        document_generator.cleanup_on_interruption()
    
    # Provide context-specific help
    if isinstance(error, ProjectFinderError):
        console.print("\n[dim]Project discovery failed. Check your directory structure and permissions.[/dim]")
    elif isinstance(error, DocumentGeneratorError):
        console.print("\n[dim]Document generation failed. Check file permissions and disk space.[/dim]")
    elif isinstance(error, FileOverwriteError):
        console.print("\n[dim]File overwrite was cancelled. Run again to retry.[/dim]")


def _handle_filesystem_error(error: OSError, document_generator: Optional[DocumentGenerator]) -> None:
    """
    Handle filesystem-related errors with specific guidance.
    
    Args:
        error: The filesystem error that occurred.
        document_generator: Optional DocumentGenerator for cleanup.
    
    Requirements: 5.1
    """
    console.print(f"\n[red]File System Error: {error}[/red]")
    
    if document_generator:
        document_generator.cleanup_on_interruption()
    
    console.print("\n[dim]Suggested solutions:[/dim]")
    
    if error.errno == 13:  # Permission denied
        console.print("  • Check file and directory permissions")
        console.print("  • Run with appropriate user permissions")
        console.print("  • Use sudo if necessary (be careful!)")
    elif error.errno == 28:  # No space left on device
        console.print("  • Free up disk space")
        console.print("  • Choose a different target directory")
    elif error.errno == 2:  # No such file or directory
        console.print("  • Check that the target directory exists")
        console.print("  • Verify the path is correct")
    else:
        console.print("  • Check file system permissions and available space")
        console.print("  • Verify the target directory is accessible")


def _handle_unexpected_error(error: Exception, document_generator: Optional[DocumentGenerator]) -> None:
    """
    Handle unexpected errors with debugging information.
    
    Args:
        error: The unexpected error that occurred.
        document_generator: Optional DocumentGenerator for cleanup.
    
    Requirements: 5.1, 5.4
    """
    console.print(f"\n[red]Unexpected Error: {error}[/red]")
    
    if document_generator:
        document_generator.cleanup_on_interruption()
    
    console.print("\n[dim]This appears to be an unexpected error. Please report this issue.[/dim]")
    console.print(f"[dim]Error type: {type(error).__name__}[/dim]")
    console.print("[dim]Include the above information when reporting the issue.[/dim]")


def _display_recovery_options() -> None:
    """
    Display recovery options for users when errors occur.
    
    Requirements: 5.2, 5.4
    """
    console.print("\n[bold yellow]Recovery Options:[/bold yellow]")
    console.print("  • Restart the wizard and try again")
    console.print("  • Check your input for errors")
    console.print("  • Ensure you have proper permissions")
    console.print("  • Use --dry-run to test without creating files")


def _display_filesystem_recovery_options() -> None:
    """
    Display filesystem-specific recovery options.
    
    Requirements: 5.1, 5.4
    """
    console.print("\n[bold yellow]File System Recovery Options:[/bold yellow]")
    console.print("  • Check available disk space")
    console.print("  • Verify directory permissions")
    console.print("  • Try a different target directory")
    console.print("  • Close other applications that might be using files")


def _display_file_contents(file_paths: list[Path]) -> None:
    """
    Display the contents of generated files with error handling.
    
    Args:
        file_paths: List of file paths to display.
    
    Requirements: 5.5
    """
    for file_path in file_paths:
        if not file_path.exists():
            console.print(f"\n[red]File not found: {file_path.name}[/red]")
            continue
            
        console.print(f"\n[bold cyan]Contents of {file_path.name}:[/bold cyan]")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Truncate very long files for display
            if len(content) > 5000:
                content = content[:5000] + "\n\n[... content truncated for display ...]"
            
            console.print(Panel(content, border_style="dim", expand=False))
            
        except UnicodeDecodeError:
            console.print(f"[red]Error: {file_path.name} contains non-UTF-8 content[/red]")
        except OSError as e:
            console.print(f"[red]Error reading {file_path.name}: {e}[/red]")
            console.print("[dim]The file may be locked by another process[/dim]")
        except Exception as e:
            console.print(f"[red]Unexpected error reading {file_path.name}: {e}[/red]")


def _list_available_templates() -> None:
    """
    List available templates and exit.
    
    Requirements: CLI enhancement
    """
    console.print("[bold cyan]Available Templates:[/bold cyan]")
    
    # Look for templates in common locations
    template_dirs = [
        Path("templates"),
        Path.cwd() / "templates",
        Path(__file__).parent.parent / "templates",
    ]
    
    template_engine = TemplateEngine(console)
    templates = template_engine.list_available_templates(template_dirs)
    
    if templates:
        for template in templates:
            console.print(f"  • {template}")
    else:
        console.print("[dim]No templates found in standard locations[/dim]")
        console.print("\n[dim]Searched in:[/dim]")
        for template_dir in template_dirs:
            console.print(f"  • {template_dir}")


def _validate_questionnaire_file(questionnaire_path: Path) -> None:
    """
    Validate a questionnaire YAML file and exit.
    
    Args:
        questionnaire_path: Path to the questionnaire file to validate.
        
    Requirements: CLI enhancement
    """
    console.print(f"[bold cyan]Validating questionnaire:[/bold cyan] {questionnaire_path}")
    
    loader = YamlQuestionnaireLoader(console)
    is_valid, errors = loader.validate_questionnaire_file(questionnaire_path)
    
    if is_valid:
        console.print("\n[bold green]✓ Questionnaire is valid![/bold green]")
        sys.exit(0)
    else:
        console.print("\n[bold red]✗ Questionnaire validation failed![/bold red]")
        for error in errors:
            console.print(f"  • {error}")
        sys.exit(1)


def _collect_yaml_configuration_with_recovery(
    dynamic_questionnaire: DynamicQuestionnaireEngine,
    template_engine: TemplateEngine,
    questionnaire_path: Path,
    project_path: Path
) -> tuple[Dict[str, Any], Any]:
    """
    Collect configuration using YAML questionnaire with error recovery.
    
    Args:
        dynamic_questionnaire: DynamicQuestionnaireEngine instance.
        template_engine: TemplateEngine instance.
        questionnaire_path: Path to the questionnaire YAML file.
        project_path: Path to the project directory.
    
    Returns:
        Tuple of (answers_dict, questionnaire_schema).
    
    Requirements: YAML questionnaire support
    """
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            # Load questionnaire schema
            schema = dynamic_questionnaire.load_questionnaire(questionnaire_path)
            
            # Set up template engine
            template_dirs = [
                questionnaire_path.parent,  # Same directory as questionnaire
                Path("templates"),
                Path.cwd() / "templates",
                Path(__file__).parent.parent / "templates",
            ]
            template_engine.setup_environment(template_dirs)
            
            # Collect answers
            answers = dynamic_questionnaire.collect_answers(schema, project_path)
            
            return answers, schema
            
        except (YamlQuestionnaireError, TemplateEngineError) as e:
            console.print(f"\n[red]Error loading questionnaire: {e}[/red]")
            if attempt < max_attempts - 1:
                console.print(f"[yellow]Retrying... (Attempt {attempt + 2}/{max_attempts})[/yellow]")
            else:
                console.print("[red]Maximum retry attempts reached.[/red]")
                _display_recovery_options()
                raise ProjectFinderError("YAML questionnaire processing failed after multiple attempts")
        except KeyboardInterrupt:
            raise  # Re-raise to be handled by main error handler
        except Exception as e:
            console.print(f"\n[red]Error during YAML questionnaire processing: {e}[/red]")
            
            if attempt < max_attempts - 1:
                console.print(f"[yellow]Retrying... (Attempt {attempt + 2}/{max_attempts})[/yellow]")
                console.print("[dim]Press Ctrl+C to cancel[/dim]")
            else:
                console.print("[red]Maximum retry attempts reached.[/red]")
                _display_recovery_options()
                raise ProjectFinderError("YAML questionnaire processing failed after multiple attempts")


def _generate_yaml_documents_with_recovery(
    template_engine: TemplateEngine,
    answers: Dict[str, Any],
    schema: Any,
    steering_path: Path
) -> None:
    """
    Generate documents using YAML templates with error recovery.
    
    Args:
        template_engine: TemplateEngine instance.
        answers: Dictionary of questionnaire answers.
        schema: The questionnaire schema.
        steering_path: Path to steering directory.
    
    Requirements: YAML template support
    """
    try:
        # Generate documents based on template configuration
        for doc_name, template_name in schema.templates.items():
            output_path = steering_path / f"{doc_name.replace('_', '-')}.md"
            
            # Check for existing file and get user confirmation if needed
            if output_path.exists():
                if not click.confirm(f"File {output_path.name} already exists. Overwrite?", default=False):
                    console.print(f"[yellow]Skipped {output_path.name}[/yellow]")
                    continue
            
            template_engine.render_to_file(
                template_name,
                output_path,
                answers,
                schema,
                steering_path.parent.parent  # project path
            )
            
    except TemplateEngineError as e:
        console.print(f"\n[red]Template error during document generation: {e}[/red]")
        _display_filesystem_recovery_options()
        raise DocumentGeneratorError(f"YAML document generation failed: {e}")
    except OSError as e:
        console.print(f"\n[red]File system error during document generation: {e}[/red]")
        _display_filesystem_recovery_options()
        raise DocumentGeneratorError(f"Document generation failed: {e}")


def _display_yaml_dry_run_summary(answers: Dict[str, Any], schema: Any, steering_path: Path) -> None:
    """
    Display what would be created in dry run mode for YAML questionnaires.
    
    Args:
        answers: Dictionary of questionnaire answers.
        schema: The questionnaire schema.
        steering_path: Path to steering directory.
    
    Requirements: YAML dry-run support
    """
    console.print("\n[bold yellow]Dry Run Summary - Files that would be created:[/bold yellow]")
    
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("File", style="cyan")
    table.add_column("Template", style="dim")
    table.add_column("Description", style="dim")
    
    for doc_name, template_name in schema.templates.items():
        filename = f"{doc_name.replace('_', '-')}.md"
        description = f"Generated from {template_name}"
        table.add_row(filename, template_name, description)
    
    console.print(table)
    console.print(f"\n[dim]Target directory: {steering_path}[/dim]")
    console.print(f"[dim]Questionnaire: {schema.metadata.name} v{schema.metadata.version}[/dim]")


def _display_yaml_success_summary(
    answers: Dict[str, Any], schema: Any, steering_path: Path, dry_run: bool
) -> None:
    """
    Display comprehensive success summary for YAML questionnaires.
    
    Args:
        answers: Dictionary of questionnaire answers.
        schema: The questionnaire schema.
        steering_path: Path to steering directory.
        dry_run: Whether this was a dry run.
    
    Requirements: YAML success summary
    """
    if dry_run:
        console.print("\n[bold green]✓ Dry run completed successfully![/bold green]")
        console.print("[dim]No files were actually created.[/dim]")
        
        # Show what would have been created
        console.print("\n[bold]Files that would be created:[/bold]")
        for doc_name, template_name in schema.templates.items():
            filename = f"{doc_name.replace('_', '-')}.md"
            console.print(f"  • [cyan]{filename}[/cyan] - [dim]from {template_name}[/dim]")
            
        console.print(f"\n[bold]Target location:[/bold] {steering_path}")
    else:
        console.print("\n[bold green]✓ Steering documents created successfully![/bold green]")
        
        # Display created files with detailed information
        console.print("\n[bold]Created files:[/bold]")
        total_size = 0
        files_created = 0
        
        for doc_name, template_name in schema.templates.items():
            filename = f"{doc_name.replace('_', '-')}.md"
            file_path = steering_path / filename
            
            if file_path.exists():
                file_size = file_path.stat().st_size
                total_size += file_size
                files_created += 1
                
                # Format file size nicely
                if file_size < 1024:
                    size_str = f"{file_size} bytes"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                console.print(f"  • [cyan]{filename}[/cyan] ([dim]{size_str}[/dim])")
            else:
                console.print(f"  • [red]{filename}[/red] ([dim]creation failed[/dim])")
        
        # Display summary statistics
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  • Files created: {files_created}")
        console.print(f"  • Total size: {total_size} bytes")
        console.print(f"  • Location: {steering_path}")
        console.print(f"  • Questionnaire: {schema.metadata.name} v{schema.metadata.version}")
        
        # Display next steps
        console.print(f"\n[bold cyan]Next Steps:[/bold cyan]")
        console.print("  • Review the generated steering documents")
        console.print("  • Commit the files to your version control system")
        console.print("  • Update the documents as your project evolves")
        console.print("  • Customize the questionnaire YAML for future use")
        
        # Offer to display file contents
        if files_created > 0:
            created_files = []
            for doc_name in schema.templates.keys():
                filename = f"{doc_name.replace('_', '-')}.md"
                file_path = steering_path / filename
                if file_path.exists():
                    created_files.append(file_path)
                    
            if click.confirm("\nWould you like to see the contents of the generated files?", default=False):
                _display_file_contents(created_files)


if __name__ == "__main__":
    main()