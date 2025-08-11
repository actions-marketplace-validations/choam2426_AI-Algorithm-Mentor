from src.config import get_github_config
from src.github_service import fetch_changed_files_for_commit
from src.logger import logger

def main():
    github_config = get_github_config()
    changed_files = fetch_changed_files_for_commit(github_config)
    logger.info(f"changed files collected: {len(changed_files)}")