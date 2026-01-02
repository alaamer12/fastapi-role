# Development

# Development Framework: Repertoire

> A systematic approach to building Symphony from milestones to production-ready features
> 

---

## 📖 Glossary

| Term                               | Definition                                                                                                                                          |
|------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **OFB Python**                     | Out of Boundary Python - refers to Python API components that handle authoritative validation, RBAC, and data persistence outside the Rust boundary |
| **Pre-validation**                 | Lightweight technical validation in Rust to prevent unnecessary HTTP requests (NOT business logic)                                                  |
| **Authoritative Validation**       | Complete validation including RBAC, business rules, and data constraints performed by OFB Python                                                    |
| **Two-Layer Architecture**         | Rust (orchestration + pre-validation) + OFB Python (validation + persistence)                                                                       |
| **Mock-Based Contract Testing**    | Testing approach using mocked dependencies to verify component contracts                                                                            |
| **WireMock Contract Verification** | HTTP endpoint mocking for testing integration with OFB Python services                                                                              |
| **Three-Layer Testing**            | Unit tests (<100ms), Integration tests (<5s), Pre-validation tests (<1ms)                                                                           |
| **Advanced Testing Requirements**  | Mandatory benchmarks, property tests, and fuzz testing when specified in acceptance criteria                                                        |
| **Quality Gates**                  | Mandatory checks: tests pass, benchmarks <15% outliers, doc tests pass, clippy clean, docs generate                                                |
| **sy-commons Integration**         | Mandatory use of sy-commons crate for error handling, logging, and utilities across all Symphony components                                         |

---

## 🎯 Overview

This framework bridges **strategic planning** (milestones) with **tactical execution** (features) using a structured, bottom-up approach that ensures rapid delivery without sacrificing quality.

**Core Philosophy:**

> Work from concrete features upward, not abstract plans downward. Each feature must prove itself before becoming part of the foundation.
> 

---

## 📁 Directory Structure

```
repertoire/
├── milestones/                 # Level-based milestone organization
│   ├── level0/                # Strategic architecture
│   │   ├── requirements.md    # High-level goals and properties
│   │   ├── design.md         # Main architecture diagram
│   │   └── notes.md          # Decisions and insights
│   ├── level1/                # Component breakdown
│   │   ├── requirements.md    # Component responsibilities
│   │   ├── design.md         # Component diagrams
│   │   └── notes.md          # Implementation notes
│   └── level2/                # Implementation details
│       ├── level2_m1/         # M1 specific requirements
│       │   ├── requirements.md # M1 specific requirements
│       │   ├── design.md      # M1 implementation diagrams
│       │   └── notes.md       # M1 decisions
│       ├── level2_m2/         # M2 specific requirements
│       │   └── ...
│       └── ...
├── features/                   # Hierarchical feature organization
│   ├── m1.1/                  # Features for milestone M1.1 (IPC Protocol)
│   │   ├── F001_message_envelope_design/
│   │   ├── F002_messagepack_serialization/
│   │   ├── F003_bincode_serialization/
│   │   └── ...
│   ├── m1.2/                  # Features for milestone M1.2 (Transport Layer)
│   │   ├── F006_transport_trait/
│   │   ├── F007_unix_socket_transport/
│   │   └── ...
│   ├── m1.3/                  # Features for milestone M1.3 (Message Bus)
│   │   └── ...
│   └── m5.1/                  # Features for milestone M5.1 (Workflow Model)
│       └── ...
└── practice/
    └── technical_pattern.md   # Technical implementation patterns
```

**Hierarchical Organization Benefits:**
- **Clear Milestone Mapping**: Features are grouped by their parent milestone
- **Dependency Management**: Related features are co-located
- **Progress Tracking**: Easy to see milestone completion status
- **Scalability**: Structure supports hundreds of features without confusion
- **Level-Based Architecture**: Three-level milestone structure (level0, level1, level2) with dedicated files for requirements, design, and notes

**New Milestone Structure:**
- **Level 0**: Highest-level architecture, one main diagram, describes system as whole
- **Level 1**: Breaks down Level 0, more details, multiple diagrams allowed  
- **Level 2**: Breaks down Level 1, concrete implementation details, one diagram per sub-milestone

**File Organization per Level:**

### requirements.md
**Purpose**: What this level is responsible for
**Content**:
- **High-level goals only** - Strategic objectives without implementation details
- **Acceptance criteria** - Measurable conditions that define completion using Gherkin-style ATDD format
- **Correctness properties** - Formal statements about what the system should do (characteristics or behaviors that should hold true across all valid executions)
- **Glossary keywords** - Domain-specific terminology and definitions
- **ATDD approach compatibility** - Requirements structured to be super applicable for Test-Driven Development

**Example Structure (Gherkin-style ATDD)**:
```markdown
### Requirement 1: Enhanced CLI Management System
**Goal**: Provide comprehensive command-line interface management

**Acceptance Criteria (Gherkin-style)**:
Scenario: Discover available CLI commands
  Given the CLI tool is installed
  When the user runs `tool --help`
  Then a list of available commands is shown

Scenario: Execute CLI command with fast response
  Given the CLI tool is ready
  When the user runs any valid command
  Then the command executes within 100ms response time

Scenario: Handle invalid commands gracefully
  Given the CLI tool is running
  When the user runs an invalid command
  Then an error message with actionable guidance is displayed

**Correctness Properties**:
- Property 1: All valid commands must return exit code 0
- Property 2: Invalid commands must return non-zero exit codes
- Property 3: Help flag (--help) must be supported by all commands

**Glossary**:
- CLI: Command Line Interface
- ATDD: Acceptance Test-Driven Development
```

### design.md  
**Purpose**: Architecture and structure representation
**Content**:
- **High-level ASCII diagrams** (recommended) - Simple, readable visual representations
- **Mermaid diagrams** (alternative) - When ASCII is insufficient
- **Architectural patterns** - How components interact and relate
- **Keep it simple and readable** - Avoid over-complexity

