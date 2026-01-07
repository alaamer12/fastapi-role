# Implementation Plan: Pure General RBAC System Completion

## Overview

NO FALLBACK FOR BACKWARD COMPATABILITIES, THIS IS ENFORCED, DO NOT WRITE ANY FALLBACK COMPATBILITY CODE

This implementation plan completes the transformation of fastapi-role into a pure general RBAC engine. **IMPLEMENTATION COMES FIRST** - we focus on eliminating all business coupling through actual code changes, then validate with tests. The goal is to create a truly business-agnostic RBAC core that works with any domain.

## Critical Business Coupling Issues Found

From comprehensive source code analysis, these **MUST BE FIXED IMMEDIATELY**:

**In `rbac_service.py` (Lines 37, 160-202, 68):**
- ❌ Inherits from `BaseService` (business database layer coupling)
- ❌ Has `get_accessible_customers()` method (business-specific customer concept)
- ❌ Uses hardcoded "superadmin" strings in ownership provider setup
- ❌ Assumes database session management through business layer

**In `rbac.py` (Lines 200-250):**
- ❌ Decorator assumes global `rbac_service` import from business layer
- ❌ Uses hardcoded business logic patterns in `_evaluate_requirement_group()`

**In `base.py` (Entire file):**
- ❌ **Entire file is business-specific** - provides database session management
- ❌ Creates business dependency that RBAC core should not have

**Current Status**: 202/202 tests passing, but system still has business coupling

## Implementation Tasks (Code First, Tests Second)

- [-] 1. IMMEDIATE: Remove All Business Coupling

- [x] 1.1 **Remove BaseService dependency from RBACService**
  - Remove `BaseService` import and inheritance from `rbac_service.py`
  - Remove database session management from RBAC core
  - Make RBACService database-agnostic (no direct DB dependencies)
  - Replace session management with optional provider pattern

- [x] 1.2 **Remove business-specific customer methods**
  - Remove `get_accessible_customers()` method completely from `rbac_service.py`
  - Remove `_customer_cache` and customer-related caching logic
  - Replace with generic `get_accessible_resources(user, resource_type)` method
  - Ensure no customer-specific concepts remain in core RBAC

- [x] 1.3 **Fix decorator service injection coupling**
  - Remove global `rbac_service` import assumption in `rbac.py`
  - Implement dependency injection pattern for RBAC service in decorators
  - Create service registry or context-based service resolution
  - Ensure decorators work with multiple service instances
  - Support both explicit service passing and dependency injection
  - Maintain backward compatibility where possible

- [x] 1.4 **Remove hardcoded superadmin strings**
  - Remove hardcoded "superadmin" string from ownership provider setup
  - Make superadmin role configurable through providers
  - Ensure all role names are data-driven, not hardcoded
  - Update all provider default configurations

- [ ] 1.5 **Document and validate decorator architecture decision**
  - Document framework-agnostic decorator approach (protects business functions)
  - Ensure decorators work with FastAPI, Flask, Django, CLI, background jobs, tests
  - Validate OR logic between multiple @require decorators
  - Validate AND logic within single @require decorator
  - Test decorator behavior with various service injection patterns

- [ ] 1.5 **Remove hardcoded superadmin strings**
  - Remove hardcoded "superadmin" string from ownership provider setup
  - Make superadmin role configurable through providers
  - Ensure all role names are data-driven, not hardcoded
  - Update all provider default configurations1.4 **Remove hardcoded superadmin strings**
  - Remove hardcoded "superadmin" string from ownership provider setup
  - Make superadmin role configurable through providers
  - Ensure all role names are data-driven, not hardcoded
  - Update all provider default configurations

- [x] 2. Implement Pure General RBAC Core

- [x] 2.1 **Create database-agnostic RBAC service**
  - Remove all database session dependencies from RBACService
  - Create optional database provider pattern for persistence needs
  - Implement pure in-memory RBAC service that works without databases
  - Ensure core RBAC logic is completely database-independent

- [x] 2.2 **Implement generic resource access methods**
  - Replace `get_accessible_customers()` with `get_accessible_resources(user, resource_type)`
  - Create `can_access(user, resource, action)` method for generic access control
  - Implement `evaluate(user, privilege)` for generic privilege evaluation
  - Ensure all methods work with arbitrary resource types

- [x] 2.3 **Complete service injection for decorators**
  - Implement dependency injection pattern for RBAC service in decorators
  - Create service registry or context-based service resolution
  - Remove global service assumptions from decorator implementation
  - Ensure decorators can work with multiple service instances

- [x] 3. Remove Database Dependencies and Business Layer Coupling

