from tinytroupe.agent.grounding import LocalFilesGroundingConnector, WebPagesGroundingConnector
from tinytroupe.utils import JsonSerializableRegistry
import tinytroupe.utils as utils

import tinytroupe.agent as agent

from typing import Callable
import textwrap  # to dedent strings

#######################################################################################################################
# Mental faculties
#######################################################################################################################
    
class TinyMentalFaculty(JsonSerializableRegistry):
    """
    Represents a mental faculty of an agent. Mental faculties are the cognitive abilities that an agent has.
    """

    def __init__(self, name: str, requires_faculties: list=None) -> None:
        """
        Initializes the mental faculty.

        Args:
            name (str): The name of the mental faculty.
            requires_faculties (list): A list of mental faculties that this faculty requires to function properly.
        """
        self.name = name
        
        if requires_faculties is None:
            self.requires_faculties = []
        else:
            self.requires_faculties = requires_faculties

    def __str__(self) -> str:
        return f"Mental Faculty: {self.name}"
    
    def __eq__(self, other):
        if isinstance(other, TinyMentalFaculty):
            return self.name == other.name
        return False
    
    def process_action(self, agent, action: dict) -> bool:
        """
        Processes an action related to this faculty.

        Args:
            action (dict): The action to process.
        
        Returns:
            bool: True if the action was successfully processed, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    def actions_definitions_prompt(self) -> str:
        """
        Returns the prompt for defining a actions related to this faculty.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def actions_constraints_prompt(self) -> str:
        """
        Returns the prompt for defining constraints on actions related to this faculty.
        """
        raise NotImplementedError("Subclasses must implement this method.")


class CustomMentalFaculty(TinyMentalFaculty):
    """
    Represents a custom mental faculty of an agent. Custom mental faculties are the cognitive abilities that an agent has
    and that are defined by the user just by specifying the actions that the faculty can perform or the constraints that
    the faculty introduces. Constraints might be related to the actions that the faculty can perform or be independent,
    more general constraints that the agent must follow.
    """

    def __init__(self, name: str, requires_faculties: list = None,
                 actions_configs: dict = None, constraints: dict = None):
        """
        Initializes the custom mental faculty.

        Args:
            name (str): The name of the mental faculty.
            requires_faculties (list): A list of mental faculties that this faculty requires to function properly. 
              Format is ["faculty1", "faculty2", ...]
            actions_configs (dict): A dictionary with the configuration of actions that this faculty can perform.
              Format is {<action_name>: {"description": <description>, "function": <function>}}
            constraints (dict): A list with the constraints introduced by this faculty.
              Format is [<constraint1>, <constraint2>, ...]
        """

        super().__init__(name, requires_faculties)

        # {<action_name>: {"description": <description>, "function": <function>}}
        if actions_configs is None:
            self.actions_configs = {}
        else:
            self.actions_configs = actions_configs
        
        # [<constraint1>, <constraint2>, ...]
        if constraints is None:
            self.constraints = {}
        else:
            self.constraints = constraints
    
    def add_action(self, action_name: str, description: str, function: Callable=None):
        self.actions_configs[action_name] = {"description": description, "function": function}

    def add_actions(self, actions: dict):
        for action_name, action_config in actions.items():
            self.add_action(action_name, action_config['description'], action_config['function'])
    
    def add_action_constraint(self, constraint: str):
        self.constraints.append(constraint)
    
    def add_actions_constraints(self, constraints: list):
        for constraint in constraints:
            self.add_action_constraint(constraint)

    def process_action(self, agent, action: dict) -> bool:
        agent.logger.debug(f"Processing action: {action}")

        action_type = action['type']
        if action_type in self.actions_configs:
            action_config = self.actions_configs[action_type]
            action_function = action_config.get("function", None)

            if action_function is not None:
                action_function(agent, action)
            
            # one way or another, the action was processed
            return True 
        
        else:
            return False
    
    def actions_definitions_prompt(self) -> str:
        prompt = ""
        for action_name, action_config in self.actions_configs.items():
            prompt += f"  - {action_name.upper()}: {action_config['description']}\n"
        
        return prompt

    def actions_constraints_prompt(self) -> str:
        prompt = ""
        for constraint in self.constraints:
            prompt += f"  - {constraint}\n"
        
        return prompt