**Guidelines**:
- Use ASCII art for maximum compatibility and simplicity
- One main diagram per level (Level 0), multiple allowed for Level 1/2
- Focus on relationships and data flow, not implementation details

### LEVEL.md
**Purpose**: The actual milestone guidemap - detailed implementation breakdown and guidance
**Content**:
- **Complete milestone breakdown** - All milestones with detailed deliverables and sub-tasks
- **Implementation guidance** - Step-by-step breakdown of what needs to be built
- **Crate/module structure** - Specific code organization and file structure
- **Success criteria** - Concrete checkboxes for completion tracking
- **Dependencies and integration points** - How components connect and depend on each other

**File Naming Convention**:
- **LEVEL0.md** - Strategic milestones (M1, M2, M3, etc.) with complete implementation roadmap
- **LEVEL1_M{X}.md** - Tactical breakdown for specific milestone M{X}
- **LEVEL2_M{X}_S{Y}.md** - Concrete implementation steps for milestone M{X}, section S{Y}

**Example Structure**:
```markdown
## 🚧 M1: Core Infrastructure (3-4 months)

**Goal**: Build the foundational systems that Symphony AIDE layer requires

### 1.1 Environment Setup & Port Definitions
**Priority**: 🔴 Critical - Foundation for H2A2 architecture

**Deliverables**:
- Hexagonal Architecture port definitions (TextEditingPort, PitPort, ExtensionPort, ConductorPort)
- Development environment setup and tooling
- Domain types and comprehensive error handling

**Crates to Create**:
```
apps/backend/crates/symphony-core-ports/
├── src/
│   ├── ports.rs         # Port trait definitions
│   ├── types.rs         # Domain types
│   ├── errors.rs        # Error types
│   └── lib.rs
```

**Success Criteria**:
- ✅ H2A2 architecture fully implemented
- ✅ All port interfaces defined and documented
- ✅ Mock adapters available for testing
```

### notes.md
**Purpose**: Incremental decision and insight tracking  
**Content**:
- **Empty by default** - No pre-populated content
- **Filled incrementally** - Added as decisions, issues, or insights emerge during development
- **Decision log** - Why certain choices were made
- **Issue tracking** - Problems encountered and their resolutions
- **Insights** - Lessons learned and important discoveries

---

## ✅ Checkbox Status System

All milestones and features use a stateful checkbox system to track progress:

**Syntax:**

- `[ ]` → **Idle** (not started)
- `[ - ]` → **In Progress** (actively being worked on)
- `[ <number> ]` → **Completed** (number indicates iteration count)

**Iteration Count Meaning:**

- `[ 1 ]` → Completed successfully on first attempt
- `[ 2 ]` → Completed, but was reopened once and completed again
- `[ 3 ]` → Completed, but was reopened twice and completed again
- `[ n ]` → Completed after (n-1) reopenings

**Example:**

```markdown
## Deliverables:
* [ ] Deliverable 1: Not started yet
* [ - ] Deliverable 2: Currently working on this
* [ 1 ] Deliverable 3: Done right the first time
* [ 3 ] Deliverable 4: Had to redo twice, now stable

```

**Why Track Iterations?**

- Identifies problematic areas that need rework
- Shows learning curve and process maturity
- Helps estimate future similar work
- Reveals hidden complexity

---

## 📊 The Milestone Hierarchy

### Level 0: Strategic Vision

**Files:** `level0/requirements.md`, `level0/design.md`, `level0/notes.md`

**Purpose:** Define the "what" and "why" at the highest level.

**File Structure:**
- **requirements.md**: High-level goals and properties, acceptance criteria, correctness properties, glossary keywords
- **design.md**: Main architecture diagram describing system as whole
- **notes.md**: Strategic decisions and insights (filled incrementally)

**Format in requirements.md:**

```markdown
## 🚧 M{NUMBER}: <NAME>

**Goal**: <Clear, measurable objective>

**Priority**: Critical | High | Medium | Low

**Status**: * [ ] | * [ - ] | * [ <number> ]

**Timeline**: <Realistic time estimate (e.g., 3-4 months)>

**Dependencies**: <List of prerequisite milestones>

**Deliverables**:
* [ ] Deliverable 1: <Concrete output>
* [ ] Deliverable 2: <Concrete output>
* [ ] Deliverable 3: <Concrete output>

**Success Metrics**:
* [ ] Metric 1: <How we measure success>
* [ ] Metric 2: <How we measure success>

**Performance Targets** (if applicable):
- [ ] <Specific measurable performance requirement>
- [ ] <Another performance target>

```

**Example from LEVEL0.md:**

```markdown
## 🚧 M1: Core Infrastructure (3-4 months)
**Status**: * [ ] - Next Priority
**Dependencies**: M0 Foundation

### Implementation Breakdown

#### 1.1 Environment Setup & Port Definitions
**Priority**: 🔴 Critical - Foundation for H2A2 architecture
**Timeline**: 2-3 weeks

**Crate Structure**:
```
apps/backend/crates/symphony-core-ports/
├── Cargo.toml
├── src/
│   ├── lib.rs           # Public API exports
│   ├── ports.rs         # Port trait definitions (TextEditingPort, PitPort, ExtensionPort, ConductorPort)
│   ├── types.rs         # Domain types and data structures
│   ├── errors.rs        # Error types and handling
│   └── mocks.rs         # Mock implementations for testing
└── tests/
    └── integration_tests.rs
```

**Concrete Deliverables**:
- [ ] Port trait definitions implemented
- [ ] Domain types defined with comprehensive error handling
- [ ] Mock adapters created for isolated testing
- [ ] Architecture documentation updated
- [ ] Development environment setup guide completed

**Performance Targets**:
- [ ] <0.3ms message latency for standard operations
- [ ] <1ms for Symphony ↔ XI-editor JSON-RPC operations
- [ ] 1,000+ operations/second throughput
- [ ] Automatic reconnection within 100ms on failure

### M1 Success Criteria Checklist
- [ ] H2A2 architecture fully implemented (Ports + Adapters + Domain + Actors)
- [ ] Two-binary architecture operational (Symphony + XI-editor)
- [ ] All concrete adapters implement their respective port interfaces
- [ ] Domain core orchestrates all components using ports only
- [ ] Actor layer provides extension process isolation
- [ ] All tests passing with >80% code coverage
- [ ] Health monitoring detects and recovers from process failures

```

