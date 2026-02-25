import os
import logging
import configparser
import rich # for rich console output
import rich.jupyter

# add current path to sys.path
import sys
sys.path.append('.')
from tinytroupe import utils # now we can import our utils

# AI disclaimers
print(\
"""
!!!!
DISCLAIMER: TinyTroupe relies on Artificial Intelligence (AI) models to generate content. 
The AI models are not perfect and may produce inappropriate or inacurate results. 
For any serious or consequential use, please review the generated content before using it.
!!!!
""")


###########################################################################
# Default parameter values
###########################################################################
# We'll use various configuration elements below
config = utils.read_config_file()
utils.pretty_print_config(config)
utils.start_logger(config)

default = {}
default["embedding_model"] = config["OpenAI"].get("EMBEDDING_MODEL", "text-embedding-3-small")
default["max_content_display_length"] = config["OpenAI"].getint("MAX_CONTENT_DISPLAY_LENGTH", 1024)
if config["OpenAI"].get("API_TYPE") == "azure":
    default["azure_embedding_model_api_version"] = config["OpenAI"].get("AZURE_EMBEDDING_MODEL_API_VERSION", "2023-05-15")


# LlamaIndex dependencies removed for TinyTruce (Gemini-native implementation)
# We rely on large context windows rather than vector search.



###########################################################################
# Fixes and tweaks
###########################################################################

# fix an issue in the rich library: we don't want margins in Jupyter!
rich.jupyter.JUPYTER_HTML_FORMAT = \
    utils.inject_html_css_style_prefix(rich.jupyter.JUPYTER_HTML_FORMAT, "margin:0px;")


