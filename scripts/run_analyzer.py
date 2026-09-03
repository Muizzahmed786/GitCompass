import sys
import json
from pathlib import Path

# Add the server directory to python path
sys.path.insert(0, str(Path(__file__).parent / 'server'))

from app.services.structure_analyzer import analyze_repository_structure

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_analyzer.py <path_to_repo>")
        sys.exit(1)
        
    repo_path = sys.argv[1]
    print(f"Analyzing {repo_path}...")
    
    try:
        structure = analyze_repository_structure(repo_path)
        print(json.dumps(structure.model_dump(), indent=2))
    except Exception as e:
        print(f"Error analyzing repository: {e}")

if __name__ == "__main__":
    main()