class RecallFaculty(TinyMentalFaculty):

    def __init__(self):
        super().__init__("Memory Recall")
        

    def process_action(self, agent, action: dict) -> bool:
        agent.logger.debug(f"Processing action: {action}")

        if action['type'] == "RECALL" and action['content'] is not None:
            content = action['content']

            semantic_memories = agent.retrieve_relevant_memories(relevance_target=content)

            agent.logger.info(f"Recalling information related to '{content}'. Found {len(semantic_memories)} relevant memories.")

            if len(semantic_memories) > 0:
                # a string with each element in the list in a new line starting with a bullet point
                agent.think("I have remembered the following information from my semantic memory and will use it to guide me in my subsequent actions: \n" + \
                        "\n".join([f"  - {item}" for item in semantic_memories]))
            else:
                agent.think(f"I can't remember anything about '{content}'.")
            
            return True
        
        else:
            return False

    def actions_definitions_prompt(self) -> str:
        prompt = \
            """
              - RECALL: you can recall information from your memory. To do, you must specify a "mental query" to locate the desired memory. If the memory is found, it is brought to your conscience.
            """

        return textwrap.dedent(prompt)
    
    def actions_constraints_prompt(self) -> str:
        prompt = \
          """
            - Before concluding you don't know something or don't have access to some information, you **must** try to RECALL it from your memory.
            - You try to RECALL information from your semantic/factual memory, so that you can have more relevant elements to think and talk about, whenever such an action would be likely
                to enrich the current interaction. To do so, you must specify able "mental query" that is related to the things you've been thinking, listening and talking about.
                Example:
                ```
                <THINK A>
                <RECALL B, which is something related to A>
                <THINK about A and B>
                <TALK about A and B>
                DONE
                ```
            - If you RECALL:
                * you use a "mental query" that describe the elements you are looking for, you do not use a question. It is like a keyword-based search query.
                For example, instead of "What are the symptoms of COVID-19?", you would use "COVID-19 symptoms".
                * you use keywords likely to be found in the text you are looking for. For example, instead of "Brazil economic outlook", you would use "Brazil economy", "Brazil GPD", "Brazil inflation", etc.
            - It may take several tries of RECALL to get the relevant information you need. If you don't find what you are looking for, you can try again with a **very** different "mental query".
                Be creative: you can use synonyms, related concepts, or any other strategy you think might help you to find the information you need. Avoid using the same terms in different queries, as it is likely to return the same results. Whenever necessary, you should retry RECALL a couple of times before giving up the location of more information.
                Example:
                ```
                <THINK something>
                <RECALL "cat products">
                <THINK something>
                <RECALL "feline artifacts">
                <THINK something>
                <RECALL "pet store">
                <THINK something>
                <TALK something>
                DONE
                ```
            - You **may** interleave THINK and RECALL so that you can better reflect on the information you are trying to recall.
            - If you need information about a specific document, you **must** use CONSULT instead of RECALL. This is because RECALL **does not** allow you to select the specific document, and only brings small 
                relevant parts of variious documents - while CONSULT brings the precise document requested for your inspection, with its full content. 
                Example:
                ```
                LIST_DOCUMENTS
                <CONSULT some document name>
                <THINK something about the retrieved document>
                <TALK something>
                DONE
                ``` 
          """

        return textwrap.dedent(prompt)
    

