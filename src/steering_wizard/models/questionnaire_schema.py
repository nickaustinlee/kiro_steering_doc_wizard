"""YAML questionnaire schema models and validation."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import re


class QuestionType(Enum):
    """Supported question types."""
    CHOICE = "choice"
    BOOLEAN = "boolean"
    TEXT = "text"
    MULTILINE = "multiline"


@dataclass
class ValidationRule:
    """Validation rules for question responses."""
    regex: Optional[str] = None
    error_message: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    required: bool = True

    def validate(self, value: str) -> tuple[bool, Optional[str]]:
        """
        Validate a value against this rule.
        
        Args:
            value: The value to validate.
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value and self.required:
            return False, "This field is required"
            
        if not value and not self.required:
            return True, None
            
        if self.min_length and len(value) < self.min_length:
            return False, f"Minimum length is {self.min_length} characters"
            
        if self.max_length and len(value) > self.max_length:
            return False, f"Maximum length is {self.max_length} characters"
            
        if self.regex:
            if not re.match(self.regex, value):
                return False, self.error_message or "Invalid format"
                
        return True, None


@dataclass
class Choice:
    """A choice option for choice-type questions."""
    value: str
    label: str
    default: bool = False


@dataclass
class Question:
    """A single question in the questionnaire."""
    id: str
    type: QuestionType
    prompt: str
    choices: List[Choice] = field(default_factory=list)
    validation: Optional[ValidationRule] = None
    condition: Optional[str] = None  # Simple condition like "use_black == true"
    retry_attempts: int = 3
    optional: bool = False
    default_value: Optional[Union[str, bool]] = None

    def evaluate_condition(self, answers: Dict[str, Any]) -> bool:
        """
        Evaluate if this question should be asked based on previous answers.
        
        Args:
            answers: Dictionary of previous answers.
            
        Returns:
            True if question should be asked, False otherwise.
        """
        if not self.condition:
            return True
            
        # Simple condition evaluation (can be extended)
        # Format: "variable_name == 'value'" or "variable_name == true"
        try:
            # Parse condition like "use_black == true" or "local_testing == 'docker'"
            parts = self.condition.split(" == ")
            if len(parts) != 2:
                return True  # Invalid condition, show question
                
            var_name = parts[0].strip()
            expected_value = parts[1].strip()
            
            if var_name not in answers:
                return False  # Variable not set yet
                
            actual_value = answers[var_name]
            
            # Handle boolean values
            if expected_value.lower() in ["true", "false"]:
                expected_bool = expected_value.lower() == "true"
                return actual_value == expected_bool
                
            # Handle string values (remove quotes if present)
            expected_str = expected_value.strip("'\"")
            return str(actual_value) == expected_str
            
        except Exception:
            return True  # On error, show the question


@dataclass
class Section:
    """A section containing related questions."""
    name: str
    title: str
    questions: List[Question] = field(default_factory=list)


@dataclass
class QuestionnaireMetadata:
    """Metadata about the questionnaire."""
    name: str
    version: str
    description: str


@dataclass
class QuestionnaireSchema:
    """Complete questionnaire schema."""
    metadata: QuestionnaireMetadata
    sections: List[Section] = field(default_factory=list)
    templates: Dict[str, str] = field(default_factory=dict)

    def get_all_questions(self) -> List[Question]:
        """Get all questions from all sections."""
        questions = []
        for section in self.sections:
            questions.extend(section.questions)
        return questions

    def get_question_by_id(self, question_id: str) -> Optional[Question]:
        """Get a question by its ID."""
        for question in self.get_all_questions():
            if question.id == question_id:
                return question
        return None

    def validate_schema(self) -> List[str]:
        """
        Validate the questionnaire schema for consistency.
        
        Returns:
            List of validation errors (empty if valid).
        """
        errors = []
        
        # Check for duplicate question IDs
        question_ids = [q.id for q in self.get_all_questions()]
        if len(question_ids) != len(set(question_ids)):
            duplicates = [qid for qid in set(question_ids) if question_ids.count(qid) > 1]
            errors.append(f"Duplicate question IDs found: {duplicates}")
            
        # Validate conditions reference existing questions
        for question in self.get_all_questions():
            if question.condition:
                try:
                    var_name = question.condition.split(" == ")[0].strip()
                    if not any(q.id == var_name for q in self.get_all_questions()):
                        errors.append(f"Question '{question.id}' references unknown variable '{var_name}' in condition")
                except Exception:
                    errors.append(f"Question '{question.id}' has invalid condition format: {question.condition}")
                    
        # Validate choice questions have choices
        for question in self.get_all_questions():
            if question.type == QuestionType.CHOICE and not question.choices:
                errors.append(f"Choice question '{question.id}' has no choices defined")
                
        return errors