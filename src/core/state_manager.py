class StateManager:
    def __init__(self):
        self.state = {}

    def set_state(self, agent_name, state_data):
        self.state[agent_name] = state_data

    def get_state(self, agent_name):
        return self.state.get(agent_name, None)

    def remove_state(self, agent_name):
        if agent_name in self.state:
            del self.state[agent_name]

    def clear_all_states(self):
        self.state.clear()