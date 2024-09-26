import re
from typing import Dict, List, Tuple
import uuid

# Statement prefixes
STATEMENT_PREFIX = ["s:", "v:", "ref:", "blank-node:"]

def preprocess_ttl(ttl_text: str) -> str:
    """
    Preprocesses a TTL (Turtle) text by normalizing whitespace and punctuation.

    This function performs the following transformations:
    1. Replaces multiple whitespace characters with a single space.
    2. Ensures that semicolons and commas are followed by a space unless they 
       are followed by another punctuation mark or the end of the text.
    3. Removes extra spaces before periods.

    Args:
        ttl_text (str): The input TTL text to preprocess.

    Returns:
        str: The preprocessed TTL text.
    """
    preprocessed = re.sub(
        r'\s+|([;,])(?!\s)|(?<=[^;\s])\s*\.',
        lambda m: ' ' if m.group(0).isspace() else f'{m.group(1)} ' if m.group(1) else '.',
        ttl_text
    )
    return preprocessed.rstrip(' .')

def split_by_periods_keep_quotes(text: str) -> List[str]:
    pattern = r'\.\s+(?=(?:[^"]*"[^"]*")*[^"]*$)'
    sections = re.split(pattern, text)
    return [section.strip() for section in sections]

def split_by_semicolons_keep_quotes(text: str) -> List[str]:
    pattern = r';\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'
    statements = re.split(pattern, text)
    return [statement.strip() for statement in statements]

def split_by_spaces_keep_quotes(text: str) -> List[str]:
    pattern = r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+'
    return re.findall(pattern, text)

# def check_for_brackets(section: str, dictionary_of_sections: Dict[str, List[List[str]]]):
#     if "[" in section:
#         print("found [ on section: " + section + "\n")
#         # get the text between the brackets
#         start = section.find("[")
#         end = section.find("]") 
        
#         new_uuid = "blank-node:" + str(uuid.uuid4())
#         new_section = section[start+1:end].strip() # get the text between the brackets
#         print("new section: " + new_section + "endshere\n")
#         statements = split_by_semicolons_keep_quotes(new_section) # split by semicolons to get triples
#         print("statements: " + str(statements) + "\n")
#         dictionary_of_sections[new_uuid] = ([split_by_spaces_keep_quotes(statement) for statement in statements])
        
#         print("new uuid: " + new_uuid + "\n")
#         print("new section: " + new_section + "\n")
#         print("dictionary of sections: " + str(dictionary_of_sections[new_uuid]) + "\n") 
#         # remove the text between the brackets and the brackets
        
#         section = section[:start] + new_uuid + section[end+1:] 
#         print("section after removing brackets: " + section + "\n")
#         section = check_for_brackets(section, dictionary_of_sections)
#     return section      

# def check_for_brackets(section: str, dictionary_of_sections: Dict[str, List[List[str]]]):
#     if "[" in section:
#         # the function only checks for the brackets in the first level, if there are any brackets inside the brackets, the function will not work
        
#         start = section.find("[")
#         end = section.find("]") 
        
#         new_uuid = "blank-node:" + str(uuid.uuid4()) # create a new subject for the section
#         new_section = section[start+1:end].strip() # get the text between the brackets
#         statements = split_by_semicolons_keep_quotes(new_section) # split by semicolons to get triples
#         dictionary_of_sections[new_uuid] = ([split_by_spaces_keep_quotes(statement) for statement in statements]) # add the triples to the dictionary of blank nodes
#         section = section[:start] + new_uuid + section[end+1:] # remove the blank node from the section and add the new subject instead
#         section = check_for_brackets(section, dictionary_of_sections) # make a recursive call to check for more brackets
#     return section    

