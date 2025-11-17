import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("Testing Agent Server")

# Define paths
CODEBASE_DIR = Path(__file__).parent / "codebase"
REPO_DIR = Path(__file__).parent

# =============================================================================
# REGEX CAPTURE GROUPS EXPLANATION
# =============================================================================
# * Parentheses `()` create a "capture group"
# * Everything matched inside parentheses is saved and retrievable via .group()
# * .group(0) = entire match (everything the regex matched)
# * .group(1) = first capture group (first set of parentheses)
# * .group(2) = second capture group (second set of parentheses)
# * Groups are specific to EACH regex search - running a new re.search() 
#   or re.findall() will overwrite/replace the previous groups
# =============================================================================


# =============================================================================
# =============================================================================
# TEST GENERATION TOOLS (from test_tools.py)
# =============================================================================
# =============================================================================

@mcp.tool
def analyze_java_file(filePath: str) -> str:
    """
    Analyze a Java source file and extract method information.
    Returns a list of methods with their signatures.
    """
    try:
        fullPath = CODEBASE_DIR / filePath
        
        # Explicit check instead of implicit "if not"
        if fullPath.exists() == False:
            return f"Error: File not found at {fullPath}"
        
        with open(fullPath, 'r') as f:
            content = f.read()
        
        # Extract package name
        # What it means:
        # * `package` - literal text "package"
        # * `\s+` - one or more whitespace characters
        # * `([\w.]+)` - capture group 1: word characters or dots (package name like org.example.Amazon)
        packagePattern = r'package\s+([\w.]+)'
        packageMatch = re.search(packagePattern, content)
        
        if packageMatch == None:
            packageName = "unknown"
        else:
            # .group(0) = entire match ("package org.example.Amazon")
            # .group(1) = first capture group ("org.example.Amazon")
            packageName = packageMatch.group(1)
        
        # Extract class name
        # What it means:
        # * `public\s+` - "public" + whitespace
        # * `class\s+` - "class" + whitespace
        # * `(\w+)` - capture group 1: word characters (class name)
        classPattern = r'public\s+class\s+(\w+)'
        classMatch = re.search(classPattern, content)
        
        if classMatch == None:
            return "Error: Could not find public class declaration"
        
        # .group(0) = entire match ("public class DeliveryPrice")
        # .group(1) = first capture group ("DeliveryPrice")
        className = classMatch.group(1)
        
        # Extract public methods
        # What it means:
        # * `public\s+` - "public" + whitespace
        # * `([\w<>,\s\[\]]+)` - capture group 1: return type (allows generics like List<Item>)
        # * `\s+` - whitespace
        # * `(\w+)` - capture group 2: method name
        # * `\s*` - optional whitespace
        # * `\(` - literal opening parenthesis
        # * `([^)]*)` - capture group 3: anything except `)` (parameters)
        # * `\)` - literal closing parenthesis
        methodPattern = r'public\s+([\w<>,\s\[\]]+)\s+(\w+)\s*\(([^)]*)\)'
        methods = re.findall(methodPattern, content)
        
        if len(methods) == 0:
            return f"No public methods found in {className}"
        
        # Format output
        result = f"Package: {packageName}\n"
        result += f"Class: {className}\n\nPublic Methods:\n"
        
        for returnType, methodName, params in methods:
            # Skip constructors (method name matches class name)
            if methodName == className:
                continue
            
            if params.strip() == "":
                paramList = "no parameters"
            else:
                paramList = params.strip()
            
            result += f"- {returnType.strip()} {methodName}({paramList})\n"
        
        return result
        
    except Exception as e:
        return f"Error analyzing file: {e}"


