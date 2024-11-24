import os
import json

# Define the folder containing the JSON files
folder_path = 'test_post_data/json_files'

# List to hold the combined JSON data
combined_data = []

# Iterate through each file in the folder
for filename in os.listdir(folder_path):
    if filename.endswith('.json'):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            combined_data.append(data)

# Write the combined data to a new JSON file
output_file = 'combined_data.json'
with open(output_file, 'w', encoding='utf-8') as outfile:
    json.dump(combined_data, outfile, indent=4)

print(f'Combined JSON data has been written to {output_file}')