def check_for_brackets(section: str, dictionary_of_sections: Dict[str, List[List[str]]]) -> str:
    # This function processes a section of text, replacing bracketed content with UUIDs
    # and storing the content in a dictionary for later reference

    def process_brackets(text: str, start: int) -> Tuple[str, int]:
        # This nested function finds the matching closing bracket for an opening bracket
        # and returns the content inside the brackets along with the end position

        # Initialize a stack to keep track of nested brackets
        stack = 1
        end = start + 1

        # Loop through the text until we find the matching closing bracket
        while stack > 0 and end < len(text):
            if text[end] == '[':
                # If we find an opening bracket, increment the stack
                stack += 1
            elif text[end] == ']':
                # If we find a closing bracket, decrement the stack
                stack -= 1
            end += 1

        # Return the content inside the brackets (stripped of whitespace) and the end position
        return text[start+1:end-1].strip(), end

    def recursive_process(text: str) -> str:
        # This nested function recursively processes the text, handling nested brackets

        # Continue processing while there are still brackets in the text
        while '[' in text:
            # Find the position of the next opening bracket
            start = text.find('[')

            # Extract the content inside the brackets
            content, end = process_brackets(text, start)

            # Recursively process any nested brackets in the extracted content
            processed_content = recursive_process(content)

            # Generate a new UUID for this bracketed content
            new_uuid = f"blank-node:{uuid.uuid4()}"

            # Split the processed content into statements
            statements = split_by_semicolons_keep_quotes(processed_content)

            # Store the split statements in the dictionary, associated with the new UUID
            dictionary_of_sections[new_uuid] = [split_by_spaces_keep_quotes(statement) for statement in statements]

            # Replace the original bracketed content in the text with the new UUID
            text = text[:start] + new_uuid + text[end:]

        # Return the processed text
        return text

    # Start the recursive processing of the input section
    return recursive_process(section)



def split_by_sections(preprocessed_text: str, dictionary_of_sections: Dict[str, List[List[str]]]):
    # Split the text into sections by periods
    sections = split_by_periods_keep_quotes(preprocessed_text)
    result = {}
    prefixes = []
    
    for section in sections:    
        if section.startswith("@prefix"):
            print(section)
            prefixes.append(section)
        # create extra sections for the text between brackets
        section = check_for_brackets(section, dictionary_of_sections)
        stripped_section = section.strip() # remove leading and trailing whitespace
        statements = split_by_semicolons_keep_quotes(stripped_section) # split by semicolons to get triples
        subject = statements[0].split(" ")[0] # get the subject of the section - the first word of the first statement
        statements[0] = statements[0].replace(subject + " ", "")
        result[subject] = [split_by_spaces_keep_quotes(statement) for statement in statements]
    return result, "\n".join(prefixes)

def recursive_conversion(sections, predicate_chain, index_chain, object, subject):
    if object not in sections:
        return

    for triple in sections[object]:
        new_predicate_chain = predicate_chain.copy()
        new_index_chain = index_chain.copy()
        new_predicate_chain.append(triple[0])
        
        if triple[1].startswith(tuple(STATEMENT_PREFIX)):
            for i, obj in enumerate(triple[1:], start=1):
                obj = obj[:-1] if obj.endswith(',') else obj
                new_index = new_index_chain + [str(i)]
                recursive_conversion(sections, new_predicate_chain, new_index, obj, subject)
        else:
            predicates = "|".join(new_predicate_chain)
            for i, obj in enumerate(triple[1:], start=1):
                obj = obj[:-1] if obj.endswith(',') else obj
                new_index = new_index_chain + [str(i)]
                indexes = ",".join(new_index)
                answer.append(f'{subject} <{predicates}>[{indexes}] {obj}')

def convert_to_new_format_old(sections: Dict[str, List[List[str]]]) -> str:
    global answer
    answer = []
    
    for subject, triples in sections.items():
        # Skip statements where the subject starts with STATEMENT_PREFIX
        # These subjects are not the main subjects, but rather used in qualitative statements
        if subject.startswith(tuple(STATEMENT_PREFIX)):
            continue
        
        for i in range(len(triples)):
            predicate_chain = [triples[i][0]] # get the first element of the triple
            
            for j, obj in enumerate(triples[i][1:], start=1):
                if obj == "[":
                    print("this is inside [", triples[i] )
                        
                # check if obj ends with comma
                obj = obj[:-1] if obj.endswith(',') else obj
                
                if len(triples[i]) > 1 and triples[i][1].startswith(tuple(STATEMENT_PREFIX)):
                    recursive_conversion(sections, predicate_chain, [str(j)], obj, subject)
                else:
                    predicate = triples[i][0]
                    answer.append(f'{subject} <{predicate}>[{j}] {obj}')
    
    return "\n".join(answer)

