import os
import re
import time
import logging
import tempfile
from typing import Dict, List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from logging.handlers import RotatingFileHandler


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


# Statement prefixes
STATEMENT_PREFIX = ("v:", "s:")
TRIPLE_STATEMENT_PREFIX = ("p:", "psv:")


def preprocess_ttl(ttl_text: str) -> str:
    """
    Preprocess the Turtle format text by removing line breaks and excess spaces.
    
    Args:
    ttl_text (str): The input Turtle format text.
    
    Returns:
    str: Preprocessed text as a single line.
    """
    preprocessed = re.sub(r'\s+', ' ', ttl_text)
    preprocessed = re.sub(r'([;,])(?!\s)', r'\1 ', preprocessed)
    preprocessed = re.sub(r'\s+\.', ' .', preprocessed)
    preprocessed = preprocessed.strip()
    if preprocessed.endswith('.'):
        preprocessed = preprocessed[:-1]
    return preprocessed


def split_by_periods_keep_quotes(text: str) -> List[str]:
    """
    Split the text by periods, preserving quoted content.

    Args:
    text (str): The input text to split.

    Returns:
    List[str]: A list of sections split by periods.
    """
    pattern = r'\.\s+(?=(?:[^"]*"[^"]*")*[^"]*$)'
    sections = re.split(pattern, text)
    return [section.strip() for section in sections]


def split_by_semicolons_keep_quotes(text: str) -> List[str]:
    """
    Split the text by semicolons, preserving quoted content.

    Args:
    text (str): The input text to split.

    Returns:
    List[str]: A list of statements split by semicolons.
    """
    pattern = r';\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'
    statements = re.split(pattern, text)
    return [statement.strip() for statement in statements]


def split_by_spaces_keep_quotes(text: str) -> List[str]:
    """
    Split the text by spaces, preserving quoted content and handling special cases.

    Args:
    text (str): The input text to split.

    Returns:
    List[str]: A list of tokens split by spaces.
    """
    pattern = r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+'
    return re.findall(pattern, text)


def split_by_sections(preprocessed_text: str) -> Dict:
    """
    Split the preprocessed text into sections based on periods.
    
    Args:
    preprocessed_text (str): The preprocessed Turtle format text.
    
    Returns:
    Dict: A dictionary with subjects as keys and lists of statement parts as values.
    """
    sections = split_by_periods_keep_quotes(preprocessed_text)
    result = {}
    
    for section in sections:
        if "[" in section:
            continue
        
        stripped_section = section.strip()
        statements = split_by_semicolons_keep_quotes(stripped_section)
        subject = statements[0].split(" ")[0]
        statements[0] = statements[0].replace(subject + " ", "")
        result[subject] = [split_by_spaces_keep_quotes(statement) for statement in statements]
    return result


def recursive_conversion(sections, predicate_chain, index_chain, object, subject):
    """
    Recursively convert nested triples to the new format.

    Args:
    sections (Dict): The dictionary of sections.
    predicate_chain (List[str]): The current chain of predicates.
    index_chain (List[str]): The current chain of indices.
    object (str): The current object being processed.
    subject (str): The original subject of the statement.
    """
    if object not in sections:
        return

    for triple in sections[object]:
        new_predicate_chain = predicate_chain.copy()
        new_index_chain = index_chain.copy()
        new_predicate_chain.append(triple[0])
        
        if triple[0].startswith(TRIPLE_STATEMENT_PREFIX):
            for i, obj in enumerate(triple[1:], start=1):
                obj = obj[:-1] if obj.endswith(',') else obj
                new_index = new_index_chain + [str(i)]
                recursive_conversion(sections, new_predicate_chain, new_index, obj, subject)
        else:
            predicate = "|".join(new_predicate_chain)
            for i, obj in enumerate(triple[1:], start=1):
                obj = obj[:-1] if obj.endswith(',') else obj
                new_index = new_index_chain + [str(i)]
                index = ",".join(new_index)
                answer.append(f'{subject} <{predicate}>[{index}] {obj}')


def convert_to_new_format(sections: Dict[str, List[List[str]]]) -> str:
    """
    Convert the parsed sections to the new format.

    Args:
    sections (Dict[str, List[List[str]]]): The dictionary of parsed sections.

    Returns:
    str: The converted text in the new format.
    """
    global answer
    answer = []
    
    for subject, triples in sections.items():
        if subject.startswith(STATEMENT_PREFIX):
            continue
        
        for triple in triples:
            predicate_chain = [triple[0]]
            index_chain = []
            
            if triple[0].startswith(TRIPLE_STATEMENT_PREFIX):
                for i, obj in enumerate(triple[1:], start=1):
                    obj = obj[:-1] if obj.endswith(',') else obj
                    recursive_conversion(sections, predicate_chain, [str(i)], obj, subject)
            else:
                predicate = triple[0]
                for i, obj in enumerate(triple[1:], start=1):
                    obj = obj[:-1] if obj.endswith(',') else obj
                    answer.append(f'{subject} <{predicate}>[{i}] {obj}')
    
    return "\n".join(answer)


@app.post("/convert")
async def convert_ttl(file: UploadFile = File(...)) -> FileResponse:
    """
    Convert uploaded TTL file to the new format.

    Args:
    file (UploadFile): The uploaded TTL file.

    Returns:
    FileResponse: The converted file as a downloadable response.
    """
    try:
        start_time = time.time()
        logger.info(f"Received file: {file.filename}")
        
        contents = await file.read()
        ttl_text = contents.decode("utf-8")
        
        TTLInput(ttl_text=ttl_text)
        
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

        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as temp_file:
            temp_file.write(new_format)
            temp_file_path = temp_file.name

        logger.info(f"Converted file saved to: {temp_file_path}")

        return FileResponse(
            temp_file_path,
            media_type='text/plain',
            filename="converted_ttl.txt",
            headers={"X-Execution-Time": str(execution_time)}
        )

    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the application status.

    Returns:
    dict: A dictionary containing the status of the application.
    """
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting the FastAPI application")
    uvicorn.run(app, host="0.0.0.0", port=8000)