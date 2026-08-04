class StateGraph:

    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.entry_point = None

    def add_node(self, name, node):
        self.nodes[name] = node

    def set_entry_point(self, name):
        self.entry_point = name

    def add_edge(self, start_name, end_name):
        self.edges[start_name] = end_name

    def execute(self, state):
        current_name = self.entry_point

        while current_name and current_name in self.nodes:
            node = self.nodes[current_name]
            state = node.run(state)
            current_name = self.edges.get(current_name, None)

        return state
