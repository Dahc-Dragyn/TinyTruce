import json
import textwrap
from datetime import datetime
from typing import Union

from tinytroupe.utils import logger


################################################################################
# Rendering and markup 
################################################################################
def inject_html_css_style_prefix(html, style_prefix_attributes):
    """
    Injects a style prefix to all style attributes in the given HTML string.

    For example, if you want to add a style prefix to all style attributes in the HTML string
    ``<div style="color: red;">Hello</div>``, you can use this function as follows:
    inject_html_css_style_prefix('<div style="color: red;">Hello</div>', 'font-size: 20px;')
    """
    return html.replace('style="', f'style="{style_prefix_attributes};')

def break_text_at_length(text: Union[str, dict], max_length: int=None) -> str:
    """
    Breaks the text (or JSON) at the specified length, inserting a "(...)" string at the break point.
    If the maximum length is `None`, the content is returned as is.
    """
    if isinstance(text, dict):
        text = json.dumps(text, indent=4)

    if max_length is None or len(text) <= max_length:
        return text
    else:
        return text[:max_length] + " (...)"

def pretty_datetime(dt: datetime) -> str:
    """
    Returns a pretty string representation of the specified datetime object.
    """
    return dt.strftime("%Y-%m-%d %H:%M")

def dedent(text: str) -> str:
    """
    Dedents the specified text, removing any leading whitespace and identation.
    """
    return textwrap.dedent(text).strip()

def wrap_text(text: str, width: int=100) -> str:
    """
    Wraps the text at the specified width.
    """
    return textwrap.fill(text, width=width)

class RichTextStyle:
    
    # Consult color options here: https://rich.readthedocs.io/en/stable/appendix/colors.html

    STIMULUS_CONVERSATION_STYLE = "bold italic cyan1"
    STIMULUS_THOUGHT_STYLE = "dim italic cyan1"
    STIMULUS_DEFAULT_STYLE = "italic"
    
    ACTION_DONE_STYLE = "grey82"
    ACTION_TALK_STYLE = "bold green3"
    ACTION_THINK_STYLE = "green"
    ACTION_DEFAULT_STYLE = "purple"

    INTERVENTION_DEFAULT_STYLE = "bright_magenta"

    AGENT_COLORS = [
        "chartreuse1", "cyan1", "gold1", "orange1", "spring_green1", 
        "hot_pink", "deep_sky_blue1", "green_yellow", "bright_magenta",
        "medium_orchid1", "yellow1", "turquoise2", "light_salmon1"
    ]

    @classmethod
    def get_agent_style(cls, name: str):
        """
        Returns a stable, vibrant color for an agent based on their name.
        """
        import hashlib
        # Simple stable hash to pick a color
        hash_val = int(hashlib.md5(name.encode()).hexdigest(), 16)
        color = cls.AGENT_COLORS[hash_val % len(cls.AGENT_COLORS)]
        return f"bold {color}"

    @classmethod
    def get_style_for(cls, kind:str, event_type:str=None):
        if kind == "stimulus" or kind=="stimuli":
            if event_type == "CONVERSATION":
                return cls.STIMULUS_CONVERSATION_STYLE
            elif event_type == "THOUGHT":
                return cls.STIMULUS_THOUGHT_STYLE
            else:
                return cls.STIMULUS_DEFAULT_STYLE
            
        elif kind == "action":
            if event_type == "DONE":
                return cls.ACTION_DONE_STYLE
            elif event_type == "TALK":
                return cls.ACTION_TALK_STYLE
            elif event_type == "THINK":
                return cls.ACTION_THINK_STYLE
            else:
                return cls.ACTION_DEFAULT_STYLE
        
        elif kind == "intervention":
            return cls.INTERVENTION_DEFAULT_STYLE

