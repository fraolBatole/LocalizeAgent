from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from localize_agent.tools.custom_tools import CountMethods, VariableUsage, FanInFanOutAnalysis, ClassCouplingAnalysis


@CrewBase
class LocalizeAgent:
    """Design Issue Localization Crew with multiple specialized agents and tasks."""
    
    # Paths to your configuration files
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @agent
    def planning_agent(self) -> Agent:
        def delegate_tasks():
            # Trigger design_issue_identification_agent
            print("Debug: Triggering design_issue_identification_agent...")
            design_issues = self.design_issue_identification_agent.run()
            print(f"Debug: Design issues identified: {design_issues}")

            # Trigger code_analyzer_agent based on design issues
            if design_issues:
                print("Debug: Triggering code_analyzer_agent...")
                analysis_results = self.code_analyzer_agent.run(input_data=design_issues)
                print(f"Debug: Code analysis results: {analysis_results}")

                # Trigger prompt_engineering_agent based on analysis results
                if analysis_results:
                    print("Debug: Triggering prompt_engineering_agent...")
                    prompt = self.prompt_engineering_agent.run(input_data=analysis_results)
                    print(f"Debug: Prompt generated: {prompt}")

            # The rest of the tasks can be executed sequentially
            print("Debug: Triggering remaining tasks sequentially...")
            self.design_issue_localization_agent.run()
            self.ranking_agent.run()

        return Agent(
            config=self.agents_config['planning_agent'],
            delegate=delegate_tasks,
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
            tools=[CountMethods(), VariableUsage(), FanInFanOutAnalysis(), ClassCouplingAnalysis()],
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
    
    @agent
    def ranking_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['ranking_agent'],
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
            output_file='localization_report.md'
        )
    
    @task
    def ranking_task(self) -> Task:
        return Task(
            config=self.tasks_config['ranking_task'],
            output_file='ranking_report.md'
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
