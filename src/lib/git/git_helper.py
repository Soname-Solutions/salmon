import subprocess
import re


def get_owner_and_repo_name():
    try:
        # Get the remote origin URL
        git_remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], text=True
        ).strip()

        # Use regex to parse owner and repo name from the URL
        match = re.match(
            r"(?:git@|https://)([\w.-]+)[:/]([\w-]+)/([\w-]+)(?:.git)?", git_remote_url
        )
        if not match:
            raise ValueError("Could not parse repo and owner from the remote URL.")

        owner, repo = match.group(2), match.group(3)
        return owner, repo

    except subprocess.CalledProcessError:
        raise Exception(
            "Unable to retrieve Git remote URL. Make sure this is a Git repository with a remote set."
        )
    except Exception as e:
        raise Exception(f"Error identifying Git repo details: {e}")