- [x] 3.1 **Remove base.py business layer dependency**
  - Delete or move `base.py` out of core RBAC package (it's business-specific)
  - Remove all imports of `BaseService` from RBAC components
  - Create optional database provider pattern if persistence is needed
  - Ensure core RBAC works without any database dependencies

- [x] 3.2 **Implement optional database provider pattern**
  - Create `DatabaseProvider` protocol for optional database operations
  - Implement `InMemoryDatabaseProvider` for database-free operation
  - Create `SQLAlchemyDatabaseProvider` for users who need database integration
  - Make database operations completely optional and pluggable

- [x] 3.3 **Remove hardcoded configuration assumptions**
  - Ensure all configuration is data-driven through `CasbinConfig`
  - Remove any remaining hardcoded paths or business assumptions
  - Validate that system works with arbitrary configuration
  - Test with multiple different configuration scenarios

- [x] 4. Enhance and Validate Current Implementation

- [x] 4.1 **Validate dynamic role system works correctly**
  - Test `create_roles()` factory with various role configurations
  - Verify `RoleRegistry` handles role validation properly
  - Ensure role composition with bitwise operations works
  - Test role system with different application scenarios

- [x] 4.2 **Validate provider architecture completeness**
  - Test all provider protocols work with custom implementations
  - Verify default providers handle edge cases correctly
  - Ensure provider registration and validation works
  - Test provider system with mock implementations

- [x] 4.3 **Validate configuration system robustness**
  - Test `CasbinConfig` with various configuration scenarios
  - Verify platformdirs integration works correctly
  - Ensure configuration validation catches errors
  - Test hierarchical configuration loading

- [x] 5. Validate and Enhance Ownership System

- [x] 5.1 **Validate ownership provider system works correctly**
  - Test `OwnershipRegistry` with various provider configurations
  - Verify wildcard provider fallback works correctly
  - Ensure ownership providers handle async operations properly
  - Test ownership system with different resource types

- [x] 5.2 **Remove any remaining hardcoded ownership logic**
  - Verify no hardcoded resource types remain in ownership checks
  - Ensure ownership system works with arbitrary resource types
  - Test ownership providers with mock implementations
  - Validate ownership system is truly generic

- [x] 6. Create Test FastAPI Application

- [x] 6.1 **Set up monorepo workspace structure**
  - Configure workspace with fastapi_role core package and test_fastapi application
  - Set up proper package dependencies and build configuration

- [x] 6.2 **Implement generic test application**
  - Create User model implementing UserProtocol (no business assumptions)
  - Create generic resource models (Document, Project, Task) for testing
  - Implement database setup with SQLite
  - Create schemas and API structure

- [x] 6.3 **Apply pure general RBAC to all endpoints**
  - Create 5+ API endpoints with different authorization patterns
  - Use dynamic roles (no hardcoded business roles)
  - Implement custom ownership providers for test resources
  - Apply @require decorators with generic resource types

- [x] 6.4 **Implement custom providers for test application**
  - Create DocumentOwnershipProvider, ProjectOwnershipProvider, TaskOwnershipProvider
  - Register providers with RBAC service
  - Test provider system with real application scenarios

- [-] 7. Create Example Applications

- [x] 7.1 **Create minimal pure RBAC example**
  - Single-file FastAPI app with no business assumptions
  - Generic resource types and dynamic roles
  - In-memory configuration
  - Basic protected endpoints

- [x] 7.2 **Create file-based configuration example**
  - Configuration-driven role and policy definition
  - Multiple generic resource types
  - Custom ownership providers
  - File-based policy storage

- [ ] 7.3 **Create database integration example**
  - Database-backed policies and roles
  - Custom providers for database integration
  - Generic resource ownership patterns

- [x] 18. Finalize Production-Ready Package

- [x] 8.1 **Complete package metadata and structure**
  - Update pyproject.toml with correct dependencies and metadata
  - Create comprehensive README with pure RBAC examples
  - Add LICENSE, CHANGELOG, CONTRIBUTING files
  - Include py.typed marker for type checking

- [x] 8.2 **Create comprehensive documentation**
  - Document all public APIs with examples
  - Create getting started guide for pure general RBAC
  - Document provider architecture and customization
  - Create migration guide from business-coupled version

- [x] 8.3 **Implement CI/CD pipeline**
  - Set up GitHub Actions for testing across Python versions
  - Add code quality checks (linting, formatting, type checking)
  - Implement automated PyPI publishing
  - Add security scanning and dependency checks

- [-] 20. COMPREHENSIVE TESTING: Ensure Robustness and Edge Cases

- [ ] 9.1 **Test decorator architecture thoroughly**
  - Test @require decorator with all supported frameworks (FastAPI, Flask, Django)
  - Test decorator with CLI functions, background jobs, and direct function calls
  - Test multiple @require decorators with complex OR logic scenarios
  - Test mixed requirements within single @require decorator (AND logic)
  - Test decorator behavior with missing users, invalid users, and edge cases
  - Test service injection patterns: explicit passing, dependency injection, context resolution
  - Test decorator error handling and error message clarity

- [ ] 9.2 **Test service injection edge cases**
  - Test decorator behavior when no service is available
  - Test decorator with multiple service instances
  - Test service injection with async and sync functions
  - Test service injection with various parameter patterns
  - Test backward compatibility with existing global service patterns
  - Test service injection error messages and debugging information

- [ ] 9.3 **Test business coupling removal thoroughly**
  - Test system works without any database dependencies
  - Test system works with arbitrary resource types (not just customer/order/quote)
  - Test system works with different user models and protocols
  - Test system works with various role configurations
  - Test system works across different business domains (CRM, e-commerce, SaaS, etc.)
  - Test no hardcoded business concepts remain in any code path

- [ ] 9.4 **Test provider system edge cases**
  - Test provider registration with invalid implementations
  - Test provider error handling and fallback behavior
  - Test provider thread safety and concurrent access
  - Test provider lifecycle management and cleanup
  - Test provider configuration validation and error reporting
  - Test provider system with mock implementations and edge cases

- [ ] 10. VALIDATION: Test Implementation (After Code is Complete)

- [ ] 10.1 **Create comprehensive business-agnostic tests**
  - Test system works with arbitrary resource types
  - Test dynamic role creation with various configurations
  - Test provider system with mock implementations
  - Verify no business-specific assumptions in any code path

- [ ] 10.2 **Create security and performance tests**
  - Test authorization bypass prevention
  - Test privilege escalation prevention
  - Benchmark permission check performance
  - Test concurrent access and thread safety

- [ ] 10.3 **Integration tests for test application**
  - Test all endpoints with various user roles and permissions
  - Verify ownership validation works correctly
  - Test error handling and response formatting

- [ ] 10.4 **Test all example applications**
  - Verify all examples work correctly
  - Test setup time meets requirements (<15 minutes)
  - Validate examples demonstrate pure general RBAC principles

- [ ] 11. Final Validation and Release

- [ ] 11.1 **Perform final validation**
  - Run comprehensive test suite (ensure 202+ tests still pass)
  - Verify package installation and distribution
  - Test all examples and documentation
  - Perform security audit

- [ ] 11.2 **Ensure pure general RBAC system is complete**
  - Verify all business coupling is removed
  - Confirm system works with arbitrary domains
  - Validate all tests pass
  - Ensure package is production-ready

## Key Principles

1. **Implementation First**: Write the code changes before writing tests
2. **No Business Assumptions**: System must work with any domain (CRM, e-commerce, SaaS, etc.)
3. **Resource Agnostic**: Use (type, id) patterns, never hardcode resource types
4. **Provider-Based**: All business-specific behavior through pluggable providers
5. **Configuration-Driven**: No hardcoded roles, paths, or business logic
6. **Pure General RBAC**: Core engine never imports or references user's business models
7. **Framework-Agnostic Decorators**: Protect business functions, not just HTTP endpoints

## Decorator Architecture Decision

**DECISION**: Keep framework-agnostic `@require` decorators that protect business functions directly.

**RATIONALE**:
- ✅ **Framework Independence**: Works with FastAPI, Flask, Django, CLI, background jobs, tests
- ✅ **Business Logic Protection**: Protects actual business functions, not just HTTP endpoints  
- ✅ **Reusability**: Same protected function callable from multiple contexts
- ✅ **Separation of Concerns**: RBAC logic stays with business logic, not transport layer
- ✅ **Testing**: Easier to test business logic with RBAC without HTTP overhead

**USAGE PATTERNS**:
```python
# Pattern 1: Direct business function protection (PREFERRED)
@require(Role.ADMIN, Permission("users", "delete"))
async def delete_user(user_id: int, current_user: User, rbac: RBACService):
    # Business logic here
    pass

# Pattern 2: FastAPI route calls protected business function
@app.delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    rbac: RBACService = Depends(get_rbac_service)
):
    return await delete_user(user_id, current_user, rbac)
```

**SERVICE INJECTION**: Support both explicit service passing and dependency injection patterns.

## Success Criteria

- [ ] No business layer dependencies remain (remove BaseService coupling)
- [ ] No customer-specific methods or concepts remain in core RBAC
- [ ] System works without any database dependencies (pure in-memory operation)
- [ ] All hardcoded role names and business concepts removed
- [ ] Decorator service injection works without global assumptions
- [ ] System works equally well for any application domain
- [ ] All business-specific behavior implemented through providers
- [ ] Core RBAC engine has zero business dependencies
- [ ] Test application demonstrates pure general RBAC principles
- [ ] Package is production-ready and publishable to PyPI
- [ ] All 202+ tests continue to pass after changes