@mcp.tool
def generate_junit_test(className: str, methodName: str, returnType: str, parameters: str = "") -> str:
    """
    Generate a JUnit 5 test case following AAA structure.
    
    Expected format:
    - className: PascalCase (e.g., "DeliveryPrice", "Calculator")
    - methodName: camelCase (e.g., "priceToAggregate", "add")
    - returnType: Java type (e.g., "double", "int", "List<Item>")
    - parameters: Full parameter list (e.g., "List<Item> cart" or "int a, int b")
    """
    try:
        # Generate test method name from camelCase method name
        # Input: "priceToAggregate" → Output: "testPriceToAggregate"
        testMethodName = f"test{methodName[0].upper()}{methodName[1:]}"
        
        # Create instance variable name from PascalCase class name
        # Input: "DeliveryPrice" → Output: "deliveryPrice"
        instanceName = className[0].lower() + className[1:]
        
        # Check if parameters include List
        hasListParam = (
            ("List<Item>" in parameters) or 
            ("List" in parameters)
        )
        
        # Build the test structure
        testLines = []
        testLines.append(f"    @Test")
        testLines.append(f'    @DisplayName("specification-based: {methodName} test case")')
        testLines.append(f"    public void {testMethodName}() {{")
        
        # ARRANGE: Create instance
        testLines.append(f"        {className} {instanceName} = new {className}();")
        testLines.append("")
        
        # ARRANGE: Setup test data
        if hasListParam:
            # Extract generic type from List<Type>
            listType = extract_list_type(parameters)
            testLines.append(f"        List<{listType}> testList = new ArrayList<>();")
            testLines.append(f"        // TODO: Add {listType} items to testList")
            testLines.append("")
            methodCall = f"{instanceName}.{methodName}(testList)"
        else:
            paramValues = generate_param_values(parameters)
            paramString = ", ".join(paramValues)
            methodCall = f"{instanceName}.{methodName}({paramString})"
        
        # ACT: Call method
        if returnType != "void":
            testLines.append(f"        {returnType} result = {methodCall};")
            testLines.append("")
        
        # ASSERT: Verify result (let LLM customize the expected values)
        assertion = generate_assertion(returnType, methodCall, returnType != "void")
        testLines.append(f"        {assertion}")
        
        testLines.append(f"    }}")
        
        return "\n".join(testLines)
        
    except Exception as e:
        return f"Error generating test: {e}"


def extract_list_type(parameters: str) -> str:
    """
    Extract the generic type from List<Type> parameter.
    
    Examples:
        Input: "List<Item> cart" → Output: "Item"
        Input: "List<String> names" → Output: "String"
    """
    if "List<" in parameters:
        # Find where "List<" starts, then skip past it to get to the type name
        # len("List<") = 5, so we add 5 to move past "List<" to the start of the type
        start = parameters.index("List<") + len("List<")
        
        # Find the closing ">" bracket after the type name
        end = parameters.index(">", start)
        
        # Extract everything between "List<" and ">"
        return parameters[start:end]
    else:
        # Default to Object if no List<> found
        return "Object"


def generate_param_values(parameters: str) -> list:
    """Generate default test values for method parameters."""
    paramValues = []
    
    if (parameters == "") or (parameters == "no parameters"):
        return paramValues
    
    params = parameters.split(',')
    
    for param in params:
        param = param.strip()
        
        if ' ' in param:
            paramType = param.split()[0]
        else:
            paramType = param
        
        if (paramType == "int") or (paramType == "Integer"):
            paramValues.append("1")
        elif (paramType == "double") or (paramType == "Double"):
            paramValues.append("1.0")
        elif paramType == "String":
            paramValues.append('"test"')
        elif (paramType == "boolean") or (paramType == "Boolean"):
            paramValues.append("true")
        else:
            paramValues.append("null")
    
    return paramValues


def generate_assertion(returnType: str, methodCall: str, hasResult: bool) -> str:
    """
    Generate appropriate assertion based on return type.
    Uses placeholder values - LLM should customize based on actual test logic.
    """
    if returnType == "void":
        return f"{methodCall};"
    elif (returnType == "double") or (returnType == "Double"):
        # Placeholder - LLM should replace 0.0 with actual expected value
        return 'assertEquals(0.0, result, "TODO: Specify expected value and assertion message");'
    elif (returnType == "int") or (returnType == "Integer"):
        # Placeholder - LLM should replace 0 with actual expected value
        return 'assertEquals(0, result, "TODO: Specify expected value and assertion message");'
    elif (returnType == "long") or (returnType == "Long"):
        # Placeholder - LLM should replace 0L with actual expected value
        return 'assertEquals(0L, result, "TODO: Specify expected value and assertion message");'
    elif (returnType == "boolean") or (returnType == "Boolean"):
        # LLM can choose assertTrue or assertFalse based on logic
        return "assertTrue(result); // TODO: Verify this is the expected boolean value"
    elif returnType == "String":
        # Placeholder - LLM should replace "expected" with actual expected string
        return 'assertEquals("expected", result, "TODO: Specify expected string");'
    elif "List<" in returnType:
        # For collections, check not null and optionally size
        return 'assertNotNull(result); // TODO: Add size checks or element assertions'
    else:
        # Generic object assertion
        return 'assertNotNull(result); // TODO: Add specific assertions for this type'


