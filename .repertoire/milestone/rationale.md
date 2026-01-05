# fastapi-role: Rationale, Decisions, Constraints & Recommendations

**Document Version:** 1.0  
**Created:** 2026-01-01  
**Purpose:** Comprehensive explanation of all design decisions, trade-offs, constraints, and high-value recommendations for the package transformation

---

## Table of Contents

1. [Guiding Principles](#1-guiding-principles)
2. [Architectural Decisions](#2-architectural-decisions)
3. [Technology Choices](#3-technology-choices)
4. [Generalization Decisions](#4-generalization-decisions)
5. [Trade-offs & Constraints](#5-trade-offs--constraints)
6. [High-Value Recommendations](#6-high-value-recommendations)
7. [Rejected Alternatives](#7-rejected-alternatives)
8. [Risk Analysis](#8-risk-analysis)

---

## 1. Guiding Principles

### 1.1 Principle of Least Surprise

**Statement:** The API should behave in ways that users expect based on common Python conventions and FastAPI patterns.

**Application:**
- Decorator syntax mirrors FastAPI's `@Depends` pattern
- Configuration uses familiar patterns (Pydantic, environment variables)
- Error messages are clear and actionable
- Type hints enable IDE autocompletion

**Rationale:**
FastAPI users expect certain patterns. By following established conventions, the learning curve is minimized. Users can focus on implementing their authorization logic rather than learning a new paradigm.

### 1.2 Progressive Disclosure of Complexity

**Statement:** Simple use cases should require minimal configuration; complex features should be available but not required.

**Application:**
- Zero-configuration defaults work out of the box
- Advanced features are discovered through documentation, not forced upfront
- Common patterns have dedicated shortcuts; everything is customizable

**Rationale:**
Most users start with simple requirements and add complexity over time. Front-loading configuration would drive away potential users. The library should grow with the user's needs.

### 1.3 Explicit Over Implicit

**Statement:** Authorization decisions should be transparent and traceable.

**Application:**
- All role checks are explicit in decorators
- Configuration is in files or code, not magic conventions
- Logging provides complete audit trails
- Failures explain what was checked and why it failed

**Rationale:**
Authorization is security-critical. Implicit behavior creates security risks and debugging difficulties. Users must be able to understand and audit every authorization decision.

### 1.4 Performance by Default

**Statement:** The library should be fast enough that users don't need to think about performance in typical use cases.

**Application:**
- Permission caching is enabled by default
- Hot paths are optimized
- Expensive operations are lazy and cached
- Performance tests enforce regression boundaries

**Rationale:**
Authorization checks occur on every request. If the library adds noticeable latency, users will bypass it or implement custom solutions. Performance must be a guaranteed property.

---

## 2. Architectural Decisions

### 2.1 Decision: Protocol-Based User Interface

**Decision:** Use `typing.Protocol` to define the User interface rather than requiring inheritance from a base class.

**Context:**
The current implementation imports `app.models.user.User` directly. For a general-purpose library, we cannot mandate a specific User class.

**Options Considered:**

| Option | Pros | Cons |
|--------|------|------|
| **Base Class** | Type safety, IDE support, can add helper methods | Requires inheritance, diamond problem with multiple libraries |
| **Duck Typing** | Maximum flexibility, works with anything | No type hints, runtime errors if interface missing |
| **Protocol** | Type safety without inheritance, structural typing | Python 3.8+ only, less familiar to some developers |
| **TypedDict** | Simple, JSON-like | No methods, read-only in practice |

**Decision Rationale:**

Protocol was chosen because:
1. **No Inheritance Required:** Users don't need to modify their existing User models
2. **Type Safety:** Static type checkers can verify compliance
3. **Runtime Checking:** `isinstance()` works with `runtime_checkable` Protocols
4. **Modern Python:** Aligns with Python 3.8+ best practices
5. **Minimal Interface:** Only requires the essential attributes

**Implications:**
- Minimum Python version is 3.9 (could support 3.8 with `typing_extensions`)
- Documentation must clearly specify the required attributes
- Runtime validation should provide helpful error messages when User doesn't match Protocol

### 2.2 Decision: Factory Pattern for Dynamic Roles

**Decision:** Use a factory function `create_roles()` to generate Role enums at runtime rather than defining static enums.

**Context:**
The current `Role` enum has hardcoded values (`SUPERADMIN`, `SALESMAN`, etc.). Different applications need different roles.

**Options Considered:**

| Option | Pros | Cons |
|--------|------|------|
| **Static Enum** | Type safe, IDE support | Cannot be customized without changing library code |
| **String-Based Roles** | Maximum flexibility | No type safety, easy typos, no IDE completion |
| **Dynamic Enum Factory** | Type safety after creation, customizable | More complex initialization, created type not known at import time |
| **Registry Pattern** | Flexible, familiar | Less elegant syntax, string-based matching |

**Decision Rationale:**

The factory pattern was chosen because:
1. **Preserves Enum Ergonomics:** `Role.ADMIN` syntax works once roles are created
2. **Type Safety:** The generated enum is a real Python enum
3. **Customizable:** Users define their own roles at initialization
4. **Bitwise Operations:** The factory can inject `__or__` for role composition
5. **Validation:** Invalid role names are caught at creation time

**Implications:**
- Roles must be created before they're used (typically at app startup)
- IDE autocompletion works for the generated roles
- Documentation must clearly explain the initialization step

### 2.3 Decision: Provider-Based Extension Architecture

**Decision:** Use a provider/registry pattern for pluggable components (ownership checking, subject extraction, etc.).

**Context:**
Resource ownership validation is inherently business-specific. The current implementation hardcodes checks for `configuration`, `quote`, `order`, etc.

**Options Considered:**

| Option | Pros | Cons |
|--------|------|------|
| **Inheritance/Override** | Familiar, powerful | Forces single implementation, testing difficulty |
| **Callback Functions** | Simple, functional | No structure, hard to document |
| **Provider Protocol** | Structured, testable, swappable | More boilerplate |
| **Plugin System** | Very flexible, discovery | Complex, overkill for this use case |

**Decision Rationale:**

Provider pattern was chosen because:
1. **Clear Interface:** Protocols define exactly what providers must implement
2. **Testable:** Providers can be mocked or replaced in tests
3. **Composable:** Multiple providers can be combined
4. **Documentary:** The interface documents expected behavior
5. **Default Implementations:** The library ships with sensible defaults

**Implications:**
- More code structure upfront
- Users implement providers for their specific needs
- The library provides base implementations to extend

### 2.4 Decision: Configuration via Dataclass

**Decision:** Use a Pydantic-style dataclass for configuration rather than dictionary or environment-only configuration.

**Context:**
Configuration is currently hardcoded in the source. A general-purpose library needs flexible configuration.

**Options Considered:**

| Option | Pros | Cons |
|--------|------|------|
| **Dictionary** | Simple, familiar | No type safety, no validation |
| **Environment Variables Only** | 12-factor app compliant | No structured nested config, string-only |
| **Pydantic Model** | Validation, env support, IDE | Additional dependency |
| **Dataclass + Manual Validation** | No deps, type hints | More work for validation |
| **attrs/dataclasses** | Built-in or small dep | Less validation than Pydantic |

**Decision Rationale:**

A dataclass with optional Pydantic integration:
1. **Zero Dependencies for Basic Use:** Dataclass is stdlib
2. **Pydantic Optional:** Users can use Pydantic if they want validation
3. **Type Hints:** IDE support and static analysis
4. **Hierarchical:** Nested configs for complex setups
5. **Factory Methods:** `from_env()`, `from_file()` for convenience

**Implications:**
- Configuration class is documented with all options
- Environment variable loading is manual but clear
- Users can validate with Pydantic if they choose

---

## 3. Technology Choices

### 3.1 Dependency: Casbin

**Current State:** Casbin is the core policy engine used by the library.

**Evaluation:**

| Aspect | Assessment |
|--------|------------|
| **Maturity** | Stable, widely used, active development |
| **Features** | RBAC, ABAC, ACL, multi-tenant, many adapters |
| **Performance** | Fast policy evaluation, caching support |
| **Python Support** | Official Python package, good documentation |
| **Size** | ~50KB, minimal dependencies |

**Decision: Keep Casbin**

**Rationale:**
1. **Feature Complete:** Supports all required authorization patterns
2. **Ecosystem:** Many storage adapters available
3. **Proven:** Used in production by many organizations
4. **Declarative:** Policy files are human-readable and auditable
5. **Standard:** PERM model is well-understood

**Constraints:**
- Users must understand Casbin's policy language
- Complex policies may be harder to debug
- Performance depends on policy complexity

**Recommendation:** Provide comprehensive documentation on Casbin policy syntax with examples specific to this library.

### 3.2 Dependency: FastAPI

**Current State:** FastAPI is required for decorator integration.

**Evaluation:**

| Aspect | Assessment |
|--------|------------|
| **Market Position** | One of the most popular Python web frameworks |
| **Stability** | Breaking changes are rare and well-documented |
| **Async Support** | First-class async/await support |
| **Typing** | Excellent type hint integration |
| **Growth** | Continuing strong adoption |

**Decision: Keep FastAPI as Core Dependency**

**Rationale:**
1. **Target Audience:** The library is specifically for FastAPI applications
2. **Integration:** Decorators need FastAPI's dependency injection
3. **Type System:** Leverages FastAPI's Pydantic integration
4. **HTTPException:** Uses FastAPI's exception handling

**Constraints:**
- Version pinning must balance stability and new features
- Major FastAPI changes may require library updates

**Recommendation:** Support FastAPI 0.100.0+ to get modern features while avoiding ancient versions.

### 3.3 Dependency: SQLAlchemy (Optional)

**Current State:** SQLAlchemy is used for query filtering and database operations.

**Evaluation:**

| Aspect | Assessment |
|--------|------------|
| **Ubiquity** | Most popular Python ORM |
| **Version** | SQLAlchemy 2.0 has significant changes |
| **Async** | Full async support in 2.0 |
| **Necessity** | Only needed for query filters and some ownership checks |

**Decision: Make SQLAlchemy Optional**

**Rationale:**
1. **Not Always Needed:** Basic RBAC doesn't require database integration
2. **Alternative ORMs:** Users might use SQLModel, Tortoise, etc.
3. **Reduced Footprint:** Fewer required dependencies
4. **Clear Separation:** Database integration is a separate concern

**Implementation:**
- Core library works without SQLAlchemy
- Query filter utilities are in an optional submodule
- Import guards prevent errors when SQLAlchemy isn't installed

### 3.4 Recommendation: Type Checking with pyright/mypy

**Benefit:** Type hints are only useful if they're verified.

**Recommendation:**
- Include `py.typed` marker for PEP 561 compliance
- Run mypy in strict mode as part of CI
- Provide inline type hint examples in docs

**Rationale:**
1. **IDE Experience:** Users get better autocompletion
2. **Error Prevention:** Type mismatches caught before runtime
3. **Documentation:** Types serve as living documentation
4. **Trust:** Published types signal professional quality

---

## 4. Generalization Decisions

### 4.1 Generalizing the Role Enum

**Current State:**
```python
class Role(Enum):
    SUPERADMIN = "superadmin"
    SALESMAN = "salesman"
    DATA_ENTRY = "data_entry"
    PARTNER = "partner"
    CUSTOMER = "customer"
```

**Problem:** These are business-specific role names.

**Generalization Strategy:**

1. **Remove Hardcoded Roles:** The library should not define any default roles
2. **Role Factory:** Provide `create_roles(role_names: list[str]) -> Type[Enum]`
3. **Preserve Syntax:** The created enum works like the static one
4. **Document Examples:** Show common role patterns without prescribing

**User Experience After Generalization:**

Instead of importing hardcoded roles, users define their own:
```python
# User defines their roles
Role = create_roles(["admin", "moderator", "user", "guest"])

# Usage is identical to before
@require(Role.ADMIN)
async def admin_endpoint(user: User): ...
```

**Why Not Strings Only:**
String-based roles (`@require("admin")`) would work but lose:
- Type checking for typos
- IDE autocompletion
- Bitwise composition syntax
- Centralized role definition

### 4.2 Generalizing Resource Ownership

**Current State:**
```python
if resource_type == "configuration":
    from app.models.configuration import Configuration
    # Check ownership through customer relationship
```

**Problem:** Hardcoded resource types and business model imports.

**Generalization Strategy:**

1. **Define Provider Protocol:**
   ```python
   class OwnershipProvider(Protocol):
       async def check_ownership(
           self, user: UserProtocol, 
           resource_type: str, 
           resource_id: Any
       ) -> bool: ...
   ```

2. **Registry for Providers:**
   ```python
   rbac.register_ownership_provider("order", MyOrderOwnershipProvider())
   ```

3. **Default Behavior:**
   - Superadmin always has access (configurable)
   - Unknown resource types: configurable deny/allow

4. **Remove Model Imports:** The library never imports user's models

**User Experience After Generalization:**

Users implement their business logic:
```python
class OrderOwnershipProvider:
    def __init__(self, db: Session):
        self.db = db
    
    async def check_ownership(self, user, resource_type, resource_id) -> bool:
        order = await self.db.get(Order, resource_id)
        return order and order.user_id == user.id

# Register at startup
rbac.register_ownership_provider("order", OrderOwnershipProvider(db))
```

### 4.3 Generalizing Configuration Paths

**Current State:**
```python
self.enforcer = casbin.Enforcer("config/rbac_model.conf", "config/rbac_policy.csv")
```

**Problem:** Hardcoded file paths.

**Generalization Strategy:**

1. **Configuration Object:**
   ```python
   config = RBACConfig(
       model_path="path/to/model.conf",
       policy_path="path/to/policy.csv",
       # or
       policy_adapter=MyDatabaseAdapter()
   )
   ```

2. **Default Locations:**
   - Look for `rbac_model.conf` in common locations
   - Fall back to embedded default model

3. **In-Memory Option:**
   - Allow passing model text directly
   - Useful for testing and simple setups

**User Experience After Generalization:**

```python
# Option 1: Custom paths
config = RBACConfig(model_path="./my_model.conf", policy_path="./my_policy.csv")

# Option 2: Use adapter
config = RBACConfig(policy_adapter=CasbinSQLAlchemyAdapter(engine))

# Option 3: In-memory for testing
config = RBACConfig(model_text=DEFAULT_RBAC_MODEL, policy_text="p, admin, *, *, allow")
```

### 4.4 Generalizing the User Identifier

**Current State:**
```python
result = self.enforcer.enforce(user.email, resource, action)
```

**Problem:** Uses `user.email` as the Casbin subject unconditionally.

**Generalization Strategy:**

1. **Configurable Subject Field:**
   ```python
   config = RBACConfig(subject_field="email")  # or "id" or "username"
   ```

2. **Custom Subject Provider:**
   ```python
   class MySubjectProvider:
       def get_subject(self, user) -> str:
           return f"{user.tenant_id}:{user.id}"
   
   config = RBACConfig(subject_provider=MySubjectProvider())
   ```

3. **Default Behavior:** Use `user.email` if no configuration provided

**Rationale:**
- Some applications use user IDs as subjects
- Multi-tenant apps may need composite subjects
- UUID-based identifiers are increasingly common

---

## 5. Trade-offs & Constraints

### 5.1 Trade-off: Simplicity vs. Flexibility

**Tension:** Simple APIs are easier to use but may not cover all use cases. Flexible APIs can do anything but are harder to learn.

**Resolution:**
- **Surface Area:** Small public API with clear extension points
- **Layered Design:** Simple facade, complex internals for those who need them
- **Documentation:** Show simple usage first, advanced later

**Constraint:** Some advanced Casbin features may not be exposed through the simple API.

### 5.2 Trade-off: Type Safety vs. Dynamic Behavior

**Tension:** Strong typing requires knowing types at import time, but roles are dynamic.

**Resolution:**
- Role factory creates real enums with full type support
- Types are "narrowed" after initialization
- `Type[Enum]` is used for role type hints before creation

**Constraint:** IDE autocompletion for roles only works after roles are created.

### 5.3 Trade-off: Performance vs. Correctness

**Tension:** Caching improves performance but may serve stale authorization decisions.

**Resolution:**
- Caching is opt-in with configurable TTL
- Explicit cache invalidation API
- Clear documentation on caching behavior

**Constraint:** Real-time policy changes may not be immediately reflected.

### 5.4 Trade-off: Zero Dependencies vs. Features

**Tension:** Fewer dependencies mean lighter package but may limit features.

**Resolution:**
- Only `casbin` and `fastapi` are required
- SQLAlchemy, Redis, etc. are optional extras
- Features requiring optional deps are in separate submodules

**Constraint:** Users must install extras for advanced features.

### 5.5 Constraint: Python Version Support

**Decision:** Support Python 3.9+

**Rationale:**
- Python 3.8 reaches end of life in October 2024
- Protocol requires 3.8+ (3.9+ for better features)
- `|` union syntax requires 3.10+ (but can use `Union[]`)
- Most FastAPI users are on 3.9+

**Trade-off:** Some users on older Python versions cannot use the library.

### 5.6 Constraint: Async-First Design

**Decision:** All authorization methods are async.

**Rationale:**
- FastAPI is async-first
- Ownership checks may require database calls
- Policy adapters may be async

**Trade-off:** Sync applications need `asyncio.run()` or sync wrappers.

**Mitigation:** Provide sync wrapper utilities if needed.

---

## 6. High-Value Recommendations

### 6.1 Recommendation: Use Pydantic for Input Validation

**Benefit:** Pydantic is already in FastAPI's dependency tree.

**Application:**
- Configuration validation with Pydantic models
- Request/response models for admin endpoints
- Automatic documentation in OpenAPI

**Value:**
- No additional dependency (Pydantic is FastAPI's core)
- Validation errors are clear and standardized
- Schema export for documentation

### 6.2 Recommendation: Integrate with FastAPI Security

**Benefit:** FastAPI has built-in security utilities that can be leveraged.

**Application:**
- Integrate with `OAuth2PasswordBearer`, `HTTPBearer`
- Provide dependency that combines auth + authorization
- Support FastAPI's security documentation

**Value:**
- Users get auth and authz in one package
- OpenAPI docs show security requirements
- Consistent with FastAPI patterns

### 6.3 Recommendation: Implement Policy Reload Without Restart

**Benefit:** Production systems need to update policies without downtime.

**Application:**
- Watch policy files for changes
- Provide API endpoint to trigger reload
- Webhook support for CI/CD integration

**Value:**
- Zero-downtime policy updates
- CI/CD can deploy policy changes separately from code
- Emergency revocation is fast

### 6.4 Recommendation: Add Policy Visualization Tools

**Benefit:** Understanding policies is challenging for complex setups.

**Application:**
- CLI tool to show effective permissions for a user
- Export policies to GraphViz format
- Web UI for policy exploration (optional add-on)

**Value:**
- Debugging authorization issues is easier
- Security audits can visualize access patterns
- Onboarding new team members is faster

### 6.5 Recommendation: Structured Logging with OpenTelemetry Support

**Benefit:** Authorization logs are critical for security auditing.

**Application:**
- Use structured log format (JSON)
- Include trace context for distributed tracing
- Support OpenTelemetry spans for authorization checks

**Value:**
- Log aggregation systems can search/filter
- Correlation with request traces
- Security information and event management (SIEM) integration

### 6.6 Recommendation: Consider pycasbin-async-redis-watcher

**Benefit:** Distributed cache invalidation for multi-instance deployments.

**Application:**
- When policies change, all instances are notified
- Uses Redis pub/sub for coordination
- Automatic cache invalidation

**Value:**
- Consistent authorization across instances
- No cache drift issues
- Scalable to many instances

### 6.7 Recommendation: Policy Testing Framework

**Benefit:** Authorization policies should be tested like code.

**Application:**
- Provide test utilities for policy verification
- Support for "what-if" queries ("Would user X have access to Y?")
- Property-based testing for policy invariants

**Value:**
- Policy changes are validated before deployment
- Regression detection for access control
- Documentation of expected behavior

### 6.8 Recommendation: Consider Authzed SpiceDB for Complex Use Cases

**Context:** For very complex authorization models, Casbin may have limitations.

**When to Consider:**
- Millions of objects with complex relationships
- Real-time global consistency requirements
- Graph-based relationship modeling (like Google Zanzibar)

**Approach:**
- Design provider interface to allow SpiceDB integration
- Document as an advanced option for enterprise users
- Keep Casbin as the default for most users

**Value:**
- Scalable to massive authorization datasets
- Proven at Google-scale (Zanzibar paper)
- Not required for typical applications

---

## 7. Rejected Alternatives

### 7.1 Rejected: Multiple Inheritance for User Model

**Proposal:** Require users to inherit from `RBACUser` base class.

**Why Rejected:**
- Conflicts with existing User model hierarchies
- Diamond inheritance problems with SQLAlchemy models
- Less Pythonic than Protocol approach
- Forces code changes in user's codebase

### 7.2 Rejected: YAML-Only Configuration

**Proposal:** Use YAML for all configuration.

**Why Rejected:**
- Adds PyYAML dependency
- YAML has security concerns (arbitrary code execution)
- Python developers often prefer Pythonic configuration
- Less IDE support than dataclasses

**Compromise:** Support YAML as optional format, not the only one.

### 7.3 Rejected: Auto-Discovery of User Model

**Proposal:** Automatically find the User model by scanning the codebase.

**Why Rejected:**
- Magic behavior hard to debug
- Multiple User models in same app cause ambiguity
- Startup time impact from reflection
- Explicit is better than implicit

### 7.4 Rejected: GraphQL-Style Authorization Directives

**Proposal:** Use custom syntax like `@authorize(role="admin")`.

**Why Rejected:**
- Invents new DSL that users must learn
- Python decorators already serve this purpose
- GraphQL-specific syntax alienates REST users
- Type checking is harder for custom syntax

### 7.5 Rejected: Removing Casbin for Custom Engine

**Proposal:** Replace Casbin with a custom authorization engine.

**Why Rejected:**
- Casbin is battle-tested and maintained
- Custom engine is significant development effort
- Casbin's ecosystem of adapters is valuable
- "Not invented here" is rarely the right choice

### 7.6 Rejected: Removing Template Helpers

**Proposal:** Focus only on API authorization, not templates.

**Why Rejected:**
- Template helpers already exist and work well
- SSR applications need client-side permission checks
- Removing features violates "preserve functionality" goal
- Minimal maintenance burden

---

## 8. Risk Analysis

### 8.1 Risk: Breaking Existing Users

**Description:** Current users rely on specific import paths and behavior.

**Likelihood:** Medium  
**Impact:** High

**Mitigation:**
1. Provide migration guide with specific instructions
2. Consider compatibility shim for transitional period
3. Version 1.0 maintains backward compatibility
4. Breaking changes only in major versions

### 8.2 Risk: Casbin Compatibility Issues

**Description:** Casbin updates may break the library.

**Likelihood:** Low  
**Impact:** Medium

**Mitigation:**
1. Pin Casbin to known-working version range
2. Monitor Casbin releases for changes
3. Test against multiple Casbin versions in CI
4. Contribute to Casbin project for critical fixes

### 8.3 Risk: Performance Regression

**Description:** Generalization may introduce performance overhead.

**Likelihood:** Medium  
**Impact:** Medium

**Mitigation:**
1. Performance tests in CI with regression thresholds
2. Benchmark against current implementation
3. Profile hot paths and optimize
4. Document performance characteristics

### 8.4 Risk: Complexity Overwhelming Users

**Description:** The generalized library may be harder to use than the original.

**Likelihood:** Medium  
**Impact:** High

**Mitigation:**
1. Progressive disclosure - simple defaults
2. Comprehensive "Getting Started" guide
3. Copy-pasteable examples for common patterns
4. Interactive playground or REPL examples

### 8.5 Risk: Inadequate Testing After Refactor

**Description:** Generalization may introduce bugs not caught by tests.

**Likelihood:** Medium  
**Impact:** High

**Mitigation:**
1. Transform existing tests to work with generalized code
2. Add property-based tests for invariants
3. Integration tests with real FastAPI apps
4. Beta testing period before 1.0 release

### 8.6 Risk: Dependency Conflicts

**Description:** Users may have conflicting versions of shared dependencies.

**Likelihood:** Low  
**Impact:** Medium

**Mitigation:**
1. Use wide version ranges where possible
2. Minimal dependency footprint
3. Optional extras for additional features
4. Document known conflicts and resolutions

---

## Summary

This document captures the reasoning behind every significant decision in transforming the `fastapi-role` library into a general-purpose PyPI package. The guiding philosophy is:

1. **Preserve all existing functionality** while removing business coupling
2. **Follow Python and FastAPI conventions** for a familiar developer experience
3. **Provide sensible defaults** with full customization capability
4. **Maintain high performance** through caching and optimization
5. **Enable extensibility** through well-defined provider interfaces

The recommendations provide pathways to additional value, and the rejected alternatives document why simpler or more complex approaches were not chosen. The risk analysis ensures the team is prepared for potential challenges during implementation.
