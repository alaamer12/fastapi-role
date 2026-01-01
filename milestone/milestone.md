# FastAPI-RBAC: Complete PyPI Package Transformation Milestone Guide

**Document Version:** 1.0  
**Created:** 2026-01-01  
**Purpose:** Comprehensive step-by-step blueprint for transforming business-coupled RBAC code into a general-purpose, production-ready PyPI package

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Phase 1: Analysis & Preparation](#2-phase-1-analysis--preparation)
3. [Phase 2: Core Generalization](#3-phase-2-core-generalization)
4. [Phase 3: Configuration Architecture](#4-phase-3-configuration-architecture)
5. [Phase 4: Extension Points & Plugin Architecture](#5-phase-4-extension-points--plugin-architecture)
6. [Phase 5: Testing Strategy Transformation](#6-phase-5-testing-strategy-transformation)
7. [Phase 6: Documentation & Examples](#7-phase-6-documentation--examples)
8. [Phase 7: Package Structure & Deployment](#8-phase-7-package-structure--deployment)
9. [Phase 8: CI/CD & Publishing](#9-phase-8-cicd--publishing)
10. [Phase 9: Post-Release & Maintenance](#10-phase-9-post-release--maintenance)
11. [Dependency Map](#11-dependency-map)

---

## 1. Executive Summary

### Current State Assessment

The existing `fastapi-role` codebase provides a comprehensive Role-Based Access Control (RBAC) system for FastAPI applications using Casbin as the policy engine. The system includes:

- **Core RBAC Classes:** `Role`, `RoleComposition`, `Permission`, `ResourceOwnership`, `Privilege`
- **Decorator System:** The `@require` decorator with multi-pattern authorization
- **Service Layer:** `RBACService` for policy evaluation, caching, and customer management
- **Query Filtering:** `RBACQueryFilter` for automatic data access control
- **Template Integration:** Jinja2 helpers for UI permission checks
- **Action Configurations:** `PageAction` and `TableAction` for RBAC-aware UI components

### Critical Business Coupling Points Identified

The following elements are tightly coupled to specific business logic and must be generalized:

1. **Hardcoded Role Enum** (`rbac.py:56-68`): Defines specific roles (`SUPERADMIN`, `SALESMAN`, `DATA_ENTRY`, `PARTNER`, `CUSTOMER`) rather than allowing dynamic role definition.

2. **Direct User Model Import** (`rbac.py:40`): `from app.models.user import User` - assumes specific User model structure.

3. **Hardcoded Configuration Paths** (`rbac.py:244`, `rbac_service.py:68`): Fixed paths `config/rbac_model.conf` and `config/rbac_policy.csv`.

4. **Business-Specific Resource Types** (`rbac_service.py:160-202`): Hardcoded `configuration`, `quote`, `order` resource ownership checks.

5. **Customer Model Coupling** (`rbac_service.py:37`): `from app.models.customer import Customer` and auto-creation logic.

6. **Database Connection Import** (`rbac.py:412-413`): `from app.database.connection import get_session_maker`.

7. **Business Exception Classes** (`rbac_service.py:31-35`): Custom exceptions from `app.core.exceptions`.

8. **Query Filter Dependencies** (`rbac.py:425-427, 458-460, 491-493`): Hardcoded model imports for `Configuration`, `Quote`, `Order`.

### Transformation Goals

Transform this codebase into a package that:
- Allows users to define their own roles dynamically
- Works with any User model implementing a simple protocol
- Enables custom resource ownership validation
- Provides pluggable storage backends
- Maintains all existing functionality while being business-agnostic

---

## 2. Phase 1: Analysis & Preparation

### Step 1.1: Complete Code Audit

**Objective:** Create a comprehensive inventory of all files, dependencies, and business-specific coupling points.

**Actions:**

1. **Document All Files:**
   - `fastapi_role/__init__.py` - Package exports and version
   - `fastapi_role/rbac.py` - Core RBAC classes and decorator (785 lines)
   - `fastapi_role/rbac_actions.py` - UI action configurations (129 lines)
   - `fastapi_role/rbac_service.py` - Service layer with caching (553 lines)
   - `config/rbac_model.conf` - Casbin model configuration
   - `config/rbac_policy.csv` - Default policy definitions

2. **Map Import Dependencies:**
   Each file's external dependencies must be categorized as:
   - **Standard Library:** `logging`, `functools`, `typing`, `enum`, `dataclasses`, `collections.abc`, `inspect`, `datetime`
   - **Third-Party:** `casbin`, `fastapi`, `sqlalchemy`, `pydantic`
   - **Business-Specific:** `app.models.user`, `app.models.customer`, `app.models.configuration`, `app.database.connection`, `app.core.exceptions`, `app.services.base`, `app.services.rbac`

3. **Identify All Hardcoded Values:**
   - Role names: `superadmin`, `salesman`, `data_entry`, `partner`, `customer`
   - Resource types: `configuration`, `quote`, `order`, `customer`, `template`
   - Default customer type: `residential`
   - File paths: `config/rbac_model.conf`, `config/rbac_policy.csv`

### Step 1.2: Requirements Gathering

**Objective:** Define what the generalized package must support.

**Functional Requirements:**
- FR-1: Dynamic role definition without code modification
- FR-2: User model protocol with minimal interface requirements
- FR-3: Pluggable resource ownership validation
- FR-4: Configurable policy storage (file, database, memory)
- FR-5: Zero-configuration defaults with override capability
- FR-6: Backward-compatible API for existing users

**Non-Functional Requirements:**
- NFR-1: Performance caching with configurable TTL
- NFR-2: Thread-safe operations
- NFR-3: Comprehensive type hints for IDE support
- NFR-4: Python 3.9+ compatibility
- NFR-5: Minimal dependency footprint

### Step 1.3: Create Refactoring Branch

**Objective:** Preserve original functionality while enabling transformation.

**Actions:**

1. Create a dedicated branch for refactoring work
2. Set up a parallel test environment to validate behavior preservation
3. Create a comprehensive test snapshot of current behavior
4. Document all existing test cases and their coverage areas

---

## 3. Phase 2: Core Generalization

### Step 2.1: Create Role Factory System

**Current Implementation Problem:**
The `Role` enum in `rbac.py:56-68` defines five specific business roles. Users cannot add, remove, or modify roles without changing the library source code.

**Generalization Approach:**

Instead of a static enum, create a **Role Factory** that generates role enums dynamically at runtime. The factory should:

1. Accept role definitions from configuration (dict, YAML, JSON, or Python code)
2. Generate an enum-like class with bitwise operation support
3. Cache the generated roles for performance
4. Provide validation for role names
5. Support role hierarchies and inheritance

**Why Enum Must Be Replaced With Dynamic Construction:**
Python enums are immutable once defined. The values are compile-time constants. To allow users to define their own roles, we need either:
- A factory pattern that creates enums from configuration
- A class-based approach that mimics enum behavior but is mutable

The factory pattern is preferred because it:
- Maintains type safety when roles are defined
- Allows IDE autocompletion when roles are created via a typed configuration
- Keeps the familiar `Role.ADMIN` syntax after initialization
- Enables validation during role creation

**Implementation Strategy:**

Create a `create_roles()` function that:
1. Takes a dictionary or list of role names
2. Creates a dynamic Enum class with bitwise OR support
3. Injects the `__or__` and `__ror__` methods for `RoleComposition` support
4. Returns the generated Role type that can be used throughout the application

Create a `RoleRegistry` class that:
1. Stores the active role configuration
2. Provides methods to validate role strings against registered roles
3. Enables runtime introspection of available roles
4. Supports role aliases for backward compatibility

### Step 2.2: Abstract User Model

**Current Implementation Problem:**
`rbac.py:40` directly imports `from app.models.user import User`, requiring users to have a specific User model in a specific location with specific attributes.

**Generalization Approach:**

Create a **User Protocol** that defines the minimal interface required:
- `id`: Any type (int, UUID, str)
- `email`: str (used as Casbin subject identifier)
- `role`: str (user's assigned role)

**Why Protocol Over Base Class:**
Using `typing.Protocol` (PEP 544) instead of inheritance:
- Does not require users to inherit from a base class
- Works with any existing User model that has the required attributes
- Enables structural subtyping - if it has the attributes, it's valid
- Avoids diamond inheritance issues in complex applications
- Is more Pythonic for modern Python codebases

**Implementation Strategy:**

Create `UserProtocol` with:
1. Required attributes: `id`, `email`, `role`
2. Optional method: `has_role(role_name: str) -> bool`

If `has_role` is not implemented, the library provides a default implementation that:
1. Compares `user.role` against the given role name
2. Handles superadmin bypass if configured
3. Supports role composition checking

### Step 2.3: Abstract Resource Ownership

**Current Implementation Problem:**
`rbac_service.py:160-202` contains hardcoded resource type handling for `configuration`, `quote`, `order`, and `customer`. Each resource type has specific database queries and relationships.

**Generalization Approach:**

Create a **Resource Ownership Provider** system that:
1. Allows users to register custom ownership validators per resource type
2. Provides a default "always allow superadmin" behavior
3. Falls back gracefully when no custom handler is registered
4. Supports async validation for database-backed checks

**Why Pluggable Providers:**
Resource ownership is inherently business-specific. A CRM might check account relationships, an e-commerce system might check order ownership, and a SaaS might check tenant membership. The library cannot anticipate all possible ownership semantics.

By using a provider pattern:
- Users register handlers for their specific resource types
- The library provides the framework and common utilities
- Unknown resource types can default to deny or allow based on configuration
- Complex ownership chains can be implemented in user code

**Implementation Strategy:**

Create `OwnershipProvider` protocol:
1. `async def check_ownership(user, resource_type: str, resource_id: Any) -> bool`

Create `OwnershipRegistry`:
1. `register(resource_type: str, provider: OwnershipProvider)`
2. `check(user, resource_type: str, resource_id: Any) -> bool`
3. Default provider for "superadmin passes all" logic

### Step 2.4: Decouple Query Filters

**Current Implementation Problem:**
`RBACQueryFilter` in `rbac.py:389-493` contains methods like `filter_configurations`, `filter_quotes`, `filter_orders` that directly import business models.

**Generalization Approach:**

The query filter concept is valuable but must be generalized. Instead of predefined filter methods, provide:
1. A base filter function that applies customer-based filtering
2. User-registrable filter functions per model type
3. Utility functions for common filter patterns

**Why Generic Filters:**
Query filtering is an advanced feature that tightly couples to the user's database schema. Rather than trying to support all possible schemas, provide:
- Building blocks for constructing filters
- Examples of how to create filters for SQLAlchemy, SQLModel, etc.
- Optional integration modules for popular ORMs

**Implementation Strategy:**

Create `QueryFilterBuilder`:
1. Accept a callable that returns accessible customer/resource IDs
2. Provide helper methods for `in_()` filter construction
3. Document usage patterns rather than implementing specific filters

The user implements their own filter methods using the primitives:
- `get_accessible_resources(user, resource_type) -> list[int]`
- Apply to their specific query syntax

---

## 4. Phase 3: Configuration Architecture

### Step 3.1: Create Configuration System

**Current Implementation Problem:**
Casbin configuration paths are hardcoded in `rbac.py:244` and `rbac_service.py:68`. Users cannot easily customize paths or use alternative storage.

**Generalization Approach:**

Create a hierarchical configuration system with multiple override levels:
1. **Library Defaults:** Built-in sensible defaults
2. **Configuration Files:** YAML, TOML, or Python config
3. **Environment Variables:** For deployment-time configuration
4. **Programmatic Override:** For complete control in code

**Configuration Categories:**

1. **Policy Configuration:**
   - `model_path`: Path to Casbin model file
   - `policy_path`: Path to Casbin policy file
   - `policy_adapter`: Custom Casbin adapter instance
   - `auto_save`: Whether to auto-save policy changes

2. **Role Configuration:**
   - `roles`: List of role definitions
   - `default_role`: Role for new users
   - `superadmin_role`: Role that bypasses all checks

3. **Behavior Configuration:**
   - `unknown_resource_policy`: "allow" or "deny" for unregistered resources
   - `cache_enabled`: Whether to use permission caching
   - `cache_ttl_seconds`: Cache time-to-live
   - `log_authorization_failures`: Whether to log denied access

4. **User Configuration:**
   - `user_identifier_field`: Which user attribute to use as Casbin subject
   - `user_role_field`: Which user attribute contains the role

**Why Hierarchical Configuration:**
Different deployment scenarios need different configuration mechanisms:
- Developers want programmatic control during development
- Operations teams want environment variables in containers
- Package users want sensible defaults that "just work"

### Step 3.2: Design Configuration Classes

**Implementation Strategy:**

Create a `RBACConfig` dataclass with:
1. All configuration options with default values
2. Type hints for validation and IDE support
3. Factory method `from_env()` for environment variable loading
4. Factory method `from_file(path)` for file-based configuration
5. Validation method to check configuration consistency

Create configuration loading priority:
1. Explicit programmatic values override all
2. Environment variables override file configuration
3. File configuration overrides defaults
4. Defaults apply when nothing else specified

### Step 3.3: Default Configuration Templates

**Deliverables:**

1. A default `rbac_model.conf` for common RBAC patterns
2. A template `rbac_policy.csv` with commented examples
3. Example configuration files for different scenarios:
   - Simple role-based access
   - Resource ownership with roles
   - Hierarchical roles with inheritance

---

## 5. Phase 4: Extension Points & Plugin Architecture

### Step 4.1: Define Extension Interfaces

**Objective:** Create clear extension points for advanced customization.

**Extension Points:**

1. **Subject Provider:**
   - Determines what value is used as the Casbin subject
   - Default: Use `user.email`
   - Custom: User ID, username, or composite value

2. **Role Provider:**
   - Determines how to get a user's roles
   - Default: Read `user.role` attribute
   - Custom: Multi-role support, role from database

3. **Policy Adapter:**
   - Determines how policies are stored
   - Default: File-based CSV
   - Custom: Database, Redis, external API

4. **Cache Provider:**
   - Determines how permission cache works
   - Default: In-memory dictionary
   - Custom: Redis, Memcached, distributed cache

5. **Ownership Provider:**
   - Determines resource ownership validation
   - Default: Superadmin always passes
   - Custom: Database lookups, external service calls

### Step 4.2: Create Provider Registration System

**Implementation Strategy:**

Create a central `RBACProviders` registry that:
1. Stores registered providers by type
2. Allows runtime registration
3. Validates provider interface compliance
4. Provides factory method for creating configured instances

Provider lifecycle:
1. Providers are registered at application startup
2. Providers are initialized with configuration when RBAC is initialized
3. Providers may implement async initialization for database connections
4. Providers should be reusable across requests

### Step 4.3: Implement Default Providers

**Deliverables:**

1. `DefaultSubjectProvider`: Returns `user.email`
2. `DefaultRoleProvider`: Returns `user.role` with optional superadmin bypass
3. `FileAdapter`: Casbin file adapter wrapper
4. `MemoryCacheProvider`: Dictionary-based cache with TTL
5. `DefaultOwnershipProvider`: Superadmin always passes, others configurable

---

## 6. Phase 5: Testing Strategy Transformation

### Step 5.1: Analyze Current Test Suite

**Current Test Files:**
- `test_rbac_core.py` (580 lines): Core RBAC class tests
- `test_rbac_decorators_advanced.py` (544 lines): Decorator pattern tests
- `test_rbac_performance.py` (579 lines): Performance and caching tests
- `test_rbac_properties.py` (280 lines): Property-based tests
- `test_rbac_service.py` (484 lines): Service layer tests
- `test_simple_decorator.py` (40 lines): Simple decorator smoke test
- `test_simple_property_tests.py` (347 lines): Simplified property tests
- `test_user_model_rbac.py` (315 lines): User model integration tests

**Issue:** Tests depend on `app.core.rbac`, `app.models.user`, `app.models.customer`, etc.

### Step 5.2: Create Test Infrastructure

**Approach:**

1. **Create Mock User Class:**
   Define a `MockUser` class that implements `UserProtocol` for testing.

2. **Create Mock Configuration:**
   Define default test configuration that doesn't require file system.

3. **Create Test Fixtures:**
   - `@pytest.fixture` for RBAC service with in-memory configuration
   - `@pytest.fixture` for users with various roles
   - `@pytest.fixture` for mock ownership providers

4. **Create Test Roles:**
   Define a standard set of test roles that all tests can use.

### Step 5.3: Transform Existing Tests

**Strategy:**

1. Preserve all test logic and assertions
2. Replace business-specific imports with library-provided mocks
3. Replace hardcoded `Role.SUPERADMIN` with configurable role from test config
4. Replace database mocks with in-memory implementations
5. Add new tests for dynamic role configuration

**Test Categories After Transformation:**

1. **Unit Tests:** Test individual classes and functions in isolation
2. **Integration Tests:** Test component interaction within the library
3. **Contract Tests:** Validate that protocols are correctly defined
4. **Property Tests:** Verify correctness properties hold across inputs
5. **Performance Tests:** Ensure caching and performance meet requirements
6. **Example Tests:** Verify documentation examples work correctly

### Step 5.4: Add New Test Categories

**New Tests Required:**

1. **Configuration Tests:**
   - Test loading from environment variables
   - Test loading from different file formats
   - Test configuration validation
   - Test configuration override priority

2. **Dynamic Role Tests:**
   - Test creating custom roles at runtime
   - Test role composition with custom roles
   - Test role registration and validation

3. **Provider Tests:**
   - Test provider registration
   - Test provider lifecycle
   - Test provider fallback behavior

4. **Compatibility Tests:**
   - Test with minimal User models
   - Test with SQLAlchemy models
   - Test with Pydantic models

---

## 7. Phase 6: Documentation & Examples

### Step 6.1: API Documentation

**Structure:**

1. **Getting Started Guide:**
   - Installation
   - Basic setup with minimal configuration
   - First protected endpoint
   - Running the example

2. **Configuration Reference:**
   - All configuration options with descriptions
   - Environment variable mapping
   - File format specifications
   - Default values

3. **API Reference:**
   - All public classes with full docstrings
   - Function signatures with type hints
   - Usage examples for each major feature

4. **Architecture Overview:**
   - How components interact
   - Extension points diagram
   - Request flow through authorization

### Step 6.2: Example Applications

**Deliverables:**

1. **Minimal Example:**
   Single-file example showing basic usage with in-memory configuration.

2. **File-Based Example:**
   Example using file-based policy configuration.

3. **Database Example:**
   Example with SQLAlchemy integration and database-backed policies.

4. **Multi-Tenant Example:**
   Example showing tenant isolation with RBAC.

5. **API Gateway Example:**
   Example showing RBAC as a middleware/gateway layer.

### Step 6.3: Migration Guide

**Content:**

1. **From Static Roles to Dynamic Roles:**
   How to migrate if you were using the hardcoded Role enum.

2. **From Hardcoded Paths to Configuration:**
   How to migrate path configurations.

3. **From Direct User Import to Protocol:**
   How to make existing User models compatible.

4. **Version Compatibility Matrix:**
   What features are available in what versions.

---

## 8. Phase 7: Package Structure & Deployment

### Step 7.1: Final Package Structure

```
fastapi-rbac/
├── src/
│   └── fastapi_rbac/
│       ├── __init__.py              # Public API exports
│       ├── core/
│       │   ├── __init__.py
│       │   ├── roles.py             # Role factory and registry
│       │   ├── permissions.py       # Permission class
│       │   ├── ownership.py         # ResourceOwnership class
│       │   ├── privilege.py         # Privilege class
│       │   └── composition.py       # RoleComposition class
│       ├── decorators/
│       │   ├── __init__.py
│       │   └── require.py           # The @require decorator
│       ├── service/
│       │   ├── __init__.py
│       │   ├── rbac_service.py      # Core service (generalized)
│       │   └── cache.py             # Cache implementations
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py              # Protocol definitions
│       │   ├── subject.py           # Subject providers
│       │   ├── role.py              # Role providers
│       │   ├── ownership.py         # Ownership providers
│       │   └── policy.py            # Policy adapters
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py          # RBACConfig class
│       │   ├── defaults.py          # Default configuration
│       │   └── loaders.py           # Configuration loaders
│       ├── templates/
│       │   ├── __init__.py
│       │   └── helpers.py           # Template integration
│       ├── actions/
│       │   ├── __init__.py
│       │   └── ui_actions.py        # PageAction, TableAction
│       ├── protocols/
│       │   ├── __init__.py
│       │   └── user.py              # UserProtocol
│       ├── exceptions.py            # Package-specific exceptions
│       └── py.typed                 # PEP 561 marker
├── tests/
│   ├── conftest.py                  # Shared fixtures
│   ├── unit/
│   │   ├── test_roles.py
│   │   ├── test_permissions.py
│   │   ├── test_decorator.py
│   │   └── ...
│   ├── integration/
│   │   ├── test_service.py
│   │   ├── test_providers.py
│   │   └── ...
│   └── property/
│       └── test_properties.py
├── docs/
│   ├── index.md
│   ├── getting-started.md
│   ├── configuration.md
│   ├── api-reference.md
│   └── examples/
├── examples/
│   ├── minimal/
│   ├── file_based/
│   ├── database/
│   └── multi_tenant/
├── config/
│   ├── rbac_model.conf              # Default model
│   └── rbac_policy.csv.example      # Example policy
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
└── CONTRIBUTING.md
```

### Step 7.2: Package Metadata (pyproject.toml)

**Key Sections:**

1. **Project Metadata:**
   - Name: `fastapi-rbac`
   - Description: Clear, searchable description
   - Keywords: `fastapi`, `rbac`, `authorization`, `casbin`, `role-based-access-control`
   - Classifiers: Python versions, framework, license

2. **Dependencies:**
   - Required: `casbin>=1.0`, `fastapi>=0.100.0`
   - Optional groups: `[sqlalchemy]`, `[redis]`, `[dev]`, `[docs]`

3. **Entry Points:**
   - None required (library, not CLI tool)

4. **Build System:**
   - Use modern build backends: `hatchling`, `flit-core`, or `setuptools`
   - Prefer `hatchling` for better project management

### Step 7.3: Version Strategy

**Approach: Semantic Versioning (SemVer)**

- **Major (X.0.0):** Breaking API changes
- **Minor (0.X.0):** New features, backward compatible
- **Patch (0.0.X):** Bug fixes, no API changes

**Initial Release Strategy:**

1. **0.1.0:** First public release with core functionality
2. **0.2.0-0.9.0:** Add features, gather feedback, refine API
3. **1.0.0:** Stable API, production-ready release

---

## 9. Phase 8: CI/CD & Publishing

### Step 8.1: GitHub Actions Workflows

**Required Workflows:**

1. **test.yml:** Run on every PR and push
   - Matrix testing: Python 3.9, 3.10, 3.11, 3.12
   - OS testing: Ubuntu, Windows, macOS
   - Run pytest with coverage
   - Upload coverage to Codecov

2. **lint.yml:** Code quality checks
   - Ruff for linting
   - Black for formatting
   - mypy for type checking
   - isort for import ordering

3. **release.yml:** Triggered by version tags
   - Build source distribution and wheels
   - Publish to PyPI
   - Create GitHub release with changelog

4. **docs.yml:** Documentation build
   - Build documentation with MkDocs/Sphinx
   - Deploy to GitHub Pages or ReadTheDocs

### Step 8.2: PyPI Publishing Process

**Steps:**

1. **Create PyPI Account:**
   - Register at pypi.org
   - Create API token for publishing
   - Add token as GitHub secret `PYPI_TOKEN`

2. **Configure Trusted Publishing:**
   - Use OIDC-based publishing from GitHub Actions
   - More secure than token-based publishing
   - Configure in PyPI project settings

3. **Build Process:**
   - Use `python -m build` to create distributions
   - Verify with `twine check dist/*`
   - Upload with `twine upload dist/*` or GitHub Action

### Step 8.3: Release Checklist

**Pre-Release:**
1. All tests passing on all Python versions
2. Documentation updated and building
3. CHANGELOG.md updated with all changes
4. Version bumped in `pyproject.toml` and `__init__.py`
5. Security audit of dependencies
6. License compliance check

**Release:**
1. Create git tag matching version
2. Push tag to trigger release workflow
3. Verify package published to PyPI
4. Verify package installable: `pip install fastapi-rbac`

**Post-Release:**
1. Announce on relevant channels
2. Monitor issues for early bug reports
3. Prepare hotfix branch if needed

---

## 10. Phase 9: Post-Release & Maintenance

### Step 10.1: Community Management

**Channels:**

1. **GitHub Issues:** Bug reports and feature requests
2. **GitHub Discussions:** Q&A and community support
3. **Discord/Slack:** Optional real-time community

**Templates:**

- Bug report template
- Feature request template
- Security vulnerability reporting process

### Step 10.2: Maintenance Schedule

**Regular Tasks:**

1. **Weekly:** Triage new issues, respond to discussions
2. **Monthly:** Dependency updates, security patches
3. **Quarterly:** Minor version releases with new features
4. **Annually:** Major version consideration, deprecation review

### Step 10.3: Deprecation Policy

**Process:**

1. Mark feature as deprecated in code with warnings
2. Document deprecation in CHANGELOG and docs
3. Keep deprecated feature for at least one minor version
4. Remove in next major version

---

## 11. Dependency Map

### Phase Dependencies

```
Phase 1 (Analysis) 
    ↓
Phase 2 (Core Generalization) ← Must complete before Phase 3-5
    ↓
Phase 3 (Configuration) ─┬─→ Phase 4 (Extension Points)
                         │
                         └─→ Phase 5 (Testing) ← Requires Phase 3+4 interfaces
                                  ↓
                              Phase 6 (Documentation) ← Requires stable API
                                  ↓
                              Phase 7 (Package Structure)
                                  ↓
                              Phase 8 (CI/CD & Publishing)
                                  ↓
                              Phase 9 (Maintenance) ← Post-release
```

### Estimated Timeline

| Phase | Estimated Duration | Dependencies |
|-------|------------------|--------------|
| Phase 1 | 1-2 days | None |
| Phase 2 | 3-5 days | Phase 1 |
| Phase 3 | 2-3 days | Phase 2 |
| Phase 4 | 2-3 days | Phase 2 |
| Phase 5 | 3-4 days | Phase 2, 3, 4 |
| Phase 6 | 2-3 days | Phase 2-5 |
| Phase 7 | 1-2 days | Phase 6 |
| Phase 8 | 1-2 days | Phase 7 |
| Phase 9 | Ongoing | Phase 8 |

**Total Estimate:** 15-24 days for initial release

---

## Appendix A: File-by-File Transformation Checklist

### fastapi_role/__init__.py
- [ ] Update exports to reflect new module structure
- [ ] Add `__version__` from single source of truth
- [ ] Update `__all__` list

### fastapi_role/rbac.py → Split into multiple modules
- [ ] Extract `Role` to `core/roles.py` with factory pattern
- [ ] Extract `RoleComposition` to `core/composition.py`
- [ ] Extract `Permission` to `core/permissions.py`
- [ ] Extract `ResourceOwnership` to `core/ownership.py`
- [ ] Extract `Privilege` to `core/privilege.py`
- [ ] Extract `RBACService` to `service/rbac_service.py` with generalization
- [ ] Extract `RBACQueryFilter` to optional module or remove
- [ ] Extract `require` decorator to `decorators/require.py`
- [ ] Remove `from app.models.user import User`
- [ ] Remove hardcoded role values
- [ ] Remove hardcoded config paths

### fastapi_role/rbac_service.py → service/rbac_service.py
- [ ] Remove customer model import
- [ ] Remove all `app.*` imports
- [ ] Replace exception classes with package exceptions
- [ ] Make resource ownership pluggable
- [ ] Remove `get_or_create_customer_for_user` (business-specific)
- [ ] Generalize cache implementation

### fastapi_role/rbac_actions.py → actions/ui_actions.py
- [ ] No major changes needed (already generic)
- [ ] Update imports

### config/rbac_model.conf
- [ ] Keep as default template
- [ ] Document customization options

### config/rbac_policy.csv
- [ ] Convert to `.example` file
- [ ] Add extensive comments

---

## Appendix B: Preserved Functionality Verification

Every existing capability must work after transformation:

| Feature | Current File | New Location | Verification Test |
|---------|-------------|--------------|-------------------|
| Role enum with bitwise OR | rbac.py:56-88 | core/roles.py | test_roles.py |
| RoleComposition | rbac.py:90-134 | core/composition.py | test_composition.py |
| Permission class | rbac.py:137-162 | core/permissions.py | test_permissions.py |
| ResourceOwnership | rbac.py:165-188 | core/ownership.py | test_ownership.py |
| Privilege bundles | rbac.py:191-229 | core/privilege.py | test_privilege.py |
| @require decorator | rbac.py:500-569 | decorators/require.py | test_decorator.py |
| Multiple decorator OR logic | rbac.py:527-566 | decorators/require.py | test_decorator_advanced.py |
| Permission caching | rbac_service.py:76-78 | service/cache.py | test_cache.py |
| PageAction/TableAction | rbac_actions.py | actions/ui_actions.py | test_actions.py |

---

This milestone guide provides the complete blueprint for transforming the business-coupled `fastapi-role` code into a general-purpose, production-ready PyPI package while preserving all existing functionality.