def convert_to_new_format(sections: Dict[str, List[List[str]]]) -> str:
    global answer
    answer = []
    
    for subject, triples in sections.items():
        # Skip statements where the subject starts with STATEMENT_PREFIX
        # These subjects are not the main subjects, but rather used in qualitative statements
        if subject.startswith(tuple(STATEMENT_PREFIX)):
            continue
        
        for i in range(len(triples)):
            predicate_chain = [triples[i][0]] # get the first element of the triple

            for j, obj in enumerate(triples[i][1:], start=1):
                if obj == "[":
                    print("this is inside [", triples[i] )
                        
                # check if obj ends with comma
                obj = obj[:-1] if obj.endswith(',') else obj
                
                if len(triples[i]) > 1 and triples[i][1].startswith(tuple(STATEMENT_PREFIX)):
                    recursive_conversion(sections, predicate_chain, [str(j)], obj, subject)
                else:
                    predicate = triples[i][0]
                    answer.append(f'{subject} <{predicate}>[{j}] {obj}')
    
    return "\n".join(answer)

def main():
    with open('input.txt', 'r', encoding='utf-8') as input_file:
        ttl_text = input_file.read()
    
    dictionary_of_sections = {}
    preprocessed = preprocess_ttl(ttl_text)
    sections, prefixes = split_by_sections(preprocessed, dictionary_of_sections)
    # merge sections with dictionary_of_sections
    for key in dictionary_of_sections:
        sections[key] = dictionary_of_sections[key]
    
    new_format = prefixes + "\n" + convert_to_new_format(sections)
    
    with open('output.txt', 'w', encoding='utf-8') as output_file:
        output_file.write(new_format)

if __name__ == "__main__":
    main()
    
    
    # import re
# from typing import Dict, List, Tuple
# import uuid

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
#             # Collect prefix definitions
#             prefixes.append(section)
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

# def recursive_conversion(sections, predicate_chain, index_chain, object, subject):
#     # Recursively convert nested structures
#     if object not in sections:
#         return

#     for triple in sections[object]:
#         new_predicate_chain = predicate_chain.copy()
#         new_index_chain = index_chain.copy()
#         new_predicate_chain.append(triple[0])
        
#         if triple[1].startswith(tuple(STATEMENT_PREFIX)):
#             # Handle nested statements
#             for i, obj in enumerate(triple[1:], start=1):
#                 obj = obj[:-1] if obj.endswith(',') else obj
#                 new_index = new_index_chain + [str(i)]
#                 recursive_conversion(sections, new_predicate_chain, new_index, obj, subject)
#         else:
#             # Create new format entries
#             predicates = "|".join(new_predicate_chain)
#             for i, obj in enumerate(triple[1:], start=1):
#                 obj = obj[:-1] if obj.endswith(',') else obj
#                 new_index = new_index_chain + [str(i)]
#                 indexes = ",".join(new_index)
#                 answer.append(f'{subject} <{predicates}>[{indexes}] {obj}')

# def convert_to_new_format(sections: Dict[str, List[List[str]]]) -> str:
#     global answer
#     answer = []
    
#     for subject, triples in sections.items():
#         # Skip special statements
#         if subject.startswith(tuple(STATEMENT_PREFIX)):
#             continue
        
#         for i in range(len(triples)):
#             predicate_chain = [triples[i][0]]

#             for j, obj in enumerate(triples[i][1:], start=1):
#                 # Remove trailing comma if present
#                 obj = obj[:-1] if obj.endswith(',') else obj
                
