import re
from typing import Dict, List, Tuple
import uuid
import time

# Statement prefixes used to identify special statements in the TTL format
STATEMENT_PREFIX = ["s:", "v:", "ref:", "blank-node:"]

def preprocess_ttl(ttl_text: str) -> str:
    """
    Preprocesses a TTL (Turtle) text by normalizing whitespace and punctuation.
    """
    # Use regex to normalize whitespace and ensure proper spacing around punctuation
    preprocessed = re.sub(
        r'\s+|([;,])(?!\s)|(?<=[^;\s])\s*\.',
        lambda m: ' ' if m.group(0).isspace() else f'{m.group(1)} ' if m.group(1) else '.',
        ttl_text
    )
    # Remove trailing spaces and periods
    return preprocessed.rstrip(' .')

def split_by_periods_keep_quotes(text: str) -> List[str]:
    """
    Split the text by periods, but keep quoted content intact.
    """
    # Regex pattern to split by periods outside of quoted content
    pattern = r'\.\s+(?=(?:[^"]*"[^"]*")*[^"]*$)'
    sections = re.split(pattern, text)
    # Strip leading and trailing whitespace from each section
    return [section.strip() for section in sections]

def split_by_semicolons_keep_quotes(text: str) -> List[str]:
    """
    Split the text by semicolons, but keep quoted content intact.
    """
    # Regex pattern to split by semicolons outside of quoted content
    pattern = r';\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'
    statements = re.split(pattern, text)
    # Strip leading and trailing whitespace from each statement
    return [statement.strip() for statement in statements]

def split_by_spaces_keep_quotes(text: str) -> List[str]:
    """
    Split the text by spaces, but keep quoted content and URIs intact.
    """
    # Regex pattern to split by spaces, but keep quoted content intact
    pattern = r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+'
    return re.findall(pattern, text)

def check_for_brackets(section: str, dictionary_of_sections: Dict[str, List[List[str]]]) -> str:
    """
    Process a section of text, replacing bracketed content with UUIDs.
    """

    def process_brackets(text: str, start: int) -> Tuple[str, int]:
        """
        Find the matching closing bracket for an opening bracket.
        """
        stack = 1
        end = start + 1
        # Iterate through the text to find the matching closing bracket
        while stack > 0 and end < len(text):
            if text[end] == '[':
                stack += 1
            elif text[end] == ']':
                stack -= 1
            end += 1
        # Return the content inside the brackets and the position after the closing bracket
        return text[start + 1:end - 1].strip(), end

    def recursive_process(text: str) -> str:
        """
        Recursively process the text, handling nested brackets.
        """
        while '[' in text:
            start = text.find('[')
            content, end = process_brackets(text, start)
            # Recursively process any nested brackets
            processed_content = recursive_process(content)
            # Generate a new UUID for this bracketed content
            new_uuid = f"blank-node:{uuid.uuid4()}"
            # Split the processed content into statements and store in dictionary
            statements = split_by_semicolons_keep_quotes(processed_content)
            dictionary_of_sections[new_uuid] = [split_by_spaces_keep_quotes(statement) for statement in statements]
            # Replace the original bracketed content with the new UUID
            text = text[:start] + new_uuid + text[end:]
        return text

    return recursive_process(section)

def split_by_sections(preprocessed_text: str, dictionary_of_sections: Dict[str, List[List[str]]]) -> Tuple[Dict[str, List[List[str]]], str]:
    """
    Split the text into sections by periods.
    """
    sections = split_by_periods_keep_quotes(preprocessed_text)
    result = {}
    prefixes = []
    
    for section in sections:
        if section.startswith("@prefix"):
            # Collect prefix definitions, ensuring the full URI is preserved
            prefixes.append(section + ' .')
        else:
            # Process bracketed content
            section = check_for_brackets(section, dictionary_of_sections)
            stripped_section = section.strip()
            statements = split_by_semicolons_keep_quotes(stripped_section)
            # Extract subject and process statements
            subject = statements[0].split(" ")[0]
            statements[0] = statements[0].replace(subject + " ", "")
            result[subject] = [split_by_spaces_keep_quotes(statement) for statement in statements]
    
    return result, "\n".join(prefixes)

