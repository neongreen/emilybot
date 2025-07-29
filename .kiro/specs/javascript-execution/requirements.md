# Requirements Document

## Introduction

This feature adds JavaScript execution capabilities to memory bot entries through an optional `.run` attribute. Users can set JavaScript code for existing aliases using the `.set <alias> .run <code>` command. The JavaScript code is executed via quickjs-emscripten with strict time and memory limits, and console.log output is captured and returned to Discord.

## Requirements

### Requirement 1

**User Story:** As a bot user, I want to add JavaScript code to existing entries so that I can create dynamic, executable content that can access the original entry content.

#### Acceptance Criteria

1. WHEN a user uses `.set <alias> .run <code>` THEN the JavaScript code SHALL be stored in the entry's run attribute
2. WHEN JavaScript code is provided with triple backticks THEN the backticks and optional language identifier SHALL be stripped
3. WHEN an entry with a `.run` attribute is displayed THEN the JavaScript code SHALL be executed and console.log output included in the response
4. WHEN the `.run` attribute is set THEN it SHALL only be allowed for existing aliases, not during alias creation
5. WHEN JavaScript code accesses the original entry content THEN it SHALL be available through a context variable

### Requirement 2

**User Story:** As a bot administrator, I want JavaScript execution to be secure and sandboxed with strict limits so that it cannot harm the system or consume excessive resources.

#### Acceptance Criteria

1. WHEN JavaScript code is executed THEN it SHALL have a maximum execution time of 1 second
2. WHEN JavaScript code is executed THEN it SHALL have strict memory limits to prevent excessive resource usage
3. WHEN JavaScript execution exceeds time limits THEN it SHALL be terminated with a timeout error
4. WHEN JavaScript execution exceeds memory limits THEN it SHALL be terminated with a memory error
5. WHEN JavaScript code is executed THEN it SHALL run in a sandboxed environment with no access to file system, network, or system resources

### Requirement 3

**User Story:** As a developer, I want a Deno-based CLI tool for JavaScript execution so that the Python code can easily invoke sandboxed JavaScript execution.

#### Acceptance Criteria

1. WHEN the system needs to execute JavaScript THEN it SHALL use a Deno CLI tool that wraps quickjs-emscripten
2. WHEN the CLI tool is invoked THEN it SHALL accept JavaScript code and context data as input
3. WHEN JavaScript execution completes successfully THEN all console.log output SHALL be captured and returned via stdout
4. WHEN JavaScript execution fails THEN error information SHALL be returned via stderr with appropriate exit codes
5. WHEN the CLI tool is needed THEN Deno dependencies SHALL be specified in nixpacks.toml

### Requirement 4

**User Story:** As a bot user, I want my JavaScript code to have access to console.log and the original entry content so that I can create meaningful dynamic output.

#### Acceptance Criteria

1. WHEN JavaScript code is executed THEN it SHALL have access to console.log for output
2. WHEN JavaScript code is executed THEN it SHALL have access to the original entry content through a context object
3. WHEN JavaScript code produces console.log output THEN all output within the 1-second limit SHALL be captured and returned
4. WHEN console.log output is returned THEN it SHALL be trimmed according to existing Discord message limits