"""YAML questionnaire loader and processor."""

import yaml
from pathlib import Path
from typing import Any, Optional
import jsonschema
from rich.console import Console

from ..models.questionnaire_schema import (
    QuestionnaireSchema,
    QuestionnaireMetadata,
    Section,
    Question,
    Choice,
    ValidationRule,
    QuestionType,
)


class YamlQuestionnaireError(Exception):
    """Base exception for YAML questionnaire errors."""
    pass


class YamlQuestionnaireLoader:
    """Loads and validates YAML questionnaire files."""

    # JSON Schema for validating YAML structure
    YAML_SCHEMA = {
        "type": "object",
        "required": ["metadata", "sections"],
        "properties": {
            "metadata": {
                "type": "object",
                "required": ["name", "version", "description"],
                "properties": {
                    "name": {"type": "string"},
                    "version": {"type": "string"},
                    "description": {"type": "string"}
                }
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "title", "questions"],
                    "properties": {
                        "name": {"type": "string"},
                        "title": {"type": "string"},
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["id", "type", "prompt"],
                                "properties": {
                                    "id": {"type": "string"},
                                    "type": {"enum": ["choice", "boolean", "text", "multiline"]},
                                    "prompt": {"type": "string"},
                                    "choices": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "required": ["value", "label"],
                                            "properties": {
                                                "value": {"type": "string"},
                                                "label": {"type": "string"},
                                                "default": {"type": "boolean"}
                                            }
                                        }
                                    },
                                    "validation": {
                                        "type": "object",
                                        "properties": {
                                            "regex": {"type": "string"},
                                            "error_message": {"type": "string"},
                                            "min_length": {"type": "integer"},
                                            "max_length": {"type": "integer"},
                                            "required": {"type": "boolean"}
                                        }
                                    },
                                    "condition": {"type": "string"},
                                    "retry_attempts": {"type": "integer"},
                                    "optional": {"type": "boolean"},
                                    "default_value": {"type": ["string", "boolean", "null"]}
                                }
                            }
                        }
                    }
                }
            },
            "templates": {
                "type": "object",
                "patternProperties": {
                    ".*": {"type": "string"}
                }
            }
        }
    }

    def __init__(self, console: Optional[Console] = None):
        """Initialize the YAML questionnaire loader."""
        self.console = console or Console()

    def load_from_file(self, yaml_path: Path) -> QuestionnaireSchema:
        """
        Load questionnaire from YAML file.
        
        Args:
            yaml_path: Path to the YAML file.
            
        Returns:
            Parsed QuestionnaireSchema.
            
        Raises:
            YamlQuestionnaireError: If loading or validation fails.
        """
        if not yaml_path.exists():
            raise YamlQuestionnaireError(f"Questionnaire file not found: {yaml_path}")
            
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise YamlQuestionnaireError(f"Invalid YAML syntax: {e}")
        except Exception as e:
            raise YamlQuestionnaireError(f"Error reading file: {e}")
            
        return self.load_from_dict(yaml_data)

    def load_from_dict(self, yaml_data: dict[str, Any]) -> QuestionnaireSchema:
        """
        Load questionnaire from dictionary data.
        
        Args:
            yaml_data: Dictionary containing questionnaire data.
            
        Returns:
            Parsed QuestionnaireSchema.
            
        Raises:
            YamlQuestionnaireError: If validation fails.
        """
        # Validate against JSON schema
        try:
            jsonschema.validate(yaml_data, self.YAML_SCHEMA)
        except jsonschema.ValidationError as e:
            raise YamlQuestionnaireError(f"Schema validation failed: {e.message}")
            
        # Parse metadata
        metadata_data = yaml_data["metadata"]
        metadata = QuestionnaireMetadata(
            name=metadata_data["name"],
            version=metadata_data["version"],
            description=metadata_data["description"]
        )
        
        # Parse sections
        sections = []
        for section_data in yaml_data["sections"]:
            questions = []
            for question_data in section_data["questions"]:
                question = self._parse_question(question_data)
                questions.append(question)
                
            section = Section(
                name=section_data["name"],
                title=section_data["title"],
                questions=questions
            )
            sections.append(section)
            
        # Parse templates
        templates = yaml_data.get("templates", {})
        
        # Create schema
        schema = QuestionnaireSchema(
            metadata=metadata,
            sections=sections,
            templates=templates
        )
        
        # Validate schema consistency
        validation_errors = schema.validate_schema()
        if validation_errors:
            raise YamlQuestionnaireError(f"Schema validation errors: {'; '.join(validation_errors)}")
            
        return schema

    def _parse_question(self, question_data: dict[str, Any]) -> Question:
        """Parse a single question from YAML data."""
        # Parse question type
        try:
            question_type = QuestionType(question_data["type"])
        except ValueError:
            raise YamlQuestionnaireError(f"Invalid question type: {question_data['type']}")
            
        # Parse choices for choice questions
        choices = []
        if "choices" in question_data:
            for choice_data in question_data["choices"]:
                choice = Choice(
                    value=choice_data["value"],
                    label=choice_data["label"],
                    default=choice_data.get("default", False)
                )
                choices.append(choice)
                
        # Parse validation rules
        validation = None
        if "validation" in question_data:
            validation_data = question_data["validation"]
            validation = ValidationRule(
                regex=validation_data.get("regex"),
                error_message=validation_data.get("error_message"),
                min_length=validation_data.get("min_length"),
                max_length=validation_data.get("max_length"),
                required=validation_data.get("required", True)
            )
            
        # Create question
        question = Question(
            id=question_data["id"],
            type=question_type,
            prompt=question_data["prompt"],
            choices=choices,
            validation=validation,
            condition=question_data.get("condition"),
            retry_attempts=question_data.get("retry_attempts", 3),
            optional=question_data.get("optional", False),
            default_value=question_data.get("default_value")
        )
        
        return question

    def validate_questionnaire_file(self, yaml_path: Path) -> tuple[bool, list[str]]:
        """
        Validate a questionnaire file without loading it completely.
        
        Args:
            yaml_path: Path to the YAML file.
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            schema = self.load_from_file(yaml_path)
            self.console.print(f"[green]✓ Questionnaire '{schema.metadata.name}' is valid[/green]")
            return True, []
        except YamlQuestionnaireError as e:
            errors.append(str(e))
            self.console.print(f"[red]✗ Validation failed: {e}[/red]")
            return False, errors
        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            self.console.print(f"[red]✗ Unexpected error: {e}[/red]")
            return False, errors