def convert_and_write_to_file(sections: Dict[str, List[List[str]]], output_file):
    """
    Convert sections to the required format and write to file.
    """
    def recursive_conversion(predicate_chain, index_chain, object, subject):
        """
        Recursively convert nested structures and write to file.
        """
        if object not in sections:
            return

        for triple in sections[object]:
            if not triple:  # Skip empty triples
                print(f"Warning: Empty triple found for object {object}")
                continue
            
            new_predicate_chain = predicate_chain + [triple[0]]
            
            if len(triple) > 1 and triple[1].startswith(tuple(STATEMENT_PREFIX)) and object != triple[1]:
                for i, obj in enumerate(triple[1:], start=1):
                    obj = obj[:-1] if obj.endswith(',') else obj
                    new_index = index_chain + [str(i)]
                    recursive_conversion(new_predicate_chain, new_index, obj, subject)
            else:
                predicates = "|".join(new_predicate_chain)
                for i, obj in enumerate(triple[1:], start=1):
                    obj = obj[:-1] if obj.endswith(',') else obj
                    new_index = index_chain + [str(i)]
                    indexes = ",".join(new_index)
                    output_file.write(f'{subject} <{predicates}>[{indexes}] {obj}\n')

    for subject, triples in sections.items():
        if subject.startswith(tuple(STATEMENT_PREFIX)):
            continue
        
        for triple in triples:
            if not triple:
                print(f"Warning: Empty triple found for subject {subject}")
                continue

            predicate_chain = [triple[0]]

            for i, obj in enumerate(triple[1:], start=1):
                obj = obj[:-1] if obj.endswith(',') else obj
                
                if len(triple) > 1 and triple[1].startswith(tuple(STATEMENT_PREFIX)) and triple[1] != subject:
                    recursive_conversion(predicate_chain, [str(i)], obj, subject)
                else:
                    predicate = triple[0]
                    output_file.write(f'{subject} <{predicate}>[{i}] {obj}\n')

def main():
    """
    Main function to read input, process TTL, and write output.
    """
    try:
        with open('einstein.ttl', 'r', encoding='utf-8') as input_file:
            ttl_text = input_file.read()
    except FileNotFoundError:
        print("Input file not found.")
        return
    
    dictionary_of_sections = {}
    
    start_time = time.time()
    preprocessed_ttl = preprocess_ttl(ttl_text)
    sections, prefixes = split_by_sections(preprocessed_ttl, dictionary_of_sections)
    end_time = time.time()
    print(f"Preprocessing executed in {end_time - start_time} seconds.")
    
    sections.update(dictionary_of_sections)
    
    start_time = time.time()
    try:
        with open('output.txt', 'w', encoding='utf-8') as output_file:
            output_file.write(prefixes + "\n")
            convert_and_write_to_file(sections, output_file)
    except IOError as e:
        print(f"Error writing to output file: {e}")
        return
    end_time = time.time()
    print(f"Conversion executed in {end_time - start_time} seconds.")

if __name__ == "__main__":
    main()

# import re
# from typing import Dict, List, Tuple
# import uuid
# import time

# # Statement prefixes used to identify special statements in the TTL format
# STATEMENT_PREFIX = ["s:", "v:", "ref:", "blank-node:"]

# def preprocess_ttl(ttl_text: str) -> str:
#     """
#     Preprocesses a TTL (Turtle) text by normalizing whitespace and punctuation.
#     """
#     # Use regex to normalize whitespace and ensure proper spacing around punctuation
#     preprocessed = re.sub(
#         r'\s+|([;,])(?!\s)|(?<=[^;\s])\s*\.',
        
#         lambda m: ' ' if m.group(0).isspace() else f'{m.group(1)} ' if m.group(1) else '.',
#         ttl_text
#     )
#     # Remove trailing spaces and periods
#     return preprocessed.rstrip(' .')

# def split_by_periods_keep_quotes(text: str) -> List[str]:
#     # Split the text by periods, but keep quoted content intact
#     pattern = r'\.\s+(?=(?:[^"]*"[^"]*")*[^"]*$)'
#     sections = re.split(pattern, text)
#     return [section.strip() for section in sections]

# def split_by_semicolons_keep_quotes(text: str) -> List[str]:
#     # Split the text by semicolons, but keep quoted content intact
#     pattern = r';\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'
#     statements = re.split(pattern, text)
#     return [statement.strip() for statement in statements]

# def split_by_spaces_keep_quotes(text: str) -> List[str]:
#     # Split the text by spaces, but keep quoted content and URIs intact
#     pattern = r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+'
#     return re.findall(pattern, text)

# def check_for_brackets(section: str, dictionary_of_sections: Dict[str, List[List[str]]]) -> str:
#     # Process a section of text, replacing bracketed content with UUIDs

#     def process_brackets(text: str, start: int) -> Tuple[str, int]:
#         # Find the matching closing bracket for an opening bracket
#         stack = 1
#         end = start + 1
#         while stack > 0 and end < len(text):
#             if text[end] == '[':
#                 stack += 1
#             elif text[end] == ']':
#                 stack -= 1
#             end += 1
#         return text[start+1:end-1].strip(), end

#     def recursive_process(text: str) -> str:
#         # Recursively process the text, handling nested brackets
#         while '[' in text:
#             start = text.find('[')
#             content, end = process_brackets(text, start)
            
