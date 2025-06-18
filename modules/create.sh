#!/bin/bash

# Define the content for requirements.txt
requirements_content="confluent-kafka==2.0.2
configparser
flask
requests"

# Traverse all directories and locate the config folder
find . -type d -name "config" | while read -r config_dir; do
  # Create the requirements.txt file with the specified content
  echo "$requirements_content" > "$config_dir/requirements.txt"
  echo "Created requirements.txt in $config_dir"
done

echo "Script execution completed!"