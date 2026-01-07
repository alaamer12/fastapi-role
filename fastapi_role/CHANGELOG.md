# Changelog

All notable changes to fastapi-role will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-07

### Added - Pure General RBAC Engine
- **🎯 Pure General RBAC**: Complete transformation to business-agnostic RBAC engine
- **🔧 Dynamic Role System**: Runtime role creation with `create_roles(names, superadmin)`
- **🌐 Framework Agnostic**: Works with FastAPI, Flask, Django, CLI apps, background jobs
- **📦 Resource Agnostic**: Generic `(type, id)` resource handling for any domain
- **🔌 Provider Architecture**: Complete pluggable system for all business logic
- **⚙️ Configuration-Driven**: All behavior defined by data, not code
- **🚀 Zero Business Assumptions**: No hardcoded roles, resources, or domain concepts

### Core Features
- `RBACService`: Pure general RBAC service with no business dependencies
- `create_roles()`: Dynamic role enum generation at runtime
- `@require`: Framework-agnostic decorator protecting business functions
- `ResourceRef`: Generic resource reference system `(type, id)`
- `Permission`: Generic permission model for any resource type
- `Privilege`: Configurable privilege bundles with data-driven evaluation

### Provider System
- `SubjectProvider`: Customizable user identifier extraction
- `RoleProvider`: Pluggable role resolution and validation
- `OwnershipProvider`: Generic resource ownership validation
- `PolicyProvider`: Configurable policy storage backends
- `CacheProvider`: Pluggable caching implementations

### Framework Support
- **FastAPI**: Native integration with dependency injection
- **Flask**: Full compatibility with Flask applications
- **Django**: Works with Django views and middleware
- **CLI**: Protect command-line functions and scripts
- **Background Jobs**: Secure async tasks and workers
- **Testing**: Easy unit and integration testing

### Configuration System
- File-based configuration (YAML, JSON, CSV)
- Environment variable configuration
- Programmatic configuration
- Hierarchical configuration loading
- Runtime configuration updates

### Removed - Business Coupling Elimination
- ❌ Removed `BaseService` dependency (was business-specific)
- ❌ Removed `get_accessible_customers()` (business-specific method)
- ❌ Removed hardcoded "superadmin" strings
- ❌ Removed customer-specific caching logic
- ❌ Removed business model imports and dependencies
- ❌ Removed hardcoded role enums
- ❌ Removed entity-specific database queries

### Changed - Pure General RBAC
- 🔄 `RBACService` now database-agnostic (no direct DB dependencies)
- 🔄 Decorators use dependency injection instead of global service
- 🔄 All resource access through generic `can_access(user, resource, action)`
- 🔄 Privilege evaluation through configurable `evaluate(user, privilege)`
- 🔄 Ownership checking through pluggable providers
- 🔄 Role system completely dynamic and configurable

### Migration Guide
```python
# Before (Business-Coupled)
from fastapi_role import Role, RBACService
rbac = RBACService()
@require(Role.ADMIN)
def admin_function(): pass

# After (Pure General RBAC)
from fastapi_role import create_roles, RBACService, require
Role = create_roles(["admin", "user"], superadmin="admin")
rbac = RBACService()
@require(Role.ADMIN)
async def admin_function(current_user: User, rbac: RBACService): pass
```

### Performance
- Optimized policy evaluation with caching
- Reduced memory footprint through provider architecture
- Improved startup time with lazy loading
- Better concurrent access handling

### Security
- Eliminated privilege escalation through hardcoded bypasses
- Comprehensive audit logging
- Thread-safe operations
- Input validation and sanitization

### Testing
- Property-based testing for universal correctness
- 200+ comprehensive test cases
- Framework compatibility testing
- Performance benchmarking
- Security vulnerability testing

## [0.1.0] - 2026-01-03

### Added
- Initial release of `fastapi-role` (formerly internal `fastapi-role`).
- Core `RBACService` for Casbin policy enforcement.
- `@require` decorator for declarative endpoint protection.
- Support for both synchronous and asynchronous SQLAlchemy sessions.
- `UserProtocol` for loose coupling with user models.
- Pluggable `Provider` architecture:
    - `SubjectProvider` (customizable user ID extraction).
    - `RoleProvider` (customizable role fetching).
    - `CacheProvider` (customizable permission caching).
    - `OwnershipProvider` (extensible resource ownership logic).
- Zero-config default setup with `platformdirs`.
- Helper utilities for query filtering.

### Changed
- Refactored internal `fastapi-role` code to be generic and reusable.
- Moved from hardcoded Roles enum to dynamic/configurable roles.
- Decoupled from specific business models (User, Customer, etc.).