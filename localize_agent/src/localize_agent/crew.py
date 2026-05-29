import os
from typing import Any

import litellm
from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Strip unsupported API params before any crew LLM is constructed.
litellm.drop_params = True

_LLM: LLM | None = None


class CompatibleLLM(LLM):
    """Omit stop for models/APIs that reject it.

    CrewAI's agent executor also appends ReAct stop sequences to ``llm.stop`` before each call.
    """

    _STOP_UNSUPPORTED_PREFIXES = ("gpt-5", "o1-", "o1/", "o3-", "o3/", "o4-", "o4/")

    def supports_stop_words(self) -> bool:
        model = self.model.lower()
        if any(token in model for token in self._STOP_UNSUPPORTED_PREFIXES):
            return False
        return super().supports_stop_words()

    def _prepare_completion_params(
        self,
        messages,
        tools=None,
    ) -> dict[str, Any]:
        params = super()._prepare_completion_params(messages, tools)
        if not self.supports_stop_words():
            params.pop("stop", None)
        return params


def _llm() -> LLM:
    global _LLM
    if _LLM is None:
        model = (
            os.getenv("MODEL")
            or os.getenv("OPENAI_MODEL_NAME")
            or "gpt-4o-mini"
        )
        _LLM = CompatibleLLM(model=model)
    return _LLM


@CrewBase
class LocalizeAgent:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def planning_agent(self) -> Agent:
        return Agent(config=self.agents_config["planning_agent"], llm=_llm())

    @agent
    def design_issue_identification_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["design_issue_identification_agent"], llm=_llm()
        )

    @agent
    def code_analyzer_agent(self) -> Agent:
        return Agent(config=self.agents_config["code_analyzer_agent"], llm=_llm())

    @agent
    def prompt_engineering_agent(self) -> Agent:
        return Agent(config=self.agents_config["prompt_engineering_agent"], llm=_llm())

    @agent
    def design_issue_localization_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["design_issue_localization_agent"], llm=_llm()
        )

    @agent
    def ranking_agent(self) -> Agent:
        return Agent(config=self.agents_config["ranking_agent"], llm=_llm())

    @task
    def planning_task(self) -> Task:
        return Task(config=self.tasks_config["planning_task"], output_file="planning_report.md")

    @task
    def design_issue_identification_task(self) -> Task:
        return Task(
            config=self.tasks_config["design_issue_identification_task"],
            output_file="issue_report.md",
        )

    @task
    def code_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["code_analysis_task"], output_file="analysis_report.md"
        )

    @task
    def prompt_engineering_task(self) -> Task:
        return Task(
            config=self.tasks_config["prompt_engineering_task"], output_file="prompt_report.md"
        )

    @task
    def design_issue_localization_task(self) -> Task:
        return Task(
            config=self.tasks_config["design_issue_localization_task"],
            output_file="localization_report.md",
        )

    @task
    def ranking_task(self) -> Task:
        return Task(config=self.tasks_config["ranking_task"], output_file="ranking_report.md")

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            llm=_llm(),
        )