---

### Level 1: Tactical Breakdown

**Files:** `level1/requirements.md`, `level1/design.md`, `level1/notes.md`

**Purpose:** Break strategic goals into implementable phases with component responsibilities.

**File Structure:**
- **requirements.md**: Component responsibilities and breakdown of Level 0 milestones
- **design.md**: Component diagrams (multiple diagrams allowed)
- **notes.md**: Implementation notes and decisions (filled incrementally)

**Format in requirements.md:**

```markdown
# Level 1 Breakdown: M{X} - <NAME>

**Status**: * [ ] | * [ - ] | * [ <number> ]

## Context
<Brief recap of parent milestone goal>

## Breakdown

### S1: <Section Name>
**Status**: * [ ] | * [ - ] | * [ <number> ]

**Objective**: <What this section achieves>

**Steps**:
* [ ] Step 1 description
* [ ] Step 2 description
* [ ] Step 3 description

**Outputs**:
* [ ] Output 1
* [ ] Output 2

---

### S2: <Section Name>
**Status**: * [ ] | * [ - ] | * [ <number> ]

**Objective**: <What this section achieves>

**Steps**:
* [ ] Step 1 description
* [ ] Step 2 description

**Outputs**:
* [ ] Output 1
* [ ] Output 2

---

## Integration Points
- How S1 connects to S2
- External dependencies
- Handoff requirements

```

---

### Level 2: Concrete Implementation Steps

**Files:** `level2/level2_m{N}/requirements.md`, `level2/level2_m{N}/design.md`, `level2/level2_m{N}/notes.md`

**Purpose:** The lowest planning level before features. Each step here becomes one or more features.

**File Structure:**
- **requirements.md**: M{N} specific requirements and concrete implementation steps
- **design.md**: M{N} implementation diagrams (one diagram per sub-milestone)
- **notes.md**: M{N} specific decisions and insights (filled incrementally)

**Example in requirements.md:**

```markdown
# Level 2 Steps: M1_S1 - Sandboxed Execution Environment

**Status**: * [ 1 ]

## Context
Create isolated execution contexts for extensions with resource limits and permission boundaries.

## Concrete Steps

### Step 1: Process Isolation Manager
**Status**: * [ 1 ]
**Timeline**: 2 days
**Priority**: 🔴 Critical

**What**: Build a manager that spawns and monitors isolated processes for extensions
**Why**: Prevents extension crashes from affecting Symphony core
**Output**: ProcessSandboxManager class with spawn/monitor/terminate methods

**Crate Structure**:
```
apps/backend/crates/symphony-process-sandbox/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── manager.rs       # ProcessSandboxManager implementation
│   ├── monitor.rs       # Health monitoring and restart logic
│   ├── isolation.rs     # Process isolation mechanisms
│   └── metrics.rs       # Resource usage tracking
└── tests/
    └── integration_tests.rs
```

**Concrete Deliverables**:
- [ ] ProcessSandboxManager with spawn/monitor/terminate methods
- [ ] Health monitoring with automatic restart capability
- [ ] Resource usage tracking (CPU, memory, network)
- [ ] Process isolation with security boundaries
- [ ] Comprehensive test coverage

**Performance Targets**:
- [ ] Process spawn time <100ms
- [ ] Health check interval <50ms
- [ ] Resource monitoring overhead <1% CPU

**Sub-tasks**:
* [ 1 ] Design process spawn interface
* [ 1 ] Implement process health monitoring
* [ 2 ] Build automatic restart logic
* [ 1 ] Add resource usage tracking

**Maps to Feature**: F001 - process_sandbox_manager

---

### Step 2: Permission Enforcement Layer
**Status**: * [ 1 ]
**Timeline**: 3 days
**Priority**: 🔴 Critical

**What**: Implement runtime permission checks for sandboxed operations
**Why**: Prevents unauthorized access to system resources
**Output**: PermissionEnforcer middleware

**Crate Structure**:
```
apps/backend/crates/symphony-permissions/
├── src/
│   ├── lib.rs
│   ├── enforcer.rs      # PermissionEnforcer implementation
│   ├── policies.rs      # Permission policy definitions
│   ├── audit.rs         # Audit logging for permission checks
│   └── validation.rs    # Permission validation logic
```

**Concrete Deliverables**:
- [ ] PermissionEnforcer middleware implementation
- [ ] Permission policy definition system
- [ ] Runtime permission validation
- [ ] Audit logging for all permission checks
- [ ] Integration with process sandbox manager

**Sub-tasks**:
* [ 1 ] Define permission model
* [ 1 ] Build enforcement hooks
* [ 1 ] Create audit logging

**Maps to Feature**: F002 - permission_enforcement

---

## Dependencies
- Step 2 requires Step 1 (can't enforce permissions without sandbox)
- External: Node.js child_process or similar

## Integration Points
- Connects to Extension Registry (M1.2)
- Used by Extension Loader (M1.3)
- Monitored by Health System (M1.4)

```

---

## 🎯 From Milestones to Features: The Transformation Process

### Step 1: Identify Feature Boundaries

**Naming Convention:** `F{XXX}_{feature_name}`

**Start at Level 2:** Each Level 2 step becomes one or more features.

**Ask:**

1. Can this step be implemented independently?
2. Does it produce a testable output?
3. Can it be verified without other steps?

**If YES to all three → It's a feature.**

**Mapping Rules:**

- **1:1 Mapping** (ideal): One Level 2 step = One feature
- **1:N Mapping**: Complex step = Multiple atomic features
- **N:1 Mapping** (rare): Multiple tiny steps = One combined feature

### Step 2: Create Feature Directory

For each identified feature:

```bash
mkdir -p repertoire/features/F{XXX}_{feature_name}
cd repertoire/features/F{XXX}_{feature_name}

```

**Examples:**

