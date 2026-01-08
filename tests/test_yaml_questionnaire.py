"""Tests for YAML questionnaire system components."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any
import tempfile
import yaml

from steering_wizard.core.yaml_questionnaire import YamlQuestionnaireLoader, YamlQuestionnaireError
from steering_wizard.core.dynamic_questionnaire import DynamicQuestionnaireEngine
from steering_wizard.core.template_engine import TemplateEngine, TemplateEngineError
from steering_wizard.models.questionnaire_schema import (
    QuestionnaireSchema, QuestionnaireMetadata, Section, Question, 
    QuestionType, Choice, ValidationRule
)


class TestYamlQuestionnaireLoader:
    """Test YAML questionnaire loading and validation."""
    
    def test_loader_initialization(self):
        """Test YamlQuestionnaireLoader initialization."""
        console = Mock()
        loader = YamlQuestionnaireLoader(console)
        assert loader.console == console
    
    def test_load_valid_questionnaire(self):
        """Test loading a valid questionnaire YAML file."""
        console = Mock()
        loader = YamlQuestionnaireLoader(console)
        
        # Create a temporary YAML file
        yaml_content = """
metadata:
  name: "Test Questionnaire"
  version: "1.0"
  description: "Test description"

sections:
  - name: "test_section"
    title: "Test Section"
    questions:
      - id: "test_question"
        type: "choice"
        prompt: "Test question?"
        choices:
          - value: "option1"
            label: "Option 1"
            default: true
          - value: "option2"
            label: "Option 2"

templates:
  development_guidelines: "dev-template.j2"
  llm_guidance: "llm-template.j2"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            schema = loader.load_from_file(temp_path)
            
            assert isinstance(schema, QuestionnaireSchema)
            assert schema.metadata.name == "Test Questionnaire"
            assert schema.metadata.version == "1.0"
            assert len(schema.sections) == 1
            assert len(schema.sections[0].questions) == 1
            assert schema.templates["development_guidelines"] == "dev-template.j2"
            
        finally:
            temp_path.unlink()
    
    def test_load_invalid_yaml_file(self):
        """Test loading an invalid YAML file."""
        console = Mock()
        loader = YamlQuestionnaireLoader(console)
        
        # Create invalid YAML
        invalid_yaml = "invalid: yaml: content: ["
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(YamlQuestionnaireError, match="Invalid YAML syntax"):
                loader.load_from_file(temp_path)
        finally:
            temp_path.unlink()
    
    def test_validate_questionnaire_file_valid(self):
        """Test validation of a valid questionnaire file."""
        console = Mock()
        loader = YamlQuestionnaireLoader(console)
        
        yaml_content = """
metadata:
  name: "Valid Questionnaire"
  version: "1.0"
  description: "Valid description"

sections:
  - name: "section1"
    title: "Section 1"
    questions:
      - id: "question1"
        type: "boolean"
        prompt: "Test question?"

templates:
  test_doc: "test-template.j2"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            is_valid, errors = loader.validate_questionnaire_file(temp_path)
            assert is_valid
            assert len(errors) == 0
        finally:
            temp_path.unlink()
    
    def test_validate_questionnaire_file_invalid(self):
        """Test validation of an invalid questionnaire file."""
        console = Mock()
        loader = YamlQuestionnaireLoader(console)
        
        # Missing required fields
        yaml_content = """
metadata:
  name: "Invalid Questionnaire"
  # Missing version and description

sections: []
templates: {}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            is_valid, errors = loader.validate_questionnaire_file(temp_path)
            assert not is_valid
            assert len(errors) > 0
        finally:
            temp_path.unlink()


