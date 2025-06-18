#!/bin/bash

# Define the module names in English
modules=("communication_module" "encryption" "task_orchestrator" "movement_calculation" "movement_limiter" "drives" "gps" "barometer" "drone_status_control" "mission_control" "sprayer_control" "sprayer" "camera" "message_sending" "internal_navigation_system")

# Create the main modules folder
mkdir -p modules

# Loop through each module name and create the folder structure
for module in "${modules[@]}"; do
  module_path="modules/$module"
  mkdir -p "$module_path/config"
  mkdir -p "$module_path/module"
  touch "$module_path/Dockerfile"
  touch "$module_path/start.py"
  touch "$module_path/module/__init__.py"
  touch "$module_path/module/producer.py"
  touch "$module_path/module/consumer.py"
done

echo "Folder structure created successfully!"