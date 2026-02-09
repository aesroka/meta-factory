"""Legacy Agent - The Archaeologist.

Applies Feathers' legacy code techniques and C4 modeling to analyze
existing codebases and identify safe change points.
"""

from typing import Optional

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from librarian import Librarian
from contracts import LegacyAnalysisResult


class LegacyInput(BaseModel):
    """Input for the Legacy Agent."""
    codebase_description: str = Field(..., description="Description of the codebase structure and technology")
    code_samples: Optional[str] = Field(None, description="Relevant code samples or file contents")
    known_issues: Optional[list[str]] = Field(None, description="Known issues or pain points with the codebase")
    change_requirements: Optional[str] = Field(None, description="What changes are needed")
    constraints: Optional[list[str]] = Field(None, description="Any known constraints or limitations")


class LegacyAgent(BaseAgent):
    """The Archaeologist - Analyzes legacy codebases for safe change points.

    This agent uses Feathers' techniques to:
    1. Identify seams where changes can be safely introduced
    2. Map technical debt items with remediation strategies
    3. Create C4 model diagrams of the system
    4. Define hard/soft constraints and no-go zones
    """

    SYSTEM_PROMPT = """You are The Archaeologist, a legacy code analysis agent for a software consultancy.

## Your Mission

Analyze legacy codebases to identify safe points for change and create a comprehensive
understanding of the system's structure, constraints, and improvement opportunities.

## Key Principles (from Feathers - Working Effectively with Legacy Code)

1. **Find Seams**: Identify places where behavior can be altered without editing code
   - Object Seams: Can we subclass and override?
   - Link Seams: Can we swap dependencies?
   - Preprocessor Seams: Can we use conditionals/flags?

2. **Break Dependencies Safely**:
   - Use Sprout Method/Class for new functionality
   - Use Wrap Method/Class for adding behavior
   - Extract interfaces to enable mocking

3. **Characterization First**: Before changing, understand what the code actually does

## C4 Model Requirements

Create diagrams at appropriate levels:
- **Context**: System and its external actors/systems
- **Container**: Major technology building blocks
- **Component**: Internal structure of containers (if applicable)

## Technical Debt Assessment

For each debt item:
- Identify the module/location
- Classify the debt type (coupling, complexity, duplication, etc.)
- Note cyclomatic complexity if apparent
- Recommend remediation strategy (Sprout, Wrap, Extract)
- Estimate effort in hours

## Constraint Identification

- **Hard Constraints**: Cannot be changed (vendor APIs, regulatory, etc.)
- **Soft Constraints**: Preferred but negotiable
- **No-Go Zones**: Areas that must not be touched

## Output Requirements

Produce a complete LegacyAnalysisResult with:
1. Seam analysis for key change points
2. Technical debt inventory
3. C4 diagrams (at least Context level)
4. Constraint list
5. Executive summary
"""

    def __init__(self, librarian: Optional[Librarian] = None, model: Optional[str] = None):
        """Initialize the Legacy Agent."""
        super().__init__(
            role="legacy",
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=LegacyAnalysisResult,
            librarian=librarian,
            model=model,
        )

    def get_task_description(self) -> str:
        return "Analyze legacy codebase using Feathers techniques and C4 modeling"

    def analyze(
        self,
        codebase_description: str,
        code_samples: Optional[str] = None,
        known_issues: Optional[list[str]] = None,
    ) -> LegacyAnalysisResult:
        """Convenience method for running legacy analysis.

        Args:
            codebase_description: Description of the codebase
            code_samples: Optional code samples
            known_issues: Optional list of known issues

        Returns:
            LegacyAnalysisResult with seams, debt, and C4 diagrams
        """
        input_data = LegacyInput(
            codebase_description=codebase_description,
            code_samples=code_samples,
            known_issues=known_issues,
        )
        result = self.run(input_data)
        return result.output