class TestDynamicQuestionnaireEngine:
    """Test dynamic questionnaire processing."""
    
    def test_engine_initialization(self):
        """Test DynamicQuestionnaireEngine initialization."""
        console = Mock()
        engine = DynamicQuestionnaireEngine(console)
        assert engine.console == console
    
    def test_load_questionnaire_success(self):
        """Test successful questionnaire loading."""
        console = Mock()
        engine = DynamicQuestionnaireEngine(console)
        
        yaml_content = """
metadata:
  name: "Test Questionnaire"
  version: "1.0"
  description: "Test description"

sections:
  - name: "test_section"
    title: "Test Section"
    questions:
      - id: "test_question"
        type: "boolean"
        prompt: "Test question?"

templates:
  test_doc: "test-template.j2"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            schema = engine.load_questionnaire(temp_path)
            assert isinstance(schema, QuestionnaireSchema)
            assert schema.metadata.name == "Test Questionnaire"
        finally:
            temp_path.unlink()
    
    @patch('steering_wizard.core.dynamic_questionnaire.Confirm.ask')
    def test_collect_answers_boolean_question(self, mock_confirm):
        """Test collecting answers for boolean questions."""
        mock_confirm.return_value = True
        
        console = Mock()
        engine = DynamicQuestionnaireEngine(console)
        
        # Create a simple schema with boolean question
        question = Question(
            id="test_bool",
            type=QuestionType.BOOLEAN,
            prompt="Test boolean question?"
        )
        section = Section(name="test", title="Test", questions=[question])
        schema = QuestionnaireSchema(
            metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
            sections=[section]
        )
        
        answers = engine.collect_answers(schema, Path("/test/path"))
        
        assert answers["test_bool"] is True
        mock_confirm.assert_called_once()
    
    @patch('steering_wizard.core.dynamic_questionnaire.Prompt.ask')
    def test_collect_answers_choice_question(self, mock_prompt):
        """Test collecting answers for choice questions."""
        mock_prompt.return_value = "1"
        
        console = Mock()
        engine = DynamicQuestionnaireEngine(console)
        
        # Create a choice question
        choices = [
            Choice(value="option1", label="Option 1"),
            Choice(value="option2", label="Option 2")
        ]
        question = Question(
            id="test_choice",
            type=QuestionType.CHOICE,
            prompt="Test choice question?",
            choices=choices
        )
        section = Section(name="test", title="Test", questions=[question])
        schema = QuestionnaireSchema(
            metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
            sections=[section]
        )
        
        answers = engine.collect_answers(schema, Path("/test/path"))
        
        assert answers["test_choice"] == "option1"
        mock_prompt.assert_called_once()
    
    def test_validate_answers_success(self):
        """Test successful answer validation."""
        console = Mock()
        engine = DynamicQuestionnaireEngine(console)
        
        # Create schema with validation
        validation = ValidationRule(regex=r"^test.*", required=True)
        question = Question(
            id="test_text",
            type=QuestionType.TEXT,
            prompt="Test text question?",
            validation=validation
        )
        section = Section(name="test", title="Test", questions=[question])
        schema = QuestionnaireSchema(
            metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
            sections=[section]
        )
        
        answers = {"test_text": "test_value"}
        
        is_valid = engine.validate_answers(answers, schema)
        assert is_valid
    
    def test_validate_answers_failure(self):
        """Test answer validation failure."""
        console = Mock()
        engine = DynamicQuestionnaireEngine(console)
        
        # Create schema with validation that will fail
        validation = ValidationRule(regex=r"^test.*", required=True)
        question = Question(
            id="test_text",
            type=QuestionType.TEXT,
            prompt="Test text question?",
            validation=validation
        )
        section = Section(name="test", title="Test", questions=[question])
        schema = QuestionnaireSchema(
            metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
            sections=[section]
        )
        
        answers = {"test_text": "invalid_value"}  # Doesn't match regex
        
        is_valid = engine.validate_answers(answers, schema)
        assert not is_valid


class TestTemplateEngine:
    """Test template engine functionality."""
    
    def test_engine_initialization(self):
        """Test TemplateEngine initialization."""
        console = Mock()
        engine = TemplateEngine(console)
        assert engine.console == console
    
    def test_setup_environment_success(self):
        """Test successful template environment setup."""
        console = Mock()
        engine = TemplateEngine(console)
        
        # Create temporary template directory
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dirs = [Path(temp_dir)]
            
            # Create a test template
            template_path = Path(temp_dir) / "test.j2"
            template_path.write_text("Hello {{ name }}!")
            
            engine.setup_environment(template_dirs)
            
            # Verify environment is set up
            assert engine.env is not None
    
    def test_render_template_success(self):
        """Test successful template rendering."""
        console = Mock()
        engine = TemplateEngine(console)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dirs = [Path(temp_dir)]
            
            # Create a test template
            template_path = Path(temp_dir) / "test.j2"
            template_path.write_text("Hello {{ answers.name }}! Project: {{ project_path }}")
            
            engine.setup_environment(template_dirs)
            
            context = {"name": "World"}
            project_path = Path("/test/project")
            
            # Create a mock schema
            schema = QuestionnaireSchema(
                metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
                sections=[]
            )
            
            result = engine.render_template("test.j2", context, schema, project_path)
            
            assert "Hello World!" in result
            assert "Project: /test/project" in result
    
    def test_render_template_not_found(self):
        """Test template rendering with missing template."""
        console = Mock()
        engine = TemplateEngine(console)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dirs = [Path(temp_dir)]
            engine.setup_environment(template_dirs)
            
            # Create a mock schema
            schema = QuestionnaireSchema(
                metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
                sections=[]
            )
            
            with pytest.raises(TemplateEngineError, match="Template not found"):
                engine.render_template("nonexistent.j2", {}, schema, Path("/test"))
    
    def test_render_to_file_success(self):
        """Test successful template rendering to file."""
        console = Mock()
        engine = TemplateEngine(console)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dirs = [Path(temp_dir)]
            
            # Create a test template
            template_path = Path(temp_dir) / "test.j2"
            template_path.write_text("Content: {{ answers.content }}")
            
            engine.setup_environment(template_dirs)
            
            # Render to output file
            output_path = Path(temp_dir) / "output.txt"
            context = {"content": "test content"}
            
            # Create a mock schema
            schema = QuestionnaireSchema(
                metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
                sections=[]
            )
            
            engine.render_to_file("test.j2", output_path, context, schema, Path("/test"))
            
            assert output_path.exists()
            assert "Content: test content" in output_path.read_text()
    
    def test_list_available_templates(self):
        """Test listing available templates."""
        console = Mock()
        engine = TemplateEngine(console)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            template_dirs = [Path(temp_dir)]
            
            # Create test templates
            (Path(temp_dir) / "template1.j2").write_text("Template 1")
            (Path(temp_dir) / "template2.j2").write_text("Template 2")
            (Path(temp_dir) / "not_template.txt").write_text("Not a template")
            
            templates = engine.list_available_templates(template_dirs)
            
            assert "template1.j2" in templates
            assert "template2.j2" in templates
            assert "not_template.txt" not in templates


class TestQuestionnaireSchemaValidation:
    """Test questionnaire schema validation logic."""
    
    def test_validation_rule_required_field(self):
        """Test validation rule for required fields."""
        rule = ValidationRule(required=True)
        
        # Test empty value
        is_valid, error = rule.validate("")
        assert not is_valid
        assert "required" in error.lower()
        
        # Test valid value
        is_valid, error = rule.validate("test")
        assert is_valid
        assert error is None
    
    def test_validation_rule_regex(self):
        """Test validation rule with regex."""
        rule = ValidationRule(regex=r"^[a-z]+$", error_message="Only lowercase letters")
        
        # Test invalid value
        is_valid, error = rule.validate("Test123")
        assert not is_valid
        assert error == "Only lowercase letters"
        
        # Test valid value
        is_valid, error = rule.validate("test")
        assert is_valid
        assert error is None
    
    def test_validation_rule_length_constraints(self):
        """Test validation rule with length constraints."""
        rule = ValidationRule(min_length=3, max_length=10)
        
        # Test too short
        is_valid, error = rule.validate("ab")
        assert not is_valid
        assert "Minimum length" in error
        
        # Test too long
        is_valid, error = rule.validate("abcdefghijk")
        assert not is_valid
        assert "Maximum length" in error
        
        # Test valid length
        is_valid, error = rule.validate("abcde")
        assert is_valid
        assert error is None
    
    def test_question_condition_evaluation(self):
        """Test question condition evaluation."""
        question = Question(
            id="conditional_q",
            type=QuestionType.TEXT,
            prompt="Conditional question?",
            condition="use_feature == true"
        )
        
        # Test condition met
        answers = {"use_feature": True}
        assert question.evaluate_condition(answers) is True
        
        # Test condition not met
        answers = {"use_feature": False}
        assert question.evaluate_condition(answers) is False
        
        # Test missing variable
        answers = {}
        assert question.evaluate_condition(answers) is False
    
    def test_questionnaire_schema_validation(self):
        """Test questionnaire schema validation."""
        # Create schema with duplicate question IDs
        question1 = Question(id="duplicate", type=QuestionType.TEXT, prompt="Q1?")
        question2 = Question(id="duplicate", type=QuestionType.TEXT, prompt="Q2?")
        
        section = Section(name="test", title="Test", questions=[question1, question2])
        schema = QuestionnaireSchema(
            metadata=QuestionnaireMetadata(name="Test", version="1.0", description="Test"),
            sections=[section]
        )
        
        errors = schema.validate_schema()
        assert len(errors) > 0
        assert any("Duplicate question IDs" in error for error in errors)


class TestYamlQuestionnaireIntegration:
    """Integration tests for the complete YAML questionnaire system."""
    
    def test_end_to_end_yaml_processing(self):
        """Test complete YAML questionnaire processing workflow."""
        console = Mock()
        
        # Create a complete questionnaire YAML
        yaml_content = """