- `F001_process_sandbox_manager`
- `F002_permission_enforcement`
- `F003_ipc_protocol`

**Sequential numbering ensures:**

- Clear implementation order
- Dependency tracking
- Progress visibility

---

## 📋 Feature Lifecycle Documents

Every feature directory contains six mandatory documents:

**IMPORTANT!!:**

- **📏 Maximum 400 lines per file**
- **🎯 Focus on essential information only**

### 1. [DEFINITION.md](http://definition.md/)

**Purpose:** Establish WHAT and WHY.

```markdown
# Feature Definition: F{XXX} - <NAME> - Inherited from milestone <MILESTONE_Number>

## Overview
<2-3 sentence summary>

## Purpose
**Problem**: <What problem does this solve?>
**Solution**: <How does this feature solve it?>
**Value**: <Why is this important?>

## Scope

### In Scope
- Capability 1
- Capability 2
- Capability 3

### Out of Scope
- Future enhancement 1
- Future enhancement 2

## Acceptance Criteria
**The feature is DONE when:**
1. [ ] Criterion 1 (measurable)
2. [ ] Criterion 2 (measurable)
3. [ ] Criterion 3 (measurable)

**Example:**
As an extension developer
I want my extension to run in an isolated process
So that crashes don't affect the main Symphony application

## Success Metrics
- Metric 1: <How we measure success>
- Metric 2: <How we measure success>

## Dependencies
### Requires (must exist first)
- F{XXX}: <Feature name>
- F{YYY}: <Feature name>

### Enables (unlocks these features)
- F{ZZZ}: <Feature name>

```

---

### 2. [PLANNING.md](http://planning.md/)

**Purpose:** Establish HOW.

**RULE:** "If it won't be used by the current feature/implementation, don't plan it."

- Only include APIs/methods that will actually call
- Remove "convenience" methods unless a test or dependent feature needs them
- Mark clearly: "Used by: F00X in scenario Y" in a comment when needed
- If uncertain whether something is needed, defer it

Example:
❌ BAD: "Add pretty_print() method for debugging"
✅ GOOD: "Defer pretty_print() - F006 not in current sprint"

```markdown
# Feature Planning: F{XXX} - <NAME>

## Implementation Approach

### High-Level Strategy
<Describe the overall approach in 2-3 paragraphs>

### Technical Decisions
1. **Decision**: <What was decided?>
   **Rationale**: <Why this choice?>
   **Alternatives Considered**: <What else was considered?>
   **Trade-offs**: <What are the pros/cons?>

2. **Decision**: <What was decided?>
   **Rationale**: <Why this choice?>
   ...

## Component Breakdown

### Component 1: <Name>
**Responsibility**: <What it does>
**Interfaces**: <How others interact with it>
**Dependencies**: <What it needs>

### Component 2: <Name>
**Responsibility**: <What it does>
**Interfaces**: <How others interact with it>
**Dependencies**: <What it needs>

## Dependencies Analysis

### External Dependencies
- Library 1: <Why needed?>
- Library 2: <Why needed?>

### Internal Dependencies
- Feature F{XXX}: <What capability needed?>
- Module XYZ: <What capability needed?>

```

---

### 3. [DESIGN.md](http://design.md/)

**Purpose:** Technical blueprint.

```markdown
# Technical Design: F{XXX} - <NAME>

## System Architecture

### Overview Diagram
[Create ASCII diagram or reference image]

### Component Interaction Flow
1. Step 1: Component A does X
2. Step 2: Component B receives X, does Y
3. Step 3: Component C does Z
...

## Module Design

### Module 1: <Name>

#### Responsibility
<What this module handles>

#### Public API
```python
class ModuleName:
    def method_1(self, param1: Type1, param2: Type2) -> ReturnType:
        """
        Description of what this does.

        Args:
            param1: Description
            param2: Description

        Returns:
            Description of return value

        Raises:
            ExceptionType: When this happens
        """
        pass
```
```

## Data Structures

### Primary Data Types

```python
@dataclass
class DataType1:
    """Description of what this represents"""
    field1: Type1  # Description
    field2: Type2  # Description

    def validate(self) -> bool:
        """Validation logic"""
        pass

```

## Database / Storage Changes

### Schema Modifications

```sql
-- If SQL database
CREATE TABLE table_name (
    column1 TYPE,
    column2 TYPE,
    ...
);

```

### File System Structure

```
/config/
  /extensions/
    /sandbox/
      permissions.json
      resource_limits.json

```

## Error Handling Strategy

### Error Categories

1. **Validation Errors**: Invalid input
    - Response: Return error to caller with details
2. **Runtime Errors**: Unexpected failures
    - Response: Log error, attempt recovery, notify user
3. **Resource Errors**: Out of memory, disk full
    - Response: Graceful degradation, clear error message

### Failure Modes & Recovery

| Failure Mode | Detection | Recovery Strategy |
| --- | --- | --- |
| Process crash | Process monitor | Restart with exponential backoff |
| Permission denied | Exception catch | Log and notify user |
| Resource limit | Metric threshold | Throttle or terminate gracefully |

### 4. TESTING.md

**Purpose:** Acceptance Test-Driven Development strategy.

```markdown
# Testing Strategy: F{XXX} - <NAME>

## Test Philosophy
<How we approach testing for this feature>

## Acceptance Tests (ATDD)

### Test 1: <Test Name>
**User Story**: <Related user story>

**Given**: <Initial state>
**When**: <Action taken>
**Then**: <Expected outcome>

**Verification**:
- [ ] Check 1
- [ ] Check 2
- [ ] Check 3

---

### Test 2: <Test Name>
[Repeat structure]

---

## Unit Tests

### Module 1: <Name>

#### Test Suite: Happy Path
- Test 1: `test_method_1_valid_input()` → Expected behavior
- Test 2: `test_method_2_valid_input()` → Expected behavior

#### Test Suite: Edge Cases
- Test 1: `test_method_1_empty_input()` → Expected behavior
- Test 2: `test_method_1_null_input()` → Expected behavior
- Test 3: `test_method_1_max_input()` → Expected behavior

#### Test Suite: Error Handling
- Test 1: `test_method_1_invalid_type()` → Raises TypeError
- Test 2: `test_method_1_out_of_range()` → Raises ValueError

---

## Integration Tests

### Integration 1: <Feature X + Feature Y>
**Scenario**: <What interaction to test>
**Setup**: <Prerequisites>
**Test Steps**:
1. Step 1
2. Step 2
3. Step 3
**Expected**: <Outcome>
**Actual**: <To be filled during implementation>

---

## Test Execution Plan

### Pre-Implementation
...

### During Implementation
...

### Post-Implementation
..

```

