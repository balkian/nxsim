"""
Simulation environment
======================
The simulation environment acts as the container of agents, monitors, and resources that are part of the simulation.

The simulation environment in nxsim subclasses the Simpy 3 simpy.Environment class to include agent methods and make it
act like an array containing the agents.

"""

import simpy
import networkx as nx
from copy import deepcopy
import weakref
from collections import Counter
from .agents import BaseAgent, BaseState

__all__ = ['BaseEnvironment', 'BaseNetworkEnvironment', 'build_simulation']


class BaseEnvironment(simpy.Environment):
    """
    Base class for simulation environments

    This class is the most basic type of simulation environment available in nxsim. BaseEnvironment is a subclass of
    simpy.Environment for discrete time simulations with additional methods and properties for relationships between
    agents in the simulation environment. The set of these relationships is what nxsim calls "structure". The presence
    of structure in an environment guides and/or limits the potential interactions between agents. Often, structure is
    some kind of spatial configuration, but it is possible to implement other kinds of limitations as well.

    BaseEnvironment by default does not have any positional structure to the arrangement, nor is there any information
    about agent-agent relationships between agents as they are stored as key-value pairs in a dictionary. In this
    "unstructured" structure, nxsim uses the agent's unique ID (uid) as the key while the agent object itself is
    the value.

    Structure can be added by passing an object with dictionary-like assignment and retrieval to the structure
    parameter. Note that the structure object must behave like a dictionary in terms of methods and
    properties to work properly. When nothing is passed to the structure parameter, BaseEnvironment becomes
    "unstructured" because it just uses a dictionary to store agents.

    See Also
    --------
    BaseNetworkEnvironment

    Examples
    --------
    Create a new environment with no associated agents, monitors and resources, and no structure.

    >>> env = BaseEnvironment()

    Because of how structure works in the context of the environment, structure can only be assigned during
    initialization. To create a new environment with a definite structure, pass a dictionary-like object to the
    "structure" parameter.

    For example, we want to create an environment with a dictionary as our "structure".

    >>> flat_structure = dict()  # a dictionary is actually "unstructured" because there is no agent-agent relationship
    >>> structured_env = BaseEnvironment(structure=flat_structure)
    >>> len(structured_env)
    0

    Agents can be added to an environment TODO

    """
    def __init__(self, structure, agent_constructor=None, initial_agent_state=None, initial_time=0,
                 possible_states=(), monitors=(), resources=()):
        """Creates a new BaseEnvironment for simulation

        Parameters
        ----------
        structure : dictionary-like, optional (default=None)
            Defines how agents are configured with respect to one another (structure) in the environment.
            If None, the the agents in the environment are stored in an unstructured manner where each agent is
            independent of any other agent. Formally, agents are stored as values in a dictionary identified using
            agent uid's as key.
        agent_constructor : BaseAgent
            Agent constructor to be used if graph is not empty.
        initial_agent_state : BaseState
            Initial state of newly created agents
        initial_time : int, optional (default=0)
            Start time of the environment at initialization.
        possible_states : set or iterable, optional (default=())
            List of states agents can have in this environment.
        monitors : list of monitor objects, optional (default=())
            List of monitors associated with this environment.
        resources : list of resource objects, optional (default=())
            List of resources used by this environment.
        """
        self.init_time = initial_time
        super().__init__(initial_time=initial_time)
        self._structure = dict() if structure is None else deepcopy(structure)  # structure must be dict-like
        self.possible_states = weakref.WeakSet(possible_states)
        self.monitors = list(monitors)
        self.resources = list(resources)

        if len(self.structure) > 0:
            for uid in self.structure.keys():
                self.structure[uid] = agent_constructor(uid, self, initial_agent_state)

    @property
    def agents(self):
        return list(self.structure.values())

    @property
    def structure(self):
        return self._structure

    def current(self):
        """Return a snapshot of the current state of the entire simulation environment.

        Returns
        -------
        BaseEnvironment
            Deep copy of the environment. Note that this may be memory-intensive.
        """
        return deepcopy(self)

    def filter(self, state=None):
        """Returns list of agents based on their state

        Parameters
        ----------
        state : BaseState object, optional (default = None)
            Used to select agents that have the same specified "state". If state is None, returns all agents regardless
            of its current state

        Returns
        -------
        list
            List of agents in the environment
        """
        if state is None:
            return self.agents  # return all regardless of state
        else:
            return [agent for agent in self.agents if agent.state == state]

    def describe(self):
        """Describe the environment in terms of number of agents registered, their states, and the structure present.
        """
        return {'agent_count': len(self),
                'possible_states': self.possible_states,
                'state_count': Counter(self.structure.values()),
                'structure': repr(type(self.structure)),
                }

    def items(self):
        """Returns the contents of the structure as key-value pairs

        Returns
        -------
        iterable
            Generator yielding one key-value tuple at a time
        """
        return self.structure.items()

    def __len__(self):
        """Returns number of agents registered in the environment"""
        return len(self.structure)

    def __contains__(self, agent):
        """Returns True if the agent is registered in this environment"""
        return any(a.uid == agent.uid for a in self.agents)

    def __getitem__(self, key):
        """Returns the agent associated with a particular key"""
        return self.structure[key]

    def __setitem__(self, key, agent):
        """Register an agent into this environment"""
        assert key not in self.structure.keys()  #
        self.structure[key] = agent
        self.process(agent.run())  # I dont understand this line!!! Part of simpy perhaps

    def __delitem__(self, key):
        """Remove agent from this environment"""
        del self.structure[key]

    def __repr__(self):
        return repr(self.structure)