metadata:
  name: "Integration Test Questionnaire"
  version: "1.0"
  description: "Test questionnaire for integration testing"

sections:
  - name: "basic_config"
    title: "Basic Configuration"
    questions:
      - id: "project_name"
        type: "text"
        prompt: "What is your project name?"
        validation:
          required: true
          min_length: 1
          max_length: 50
      - id: "use_testing"
        type: "boolean"
        prompt: "Do you want to include testing?"
        default_value: true
      - id: "testing_framework"
        type: "choice"
        prompt: "Which testing framework?"
        condition: "use_testing == true"
        choices:
          - value: "pytest"
            label: "Pytest"
            default: true
          - value: "unittest"
            label: "Unittest"

templates:
  development_guidelines: "dev-guidelines.j2"
  llm_guidance: "llm-guidance.j2"
"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create questionnaire file
            questionnaire_path = Path(temp_dir) / "test-questionnaire.yaml"
            questionnaire_path.write_text(yaml_content)
            
            # Create template files
            dev_template = Path(temp_dir) / "dev-guidelines.j2"
            dev_template.write_text("Project: {{ answers.project_name }}\nTesting: {{ answers.use_testing }}")
            
            llm_template = Path(temp_dir) / "llm-guidance.j2"
            llm_template.write_text("Framework: {{ answers.testing_framework if answers.use_testing else 'None' }}")
            
            # Test the complete workflow
            loader = YamlQuestionnaireLoader(console)
            engine = DynamicQuestionnaireEngine(console)
            template_engine = TemplateEngine(console)
            
            # Load questionnaire
            schema = loader.load_from_file(questionnaire_path)
            assert schema.metadata.name == "Integration Test Questionnaire"
            
            # Setup template engine
            template_engine.setup_environment([Path(temp_dir)])
            
            # Simulate answers
            answers = {
                "project_name": "TestProject",
                "use_testing": True,
                "testing_framework": "pytest"
            }
            
            # Validate answers
            is_valid = engine.validate_answers(answers, schema)
            assert is_valid
            
            # Render templates
            dev_output = template_engine.render_template("dev-guidelines.j2", answers, schema, Path("/test"))
            assert "Project: TestProject" in dev_output
            assert "Testing: True" in dev_output
            
            llm_output = template_engine.render_template("llm-guidance.j2", answers, schema, Path("/test"))
            assert "Framework: pytest" in llm_output