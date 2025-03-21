from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class LocalizeAgent:
    """Design Issue Localization Crew with multiple specialized agents and tasks."""
    
    # Paths to your configuration files
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @agent
    def planning_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['planning_agent'],
            verbose=True
        )
    
    @agent
    def design_issue_identification_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['design_issue_identification_agent'],
            verbose=False
        )
    
    @agent
    def code_analyzer_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['code_analyzer_agent'],
            verbose=False
        )
    
    @agent
    def prompt_engineering_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['prompt_engineering_agent'],
            verbose=True
        )
    
    @agent
    def design_issue_localization_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['design_issue_localization_agent'],
            verbose=False
        )
    
    @task
    def planning_task(self) -> Task:
        return Task(
            config=self.tasks_config['planning_task'],
            output_file='planning_report.md',
        )
    
    @task
    def design_issue_identification_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_issue_identification_task'],
            output_file='issue_report.md'
        )
    
    @task
    def code_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['code_analysis_task'],
            output_file='analysis_report.md'
        )
    
    @task
    def prompt_engineering_task(self) -> Task:
        return Task(
            config=self.tasks_config['prompt_engineering_task'],
            output_file='prompt_report.md'
        )
    
    @task
    def design_issue_localization_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_issue_localization_task'],
            output_file='final_report.md'
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Code Analysis Crew that orchestrates all agents and tasks."""
        return Crew(
            agents=self.agents,    # Automatically registered via @agent
            tasks=self.tasks,      # Automatically registered via @task
            process=Process.sequential,
            verbose=True
        )
