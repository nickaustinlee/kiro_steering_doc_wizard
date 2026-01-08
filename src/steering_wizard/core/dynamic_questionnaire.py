"""Dynamic questionnaire engine that processes YAML-defined questions."""

from pathlib import Path
from typing import Any, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from ..models.questionnaire_schema import (
    QuestionnaireSchema,
    Question,
    QuestionType,
    Choice,
)
from .yaml_questionnaire import YamlQuestionnaireLoader


class DynamicQuestionnaireEngine:
    """Processes YAML-defined questionnaires dynamically."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the dynamic questionnaire engine."""
        self.console = console or Console()
        self.loader = YamlQuestionnaireLoader(console)

    def load_questionnaire(self, questionnaire_path: Path) -> QuestionnaireSchema:
        """
        Load questionnaire from YAML file.
        
        Args:
            questionnaire_path: Path to the questionnaire YAML file.
            
        Returns:
            Loaded QuestionnaireSchema.
        """
        return self.loader.load_from_file(questionnaire_path)

    def collect_answers(
        self, 
        schema: QuestionnaireSchema, 
        project_path: Path
    ) -> dict[str, Any]:
        """
        Collect answers from user based on the questionnaire schema.
        
        Args:
            schema: The questionnaire schema to process.
            project_path: Path to the project directory.
            
        Returns:
            Dictionary of collected answers.
        """
        # Display welcome message
        self.console.print(
            Panel.fit(
                f"[bold blue]{schema.metadata.name}[/bold blue]\n"
                f"[dim]{schema.metadata.description}[/dim]",
                border_style="blue",
            )
        )

        self.console.print(f"\n[bold]Project Path:[/bold] {project_path}")
        self.console.print()

        answers = {}

        # Process each section
        for section in schema.sections:
            self.console.print(f"[bold cyan]{section.title}[/bold cyan]")
            
            # Process questions in this section
            for question in section.questions:
                # Check if question should be asked based on conditions
                if not question.evaluate_condition(answers):
                    continue
                    
                # Ask the question and collect answer
                answer = self._ask_question(question, answers)
                if answer is not None:
                    answers[question.id] = answer
                    
            self.console.print()  # Add spacing between sections

        return answers

    def _ask_question(self, question: Question, current_answers: dict[str, Any]) -> Any:
        """
        Ask a single question and return the answer.
        
        Args:
            question: The question to ask.
            current_answers: Current answers (for context).
            
        Returns:
            The user's answer, or None if skipped.
        """
        if question.type == QuestionType.CHOICE:
            return self._ask_choice_question(question)
        elif question.type == QuestionType.BOOLEAN:
            return self._ask_boolean_question(question)
        elif question.type == QuestionType.TEXT:
            return self._ask_text_question(question)
        elif question.type == QuestionType.MULTILINE:
            return self._ask_multiline_question(question)
        else:
            self.console.print(f"[red]Unknown question type: {question.type}[/red]")
            return None

    def _ask_choice_question(self, question: Question) -> Optional[str]:
        """Ask a multiple choice question."""
        self.console.print(f"\n{question.prompt}:")
        
        # Display choices
        choice_map = {}
        default_choice = None
        
        for i, choice in enumerate(question.choices, 1):
            choice_map[str(i)] = choice.value
            marker = " (default)" if choice.default else ""
            self.console.print(f"  {i}. {choice.label}{marker}")
            if choice.default:
                default_choice = str(i)
        
        # Get user choice
        valid_choices = list(choice_map.keys())
        choice = Prompt.ask(
            "Select your choice",
            choices=valid_choices,
            default=default_choice
        )
        
        return choice_map[choice]

    def _ask_boolean_question(self, question: Question) -> bool:
        """Ask a yes/no question."""
        default_value = question.default_value if question.default_value is not None else False
        return Confirm.ask(question.prompt, default=default_value)

    def _ask_text_question(self, question: Question) -> Optional[str]:
        """Ask a text input question."""
        for attempt in range(question.retry_attempts):
            try:
                answer = Prompt.ask(
                    question.prompt,
                    default=question.default_value or ""
                )
                
                # Skip validation if empty and optional
                if not answer and question.optional:
                    return None
                    
                # Validate answer
                if question.validation:
                    is_valid, error_message = question.validation.validate(answer)
                    if not is_valid:
                        self.console.print(f"[red]{error_message}[/red]")
                        if attempt < question.retry_attempts - 1:
                            self.console.print(f"Attempts remaining: {question.retry_attempts - attempt - 1}")
                            continue
                        else:
                            self.console.print("[yellow]Maximum attempts reached. Skipping question.[/yellow]")
                            return None
                
                return answer
                
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Input cancelled by user.[/yellow]")
                if question.optional:
                    return None
                if Confirm.ask("Skip this question?", default=True):
                    return None
                continue
            except Exception as e:
                self.console.print(f"[red]Error during input: {e}[/red]")
                if attempt < question.retry_attempts - 1:
                    self.console.print("Please try again.")
                    continue
                else:
                    self.console.print("[yellow]Skipping question due to repeated errors.[/yellow]")
                    return None
        
        return None

    def _ask_multiline_question(self, question: Question) -> Optional[str]:
        """Ask a multiline text input question."""
        self.console.print(f"\n[dim]{question.prompt}:[/dim]")

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
            if question.optional:
                return None
            self.console.print("[yellow]Skipping multiline input.[/yellow]")
            return None

        # Remove trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()

        if not lines:
            return None

        return "\n".join(lines)

    def display_answers_summary(self, answers: dict[str, Any], schema: QuestionnaireSchema) -> None:
        """
        Display a summary of collected answers.
        
        Args:
            answers: Dictionary of collected answers.
            schema: The questionnaire schema.
        """
        self.console.print("\n[bold cyan]Configuration Summary[/bold cyan]")

        for section in schema.sections:
            section_has_answers = any(
                question.id in answers 
                for question in section.questions
            )
            
            if not section_has_answers:
                continue
                
            self.console.print(f"\n[bold]{section.title}:[/bold]")
            
            for question in section.questions:
                if question.id not in answers:
                    continue
                    
                answer = answers[question.id]
                
                # Format the answer for display
                if question.type == QuestionType.BOOLEAN:
                    display_answer = "Yes" if answer else "No"
                elif question.type == QuestionType.CHOICE:
                    # Find the label for the choice
                    choice_label = next(
                        (choice.label for choice in question.choices if choice.value == answer),
                        answer
                    )
                    display_answer = choice_label
                elif question.type == QuestionType.MULTILINE and answer:
                    display_answer = f"Yes ({len(answer)} characters)"
                else:
                    display_answer = str(answer) if answer else "Not specified"
                
                # Use a more readable prompt for display
                display_prompt = question.prompt.replace("Do you want to", "").replace("?", "").strip()
                if not display_prompt:
                    display_prompt = question.id.replace("_", " ").title()
                    
                self.console.print(f"  {display_prompt}: {display_answer}")

    def validate_answers(self, answers: dict[str, Any], schema: QuestionnaireSchema) -> bool:
        """
        Validate collected answers against the schema.
        
        Args:
            answers: Dictionary of collected answers.
            schema: The questionnaire schema.
            
        Returns:
            True if all answers are valid, False otherwise.
        """
        validation_errors = []

        for question in schema.get_all_questions():
            if question.id not in answers:
                if not question.optional and question.evaluate_condition(answers):
                    validation_errors.append(f"Required question '{question.id}' was not answered")
                continue
                
            answer = answers[question.id]
            
            # Validate text answers
            if question.type in [QuestionType.TEXT, QuestionType.MULTILINE] and question.validation:
                is_valid, error_message = question.validation.validate(str(answer))
                if not is_valid:
                    validation_errors.append(f"Question '{question.id}': {error_message}")

        if validation_errors:
            self.console.print("\n[red]Validation Errors:[/red]")
            for error in validation_errors:
                self.console.print(f"  • {error}")
            return False

        self.console.print("\n[green]✓ All answers validated successfully![/green]")
        return True