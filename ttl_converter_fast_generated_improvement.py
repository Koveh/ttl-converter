
import re
from typing import Dict, List, Tuple
import uuid
from collections import defaultdict

STATEMENT_PREFIX = frozenset(["s:", "v:", "ref:", "blank-node:"])

def preprocess_ttl(ttl_text: str) -> str:
    return re.sub(r'\s+|([;,])(?!\s)|(?<=[^;\s])\s*\.', 
                  lambda m: ' ' if m.group(0).isspace() else f'{m.group(1)} ' if m.group(1) else '.', 
                  ttl_text).rstrip(' .')

def split_by_delimiter(text: str, delimiter: str) -> List[str]:
    pattern = re.compile(f'{re.escape(delimiter)}\\s*(?=(?:[^"]*"[^"]*")*[^"]*$)')
    return [segment.strip() for segment in pattern.split(text)]

def tokenize_statement(statement: str) -> List[str]:
    return re.findall(r'"(?:\\.|[^"\\])*"[^\s]*|"(?:\\.|[^"\\])*"|[^\s"]+', statement)

def process_nested_structures(section: str) -> Tuple[str, Dict[str, List[List[str]]]]:
    blank_node_map = {}
    stack = []
    result = []
    current = ''
    
    for char in section:
        if char == '[':
            if stack:
                current += char
            stack.append(len(result))
        elif char == ']' and stack:
            if len(stack) > 1:
                current += char
            else:
                blank_node_id = f"blank-node:{uuid.uuid4()}"
                statements = split_by_delimiter(current, ';')
                blank_node_map[blank_node_id] = [tokenize_statement(stmt) for stmt in statements]
                result.append(blank_node_id)
                current = ''
            stack.pop()
        elif stack:
            current += char
        else:
            result.append(char)
    
    return ''.join(result), blank_node_map

def parse_ttl_content(normalized_text: str) -> Tuple[Dict[str, List[List[str]]], str]:
    sections = split_by_delimiter(normalized_text, '.')
    parsed_data = defaultdict(list)
    prefix_definitions = []
    blank_node_map = {}
    
    for section in sections:
        if section.startswith("@prefix"):
            prefix_definitions.append(section + ' .')
        else:
            processed_section, new_blank_nodes = process_nested_structures(section)
            blank_node_map.update(new_blank_nodes)
            statements = split_by_delimiter(processed_section, ';')
            if statements:
                subject, *predicates = statements[0].split(None, 1)
                parsed_data[subject].extend([tokenize_statement(stmt) for stmt in predicates + statements[1:]])
    
    parsed_data.update(blank_node_map)
    return dict(parsed_data), "\n".join(prefix_definitions)

def convert_to_new_format(sections: Dict[str, List[List[str]]]) -> List[str]:
    def recursive_conversion(object, predicate_chain, index_chain):
        if object not in sections:
            return []
        
        result = []
        for i, triple in enumerate(sections[object], start=1):
            new_predicate_chain = predicate_chain + [triple[0]]
            new_index_chain = index_chain + [str(i)]
            
            if len(triple) > 1 and triple[1].startswith(STATEMENT_PREFIX):
                result.extend(recursive_conversion(triple[1], new_predicate_chain, new_index_chain))
            else:
                predicates = "|".join(new_predicate_chain)
                indexes = ",".join(new_index_chain)
                for j, obj in enumerate(triple[1:], start=1):
                    obj = obj[:-1] if obj.endswith(',') else obj
                    result.append(f'{subject} <{predicates}>[{indexes},{j}] {obj}')
        return result

    answer = []
    for subject, triples in sections.items():
        if not subject.startswith(STATEMENT_PREFIX):
            answer.extend(recursive_conversion(subject, [], []))
    
    return answer

def main():
    with open('input.txt', 'r', encoding='utf-8') as input_file:
        ttl_text = input_file.read()
    
    preprocessed_ttl = preprocess_ttl(ttl_text)
    sections, prefixes = parse_ttl_content(preprocessed_ttl)
    new_format = prefixes + "\n" + "\n".join(convert_to_new_format(sections))
    
    with open('output.txt', 'w', encoding='utf-8') as output_file:
        output_file.write(new_format)

if __name__ == "__main__":
    main()