#                 if len(triples[i]) > 1 and triples[i][1].startswith(tuple(STATEMENT_PREFIX)):
#                     # Handle nested structures
#                     recursive_conversion(sections, predicate_chain, [str(j)], obj, subject)
#                 else:
#                     # Create new format entry
#                     predicate = triples[i][0]
#                     answer.append(f'{subject} <{predicate}>[{j}] {obj}')
    
#     return "\n".join(answer)

# def main():
#     # Read input file
#     with open('input.txt', 'r', encoding='utf-8') as input_file:
#         ttl_text = input_file.read()
    
#     # Process the TTL text
#     dictionary_of_sections = {}
#     preprocessed_ttl = preprocess_ttl(ttl_text)
#     sections, prefixes = split_by_sections(preprocessed_ttl, dictionary_of_sections)
    
#     # Merge processed sections
#     for key in dictionary_of_sections:
#         sections[key] = dictionary_of_sections[key]
    
#     # Convert to new format
#     new_format = prefixes + "\n" + convert_to_new_format(sections)
    
#     # Write output file
#     with open('output.txt', 'w', encoding='utf-8') as output_file:
#         output_file.write(new_format)

# if __name__ == "__main__":
#     main()









# import re
# from typing import Dict, List, Tuple
# import uuid

# # Prefixes used to identify special statements in the TTL format
# SPECIAL_STATEMENT_PREFIXES = ["s:", "v:", "ref:", "blank-node:"]

# def normalize_ttl_text(ttl_text: str) -> str:
#     """
#     Normalizes TTL (Turtle) text by standardizing whitespace and punctuation.
#     """
#     # Standardize whitespace and ensure proper spacing around punctuation
#     normalized = re.sub(
#         r'\s+|([;,])(?!\s)|(?<=[^;\s])\s*\.',
#         lambda m: ' ' if m.group(0).isspace() else f'{m.group(1)} ' if m.group(1) else '.',
#         ttl_text
#     )
#     # Remove trailing spaces and periods
#     return normalized.rstrip(' .')

# def split_preserving_quotes(text: str, delimiter: str) -> List[str]:
#     # Split text by delimiter while preserving content within quotes
#     # Use a raw string for the regex pattern to avoid escape sequence issues
#     pattern = r'{}\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'.format(re.escape(delimiter))
#     segments = re.split(pattern, text)
#     return [segment.strip() for segment in segments]

# def tokenize_statement(statement: str) -> List[str]:
#     # Break a statement into tokens, preserving quoted content and URIs
#     return re.findall(r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+', statement)

# def process_nested_structures(section: str, blank_node_map: Dict[str, List[List[str]]]) -> str:
#     def find_matching_bracket(text: str, start: int) -> Tuple[str, int]:
#         # Find the matching closing bracket and return the content and end position
#         bracket_count = 1
#         end = start + 1
#         while bracket_count > 0 and end < len(text):
#             if text[end] == '[':
#                 bracket_count += 1
#             elif text[end] == ']':
#                 bracket_count -= 1
#             end += 1
#         return text[start+1:end-1].strip(), end

#     def process_recursively(text: str) -> str:
#         # Process nested structures recursively
#         while '[' in text:
#             start = text.find('[')
#             content, end = find_matching_bracket(text, start)
            
#             processed_content = process_recursively(content)
            
#             # Generate a unique ID for the blank node
#             blank_node_id = f"blank-node:{uuid.uuid4()}"
            
#             # Parse the processed content and store in the blank node map
#             statements = split_preserving_quotes(processed_content, ';')
#             blank_node_map[blank_node_id] = [tokenize_statement(stmt) for stmt in statements]
            
#             # Replace the bracketed content with the blank node ID
#             text = text[:start] + blank_node_id + text[end:]
#         return text

#     return process_recursively(section)

# def parse_ttl_content(normalized_text: str, blank_node_map: Dict[str, List[List[str]]]):
#     # Split the normalized text into sections
#     sections = split_preserving_quotes(normalized_text, '.')
#     parsed_data = {}
#     prefix_definitions = []
    
