import os
import re
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("persona_scrubber")

PERSONA_DIRS = [
    "personas/agents",
    "personas/fragments"
]

SCRUB_RULES = [
    # Replace literal word counts with qualitative descriptors
    (r"(\d+)-word clause limit", "Prefer short, punchy clauses and rapid-fire delivery"),
    (r"(\d+)-word (limit|count)", "Maintain a concise and clinical word count"),
    (r"max_words_per_clause\": \d+", "clause_structure\": \"concise\""),
    (r"max_words_per_sentence\": \d+", "sentence_structure\": \"brief\""),
    (r"Maintain the (\d+)-word clause limit", "Emphasize rapid, staccato clause delivery"),
    (r"Output exactly (\d+) to (\d+) words", "Provide a detailed and comprehensive response"),
    (r"Exactly (\d+) words", "Be concisely focused and brief"),
    (r"(\d+) words per minute", "Maintain a slow, deliberate cadence"),
]

def scrub_content(content):
    modified = False
    new_content = content
    for pattern, replacement in SCRUB_RULES:
        if re.search(pattern, new_content, re.IGNORECASE if isinstance(pattern, str) else 0):
            new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE if isinstance(pattern, str) else 0)
            modified = True
    return new_content, modified

def main():
    logger.info("Starting Persona Scrubbing Operation...")
    files_processed = 0
    files_modified = 0

    for directory in PERSONA_DIRS:
        if not os.path.exists(directory):
            logger.warning(f"Directory {directory} not found. Skipping.")
            continue
            
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith((".json", ".md", ".txt")):
                    file_path = os.path.join(root, file)
                    files_processed += 1
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            
                        new_content, modified = scrub_content(content)
                        
                        if modified:
                            logger.info(f"Scrubbed: {file_path}")
                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(new_content)
                            files_modified += 1
                    except Exception as e:
                        logger.error(f"Failed to process {file_path}: {e}")

    logger.info(f"Operation complete. Processed {files_processed} files, modified {files_modified} files.")

if __name__ == "__main__":
    main()
