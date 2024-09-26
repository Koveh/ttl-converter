# import csv
# import re

# def process_line(line):
#     # Skip lines that end with a period.
#     if line.strip().endswith('.'):
#         return None
    
#     # Split the line into parts
#     parts = line.strip().split(' ', 2)
#     if len(parts) < 3:
#         return None
    
#     subject, predicate, rest = parts
    
#     # Process the subject
#     subject = subject.lstrip('<').rstrip('>')
    
#     # Process the predicate
#     predicate = predicate.lstrip('<').rstrip('>')
    
#     # Extract the object and language tag if present
#     match = re.match(r'(\[(\d+)\])?\s*(.+?)(@\w+)?$', rest)
#     if not match:
#         return None
    
#     index, obj, lang = match.group(2), match.group(3), match.group(4)
    
#     # Process the object
#     obj = obj.strip('"')  # Remove surrounding quotes if present
    
#     # Combine the processed parts
#     result = [subject, predicate, index or '1', obj]
#     if lang:
#         result.append(lang.lstrip('@'))
    
#     return result

# def process_file(input_file, output_file):
#     try:
#         with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
#             writer = csv.writer(outfile, delimiter='¤')
#             for i, line in enumerate(infile):
#                 processed_line = process_line(line)
#                 if processed_line:
#                     writer.writerow([i] + processed_line)
    
#     except Exception as e:
#         print(f"Error occurred: {e}")

# if __name__ == "__main__":
#     process_file('output.txt', 'output.csv')#

import pandas as pd
import math
import re
import csv

def parse_prefix(line):
    match = re.match(r'@prefix (\w+): <(.+)> \.', line.strip())
    if match:
        return match.groups()
    return None

def parse_data_line(line):
    match = re.match(r'(\S+)\s+<(\S+)>\[(\d+)\]\s+(.+)', line.strip())
    if match:
        subject, predicate, index, obj = match.groups()
        return [subject, predicate, index, obj.strip('"')]
    return None

def process_file(input_file, output_file):
    try:
        prefixes = {}
        data = []
        parsing_prefixes = True

        with open(input_file, 'r', encoding='utf-8') as file:
            for line in file:
                if parsing_prefixes:
                    prefix = parse_prefix(line)
                    if prefix:
                        prefixes[prefix[0]] = prefix[1]
                    elif line.strip():  # If line is not empty, switch to data parsing
                        parsing_prefixes = False
                
                if not parsing_prefixes:
                    parsed = parse_data_line(line)
                    if parsed:
                        data.append(parsed)

        # Save processed data to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter='\'')
            writer.writerow(['Subject', 'Predicate', 'Index', 'Object'])  # Write header
            writer.writerows(data)

        print(f"Processed data saved to {output_file}")

        # Calculate and display statistics
        df = pd.DataFrame(data, columns=['Subject', 'Predicate', 'Index', 'Object'])
        results = []
        for column in df.columns:
            unique_count = df[column].nunique()
            bits_required = math.ceil(math.log2(unique_count)) if unique_count > 1 else 1
            results.append({
                'Column': column,
                'Unique Count': unique_count,
                'Bits Required': bits_required
            })
        
        results_df = pd.DataFrame(results)
        print("\nData Analysis:")
        print(results_df.to_string(index=False))
        
        print("\nPrefix Declarations:")
        for prefix, uri in prefixes.items():
            print(f"{prefix}: {uri}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    input_file = 'output.txt'  # Your input file
    output_file = 'output.csv'  # The output CSV file
    process_file(input_file, output_file)