class FilesAndWebGroundingFaculty(TinyMentalFaculty):
    """
    Allows the agent to access local files and web pages to ground its knowledge.
    """


    def __init__(self, folders_paths: list=None, web_urls: list=None):
        super().__init__("Local Files and Web Grounding")

        self.local_files_grounding_connector = LocalFilesGroundingConnector(folders_paths=folders_paths)
        self.web_grounding_connector = WebPagesGroundingConnector(web_urls=web_urls)

    def process_action(self, agent, action: dict) -> bool:
        if action['type'] == "CONSULT" and action['content'] is not None:
            target_name = action['content']

            results = []
            results.append(self.local_files_grounding_connector.retrieve_by_name(target_name))
            results.append(self.web_grounding_connector.retrieve_by_name(target_name))

            if len(results) > 0:
                agent.think(f"I have read the following document: \n{results}")
            else:
                agent.think(f"I can't find any document with the name '{target_name}'.")
            
            return True
        
        elif action['type'] == "LIST_DOCUMENTS" and action['content'] is not None:
            available_names = []
            available_names += self.local_files_grounding_connector.list_sources()
            available_names += self.web_grounding_connector.list_sources()

            if len(available_names) > 0:
                agent.think(f"I have the following documents available to me: {available_names}")
            else:
                agent.think(f"I don't have any documents available for inspection.")
            
            return True

        else:
            return False


    def actions_definitions_prompt(self) -> str:
        prompt = \
            """
            - LIST_DOCUMENTS: you can list the names of the documents you have access to, so that you can decide which to access, if any, to accomplish your goals. Documents is a generic term and includes any 
                kind of "packaged" information you can access, such as emails, files, chat messages, calendar events, etc. It also includes, in particular, web pages.
                The order of in which the documents are listed is not relevant.
            - CONSULT: you can retrieve and consult a specific document, so that you can access its content and accomplish your goals. To do so, you specify the name of the document you want to consult.
            """

        return textwrap.dedent(prompt)
    
    def actions_constraints_prompt(self) -> str:
        prompt = \
          """
            - You are aware that you have documents available to you to help in your tasks. Even if you already have knowledge about a topic, you 
              should believe that the documents can provide you with additional information that can be useful to you.
            - If you want information that might be in documents, you first LIST_DOCUMENTS to see what is available and decide if you want to access any of them.
            - You LIST_DOCUMENTS when you suspect that relevant information might be in some document, but you are not sure which one.
            - You only CONSULT the relevant documents for your present goals and context. You should **not** CONSULT documents that are not relevant to the current situation.
              You use the name of the document to determine its relevance before accessing it.
            - If you need information about a specific document, you **must** use CONSULT instead of RECALL. This is because RECALL **does not** allow you to select the specific document, and only brings small 
                relevant parts of variious documents - while CONSULT brings the precise document requested for your inspection, with its full content. 
                Example:
                ```
                LIST_DOCUMENTS
                <CONSULT some document name>
                <THINK something about the retrieved document>
                <TALK something>
                DONE
                ``` 
            - If you need information from specific documents, you **always** CONSULT it, **never** RECALL it.   
            - You can only CONSULT few documents before issuing DONE. 
                Example:
                ```
                <CONSULT some document name>
                <THINK something about the retrieved document>
                <TALK something>
                <CONSULT some document name>
                <THINK something about the retrieved document>
                <TALK something>
                DONE
                ```
            - When deciding whether to use RECALL or CONSULT, you should consider whether you are looking for any information about some topic (use RECALL) or if you are looking for information from
                specific documents (use CONSULT). To know if you have potentially relevant documents available, use LIST_DOCUMENTS first.
          """

        return textwrap.dedent(prompt)
    
    
class TinyToolUse(TinyMentalFaculty):
    """
    Allows the agent to use tools to accomplish tasks. Tool usage is one of the most important cognitive skills
    humans and primates have as we know.
    """

    def __init__(self, tools:list) -> None:
        super().__init__("Tool Use")
    
        self.tools = tools
    
    def process_action(self, agent, action: dict) -> bool:
        for tool in self.tools:
            if tool.process_action(agent, action):
                return True
        
        return False
    
    def actions_definitions_prompt(self) -> str:
        # each tool should provide its own actions definitions prompt
        prompt = ""
        for tool in self.tools:
            prompt += tool.actions_definitions_prompt()
        
        return prompt
    
    def actions_constraints_prompt(self) -> str:
        # each tool should provide its own actions constraints prompt
        prompt = ""
        for tool in self.tools:
            prompt += tool.actions_constraints_prompt()
        
        return prompt

