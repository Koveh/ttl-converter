# import pandas as pd
# import math
# import warnings

# def analyze_csv(file_path, suppress_warnings=True):
#     try:
#         if suppress_warnings:
#             # Suppress the specific warning
#             warnings.filterwarnings("ignore", category=pd.errors.ParserWarning)

#         # Read the CSV file with explicit engine specification
#         df = pd.read_csv(file_path, sep='¤', header=None, encoding='utf-8', engine='python')
        
#         # Assign column names
#         column_names = ['Enumeration', 'Subject', 'Predicate', 'Index', 'Object', 'Language']
#         df.columns = column_names[:len(df.columns)]
        
#         # Calculate unique counts and bits required
#         results = []
#         for column in df.columns:
#             unique_count = df[column].nunique()
#             bits_required = math.ceil(math.log2(unique_count)) if unique_count > 1 else 1
#             results.append({
#                 'Column': column,
#                 'Unique Count': unique_count,
#                 'Bits Required': bits_required
#             })
        
#         # Create a DataFrame for results
#         results_df = pd.DataFrame(results)
        
#         # Display the results
#         print(results_df.to_string(index=False))
        
#         # Optional: Save results to a CSV file
#         results_df.to_csv('column_analysis.csv', index=False)
#         print("\nResults saved to 'column_analysis.csv'")
        
#     except Exception as e:
#         print(f"An error occurred: {e}")

# if __name__ == "__main__":
#     file_path = 'output.csv'
#     analyze_csv(file_path)


import pandas as pd
import math

# Read the CSV file with ¤ as the separator
input_file_path = 'output.csv'
df = pd.read_csv(input_file_path, sep='¤')

# Function to calculate the number of bits required to represent unique elements
def bits_required(unique_count):
    if unique_count > 0:
        return math.ceil(math.log2(unique_count))
    else:
        return 0

# Initialize a list to hold the formatted output
output = []

# Iterate through each column to count unique elements and calculate bits required
for column in df.columns:
    unique_count = df[column].nunique()
    bits = bits_required(unique_count)
    output.append(f"{column:<12} {unique_count:<14} {bits:<14}")

# Print the header
print(f"{'Column':<12} {'Unique Count':<14} {'Bits Required':<14}")

# Print each row of the output
for line in output:
    print(line)