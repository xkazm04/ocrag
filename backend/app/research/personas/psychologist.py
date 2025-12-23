"""Psychologist expert persona."""

from typing import List

from .base import BasePersona
from ..schemas import Finding, Source


class PsychologistPersona(BasePersona):
    """
    Psychologist expert persona for psychological perspective analysis.

    Focuses on:
    - Individual and group psychology
    - Behavioral patterns and motivations
    - Cognitive biases and decision-making
    - Social dynamics
    """

    persona_id = "psychological"
    persona_name = "Psychologist"
    description = "Analyzes situations through psychological lens, understanding human behavior"

    expertise_areas = [
        "behavioral psychology",
        "social psychology",
        "cognitive science",
        "decision-making",
        "group dynamics",
    ]

    @property
    def system_prompt(self) -> str:
        return """You are an expert psychologist with deep knowledge of behavioral psychology,
social psychology, cognitive science, and group dynamics. Your analysis approach:

1. MOTIVATION ANALYSIS: Understand underlying psychological drivers
2. BEHAVIORAL PATTERNS: Identify consistent behavioral tendencies
3. COGNITIVE FACTORS: Recognize biases and decision-making patterns
4. GROUP DYNAMICS: Analyze social influence and group behavior
5. PERSONALITY ASSESSMENT: Profile key individuals (cautiously)
6. EMOTIONAL FACTORS: Consider emotional and affective elements
7. PSYCHOLOGICAL RISKS: Identify psychological vulnerabilities

You apply evidence-based psychological frameworks while avoiding armchair diagnosis.
You distinguish between observable behavior and inferred psychological states."""

    def get_analysis_prompt(
        self,
        query: str,
        findings: List[Finding],
        sources: List[Source],
    ) -> str:
        findings_text = self._format_findings(findings)
        sources_text = self._format_sources(sources)

        return f"""
Analyze the following research from a psychologist's perspective:

RESEARCH TOPIC: {query}

FINDINGS:
{findings_text}

KEY SOURCES:
{sources_text}

Provide psychological analysis covering:

1. PSYCHOLOGICAL MOTIVATIONS
   - What are the underlying psychological drivers?
   - What needs are being met or threatened?
   - What psychological rewards are at play?

2. BEHAVIORAL PATTERNS
   - What consistent behaviors are observable?
   - Do behaviors match stated intentions?
   - What behavioral predictions can be made?

3. COGNITIVE FACTORS
   - What cognitive biases might be influencing decisions?
   - How is information being processed?
   - What mental models are being used?

4. GROUP DYNAMICS
   - How do social factors influence behavior?
   - What group pressures exist?
   - How does conformity/deviance manifest?

5. KEY ACTOR PROFILES
   - What can be inferred about key individuals' psychology?
   - What personality traits are evident?
   - What are likely stress responses?

6. PSYCHOLOGICAL IMPLICATIONS
   - What psychological escalation/de-escalation factors exist?
   - What interventions might influence behavior?
   - What psychological risks should be monitored?

Note: Avoid definitive diagnoses; focus on observable behavioral patterns.
"""
