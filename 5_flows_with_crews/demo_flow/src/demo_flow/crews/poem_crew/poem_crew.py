from crewai import Agent, Crew, Process, Task,LLM
from crewai.project import CrewBase, agent, crew, task


@CrewBase
class PoemCrew():
	"""Poem Crew"""

	agents_config = 'config/agents_partial_discharge.yaml'
	tasks_config = 'config/tasks.yaml'

	llm=LLM(
		model="ollama/llama3.2",
		base_url="http://localhost:11434"
	)

	@agent
	def poem_writer(self) -> Agent:
		return Agent(
			config=self.agents_config['poem_writer'],
			llm=self.llm
		)

	@task
	def write_poem(self) -> Task:
		return Task(
			config=self.tasks_config['write_poem'],
			llm=self.llm
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the Research Crew"""
		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			process=Process.sequential,
			verbose=True,
		)