---

### 5. [IMPLEMENTATION.md](http://implementation.md/)

**Purpose:** Track actual coding work.

```markdown
# Implementation Log: F{XXX} - <NAME>

## Implementation Status

**Started**: <date>
**Completed**: <date> (or "In Progress")
**Implementer**: <name>
**Overall Status**: * [ ] | * [ - ] | * [ <number> ]

## Progress Tracking

### Phase 1: <Phase Name>
**Status**: * [ ] | * [ - ] | * [ <number> ]

* [ 1 ] Task 1: <description>
  - File: `path/to/file.py`
  - Lines: 120-180
  - Notes: <any important details>

* [ - ] Task 2: <description>
  - Status: Blocked by <reason>

* [ 1 ] Task 3: <description>

---

### Phase 2: <Phase Name>
**Status**: * [ ] | * [ - ] | * [ <number> ]

[Repeat structure]

---

## Code Structure

### Files Created/Modified
* [ 1 ] `path/to/file1.py` (new): <purpose>
* [ 1 ] `path/to/file2.py` (modified): <changes>
* [ - ] `path/to/file3.py` (new): <purpose>

### Key Classes/Functions
```python
# Snippet of important implementation
class ImportantClass:
    def critical_method(self):
        # Implementation note
        pass

```

## Design Decisions During Implementation

### Decision 1: <What changed from design?>

**Original Plan**: <What was planned>
**Actual Implementation**: <What was done>
**Reason**: <Why the change?>
**Impact**: <Affects what?>

---

## Documentation Updates

- [ ]  Updated API documentation [IF EXISTS]
- [ ]  Updated architecture diagrams

---

### 6. AGREEMENT.md

**Purpose:** BIF (Blind Inspection Framework) evaluation of the implemented feature.
**Created:** After IMPLEMENTATION.md is complete, before VERIFICATION.md
**This document is auto-generated using the BIF framework. See the BIF documentation for details.**

```markdown
# BIF Evaluation: F{XXX} - <NAME>

**Evaluation Date**: <date>
**Evaluated By**: <name>
**Component Path**: <path to code>
**Total LOC**: <lines of code>

---

## Feature Identification

| Feature | Location | LOC | Type |
|---------|----------|-----|------|
| Atomic Feature 1 | path/to/file.py:120-180 | 60 | Core |
| Atomic Feature 2 | path/to/file.py:200-250 | 50 | Helper |
| ... | ... | ... | ... |

---

## Feature-by-Feature Evaluation

### Atomic Feature 1: <Name>

**Location**: `path/to/file.py:120-180`

#### 1. Feature Completeness
**Rating**: Partial (35%)

**Evidence**:
- Lines 120-140: Basic implementation exists
- Lines 141-160: Missing edge case handling
- Lines 161-180: No validation logic

**Missing**:
- Input validation
- Error recovery
- Configuration options

---

#### 2. Code Quality / Maintainability
**Rating**: Basic
**Reasoning**: Code follows basic patterns but has several maintainability issues that increase long-term costs

**Evidence**:
- Line 125: Nested if statements (4 levels deep) - violates readability guidelines
- Line 145: Magic number `1000` without explanation - reduces maintainability
- Line 160: Duplicated logic from line 130 - DRY principle violation

**Issues**:
- Excessive nesting violates KISS principle
- No separation of concerns between validation and processing
- Code duplication increases maintenance burden

---

#### 3. Documentation & Comments
**Rating**: None

**Evidence**:
- No JSDoc/TSDoc comments
- No inline explanations
- Variable names unclear (e.g., `x`, `tmp`)

---

#### 4. Reliability / Fault-Tolerance
**Rating**: Medium

**Evidence**:
- Lines 130-135: try-catch block present
- Line 140: No null checks before property access
- Line 150: No input validation

**Risks**:
- Potential null pointer exceptions
- Unhandled invalid input

---

#### 5. Performance & Efficiency
**Rating**: Poor
**Reasoning**: Multiple algorithmic and implementation inefficiencies that will cause performance degradation under load

**Evidence**:
- Line 125: O(n²) nested loop, should be O(n) - algorithmic inefficiency
- Line 145: No debouncing for frequent calls - unnecessary processing overhead
- Line 160: Creating new object on every iteration - memory allocation pressure

**Issues**:
- Algorithm complexity too high for expected data sizes
- Unnecessary object creation in hot path
- No optimization for common case scenarios

---

#### 6. Integration & Extensibility
**Rating**: Partial

**Evidence**:
- Line 120: Hard-coded configuration
- Line 135: No plugin interface
- Line 155: Tightly coupled to Component X

**Issues**:
- Cannot toggle feature on/off
- No extension points
- Tight coupling prevents testing

---

#### 7. Maintenance & Support
**Rating**: Low

**Evidence**:
- Feature spans 3 files with no clear boundary
- 5 external dependencies
- No unit tests found

**Issues**:
- Difficult to modify without side effects
- Many dependencies increase maintenance cost
- Untestable in isolation

---

#### 8. Stress Collapse Estimation
**Prediction**: `1000+ suggestions → UI freeze >500ms`

**Based On**:
- Line 125: O(n²) loop will scale poorly
- Line 145: No throttling mechanism
- Line 160: Memory allocation grows linearly

**Confidence**: High (code structure clearly shows bottleneck)

---

[Repeat for each atomic feature...]

