---
mode: "agent"
tools: [
  "run_maven_tests",
  "analyze_coverage_gaps",
  "analyze_java_file",
  "generate_junit_test",
  "write_test_file",
  "str_replace",
  "git_add_all",
  "git_commit",
  "git_push"
]
description: "Generate tests to improve coverage in math package"
---

## Rules

- Work ONLY on: `org.apache.commons.lang3.math` package
- Current branch: `phase4-coverage-agent` (never switch)
- Do ONE iteration then STOP

## Workflow

1. Baseline: Run tests, get current coverage
2. Find gap: Pick ONE uncovered method in NumberUtils
3. Analyze: Read the method's source code
4. Generate: Create test skeleton
5. Write: Save test file
6. Customize: Use str_replace to fix TODOs with real values
7. Verify: Run tests - must pass
8. Commit: Stage, commit, push
9. STOP: Report what you did

## Example str_replace Usage
```python
# Before (generated skeleton):
assertEquals(0, result, "TODO: Specify expected value");

# After (you analyze source and determine correct value):
str_replace(
  filePath="src/test/java/org/apache/commons/lang3/math/NumberUtilsTest.java",
  oldText='assertEquals(0, result, "TODO: Specify expected value");',
  newText='assertEquals(15, result, "max(5,10,15) should return 15");'
)
```

## Commit Message Format
```
[Coverage] Add test for NumberUtils.methodName

- Tests: [what you tested]
- Edge case: [e.g., "negative numbers"]
```

## When to Stop

- One test committed successfully
- Test fails after 2 fix attempts
- Any tool error

After stopping, tell me what method you tested and what to do next.