#             # Recursively process any nested brackets
#             processed_content = recursive_process(content)
            
#             # Generate a new UUID for this bracketed content
#             new_uuid = f"blank-node:{uuid.uuid4()}"
            
#             # Split the processed content into statements and store in dictionary
#             statements = split_by_semicolons_keep_quotes(processed_content)
#             dictionary_of_sections[new_uuid] = [split_by_spaces_keep_quotes(statement) for statement in statements]
            
#             # Replace the original bracketed content with the new UUID
#             text = text[:start] + new_uuid + text[end:]
#         return text

#     # Start the recursive processing of the input section
#     return recursive_process(section)

# def split_by_sections(preprocessed_text: str, dictionary_of_sections: Dict[str, List[List[str]]]):
#     # Split the text into sections by periods
#     sections = split_by_periods_keep_quotes(preprocessed_text)
#     result = {}
#     prefixes = []
    
#     for section in sections:    
#         if section.startswith("@prefix"):
#             # Collect prefix definitions, ensuring the full URI is preserved
#             prefixes.append(section + ' .')
#         else:
#             # Process bracketed content
#             section = check_for_brackets(section, dictionary_of_sections)
#             stripped_section = section.strip()
#             statements = split_by_semicolons_keep_quotes(stripped_section)
            
#             # Extract subject and process statements
#             subject = statements[0].split(" ")[0]
#             statements[0] = statements[0].replace(subject + " ", "")
#             result[subject] = [split_by_spaces_keep_quotes(statement) for statement in statements]
    
#     return result, "\n".join(prefixes)

# def convert_and_write_to_file(sections: Dict[str, List[List[str]]], output_file):
#     def recursive_conversion(predicate_chain, index_chain, object, subject):
#         if object not in sections:
#             return

#         for triple in sections[object]:
#             if not triple:  # Skip empty triples
#                 print(f"Warning: Empty triple found for object {object}")
#                 continue
            
#             new_predicate_chain = predicate_chain + [triple[0]]
            
#             if len(triple) > 1 and triple[1].startswith(tuple(STATEMENT_PREFIX)) and object != triple[1]:
#                 # Handle nested statements
#                 for i, obj in enumerate(triple[1:], start=1):
#                     obj = obj[:-1] if obj.endswith(',') else obj
#                     new_index = index_chain + [str(i)]
#                     recursive_conversion(new_predicate_chain, new_index, obj, subject)
#             else:
#                 # Create new format entries
#                 predicates = "|".join(new_predicate_chain)
#                 for i, obj in enumerate(triple[1:], start=1):
#                     obj = obj[:-1] if obj.endswith(',') else obj
#                     new_index = index_chain + [str(i)]
#                     indexes = ",".join(new_index)
#                     output_file.write(f'{subject} <{predicates}>[{indexes}] {obj}\n')

#     for subject, triples in sections.items():
#         # Skip special statements
#         if subject.startswith(tuple(STATEMENT_PREFIX)):
#             continue
        
#         for triple in triples:
#             if not triple:
#                 print(f"Warning: Empty triple found for subject {subject}")
#                 continue

#             predicate_chain = [triple[0]]

#             for i, obj in enumerate(triple[1:], start=1):
#                 # Remove trailing comma if present
#                 obj = obj[:-1] if obj.endswith(',') else obj
                
#                 if len(triple) > 1 and triple[1].startswith(tuple(STATEMENT_PREFIX)) and triple[1] != subject:
#                     # Handle nested structures
#                     recursive_conversion(predicate_chain, [str(i)], obj, subject)
#                 else:
#                     # Create new format entry
#                     predicate = triple[0]
#                     output_file.write(f'{subject} <{predicate}>[{i}] {obj}\n')

# def main():
#     # Read input file

#     with open('einstein.ttl', 'r', encoding='utf-8') as input_file:
#         ttl_text = input_file.read()
    
#     # Process the TTL text
#     dictionary_of_sections = {}
    
#     start_time = time.time()
#     preprocessed_ttl = preprocess_ttl(ttl_text)
#     sections, prefixes = split_by_sections(preprocessed_ttl, dictionary_of_sections)
#     end_time = time.time()
#     execution_time = end_time - start_time
#     print(f"Preprocessing executed in {execution_time} seconds.")
    
#     # Merge processed sections
#     sections.update(dictionary_of_sections)
    
#     start_time = time.time()
#     # Write output file
#     with open('output.txt', 'w', encoding='utf-8') as output_file:
#         # Write prefixes
#         output_file.write(prefixes + "\n")
        
#         # Convert and write directly to file
#         convert_and_write_to_file(sections, output_file)
#     end_time = time.time()
#     execution_time = end_time - start_time
#     print(f"Conversion executed in {execution_time} seconds.")

# if __name__ == "__main__":
#     main()