```

---

### 7. [VERIFICATION.md](http://verification.md/)

**Purpose:** Final Definition of Done checklist. References [AGREEMENT.md](http://agreement.md/) findings.

```markdown
# Verification Report: F{XXX} - <NAME>

## Verification Date
**Verified By**: <name>
**Date**: <date>
**Status**: ✅ COMPLETE | ⚠️ INCOMPLETE | ❌ FAILED

---

## Acceptance Criteria Verification

### From DEFINITION.md

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Criterion 1 | ✅ PASS | Link to test result |
| Criterion 2 | ✅ PASS | Link to test result |
| Criterion 3 | ⚠️ PARTIAL | Reason |

**Overall Acceptance**: ✅ PASS / ⚠️ NEEDS WORK / ❌ FAIL

---

## Test Verification

### Acceptance Tests (ATDD)
* [ 1 ] All acceptance tests written
* [ 1 ] All acceptance tests pass
* [ 2 ] Edge cases covered (had to add more tests)

### Unit Tests
* [ 1 ] All unit tests written
* [ 1 ] All unit tests pass
* [ 1 ] >80% code coverage achieved

**Coverage Report**: <link or summary>

### Integration Tests
* [ 1 ] All integration tests pass
* [ 1 ] No regressions in dependent features

---

## Code Quality Verification

### Static Analysis
* [ 1 ] No linting errors
* [ 1 ] Type checking passes (if applicable)
* [ 1 ] Security scanning clean

### Code Review
* [ 1 ] Reviewed by: <name>
* [ 1 ] All comments addressed
* [ 1 ] Design patterns consistent

---

## BIF Evaluation Review

### AGREEMENT.md Findings

**Reference**: See `AGREEMENT.md` for full BIF evaluation

