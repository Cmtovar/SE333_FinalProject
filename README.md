# MCP Testing Agent

**Author:** Cristian Tovar  
**Course:** SE333 Final Project  
**GitHub:** https://github.com/Cmtovar/SE333_FinalProject

## Overview

This project is an intelligent software agent built using Model Context Protocol (MCP). It automatically generates JUnit test cases and improves code coverage for Java Maven projects.

The agent uses Claude Haiku through VS Code to analyze code, generate tests, run Maven, parse JaCoCo coverage reports, and manage Git workflows.

## How It Works

In the MCP protocol, the LLM is positioned so that it must first speak with the server. The LLM can only make changes to your codebase if it talks through one of the mcp.tools you give them. This makes the tools critical to making the LLM capable of doing its work.

## Setup

**Requirements:**
- VS Code with Chat view
- Node.js 18+
- Python 3.8+
- Java 11+ and Maven 3.6+
- Git

**Start the server:**
```bash
fastmcp run server.py
```

Note: `python server.py` doesn't work with VS Code Agent mode. Use `fastmcp run server.py` instead.

**Connect to VS Code:**
1. Press `CTRL+SHIFT+P`
2. Search for "MCP: Add Server"
3. Paste your MCP server URL
4. Enable Auto-Approve in Chat Settings

## Tools

### Phase 2: Testing Tools

**analyze_java_file** - Reads Java files so the LLM can understand the code structure

**generate_junit_test** - Generates JUnit test code using Arrange-Act-Assert framework. I referenced my older assignments to get a template for what a unit test structure looks like. The template leaves assertions as TODO markers.

**write_test_file** - Writes the generated test code into a real *.java file

**str_replace** - Modifies existing test files. The template code leaves the assertion as a TODO that the LLM can go back to fix after the Java file is written.

**run_maven_tests** - Executes Maven tests. This literally allows the LLM to use the terminal.

**analyze_coverage_gaps** - Parses JaCoCo XML reports from `target/site/jacoco/jacoco.xml`. When the LLM reads the report, it ends up being a lot of data without interpretation. I tried to offer test suggestions based on method type (e.g. "get", "set", "equals").

### Phase 3: Git Tools

**git_status** - Returns current git status. Other git tools incorporate git status in their implementations. This method lets the LLM see git status on its own to know that its work is done.

**git_add_all** - Stages all changes using `git add .` with the `--short` option. I decided to use the `--short` option and parse that because it requires less text parsing.

**git_commit** - Creates commits. Each time a commit is made, there is a hash code identifier. I wanted to keep this close because it's how I'd log which commits were created by the LLM and which were created by myself.

**git_pull_request** - Creates pull requests. A git pull request is made by the LLM to be approved by the human.

## Results

The agent completed 5 testing iterations on a real codebase from D2L. It generated 5 new passing JUnit test cases, all following the Arrange-Act-Assert framework.

Each iteration improved code coverage. The process was tracked in `coverage_log.md`.

## Design Decisions

**Distributed Control:** Rather than relying solely on prompt engineering through `tester.prompt.md`, control logic was embedded within individual tools. This makes the code more maintainable.

**Two-Phase Test Generation:** The template leaves assertions as TODO markers. Suppose the logic of the method changes such that a partition isn't where it used to be. If the LLM already wrote Java code to a *.java file and it exists in the codebase, it makes more sense to modify the existing assertions than to rewrite the file every time.

**Scope Limitation:** My prompt purposefully minimized the scope of what the AI could see in the codebase. I only wanted to see the AI make one new passing test each iteration.

## Project Structure

```
.
├── server.py              # MCP server with all tools
├── .github/
│   └── prompts/
│       └── tester.prompt.md
├── coverage_log.md        # Manual tracking of LLM commits
└── codebase/              # Test target (from D2L)
```

## Video Demo

See the 4-minute demo showing the agent running through iterations and generating tests automatically.

## Notes

Phase 5 (creative extensions) was not completed due to time constraints.

---

**Last Updated:** November 16, 2025
