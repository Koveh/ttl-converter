import re
import uuid
from typing import Iterator, Tuple, Dict, List
from collections import defaultdict

STATEMENT_PREFIX = frozenset(["s:", "v:", "ref:", "blank-node:"])

def preprocess_line(line: str) -> str:
    return re.sub(r'\s+|([;,])(?!\s)|(?<=[^;\s])\s*\.', 
                  lambda m: ' ' if m.group(0).isspace() else f'{m.group(1)} ' if m.group(1) else '.', 
                  line.strip())

def process_file(file_path: str) -> Iterator[Tuple[str, str]]:
    current_subject = None
    current_predicate = None
    current_statement = []

    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = preprocess_line(line)
            if line.startswith('@prefix'):
                yield 'prefix', line
                continue

            if line.startswith(('<', 'wd:', 'blank-node:')):
                if current_subject:
                    yield 'statement', ' '.join(current_statement)
                current_subject = line.split()[0]
                current_statement = [current_subject]
                current_predicate = None
            elif line.startswith(('a ', '<', 'wdt:', 'p:')):
                if current_predicate:
                    yield 'statement', ' '.join(current_statement)
                current_predicate = line.split()[0]
                current_statement = [current_subject, current_predicate]
            else:
                current_statement.extend(line.split())

            if line.endswith('.'):
                yield 'statement', ' '.join(current_statement)
                current_statement = []
                current_predicate = None

    if current_statement:
        yield 'statement', ' '.join(current_statement)

def parse_statement(statement: str) -> Tuple[str, List[List[str]]]:
    parts = statement.split()
    subject = parts[0]
    predicates = []
    current_predicate = []

    for part in parts[1:]:
        if part in ('a', 'wdt:', 'p:') or part.startswith(('<', 'wdt:', 'p:')):
            if current_predicate:
                predicates.append(current_predicate)
            current_predicate = [part]
        else:
            current_predicate.append(part)

    if current_predicate:
        predicates.append(current_predicate)

    return subject, predicates

def process_nested_structures(statement: str) -> Tuple[str, Dict[str, List[List[str]]]]:
    blank_node_map = {}
    stack = []
    result = []
    current = ''
    
    for char in statement:
        if char == '[':
            if stack:
                current += char
            stack.append(len(result))
        elif char == ']' and stack:
            if len(stack) > 1:
                current += char
            else:
                blank_node_id = f"blank-node:{uuid.uuid4()}"
                blank_node_map[blank_node_id] = current.strip().split(';')
                result.append(blank_node_id)
                current = ''
            stack.pop()
        elif stack:
            current += char
        else:
            result.append(char)
    
    return ''.join(result), blank_node_map

def convert_to_new_format(statement: str, blank_nodes: Dict[str, List[str]]) -> Iterator[str]:
    def process_predicate(subj, pred_chain, index_chain, obj):
        if obj in blank_nodes:
            for i, nested_pred in enumerate(blank_nodes[obj], start=1):
                new_pred_chain = pred_chain + [nested_pred.split()[0]]
                new_index_chain = index_chain + [str(i)]
                yield from process_predicate(subj, new_pred_chain, new_index_chain, ' '.join(nested_pred.split()[1:]))
        else:
            predicates = '|'.join(pred_chain)
            indexes = ','.join(index_chain)
            yield f"{subj} <{predicates}>[{indexes}] {obj}"

    subject, predicates = parse_statement(statement)
    for i, predicate in enumerate(predicates, start=1):
        yield from process_predicate(subject, [predicate[0]], [str(i)], ' '.join(predicate[1:]))

def main(input_file: str, output_file: str):
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for item_type, item in process_file(input_file):
            if item_type == 'prefix':
                out_file.write(item + '\n')
            elif item_type == 'statement':
                processed_statement, blank_nodes = process_nested_structures(item)
                for new_format_line in convert_to_new_format(processed_statement, blank_nodes):
                    out_file.write(new_format_line + '\n')

if __name__ == "__main__":
    main('einstein.ttl', 'output.txt')