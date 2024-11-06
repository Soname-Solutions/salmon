import subprocess
import re

NA_VALUE = "N/A"


def _get_commit_history():
    """
    Retrieves the full commit history with tags and messages from the current Git repository.

    Returns:
        list: A list of strings, each representing a line from the commit history.
    """
    try:
        # Get the full commit history with tags and messages
        result = subprocess.run(
            ["git", "log", "--decorate=full", "--pretty=format:%H %d"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.split("\n")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return []


def _find_current_commit_and_latest_ver(commit_history):
    """
    Finds the current commit hash and the latest version tag in the given commit history.

    This function searches through the commit history for tags matching the pattern `refs/tags/ver_x.x`
    where `x.x` represents arbitrary numbers. It returns the current commit hash and the latest version found.

    Args:
        commit_history (list): A list of strings representing the commit history.

    Returns:
        tuple: A tuple containing the current commit hash (str) and the latest version occured (str) or None if no version is found.
    """
    pattern = re.compile(r"refs/tags/(ver_\d+\.\d+)")
    latest_commit_hash = NA_VALUE

    for entry in commit_history:
        if latest_commit_hash == NA_VALUE:
            latest_commit_hash = entry.split(" ", 1)[0]
        _, refs = entry.split(" ", 1)
        match = pattern.search(refs)
        if match:
            version = match.group(1)
            return latest_commit_hash, version

    return latest_commit_hash, NA_VALUE


def get_current_commit_and_latest_ver():
    """
    Retrieves the current commit hash and the latest version tag from the current Git repository.

    Returns:
        tuple: A tuple containing the current commit hash (str) and the latest version (str) or None if an error occurs.
    """
    try:
        commit_history = _get_commit_history()
        return _find_current_commit_and_latest_ver(commit_history)
    except:
        return NA_VALUE, NA_VALUE