**Critical Issues from BIF**:
* [ 1 ] Issue 1: Performance bottleneck → Fixed (see commit #abc123)
* [ 1 ] Issue 2: Missing error handling → Fixed (see commit #def456)
* [ - ] Issue 3: Documentation gaps → In progress

**Overall BIF Readiness**: ✅ Production Ready | 🟡 Staging Ready | ⚠️ Development | ❌ Not Ready

**Actions Taken**:
1. Fixed all High Priority issues identified in BIF
2. Addressed 3/5 Medium Priority issues
3. Documented remaining technical debt in backlog

---

## Documentation Verification

* [ 1 ] API documentation complete
* [ 1 ] User guide updated
* [ 1 ] Developer guide updated
* [ 2 ] Architecture diagrams accurate (had to revise once)
* [ 1 ] Code comments adequate

---

## Deployment Readiness

### Pre-Deployment Checklist
* [ 1 ] All tests pass in CI/CD
* [ 1 ] Staging environment tested
* [ 1 ] Rollback plan documented
* [ 1 ] Monitoring configured
* [ 1 ] Alerts configured

### Configuration
* [ 1 ] Default configuration set
* [ 1 ] Configuration documented
* [ 1 ] Migration script ready (if needed)

### Performance Validation
* [ 1 ] Load testing completed
* [ 1 ] Stress collapse scenarios validated (from BIF predictions)
* [ 1 ] Resource usage within limits

---

## Known Limitations / Future Work

### Limitations
* [ ] Limitation 1: <description>
   - Impact: <who affected?>
   - Mitigation: <how to work around?>

### Deferred Features
* [ ] Feature X: <why deferred?>
   - Planned for: Milestone M{Y}
   - Tracked in: Issue #123

### Technical Debt
* [ ] Debt item 1: <description>
   - Severity: Low/Medium/High
   - Plan: <when to address?>
   - Tracked in: Issue #456

```

---

## 🔄 The Complete Workflow

### Phase 1: Strategic Planning (Top-Down)

```
1. Define level0/requirements.md milestones with checkboxes
   * [ ] for each deliverable/metric
   ↓
2. Break each milestone into level1/requirements.md sections
   * [ ] for each step/output
   ↓
3. Break each section into level2/level2_m{N}/requirements.md steps
   * [ ] for each sub-task
   ↓
4. Validate that Level 2 steps are implementable
   ↓
5. Update all checkboxes as work progresses
   * [ ] → * [ - ] → * [ 1 ] → * [ 2 ] (if reopened)

```

**Output:** Complete milestone hierarchy with status tracking.

---

### Phase 2: Feature Extraction (Bottom-Up)

```
6. Start at Level 2 (lowest planning level)
   - Read requirements.md from level2/level2_m{N}/ directories
   ↓
7. For each Level 2 step:
   - Identify atomic features
   - Create feature directories
   - Number sequentially (F001, F002, ...)
   * [ ] Initialize each feature
   ↓
8. Map dependencies between features
   ↓
9. Prioritize features by milestone priority

```

**Output:** Complete feature list with dependencies and priorities.

---

### Phase 3: Feature Development (Iterative)

For each feature in priority order:

```
10. Create DEFINITION.md
    * [ ] Define scope, criteria, metrics
    ↓
11. Create PLANNING.md
    * [ ] Plan approach, components, dependencies
    ↓
12. Create DESIGN.md
    * [ ] Design architecture, APIs, data structures
    ↓
13. Create TESTING.md
    * [ ] Write acceptance tests (ATDD)
    * [ ] Define unit tests
    * [ ] Define integration tests
    ↓
14. Create IMPLEMENTATION.md
    * [ - ] Start implementation
    * [ ] Track progress per phase
    * [ ] Document decisions
    * [ 1 ] Complete implementation
    ↓
15. Create AGREEMENT.md
    * [ ] Run BIF evaluation
    * [ ] Identify all atomic features
    * [ ] Evaluate across 8 dimensions
    * [ ] Document findings and recommendations
    ↓
16. Create VERIFICATION.md
    * [ ] Verify acceptance criteria
    * [ ] Check all tests pass
    * [ ] Review BIF findings
    * [ ] Address critical issues
    * [ ] Final sign-off
    * [ 1 ] Feature complete!
    ↓
17. Update parent milestone checkboxes
    * [ 1 ] Mark corresponding deliverable as complete

```

**Output:** Production-ready feature with full documentation and quality validation.

---

### Phase 4: Iteration Tracking

```
18. Monitor checkbox status across all levels
    * [ ] → New/Not started
    * [ - ] → In progress
    * [ 1 ] → Completed first time
    * [ 2 ] → Completed after 1 reopening
    * [ 3 ] → Completed after 2 reopenings
    ↓
19. Identify patterns in iteration counts
    - High iteration counts (3+) indicate:
      * Underestimated complexity
      * Unclear requirements
      * Technical challenges
      * Need for process improvement
    ↓
20. Use insights to improve future estimates

```

---

## 📊 Milestone Naming Convention

### Hierarchical Breakdown Pattern

The milestone hierarchy uses a dot-notation system that clearly shows the breakdown level:

**Pattern:**

- **M{N}** → Level 0 (Strategic milestone)
- **M{N.X}** → Level 1 (Section X of milestone N)
- **M{N.X.Y}** → Level 2 (Step Y of section X of milestone N)

**Example Hierarchy:**

```
M1 (Level 0: Orchestra Kit Foundation)
├── M1.1 (Level 1: Sandboxed Execution Environment)
│   ├── M1.1.1 (Level 2: Process Isolation Manager)
│   ├── M1.1.2 (Level 2: Permission Enforcement Layer)
│   ├── M1.1.3 (Level 2: Resource Limit Controls)
│   └── M1.1.4 (Level 2: IPC Protocol)
├── M1.2 (Level 1: Manifest System)
│   ├── M1.2.1 (Level 2: Manifest Schema Design)
│   ├── M1.2.2 (Level 2: Parser Implementation)
│   ├── M1.2.3 (Level 2: Permission Mapping)
│   └── M1.2.4 (Level 2: Dependency Resolution)
└── M1.3 (Level 1: Extension Lifecycle)
    ├── M1.3.1 (Level 2: Installation Pipeline)
    ├── M1.3.2 (Level 2: Update Mechanism)
    └── M1.3.3 (Level 2: Uninstall Handler)

M2 (Level 0: Sheet Music Renderer)
├── M2.1 (Level 1: Canvas Engine)
│   ├── M2.1.1 (Level 2: WebGL Context)
│   └── M2.1.2 (Level 2: Render Loop)
└── M2.2 (Level 1: Notation Parser)
    ├── M2.2.1 (Level 2: MusicXML Parser)
    └── M2.2.2 (Level 2: ABC Notation Parser)

```

---

## 🔄 Navigation Between Levels

### Bottom-Up (from feature to strategy):

```
F001 (Feature)
    ↓ references
M1.1.1 (Level 2 Step)
    ↓ contained in
M1.1 (Level 1 Section)
    ↓ contained in
M1 (Level 0 Milestone)

```

### Top-Down (from strategy to implementation):

```
M1 (Level 0)
    ↓ breaks down into
M1.1, M1.2, M1.3 (Level 1)
    ↓ M1.1 breaks down into
M1.1.1, M1.1.2, M1.1.3, M1.1.4 (Level 2)
    ↓ M1.1.1 maps to
F001 (Feature)
    ↓ implements via
7 lifecycle documents

```

---

## 📊 Status Tracking Across Levels

### Propagation Rules:

1. **Level 2 → Level 1**:
    - M1.1 status = aggregate of M1.1.1, M1.1.2, M1.1.3, M1.1.4
    - If all are `[ 1 ]`, then M1.1 becomes `[ 1 ]`
    - If any is `[ - ]`, then M1.1 is `[ - ]`
    - If any is `[ ]`, then M1.1 is `[ ]`
2. **Level 1 → Level 0**:
    - M1 status = aggregate of M1.1, M1.2, M1.3
    - Same aggregation rules apply
3. **Feature → Level 2**:
    - When F001 [VERIFICATION.md](http://verification.md/) shows `[ 1 ]`
    - Update M1.1.1 to `[ 1 ]`
    - Propagate upward

### Example Status Flow:

```
F001 completed → * [ 1 ]
    ↓
M1.1.1 updated → * [ 1 ]
    ↓
Check M1.1.2, M1.1.3, M1.1.4
    ↓
All complete? → M1.1 updated → * [ 1 ]
    ↓
Check M1.2, M1.3
    ↓
All complete? → M1 updated → * [ 1 ]

```

---

## 🎯 Quick Reference Card

### Milestone Naming:

- `M1` = Level 0 milestone
- `M1.1` = Level 1 section of M1
- `M1.1.1` = Level 2 step of M1.1

### File Locations:

- `level0/requirements.md` → Contains all `M{N}` strategic milestones
- `level1/requirements.md` → Contains all `M{N.X}` tactical sections  
- `level2/level2_m{N}/requirements.md` → Contains all `M{N.X.Y}` implementation steps

### Status Checkboxes:

- `[ ]` = Not started
- `[ - ]` = In progress
- `[ 1 ]` = Done (first time)
- `[ 2+ ]` = Done (reopened n-1 times)

### Feature Mapping:

- Each `M{N.X.Y}` → One or more `F{XXX}`
- Feature references parent in [DEFINITION.md](http://definition.md/)
- Feature completion updates parent checkbox

---

***Now you have a complete, traceable system from strategic vision to production code!** 🎼*

---

## 🧪 Advanced Testing Requirements

### Mandatory Quality Gates

**CRITICAL**: All Symphony components must pass these quality gates before completion:

#### 1. Test Execution Gates
- **Unit Tests**: All tests pass WITHOUT warnings or failures
- **Integration Tests**: All tests pass WITHOUT warnings or failures  
- **Documentation Tests**: All doc tests pass WITHOUT warnings or failures
- **Failed Test Recovery**: Use `cargo nextest run \--failed` to rerun only failed tests
- **MANDATORY**: Use nextest whenever possible - `cargo nextest run` preferred over `cargo test`

#### 2. Performance Gates
- **Benchmarks**: When benchmarks exist, must pass with <15% outliers
- **Performance Targets**: Must meet specific targets defined in acceptance criteria
- **Stress Testing**: Must handle collapse scenarios identified in BIF evaluation

#### 3. Code Quality Gates
- **Clippy**: All clippy checks pass (zero warnings tolerance)
- **Documentation**: All public APIs documented, docs generate successfully
- **Warnings**: Zero tolerance for any compiler or tool warnings

### Advanced Testing Integration

**When Required by Acceptance Criteria:**

#### Benchmark Testing
```toml
[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }
```

**Usage**: Performance-critical components must include criterion benchmarks
**Threshold**: <15% outliers in benchmark results
**Command**: `cargo bench` (integrated with quality gates)

#### Property-Based Testing
```toml
[dev-dependencies]
proptest = "1.4"
```

**Usage**: Algorithm correctness validation with generated test cases
**Coverage**: Critical algorithms and data structure invariants
**Integration**: Part of standard test suite execution

#### Fuzz Testing
```toml
[dev-dependencies]
cargo-fuzz = "0.11"
```

**Usage**: Security-critical components and parsers
**Duration**: Minimum 10 minutes continuous fuzzing
**Integration**: CI/CD pipeline for critical paths

### Mandatory Feature Flags Template

**REQUIRED**: All Symphony crates must include these feature flags:

```toml
[features]
# Default runs only fast unit tests
default = []

# Individual test category features
unit = []
integration = []
e2e = []

# Performance and validation features
slow = []
benchmarks = []
property_tests = []
fuzz_tests = []

# Business domain features (customize per crate)
auth = []
users = []
services = []
repositories = []
redis = []

# CI/CD management
ci_cd_issue = []  # Do not include until explicitly mentioned by user
```

### sy-commons Integration Requirements

**MANDATORY**: All Symphony components must:

1. **Use sy-commons for error handling**:
   ```rust
   use sy_commons::error::SymphonyError;
   ```

2. **Use duck!() for debugging**:
   ```rust
   use sy_commons::debug::duck;
   duck!("Suspicious operation: {}", operation_details);
   ```

3. **Follow sy-commons patterns**:
   - Configuration management via sy_commons::config
   - Logging via sy_commons::logging
   - Filesystem operations via sy_commons::filesystem
   - Pre-validation via sy_commons::prevalidation

### Documentation Standards

**MANDATORY**: Prevent documentation warnings:

1. **Crate-level documentation**:
   ```rust
   //! # Crate Name
   //! 
   //! Brief description of crate purpose and functionality.
   ```

2. **Struct field documentation**:
   ```rust
   pub struct Config {
       /// The server port to bind to
       pub port: u16,
       /// Maximum number of concurrent connections
       pub max_connections: usize,
   }
   ```

3. **Enum variant documentation**:
   ```rust
   pub enum LogLevel {
       /// Debug level logging
       Debug,
       /// Information level logging
       Info,
   }
   ```

### Test Organization Standards

**Directory Structure**:
```
crate_name/
├── src/
├── tests/
│   ├── integration_tests.rs
│   └── fixtures/
├── benches/
│   └── performance_bench.rs
└── fuzz/
    └── fuzz_targets/
```

**Test Execution Commands**:
- `cargo test` - All tests including doc tests (FALLBACK ONLY)
- `cargo nextest run` - Fast parallel test execution (MANDATORY PREFERRED)
- `cargo nextest run \--failed` - Rerun only failed tests
- `cargo bench` - Performance benchmarks
- `cargo fuzz run target_name` - Fuzz testing

**MANDATORY Quote Escaping**: Always escape quotes in feature flags:
- ✅ CORRECT: `cargo nextest run \--features "unit,integration"`
- ❌ WRONG: `cargo nextest run --features unit,integration`

### Quality Assurance Checklist

**Before Feature Completion**:
- [ ] All unit tests pass (cargo nextest run - PREFERRED)
- [ ] All integration tests pass (cargo nextest run - PREFERRED)
- [ ] All documentation tests pass (cargo test --doc)
- [ ] All benchmarks pass with <15% outliers (cargo bench)
- [ ] Zero clippy warnings (cargo clippy)
- [ ] Documentation generates successfully (cargo doc)
- [ ] sy-commons integration verified
- [ ] Feature flags properly configured
- [ ] duck!() debugging used appropriately

**MANDATORY**: Use `cargo nextest run` instead of `cargo test` whenever possible

## Test Types Overview

| Test Type | Name | Needed (%) | Why this value | Covered somewhere else |
|-----------|------|------------|----------------|------------------------|
| Unit Tests | `#[test]` | 80% | Core logic, fast, reliable, easy to maintain | |
| Integration Tests | `tests/` | 60% | Ensure components work together | Unit tests |
| Snapshot Tests | `insta` | 30% | Large structured outputs, stable APIs | Integration tests |
| BDD Tests | `cucumber-rs` | 5% | Business-level behavior only | Unit / Integration |
| Property Tests | `proptest` | 10% | Edge cases, invariants | Unit tests |

**Notes**: Percentages are guidelines, not strict rules. Avoid duplication if test type is already satisfied elsewhere.

### JSON Snapshot Testing with insta

Use insta snapshot testing only when it makes sense:

✅ **Use insta when**:
- **Structured outputs**: JSON, YAML, maps, trees, ASTs
- **Large/deeply nested data**: Hard to test field-by-field
- **Stable APIs**: Public or semi-public API responses
- **Config outputs**: Configuration files, logs, GraphQL responses

❌ **Do NOT use insta when**:
- **Dynamic values**: timestamps, UUIDs, random IDs
- **Core business logic**: money calculations, permissions, rules
- **Simple outputs**: `assert_eq!(result, 42)` is sufficient
- **Highly volatile data**: Frequently changing structures

### BDD Tests (cucumber-rs)

BDD tests are usually NOT needed - use only when:
- Business-level behavior must be validated by non-developers
- Features are defined by business stakeholders
- Cross-system flows need human-readable scenarios
- If no strong reason exists → do not add BDD tests

**Performance Validation**:
- [ ] Benchmark results within acceptable ranges
- [ ] Property tests validate algorithm correctness
- [ ] Fuzz testing completed for security-critical components
- [ ] Stress collapse scenarios tested and documented