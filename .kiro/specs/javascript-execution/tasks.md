# Implementation Plan

- [x] 1. Set up Deno JavaScript executor infrastructure
  - Create js-executor directory structure with TypeScript files
  - Set up quickjs-emscripten integration in Deno
  - _Requirements: 3.1_

- [x] 2. Implement core JavaScript execution engine
  - [x] 2.1 Create Deno CLI script for JavaScript execution
    - Write main.ts that accepts JavaScript code and context as arguments
    - Integrate quickjs-emscripten for sandboxed execution
    - Implement 1-second timeout mechanism
    - _Requirements: 3.1, 3.2, 2.1_

  - [x] 2.2 Implement console.log capture and context injection
    - Capture all console.log output during execution
    - Inject context object with entry data into JavaScript environment
    - Return captured output via stdout
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 2.3 Add error handling and resource limits
    - Handle timeout errors with appropriate exit codes
    - Handle syntax and runtime errors with stderr output
    - Implement basic memory limits through quickjs configuration
    - _Requirements: 2.1, 2.3, 2.4, 3.4_

- [x] 3. Update database schema and models
  - Add optional `run` field to Entry dataclass
  - Update database initialization to handle new field
  - Ensure backward compatibility with existing entries
  - _Requirements: 1.1_

- [x] 4. Implement Python JavaScript executor service
  - [x] 4.1 Create JavaScriptExecutor class
    - Write executor class that calls Deno CLI subprocess
    - Implement timeout handling and process management
    - Handle stdout/stderr parsing and error classification
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 4.2 Add code parsing utilities
    - Implement triple backtick stripping functionality
    - Handle various backtick formats (plain, ```js, ```javascript)
    - Create context object from Entry data
    - _Requirements: 1.2, 4.2_

- [x] 5. Create .set command handler for .run attribute
  - [x] 5.1 Add command parsing for .set <alias> .run syntax
    - Parse .set command to identify .run subcommand
    - Extract alias name and JavaScript code from message
    - Validate that alias exists before setting .run attribute
    - _Requirements: 1.1, 1.4_

  - [x] 5.2 Implement .run attribute setting logic
    - Update existing entry with JavaScript code
    - Store parsed and cleaned JavaScript code in database
    - Provide confirmation message to user
    - _Requirements: 1.1, 1.2_

- [x] 6. Integrate JavaScript execution into entry display
  - [x] 6.1 Modify entry display logic to detect .run attribute
    - Check for .run attribute when displaying entries
    - Execute JavaScript code when .run is present
    - Combine JavaScript output with original content
    - _Requirements: 1.3, 4.3_

  - [x] 6.2 Add error handling and fallback display
    - Handle JavaScript execution errors gracefully
    - Display trimmed error messages to users
    - Fall back to original content when execution fails
    - Apply existing message trimming to JavaScript output
    - _Requirements: 1.3, 2.2, 4.4_

- [-] 7. Write basic unit tests
  - [ ] 7.1 Test code parsing functionality
    - Test triple backtick stripping with various formats
    - Test context object generation from Entry data
    - Verify proper handling of edge cases in code parsing
    - _Requirements: 1.2, 4.2_

  - [ ] 7.2 Test JavaScript execution output
    - Test simple console.log output capture
    - Test context object access in JavaScript
    - Test multiple console.log statements
    - Compare expected vs actual string output
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 8. Configure deployment (nixpacks.toml)
  - Add Deno to nixpacks.toml dependencies
  - Configure build phase to cache Deno dependencies
  - _Requirements: 3.5_