#     for section in sections:    
#         if section.startswith("@prefix"):
#             # Collect prefix definitions
#             prefix_definitions.append(section)
#         else:
#             # Process and parse non-prefix sections
#             processed_section = process_nested_structures(section, blank_node_map)
#             statements = split_preserving_quotes(processed_section, ';')
            
#             # Extract subject and process statements
#             subject = statements[0].split(" ")[0]
#             statements[0] = statements[0].replace(subject + " ", "")
#             parsed_data[subject] = [tokenize_statement(stmt) for stmt in statements]
    
#     return parsed_data, "\n".join(prefix_definitions)

# def convert_nested_structure(parsed_data, predicate_chain, index_chain, current_object, main_subject):
#     # Recursively convert nested structures to the new format
#     if current_object not in parsed_data:
#         return

#     for triple in parsed_data[current_object]:
#         new_predicate_chain = predicate_chain.copy()
#         new_index_chain = index_chain.copy()
#         new_predicate_chain.append(triple[0])
        
#         if triple[1].startswith(tuple(SPECIAL_STATEMENT_PREFIXES)):
#             # Handle nested special statements
#             for i, obj in enumerate(triple[1:], start=1):
#                 obj = obj[:-1] if obj.endswith(',') else obj
#                 new_index = new_index_chain + [str(i)]
#                 convert_nested_structure(parsed_data, new_predicate_chain, new_index, obj, main_subject)
#         else:
#             # Create new format entries for regular statements
#             predicate_sequence = "|".join(new_predicate_chain)
#             for i, obj in enumerate(triple[1:], start=1):
#                 obj = obj[:-1] if obj.endswith(',') else obj
#                 new_index = new_index_chain + [str(i)]
#                 index_sequence = ",".join(new_index)
#                 converted_triples.append(f'{main_subject} <{predicate_sequence}>[{index_sequence}] {obj}')


# def transform_to_new_format(parsed_data: Dict[str, List[List[str]]]) -> str:
#     global converted_triples
#     converted_triples = []
    
#     for subject, triples in parsed_data.items():
#         # Skip special statements
#         if subject.startswith(tuple(SPECIAL_STATEMENT_PREFIXES)):
#             continue
        
#         for triple in triples:
#             # Check if the triple is not empty before processing
#             if triple:
#                 predicate_chain = [triple[0]]

#                 for i, obj in enumerate(triple[1:], start=1):
#                     # Remove trailing comma if present
#                     obj = obj[:-1] if obj.endswith(',') else obj
                    
#                     if len(triple) > 1 and triple[1].startswith(tuple(SPECIAL_STATEMENT_PREFIXES)):
#                         # Handle nested structures
#                         convert_nested_structure(parsed_data, predicate_chain, [str(i)], obj, subject)
#                     else:
#                         # Create new format entry for regular statements
#                         predicate = triple[0]
#                         converted_triples.append(f'{subject} <{predicate}>[{i}] {obj}')
#             else:
#                 print(f"Warning: Empty triple found for subject {subject}")
    
#     return "\n".join(converted_triples)

# def main():
#     # Read the input TTL file
#     with open('input.txt', 'r', encoding='utf-8') as input_file:
#         raw_ttl_text = input_file.read()
    
#     # Process the TTL content
#     blank_node_map = {}
#     normalized_text = normalize_ttl_text(raw_ttl_text)
#     parsed_data, prefix_definitions = parse_ttl_content(normalized_text, blank_node_map)
    
#     # Merge parsed data with blank node map
#     parsed_data.update(blank_node_map)
    
#     # Transform the parsed data to the new format
#     transformed_data = prefix_definitions + "\n" + transform_to_new_format(parsed_data)
    
#     # Write the transformed data to the output file
#     with open('output.txt', 'w', encoding='utf-8') as output_file:
#         output_file.write(transformed_data)

# if __name__ == "__main__":
#     main()

