# from fastapi import FastAPI, File, UploadFile, HTTPException
# from fastapi.responses import FileResponse
# from pydantic import BaseModel, field_validator
# import re
# from typing import List, Dict, Any, Tuple
# from collections import defaultdict
# import logging
# import os
# from logging.handlers import RotatingFileHandler
# import tempfile

# # Set up logging
# log_dir = os.path.dirname(os.path.abspath(__file__))
# log_file = os.path.join(log_dir, 'log.txt')

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=1)
# handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)

# logger.addHandler(handler)

# app = FastAPI()

# # Global variables
# statement_prefix = ("v:", "s:")
# triple_statement_prefix = ("p:", "psv:")

# class TTLInput(BaseModel):
#     ttl_text: str

#     @field_validator('ttl_text')
#     @classmethod
#     def validate_ttl_text(cls, v: str) -> str:
#         if not v.strip():
#             raise ValueError('TTL text cannot be empty')
#         if not re.search(r'\w+:\w+', v):
#             raise ValueError('Invalid TTL format')
#         return v

# # ... [rest of the functions remain the same] ...

# def preprocess_ttl(ttl_text: str) -> str:
#     preprocessed = re.sub(r'\s+', ' ', ttl_text)
#     preprocessed = re.sub(r'([;,])(?!\s)', r'\1 ', preprocessed)
#     preprocessed = re.sub(r'\s+\.', ' .', preprocessed)
#     if preprocessed[-1] == ".":
#         preprocessed = preprocessed[:-1]
#     return preprocessed.strip()

# def split_by_sections(preprocessed_text: str) -> Dict:
#     sections = re.split(r'\.\\s+(?=[^\s])', preprocessed_text)
#     result = dict()
    
#     if sections[-1][-1] == ".":
#         sections[-1] = sections[-1][:-1]
    
#     for section in sections:
#         stripped_section = section.strip()
#         statements = [statement.strip() for statement in stripped_section.split(";")]
#         subject = statements[0].split(" ")[0]
#         statements[0] = statements[0].replace(subject + " ", "")
#         statement_parts = [statement.split(" ") for statement in statements]
#         result[subject] = statement_parts
#     return result

# def recursive_conversion(sections, predicate_chain, index_chain, object, subject):
#     if object not in sections:
#         logger.warning(f"Statement not found: {object}. Skipping.")
#         return

#     for triple in sections[object]:
#         new_predicate_chain = predicate_chain.copy()
#         new_index_chain = index_chain.copy()
#         new_predicate_chain.append(triple[0])
        
#         if triple[0].startswith(triple_statement_prefix):
#             for i, obj in enumerate(triple[1:], start=1):
#                 if obj.endswith(','):
#                     obj = obj[:-1]
#                 new_index = new_index_chain + [str(i)]
#                 recursive_conversion(sections, new_predicate_chain, new_index, obj, subject)
#         else:
#             predicate = "|".join(new_predicate_chain)
#             for i, obj in enumerate(triple[1:], start=1):
#                 if obj.endswith(','):
#                     obj = obj[:-1]
#                 new_index = new_index_chain + [str(i)]
#                 index = ",".join(new_index)
#                 answer.append(f"{subject} <{predicate}>[{index}] {obj}")

# def convert_to_new_format(sections: Dict[str, List[List[str]]]) -> str:
#     global answer
#     answer = []
    
#     for subject, triples in sections.items():
#         if subject.startswith(statement_prefix):
#             continue
        
#         for triple in triples:
#             predicate_chain = [triple[0]]
#             index_chain = []
            
#             if triple[0].startswith(triple_statement_prefix):
#                 for i, obj in enumerate(triple[1:], start=1):
#                     if obj.endswith(','):
#                         obj = obj[:-1]
#                     recursive_conversion(sections, predicate_chain, [str(i)], obj, subject)
#             else:
#                 predicate = triple[0]
#                 for i, obj in enumerate(triple[1:], start=1):
#                     if obj.endswith(','):
#                         obj = obj[:-1]
#                     answer.append(f"{subject} <{predicate}>[{i}] {obj}")
    