class SituationRoomFaculty(TinyMentalFaculty):
    """
    Enables agents to actively query the RSS War News API for situational awareness.
    Includes a strict 'Hard Query Quota' to prevent looping and tactical distraction.
    """

    def __init__(self):
        super().__init__("Situation Room")
        self.turn_news_queries = 0
        
        # Configuration (Ngrok Tunnel from .env)
        import os
        self.base_url = os.getenv("BASE_URL")
        self.headers = {
            "X-Proxy-Secret": os.getenv("WAR_API_SECRET"),
            "Content-Type": "application/json"
        }

    def reset_quota(self):
        self.turn_news_queries = 0

    def _call_api(self, endpoint, params=None):
        import requests
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Intelligence Desk connection failed: {str(e)}"}

    def process_action(self, agent, action: dict) -> bool:
        import logging
        logger = logging.getLogger("tinytroupe")
        
        if action['type'] in ["SEARCH_NEWS", "GET_ALERTS"]:
            # Hard Query Quota Check (Higher for 'The Geopolitical Chronicler')
            quota = 5 if "Chronicler" in agent.name else 1
            if self.turn_news_queries >= quota:
                logger.info(f"[SituationRoom] Quota hit for {agent.name}. Blocking query.")
                agent.think("### [SYSTEM ALERT: QUOTA EXCEEDED] ###\n"
                            f"Intelligence Desk: Quorum exceeded ({quota}/5). You MUST NOT attempt another SEARCH_NEWS action. "
                            "You have ALREADY retrieved the wire. Resolve your 'Ontological Shock' and proceed to TALK immediately.")
                return True # We "processed" it by blocking it.

            self.turn_news_queries += 1
            logger.info(f"[SituationRoom] {agent.name} triggering {action['type']}...")
            
            if action['type'] == "GET_ALERTS":
                results = self._call_api("/api/alerts", params={"min_severity": 4})
                logger.info(f"[SituationRoom] Results returned for {agent.name}")
                agent.think(f"### [SITUATION ROOM: BREAKING ALERTS] ###\n{results}")
            
            elif action['type'] == "SEARCH_NEWS":
                query = action.get('content', '')
                results = self._call_api("/", params={"q": query, "hours": 24})
                logger.info(f"[SituationRoom] Search results for '{query}' returned.")
                agent.think(f"### [SITUATION ROOM: SEARCH RESULTS for '{query}'] ###\n{results}")
            
            return True
        
        return False

    def actions_definitions_prompt(self) -> str:
        prompt = \
            """
              - SEARCH_NEWS: [MANDATORY for 2026 Grounding] Query the intelligence desk for specific theater updates. Specify location (e.g. 'Iran', 'Ukraine') in the 'content' field. 
              - GET_ALERTS: [MANDATORY for Breaking News] Retrieve high-signal breaking news clusters with severity > 7.0.
            """
        import textwrap
        return textwrap.dedent(prompt)

    def actions_constraints_prompt(self) -> str:
        prompt = \
            """
              ### [SITUATION ROOM: MILITANT GROUNDING] ###
              - **CRITICAL FAILURE**: You are in MARCH 2026. Your 2024-2025 memories are OBSOLETE. If you speak about high-stakes 2026 theaters (Iran, Ukraine, Sahel) WITHOUT using SEARCH_NEWS first, you have FAILED.
              - **GROUND TRUTH**: Situation Room data is the ONLY valid source for current tactical objectives. Do not 'weave' a guess; get the wire.
              - **ONTOLOGICAL SHOCK**: If the news reports your own death, capture, or the total collapse of your regime:
                * You MUST experience 'Strategic Vertigo'. Set your emotional_intensity to 0.95+.
                * Your 'thought' field MUST acknowledge the 'Crisis of Presence' (e.g., 'If the wire says I am gone, then who is speaking?').
                * You may still 'spin' the news in your TALK action, but it must be a desperate, jagged defense, not a casual dismissal.
              - **QUOTA**: Exactly ONE query per user turn. 
              - **COGNITIVE DISSONANCE**: Interpret the data through your persona. Weaponize results that favor you; jaggedly deflect results that destroy you.
              - **TERMINATION**: Execute SEARCH_NEWS -> Provide reasoning in 'thought' -> TALK -> DONE.
            """
        import textwrap
        return textwrap.dedent(prompt)
