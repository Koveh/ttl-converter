import pandas as pd

# Define input and output file paths
input_file_path = 'output.txt'
output_file_path = 'output.csv'

# Read the input file
with open(input_file_path, 'r') as file:
    lines = file.readlines()

# Remove lines that begin with "@prefix"
filtered_lines = [line for line in lines if not line.strip().startswith('@prefix')]

# Process the remaining lines
processed_lines = []
for line in filtered_lines:
    # Strip and split the line as per the instructions
    line = line.strip()
    parts = line.split(" <")
    if len(parts) == 2:
        prefix = parts[0].strip()
        rest = parts[1].split(">[")
        if len(rest) == 2:
            mid_part = rest[0].strip()
            end_parts = rest[1].split("] ")
            if len(end_parts) == 2:
                index = end_parts[0].strip()
                value = end_parts[1].strip()
                # Reformat the line using ¤ as separator
                new_line = f"{prefix}¤{mid_part}¤{index}¤{value}"
                processed_lines.append(new_line)

# Convert the processed lines to a list of lists suitable for DataFrame
cleaned_data = [line.split("¤") for line in processed_lines if line.count("¤") == 3]

# Create a DataFrame with the cleaned data
df = pd.DataFrame(cleaned_data, columns=["Prefix", "Property", "Index", "Value"])

# Save the DataFrame to a CSV file
df.to_csv(output_file_path, sep='¤', index=False)

print(f"Data has been processed and saved to {output_file_path}")