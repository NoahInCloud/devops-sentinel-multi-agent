class TaskScheduler:
    def __init__(self):
        self.tasks = []

    def schedule_task(self, task):
        self.tasks.append(task)

    def execute_tasks(self):
        for task in self.tasks:
            task.run()
        self.tasks.clear()