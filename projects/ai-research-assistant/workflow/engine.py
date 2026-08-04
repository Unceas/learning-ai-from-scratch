class Workflow:

    def __init__(self):

        self.nodes = []

    def add_node(self, node):

        self.nodes.append(node)

    def execute(self, state):

        for node in self.nodes:

            state = node.run(state)

        return state