class BaseNetworkEnvironment(BaseEnvironment):
    """An environment that uses a network structure to control the spatial configuration of agents.

    This is a subclass of BaseEnvironment that uses a Networkx graph for its structure

    Parameters
    ----------
    graph : Networkx Graph
    initial_time : int

    See Also
    --------
    BaseEnvironment

    """
    def __init__(self, graph=None, agent_constructor=None, initial_agent_state=None, initial_time=0,
                 possible_states=(), monitors=(), resources=()):
        """Creates a new BaseNetworkEnvironment for simulation regulated by a network structure

        Parameters
        ----------
        graph : nx.Graph
            Networkx graph
        agent_constructor : BaseAgent
            Agent constructor to be used if graph is not empty.
        initial_agent_state : BaseState
            Initial state of newly created agents
        initial_time : int, optional (default=0)
            Start time of the environment at initialization.
        possible_states : set or iterable, optional (default=())
            List of states agents can have in this environment.
        monitors : list of monitor objects, optional (default=())
            List of monitors associated with this environment.
        resources : list of resource objects, optional (default=())
            List of resources used by this environment.

        """
        if not graph:  # None
            graph = nx.Graph()  # empty graph

        if isinstance(graph, nx.Graph):
            super().__init__(graph, agent_constructor=agent_constructor, initial_agent_state=initial_agent_state,
                             initial_time=initial_time, possible_states=possible_states,
                             monitors=monitors, resources=resources)
        else:
            raise TypeError('Structure must be a Networkx Graph object or a subclass.')

    @property
    def agents(self):
        return list(dict(self.structure.nodes(data=True)).values())

    def add_edges(self, agent_1, agent_2):
        NotImplementedError()
        pass

    def items(self):
        return ((i, self.__getitem__(i)) for i in self.structure.nodes())

    def __contains__(self, agent):
        """Returns True if the agent is registered in this environment"""
        return any(a.uid == agent.uid for a in self.agents)

    def __getitem__(self, node_id):
        """Returns the agent given its associated node ID"""
        return self.structure.node[node_id]

    def __setitem__(self, node_id, agent):
        # TODO : check if node id is present in the network
        self.structure.node[node_id] = agent
        self.process(agent.run())

    def __delitem__(self, node_id):
        self.structure.remove_node(node_id)
