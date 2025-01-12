import os
import subprocess

# Define the path to the directory containing projects
directory_path = '/path/to/your/projects'

# Function to get the list of projects sorted by modification time
def get_sorted_projects(dir_path):
    try:
        # Get all entries in the directory with full path
        projects_with_path = [os.path.join(dir_path, project) for project in os.listdir(dir_path)]

        # Filter only directories, ignoring files
        projects_dirs = [project for project in projects_with_path if os.path.isdir(project)]

        # Sort projects based on last modification time in descending order
        projects_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        return projects_dirs
    except Exception as e:
        print(f"Error in getting projects: {e}")
        return []

# Function to open the newest project
def open_newest_project(proj_list):
    if proj_list:
        newest_project = proj_list[0]
        try:
            print(f"Opening project: {newest_project}")
            subprocess.run(['open', newest_project])
        except Exception as e:
            print(f"Failed to open project: {e}")
    else:
        print("No projects available to open.")

# Get the sorted list of projects
sorted_projects = get_sorted_projects(directory_path)

# Open the newest project
open_newest_project(sorted_projects)