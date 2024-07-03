from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import logging
import os
from logging.handlers import RotatingFileHandler
import tempfile
import time
import shlex

import csv
from io import StringIO
from typing import Dict


# Set up logging
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'log.txt')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)

app = FastAPI()

class TTLInput(BaseModel):
    ttl_text: str

    @field_validator('ttl_text')
    @classmethod
    def validate_ttl_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('TTL text cannot be empty')
        if not re.search(r'\w+:\w+', v):
            raise ValueError('Invalid TTL format')
        return v

import re
from typing import Dict, List

# statement prefixes.
statement_prefix = ("v:", "s:")
triple_statement_prefix = ("p:", "psv:")

def preprocess_ttl(ttl_text: str) -> str:
    """
    Preprocess the Turtle format text by removing line breaks and excess spaces.
    
    Args:
    ttl_text (str): The input Turtle format text.
    
    Returns:
    str: Preprocessed text as a single line.
    """
    # Remove line breaks and excess spaces, but preserve important whitespace
    preprocessed = re.sub(r'\s+', ' ', ttl_text)
    # Ensure space after semicolons and commas for readability
    preprocessed = re.sub(r'([;,])(?!\s)', r'\1 ', preprocessed)
    # Remove space before period at the end of statements
    preprocessed = re.sub(r'\s+\.', ' .', preprocessed)
        
    preprocessed = preprocessed.strip()
    # remove the last dot " ." from the string
    if preprocessed[-1] == ".":
        preprocessed = preprocessed[:-1]
    
    return preprocessed

def split_preserve_quotes(s):
            # pattern = r'"[^"]*"[^\s]*|"[^"]*"|[^\s"]+'
            # return re.findall(pattern, s)
            # This regex matches:
            # 1. Quoted content (ignoring escaped quotes) followed immediately by non-space characters
            # 2. Or just quoted content (ignoring escaped quotes)
            # 3. Or non-space characters (including escaped quotes)
            #pattern = r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+'
            pattern = r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+'
            return re.findall(pattern, s)
               
def split_by_sections(preprocessed_text: str) -> Dict: 
    """
    Split the preprocessed text into sections based on periods.
    
    Args:
    preprocessed_text (str): The preprocessed Turtle format text.
    
    Returns:
    Dict: A dictionary with subjects as keys and lists of statement parts as values.
    """
    # Split by period, but not if it's part of a data type or URL
    sections = re.split(r'\.\s+(?=[^\s])', preprocessed_text)
    result = dict()
    
    for section in sections:
        if "[" in section:
            # skip the section
            continue
        
        stripped_section = section.strip() # remove leading and trailing whitespaces
        #split section by ; and remove leading and trailing whitespaces
        statements = [statement.strip() for statement in stripped_section.split(";")]
        # get first word in the list (till the first space)
        subject = statements[0].split(" ")[0]
        # pop subject from the string, add " " to remove the leading space
        statements[0] = statements[0].replace(subject + " ", "")
        # split the statement preserving quotes and the spaces inside the quotes
        result[subject] = [split_preserve_quotes(statement) for statement in statements]
    return result

def recursive_conversion(sections, predicate_chain, index_chain, object, subject):
    if object not in sections:
        return
    
    for triple in sections[object]:
        new_predicate_chain = predicate_chain.copy()
        new_index_chain = index_chain.copy()
        new_predicate_chain.append(triple[0])
        
        if triple[0].startswith(triple_statement_prefix):
            for i, obj in enumerate(triple[1:], start=1):
                if obj.endswith(','):
                    obj = obj[:-1]  # Remove trailing comma
                new_index = new_index_chain + [str(i)]
                recursive_conversion(sections, new_predicate_chain, new_index, obj, subject)
        else:
            predicate = "|".join(new_predicate_chain)
            for i, obj in enumerate(triple[1:], start=1):
                if obj.endswith(','):
                    obj = obj[:-1]  # Remove trailing comma
                new_index = new_index_chain + [str(i)]
                index = ",".join(new_index)
                answer.append(f'{subject} <{predicate}>[{index}] {obj}')

def convert_to_new_format(sections: Dict[str, List[List[str]]]) -> str:
    global answer
    answer = []
    
    for subject, triples in sections.items():
        if subject.startswith(statement_prefix):
            continue
        
        for triple in triples:
            predicate_chain = [triple[0]]
            index_chain = []
            
            if triple[0].startswith(triple_statement_prefix):
                for i, obj in enumerate(triple[1:], start=1):
                    if obj.endswith(','):
                        obj = obj[:-1]  # Remove trailing comma
                    recursive_conversion(sections, predicate_chain, [str(i)], obj, subject)
            else:
                predicate = triple[0]
                for i, obj in enumerate(triple[1:], start=1):
                    if obj.endswith(','):
                        obj = obj[:-1]  # Remove trailing comma
                    answer.append(f'{subject} <{predicate}>[{i}] {obj}')
    
    return "\n".join(answer)

@app.post("/convert")
async def convert_ttl(file: UploadFile = File(...)):
    try:
        start_time = time.time()
        logger.info(f"Received file: {file.filename}")
        
        # Read the contents of the uploaded file
        contents = await file.read()
        ttl_text = contents.decode("utf-8")
        
        # Validate the TTL text
        TTLInput(ttl_text=ttl_text)  # This will raise an error if validation fails
        
        logger.info("Starting TTL conversion")
        preprocessed = preprocess_ttl(ttl_text)
        logger.debug(f"Preprocessed TTL: {preprocessed}")
        sections = split_by_sections(preprocessed)
        logger.debug(f"Split sections: {sections}")
        new_format = convert_to_new_format(sections)
        logger.info("TTL conversion completed successfully")

        end_time = time.time()
        execution_time = end_time - start_time

        logger.info(f"Conversion completed in {execution_time:.2f} seconds")

        # Create a temporary file to store the converted content
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as temp_file:
            temp_file.write(new_format)
            temp_file_path = temp_file.name

        logger.info(f"Converted file saved to: {temp_file_path}")

        # Return the file as a downloadable response
        return FileResponse(temp_file_path, media_type='text/plain', filename="converted_ttl.txt", headers={"X-Execution-Time": str(execution_time)})

    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")


@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the FastAPI application")
    uvicorn.run(app, host="0.0.0.0", port=8000)