@mcp.tool
def write_test_file(className: str, packageName: str, testMethods: str) -> str:
    """
    Write a complete JUnit 5 test file to the test directory.
    """
    try:
        packagePath = packageName.replace('.', '/')
        
        testDir = CODEBASE_DIR / "src" / "test" / "java" / packagePath
        testFileName = f"{className}Test.java"
        testFilePath = testDir / testFileName
        
        testDir.mkdir(parents=True, exist_ok=True)
        
        # Using import java.util.*; for flexibility
        testClass = f"""package {packageName};

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

public class {className}Test {{
{testMethods}
}}
"""
        
        with open(testFilePath, 'w') as f:
            f.write(testClass)
        
        return f"Test file created successfully at: {testFilePath}"
        
    except Exception as e:
        return f"Error writing test file: {e}"


@mcp.tool
def run_maven_tests(cleanFirst: bool = True) -> str:
    """
    Execute Maven tests and return a human-readable summary.
    
    Args:
        cleanFirst: If True, run 'mvn clean' before testing for fresh build
    
    Returns:
        Plain text summary of test results including:
        - Pass/fail status
        - Test statistics (run, failures, errors, skipped)
        - Coverage report location
        - Failed test details
    """
    try:
        # Run maven clean if requested
        if cleanFirst == True:
            cleanResult = subprocess.run(
                ["mvn", "clean"],
                cwd=CODEBASE_DIR,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if cleanResult.returncode != 0:
                return f"Error: Maven clean failed\n{cleanResult.stderr}"
        
        # Run maven tests
        testResult = subprocess.run(
            ["mvn", "test"],
            cwd=CODEBASE_DIR,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Combine stdout and stderr
        output = testResult.stdout + testResult.stderr
        
        # Extract test statistics from Maven output
        # What it means:
        # * `Tests run:` - literal text "Tests run:"
        # * `\s*` - optional whitespace
        # * `(\d+)` - capture group 1: one or more digits (tests run count)
        # * `, Failures:` - literal text ", Failures:"
        # * `\s*(\d+)` - capture group 2: failures count
        # * Similar pattern for Errors and Skipped
        statsPattern = r'Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)'
        statsMatch = re.search(statsPattern, output)
        
        # Parse the captured groups
        if statsMatch == None:
            # No test statistics found in output
            testsRun = 0
            failures = 0
            errors = 0
            skipped = 0
        else:
            # .group(1) = tests run count
            # .group(2) = failures count
            # .group(3) = errors count
            # .group(4) = skipped count
            testsRun = int(statsMatch.group(1))
            failures = int(statsMatch.group(2))
            errors = int(statsMatch.group(3))
            skipped = int(statsMatch.group(4))
        
        # Check if build was successful
        if testResult.returncode == 0:
            success = True
        else:
            success = False
        
        # Check if JaCoCo coverage report was generated
        jacocoPath = CODEBASE_DIR / "target" / "site" / "jacoco" / "jacoco.xml"
        
        if jacocoPath.exists() == True:
            coverageReportLocation = str(jacocoPath)
        else:
            coverageReportLocation = "Coverage report not generated"
        
        # Build summary
        resultLines = []
        resultLines.append("=" * 50)
        resultLines.append("MAVEN TEST RESULTS")
        resultLines.append("=" * 50)
        resultLines.append("")
        
        if success == True:
            resultLines.append("Status: PASS")
        else:
            resultLines.append("Status: FAIL")
        
        resultLines.append(f"Tests Run: {testsRun}")
        resultLines.append(f"Failures: {failures}")
        resultLines.append(f"Errors: {errors}")
        resultLines.append(f"Skipped: {skipped}")
        resultLines.append("")
        resultLines.append(f"Coverage Report: {coverageReportLocation}")
        resultLines.append("")
        
        # Extract individual test failures if any exist
        if failures > 0 or errors > 0:
            resultLines.append("Failed Tests:")
            
            # Extract failure details from output
            # This regex finds test failure sections in Maven output
            # What it means:
            # * `(\w+Test)` - capture group 1: test class name ending in "Test"
            # * `\.(\w+)` - literal dot + capture group 2: test method name
            # * `\s+Time elapsed:` - whitespace + literal "Time elapsed:"
            # * `.*?` - any characters (non-greedy)
            # * `<<<\s+FAILURE!` - literal "<<< FAILURE!"
            failurePattern = r'(\w+Test)\.(\w+)\s+Time elapsed:.*?<<<\s+(?:FAILURE|ERROR)!'
            failureMatches = re.findall(failurePattern, output)
            
            for testClass, testMethod in failureMatches:
                resultLines.append(f"  - {testClass}.{testMethod}()")
            
            resultLines.append("")
        
        # Add last 1000 characters of output for debugging
        resultLines.append("Last output (for debugging):")
        resultLines.append(output[-1000:])
        
        return "\n".join(resultLines)
        
    except subprocess.TimeoutExpired:
        return "Error: Maven test execution timed out after 5 minutes"
    except Exception as e:
        return f"Error running Maven tests: {e}"


@mcp.tool
def analyze_coverage_gaps() -> str:
    """
    Analyze JaCoCo coverage report and provide recommendations.
    
    Returns:
        Plain text report with:
        - Overall coverage statistics
        - List of classes with low coverage
        - Specific methods that need tests
        - Actionable suggestions
    """
    jacocoPath = CODEBASE_DIR / "target" / "site" / "jacoco" / "jacoco.xml"
    
    if jacocoPath.exists() == False:
        return "Error: JaCoCo report not found. Run mvn test first."
    
    try:
        # Parse the XML file
        tree = ET.parse(jacocoPath)
        root = tree.getroot()
        
        # Extract coverage data from XML
        coverageData = process_coverage_xml(root)
        
        # Build and return the report
        report = build_coverage_report(coverageData)
        return report
        
    except ET.ParseError as e:
        return f"Error: Failed to parse JaCoCo XML - {e}"
    except Exception as e:
        return f"Error analyzing coverage: {e}"


def process_coverage_xml(root):
    """
    Extract coverage statistics from JaCoCo XML root element.
    Processes all packages, classes, and methods to gather coverage data.
    
    Args:
        root: The root element of the parsed JaCoCo XML tree
        
    Returns:
        Dictionary containing coverage statistics and sorted list of classes needing tests
    """
    # Initialize overall statistics
    totalInstructionCovered = 0
    totalInstructionMissed = 0
    totalLineCovered = 0
    totalLineMissed = 0
    
    # Store classes with coverage gaps
    classesNeedingTests = []
    
    # Process each package in the report
    for package in root.findall('.//package'):
        # Extract package name and convert from path format to Java format
        # Example: "org/apache/commons" → "org.apache.commons"
        packageName = package.get('name', 'unknown')
        packageName = packageName.replace('/', '.')
        
        # Process each class in this package
        for myClass in package.findall('class'):
            # Get class name (just the class, not full path)
            classFullName = myClass.get('name', 'unknown')
            classParts = classFullName.split('/')
            className = classParts[-1]  # Last element is the class name
            
            # Get source file name
            sourceFile = myClass.get('sourcefilename', 'unknown')
            
            # Track this class's coverage
            classInstructionCovered = 0
            classInstructionMissed = 0
            uncoveredMethods = []
            
            # Process each method in this class
            for method in myClass.findall('method'):
                methodName = method.get('name', 'unknown')
                
                # Get instruction coverage for this method
                methodCovered = 0
                methodMissed = 0
                
                for counter in method.findall('counter'):
                    counterType = counter.get('type')
                    
                    if counterType == 'INSTRUCTION':
                        methodCovered = int(counter.get('covered', 0))
                        methodMissed = int(counter.get('missed', 0))
                
                # Calculate method coverage percentage
                methodTotal = methodCovered + methodMissed
                
                if methodTotal > 0:
                    methodCoveragePct = (methodCovered / methodTotal) * 100
                else:
                    methodCoveragePct = 0
                
                # If method has any uncovered instructions, track it
                if methodMissed > 0:
                    uncoveredMethods.append({
                        'name': methodName,
                        'coverage': methodCoveragePct,
                        'missed': methodMissed
                    })
            
            # Get class-level counters
            for counter in myClass.findall('counter'):
                counterType = counter.get('type')
                covered = int(counter.get('covered', 0))
                missed = int(counter.get('missed', 0))
                
                if counterType == 'INSTRUCTION':
                    classInstructionCovered = covered
                    classInstructionMissed = missed
                    
                    # Add to overall totals
                    totalInstructionCovered = totalInstructionCovered + covered
                    totalInstructionMissed = totalInstructionMissed + missed
                
                if counterType == 'LINE':
                    totalLineCovered = totalLineCovered + covered
                    totalLineMissed = totalLineMissed + missed
            
            # Calculate class coverage percentage
            classTotal = classInstructionCovered + classInstructionMissed
            
            if classTotal > 0:
                classCoveragePct = (classInstructionCovered / classTotal) * 100
            else:
                classCoveragePct = 0
            
            # If class has coverage gaps, store it
            if classCoveragePct < 100 and classTotal > 0:
                classesNeedingTests.append({
                    'package': packageName,
                    'class': className,
                    'source_file': sourceFile,
                    'coverage': classCoveragePct,
                    'methods': uncoveredMethods
                })
    
    # Sort classes by coverage (lowest first)
    classesNeedingTestsSorted = classesNeedingTests.copy()
    classesNeedingTestsSorted.sort(key=get_class_coverage)
    
    # Return all collected data
    return {
        'total_instruction_covered': totalInstructionCovered,
        'total_instruction_missed': totalInstructionMissed,
        'total_line_covered': totalLineCovered,
        'total_line_missed': totalLineMissed,
        'classes_needing_tests': classesNeedingTestsSorted
    }


def get_class_coverage(classDict):
    """
    Helper function to extract coverage percentage from a class dictionary.
    Used as the sort key for ordering classes by coverage.
    
    Args:
        classDict: Dictionary containing class information including 'coverage' key
        
    Returns:
        Float coverage percentage
    """
    return classDict['coverage']


def build_coverage_report(coverageData):
    """
    Build a human-readable coverage report from extracted data.
    
    Args:
        coverageData: Dictionary with coverage statistics and sorted class list
        
    Returns:
        Formatted string report
    """
    # Calculate overall coverage percentages
    totalInstructions = coverageData['total_instruction_covered'] + coverageData['total_instruction_missed']
    totalLines = coverageData['total_line_covered'] + coverageData['total_line_missed']
    
    if totalInstructions > 0:
        overallInstructionPct = (coverageData['total_instruction_covered'] / totalInstructions) * 100
    else:
        overallInstructionPct = 0
    
    if totalLines > 0:
        overallLinePct = (coverageData['total_line_covered'] / totalLines) * 100
    else:
        overallLinePct = 0
    
    # Start building the report
    reportLines = []
    reportLines.append("=" * 60)
    reportLines.append("COVERAGE ANALYSIS & RECOMMENDATIONS")
    reportLines.append("=" * 60)
    reportLines.append("")
    reportLines.append("Overall Coverage:")
    reportLines.append(f"  Instruction Coverage: {overallInstructionPct:.1f}% ({coverageData['total_instruction_covered']}/{totalInstructions})")
    reportLines.append(f"  Line Coverage: {overallLinePct:.1f}% ({coverageData['total_line_covered']}/{totalLines})")
    reportLines.append("")
    
    sortedClasses = coverageData['classes_needing_tests']
    
    # Check if we have perfect coverage
    if len(sortedClasses) == 0:
        reportLines.append("Perfect! All classes have 100% coverage.")
        return "\n".join(reportLines)
    
    reportLines.append(f"Found {len(sortedClasses)} class(es) needing more tests:")
    reportLines.append("")
    
    # Show top 10 classes needing attention
    maxClassesToShow = 10
    if len(sortedClasses) < maxClassesToShow:
        maxClassesToShow = len(sortedClasses)
    
    for i in range(maxClassesToShow):
        clsInfo = sortedClasses[i]
        
        reportLines.append("-" * 60)
        reportLines.append(f"{i + 1}. {clsInfo['class']} ({clsInfo['coverage']:.1f}% covered)")
        reportLines.append(f"   Location: {clsInfo['package']}/{clsInfo['source_file']}")
        reportLines.append("")
        
        # Show uncovered methods
        if len(clsInfo['methods']) > 0:
            reportLines.append("   Uncovered/Partially Covered Methods:")
            
            # Show up to 5 methods
            maxMethods = 5
            if len(clsInfo['methods']) < maxMethods:
                maxMethods = len(clsInfo['methods'])
            
            for j in range(maxMethods):
                method = clsInfo['methods'][j]
                reportLines.append(f"      - {method['name']}() - {method['coverage']:.0f}% covered")
                
                # Generate suggestion based on method name
                suggestion = get_test_suggestion(method['name'])
                if suggestion != "":
                    reportLines.append(f"        Suggestion: {suggestion}")
            
            if len(clsInfo['methods']) > maxMethods:
                remaining = len(clsInfo['methods']) - maxMethods
                reportLines.append(f"      ... and {remaining} more methods")
        
        reportLines.append("")
    
    if len(sortedClasses) > maxClassesToShow:
        remaining = len(sortedClasses) - maxClassesToShow
        reportLines.append(f"... and {remaining} more classes with coverage gaps.")
        reportLines.append("")
    
    reportLines.append("=" * 60)
    reportLines.append("Next Steps:")
    reportLines.append("  1. Focus on classes with lowest coverage first")
    reportLines.append("  2. Write tests for uncovered methods")
    reportLines.append("  3. Test edge cases: null inputs, empty collections, boundary values")
    reportLines.append("  4. Re-run 'mvn test' to measure improvement")
    
    return "\n".join(reportLines)


def get_test_suggestion(methodName: str) -> str:
    """
    Generate a test suggestion based on method name patterns.
    Returns empty string if no specific pattern matches.
    """
    methodLower = methodName.lower()
    
    # Check for common method name patterns
    if 'get' in methodLower or 'is' in methodLower:
        return "Test return value for various object states"
    
    if 'set' in methodLower:
        return "Test with valid/invalid inputs, verify state changes"
    
    if 'add' in methodLower or 'insert' in methodLower:
        return "Test adding to empty/full collections, duplicate items"
    
    if 'remove' in methodLower or 'delete' in methodLower:
        return "Test removing existing/non-existing items, empty collection"
    
    if 'calculate' in methodLower or 'compute' in methodLower:
        return "Test with boundary values, negative numbers, zero, large numbers"
    
    if 'validate' in methodLower or 'check' in methodLower:
        return "Test valid/invalid inputs, edge cases"
    
    if 'find' in methodLower or 'search' in methodLower:
        return "Test with found/not found scenarios, empty results"
    
    if 'equals' in methodLower or 'compare' in methodLower:
        return "Test equality/inequality cases, null comparisons"
    
    # No specific pattern matched
    return "Write test covering all execution paths"

@mcp.tool
def str_replace(filePath: str, oldText: str, newText: str) -> str:
    """
    Replace text in a file. Useful for fixing placeholder assertions in generated tests.
    
    Args:
        filePath: Path to file relative to codebase (e.g., "src/test/java/CalculatorTest.java")
        oldText: Exact text to find and replace (can span multiple lines)
        newText: Text to replace with
        
    Returns:
        Success message with number of replacements made, or error message
        
    Example:
        str_replace(
            "src/test/java/com/example/CalculatorTest.java",
            'assertEquals(0, result, "TODO: Specify expected value");',
            'assertEquals(5, result, "2 + 3 should equal 5");'
        )
    """
    try:
        fullPath = CODEBASE_DIR / filePath
        
        # Check if file exists
        if fullPath.exists() == False:
            return f"Error: File not found at {fullPath}"
        
        # Read the current file content
        with open(fullPath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if old text exists in file
        if oldText not in content:
            return f"Error: Text to replace not found in {filePath}\nLooked for: {oldText[:100]}..."
        
        # Count occurrences before replacement
        occurrenceCount = content.count(oldText)
        
        # Perform replacement
        updatedContent = content.replace(oldText, newText)
        
        # Write back to file
        with open(fullPath, 'w', encoding='utf-8') as f:
            f.write(updatedContent)
        
        return f"Success: Replaced {occurrenceCount} occurrence(s) in {filePath}"
        
    except Exception as e:
        return f"Error replacing text: {e}"

# =============================================================================
# =============================================================================
# GIT AUTOMATION TOOLS (from git_tools.py)
# =============================================================================
# =============================================================================


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


# =============================================================================
# =============================================================================
# EXAMPLE TOOL
# =============================================================================
# =============================================================================


# Example custom tool
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


# =============================================================================
# =============================================================================
# RUN SERVER
# =============================================================================
# =============================================================================

if __name__ == "__main__":
    mcp.run(transport="sse")