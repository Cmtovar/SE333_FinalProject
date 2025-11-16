"""Git automation tools for MCP server."""
import subprocess
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("Git Tools")
REPO_DIR = Path(__file__).parent


@mcp.tool
def git_status() -> str:
    """
    Get current git repository status.
    
    Returns:
        Plain text output showing repository state
    """
    try:
        # Run git status with short format for cleaner output
        # 
        # The --short flag outputs in "porcelain" format: "XY filename"
        # This is a machine-readable format with 2 status characters:
        #   Position 0 (X) = staged status (what's in the index)
        #   Position 1 (Y) = unstaged status (what's in working directory)
        #   Position 3+ = filename (after "XY ")
        # 
        # Status codes:
        #   M = modified
        #   A = added (new file)
        #   D = deleted
        #   ?? = untracked (git doesn't know about this file)
        #   (space) = clean/unchanged
        # 
        # Example outputs:
        #   "M  server.py"      = modified and staged, working directory clean
        #   " M server.py"      = modified in working directory, not staged
        #   "MM server.py"      = staged modification + additional unstaged changes
        #   "A  git_tools.py"   = new file, staged
        #   "?? temp.txt"       = untracked file
        #   "D  old_file.py"    = deleted and staged
        # 
        # Why two positions? A file can be in different states simultaneously.
        # For example, you can stage changes, then make more changes after staging.
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = result.stdout.strip()
        
        # Check if repository is clean (no output means clean)
        if output == "":
            return "Repository Status: Clean\nNo changes to commit"
        else:
            return f"Repository Status: Changes detected\n\n{output}"
            
    except subprocess.TimeoutExpired:
        return "Error: Git status command timed out"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool
def git_add_all() -> str:
    """
    Stage all changes for commit.
    Relies on .gitignore to exclude unwanted files.
    
    Returns:
        Success message with count of staged files
    """
    try:
        # Stage all changes using git add .
        # The '.' means add everything in current directory and subdirectories
        # .gitignore file automatically excludes patterns like:
        # - target/ (Maven build output)
        # - .venv/ (Python virtual environment)
        # - __pycache__/ (Python cache)
        # - *.class (compiled Java files)
        addResult = subprocess.run(
            ["git", "add", "."],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check if add command succeeded
        if addResult.returncode != 0:
            return f"Error: Failed to stage files\n{addResult.stderr}"
        
        # Get status to see what was actually staged
        statusResult = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        stagedFiles = []
        
        # Parse status output to find staged files
        # Looking for lines where position 0 (staged status) is not a space
        # Position 0 = A (added), M (modified), or D (deleted) means staged
        for line in statusResult.stdout.split('\n'):
            if line == "":
                continue
            
            # Check first character (position 0) for staged status
            if line[0] in ['A', 'M', 'D']:
                # Extract filename starting at position 3
                # Format: "XY filename" so filename starts after "XY "
                filename = line[3:].strip()
                stagedFiles.append(filename)
        
        fileCount = len(stagedFiles)
        
        if fileCount > 0:
            # Show first 10 files
            fileList = '\n  '.join(stagedFiles[:10])
            
            # If more than 10 files, indicate there are more
            if fileCount > 10:
                remaining = fileCount - 10
                fileList = fileList + f"\n  ... and {remaining} more file(s)"
            
            return f"Staging Status: Success\nStaged {fileCount} file(s)\n\nFiles:\n  {fileList}"
        else:
            return "Staging Status: No changes to stage"
            
    except subprocess.TimeoutExpired:
        return "Error: Git add command timed out"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool
def git_commit(message: str) -> str:
    """
    Commit staged changes with the provided message.
    
    Args:
        message: Commit message (used exactly as provided)
    
    Returns:
        Commit status and hash
    """
    try:
        # Check if there are any changes to commit
        # git status --short returns empty string when repository is clean
        # Clean = no modified files, nothing staged, nothing to commit
        statusResult = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if statusResult.stdout.strip() == "":
            return "Error: No staged changes to commit"
        
        # Execute commit with provided message
        # -m flag specifies the commit message
        # Message is used exactly as provided (no modification)
        commitResult = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check if commit succeeded
        if commitResult.returncode != 0:
            return f"Error: Commit failed\n{commitResult.stderr}"
        
        output = commitResult.stdout
        
        # Try to extract commit hash from output
        # Git commit output format: [branch hash] message
        # Example: [main a3f2c1b] Add Calculator tests
        commitHash = "unknown"
        
        if "[" in output:
            # Find content between brackets
            hashStart = output.find("[") + 1
            hashEnd = output.find("]", hashStart)
            
            if hashEnd > hashStart:
                # Extract text between brackets
                hashPart = output[hashStart:hashEnd]
                
                # Split on whitespace
                # Format is "branch hash" so hash is second element
                parts = hashPart.split()
                
                if len(parts) >= 2:
                    commitHash = parts[1]
        
        return f"Commit Status: Success\nCommit hash: {commitHash}\nMessage: {message}"
        
    except subprocess.TimeoutExpired:
        return "Error: Git commit command timed out"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool
def git_push(remote: str = "origin") -> str:
    """
    Push commits to remote repository.
    Uses existing git credential helper for authentication.
    
    Args:
        remote: Name of remote repository (default: origin)
    
    Returns:
        Push status
    """
    try:
        # Push to specified remote
        # Git automatically uses stored credentials from:
        #   - macOS: Keychain
        #   - Windows: Git Credential Manager
        #   - Linux: credential helper (configured in git config)
        # 
        # No need to handle authentication in this code - git does it automatically
        # As long as you've pushed from terminal before, credentials are saved
        pushResult = subprocess.run(
            ["git", "push", remote],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Check if push succeeded
        if pushResult.returncode != 0:
            # Push failed - return error information
            errorOutput = pushResult.stderr
            return f"Push Status: Failed\nRemote: {remote}\n\nError:\n{errorOutput}"
        
        # Push succeeded
        # Git writes progress info (Counting objects, Writing objects, etc.) to stderr
        # stdout is typically empty for git push
        # Combine both streams to show user the full output
        output = pushResult.stdout + pushResult.stderr
        
        return f"Push Status: Success\nRemote: {remote}\n\nOutput:\n{output}"
        
    except subprocess.TimeoutExpired:
        return "Error: Git push command timed out after 60 seconds"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool
def git_pull_request(base: str = "main", title: str = "", body: str = "") -> str:
    """
    Create a pull request using GitHub CLI.
    Requires GitHub CLI (gh) to be installed and authenticated.
    
    Args:
        base: Base branch to merge into (default: main)
        title: Pull request title
        body: Pull request description
    
    Returns:
        Pull request creation status and URL
    """
    try:
        # Check if gh CLI is installed
        checkResult = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if checkResult.returncode != 0:
            return "Error: GitHub CLI not found - install from https://cli.github.com"
        
        # Create pull request
        # --base: branch to merge into
        # --title: PR title
        # --body: PR description
        prResult = subprocess.run(
            ["gh", "pr", "create", 
             "--base", base,
             "--title", title,
             "--body", body],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if prResult.returncode != 0:
            return f"Error: Pull request creation failed\n{prResult.stderr}"
        
        # Extract PR URL from output
        # gh pr create outputs the URL as the last line
        output = prResult.stdout.strip()
        lines = output.split('\n')
        prUrl = lines[-1] if len(lines) > 0 else "URL not found"
        
        return f"Pull Request Created\nURL: {prUrl}\nBase: {base}\nTitle: {title}"
        
    except FileNotFoundError:
        return "Error: GitHub CLI not found - install from https://cli.github.com"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"