#     return "\n".join(answer)

# @app.post("/convert")
# async def convert_ttl(file: UploadFile = File(...)):
#     try:
#         logger.info(f"Received file: {file.filename}")
        
#         # Read the contents of the uploaded file
#         contents = await file.read()
#         ttl_text = contents.decode("utf-8")
        
#         # Validate the TTL text
#         TTLInput(ttl_text=ttl_text)  # This will raise an error if validation fails
        
#         logger.info("Starting TTL conversion")
#         preprocessed = preprocess_ttl(ttl_text)
#         logger.debug(f"Preprocessed TTL: {preprocessed}")
#         sections = split_by_sections(preprocessed)
#         logger.debug(f"Split sections: {sections}")
#         new_format = convert_to_new_format(sections)
#         logger.info("TTL conversion completed successfully")

#         # Create a temporary file to store the converted content
#         with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt') as temp_file:
#             temp_file.write(new_format)
#             temp_file_path = temp_file.name

#         logger.info(f"Converted file saved to: {temp_file_path}")

#         # Return the file as a downloadable response
#         return FileResponse(temp_file_path, media_type='text/plain', filename="converted_ttl.txt")

#     except Exception as e:
#         logger.error(f"Conversion failed: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=400, detail=f"Conversion failed: {str(e)}")

# @app.get("/health")
# async def health_check():
#     logger.info("Health check endpoint accessed")
#     return {"status": "healthy"}

# if __name__ == "__main__":
#     import uvicorn
#     logger.info("Starting the FastAPI application")
#     uvicorn.run(app, host="0.0.0.0", port=8000)

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

# Global variables
statement_prefix = ("v:", "s:")
triple_statement_prefix = ("p:", "psv:")

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

def preprocess_ttl(ttl_text: str) -> str:
    preprocessed = re.sub(r'\s+', ' ', ttl_text)
    preprocessed = re.sub(r'([;,])(?!\s)', r'\1 ', preprocessed)
    preprocessed = re.sub(r'\s+\.', ' .', preprocessed)
    if preprocessed[-1] == ".":
        preprocessed = preprocessed[:-1]
    return preprocessed.strip()

def split_by_sections(preprocessed_text: str) -> Dict:
    sections = re.split(r'\.\\s+(?=[^\s])', preprocessed_text)
    result = dict()
    
    if sections[-1][-1] == ".":
        sections[-1] = sections[-1][:-1]
    
    for section in sections:
        stripped_section = section.strip()
        statements = [statement.strip() for statement in stripped_section.split(";")]
        subject = statements[0].split(" ")[0]
        statements[0] = statements[0].replace(subject + " ", "")
        statement_parts = [statement.split(" ") for statement in statements]
        result[subject] = statement_parts
    return result

def recursive_conversion(sections, predicate_chain, index_chain, object, subject):
    if object not in sections:
        logger.warning(f"Statement not found: {object}. Skipping.")
        return

    for triple in sections[object]:
        new_predicate_chain = predicate_chain.copy()
        new_index_chain = index_chain.copy()
        new_predicate_chain.append(triple[0])
        
        if triple[0].startswith(triple_statement_prefix):
            for i, obj in enumerate(triple[1:], start=1):
                if obj.endswith(','):
                    obj = obj[:-1]
                new_index = new_index_chain + [str(i)]
                recursive_conversion(sections, new_predicate_chain, new_index, obj, subject)
        else:
            predicate = "|".join(new_predicate_chain)
            for i, obj in enumerate(triple[1:], start=1):
                if obj.endswith(','):
                    obj = obj[:-1]
                new_index = new_index_chain + [str(i)]
                index = ",".join(new_index)
                answer.append(f"{subject} <{predicate}>[{index}] {obj}")

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
                        obj = obj[:-1]
                    recursive_conversion(sections, predicate_chain, [str(i)], obj, subject)
            else:
                predicate = triple[0]
                for i, obj in enumerate(triple[1:], start=1):
                    if obj.endswith(','):
                        obj = obj[:-1]
                    answer.append(f"{subject} <{predicate}>[{i}] {obj}")
    
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