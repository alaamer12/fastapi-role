# fastapi-role: System Design Document

**Document Version:** 1.0  
**Created:** 2026-01-01  
**Purpose:** Comprehensive design documentation of the current and target system architectures

---

## Table of Contents

1. [Current System Design](#1-current-system-design)
2. [Target System Design](#2-target-system-design)
3. [Component Designs](#3-component-designs)
4. [Data Flow Diagrams](#4-data-flow-diagrams)
5. [API Design](#5-api-design)
6. [Extension Architecture](#6-extension-architecture)
7. [Configuration Design](#7-configuration-design)
8. [Migration Architecture](#8-migration-architecture)

---

## 1. Current System Design

### 1.1 System Overview

The current `fastapi-role` implementation provides a Casbin-based RBAC system tightly integrated with a specific FastAPI application.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      fastapi_role/                           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │   rbac.py   │  │rbac_service │  │  rbac_actions.py    │  │   │
│  │  │             │  │    .py      │  │                     │  │   │
│  │  │ - Role      │  │             │  │ - PageAction        │  │   │
│  │  │ - Permission│  │ - RBACService│ │ - TableAction       │  │   │
│  │  │ - Privilege │  │ - Caching   │  │                     │  │   │
│  │  │ - @require  │  │ - Ownership │  │                     │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │   │
│  │         │                │                                    │   │
│  │         │                │                                    │   │
│  │         ▼                ▼                                    │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │                 app/ (Business Layer)                    │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │   │
│  │  │  │ models/user  │  │models/customer│ │models/config │   │  │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │   │
│  │  │  │services/base │  │core/exceptions│ │database/conn │   │  │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                       config/                                │   │
│  │   rbac_model.conf              rbac_policy.csv              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Current Component Dependencies

```
rbac.py
├── Standard Library
│   ├── logging
│   ├── collections.abc.Callable
│   ├── enum.Enum
│   ├── functools.wraps
│   └── typing (Any, Optional)
├── Third-Party
│   ├── casbin
│   ├── fastapi.HTTPException
│   └── sqlalchemy.select
└── Business-Specific (COUPLING POINTS)
    └── app.models.user.User ❌

rbac_service.py
├── Standard Library
│   ├── logging
│   ├── datetime
│   └── typing
├── Third-Party
│   ├── casbin
│   ├── sqlalchemy (select, IntegrityError, AsyncSession)
└── Business-Specific (COUPLING POINTS)
    ├── app.core.exceptions.* ❌
    ├── app.core.rbac (Privilege, Role) ❌
    ├── app.models.customer.Customer ❌
    ├── app.models.user.User ❌
    └── app.services.base.BaseService ❌
```

### 1.3 Current Class Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              CORE CLASSES                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐       ┌──────────────────────┐                       │
│  │      Role        │       │   RoleComposition    │                       │
│  │    <<enum>>      │       │                      │                       │
│  ├──────────────────┤       ├──────────────────────┤                       │
│  │ SUPERADMIN       │ ──or──│ roles: list[Role]    │                       │
│  │ SALESMAN         │       ├──────────────────────┤                       │
│  │ DATA_ENTRY       │       │ __or__()             │                       │
│  │ PARTNER          │       │ __contains__()       │                       │
│  │ CUSTOMER         │       └──────────────────────┘                       │
│  ├──────────────────┤                                                       │
│  │ __or__()         │                                                       │
│  │ __ror__()        │                                                       │
│  └──────────────────┘                                                       │
│                                                                             │
│  ┌──────────────────┐       ┌──────────────────────┐                       │
│  │   Permission     │       │  ResourceOwnership   │                       │
│  ├──────────────────┤       ├──────────────────────┤                       │
│  │ resource: str    │       │ resource_type: str   │                       │
│  │ action: str      │       │ id_param: str        │                       │
│  │ context: dict    │       ├──────────────────────┤                       │
│  ├──────────────────┤       │ __str__()            │                       │
│  │ __str__()        │       └──────────────────────┘                       │
│  │ __repr__()       │                                                       │
│  └──────────────────┘                                                       │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                          Privilege                                  │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │ roles: list[Role]                                                   │    │
│  │ permission: Permission                                              │    │
│  │ resource: Optional[ResourceOwnership]                               │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │ __str__(), __repr__()                                               │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE LAYER                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                          RBACService                                │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │ enforcer: casbin.Enforcer                                           │    │
│  │ _permission_cache: dict[str, bool]                                  │    │
│  │ _customer_cache: dict[int, list[int]]                               │    │
│  │ _privilege_cache: dict[str, bool]                                   │    │
│  │ _cache_timestamp: datetime                                          │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │ + check_permission(user, resource, action, context) → bool          │    │
│  │ + check_resource_ownership(user, resource_type, resource_id) → bool │    │
│  │ + get_accessible_customers(user) → list[int]                        │    │
│  │ + get_or_create_customer_for_user(user) → Customer                  │    │
│  │ + assign_role_to_user(user, role) → None                            │    │
│  │ + assign_customer_to_user(user, customer_id) → None                 │    │
│  │ + check_privilege(user, privilege) → bool                           │    │
│  │ + clear_cache() → None                                              │    │
│  │ + is_cache_expired(max_age_minutes) → bool                          │    │
│  │ + get_cache_stats() → dict                                          │    │
│  │ + initialize_user_policies(user) → None                             │    │
│  │ - _find_customer_by_email(email) → Optional[Customer]               │    │
│  │ - _create_customer_from_user(user) → Customer                       │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        RBACQueryFilter                              │    │
│  ├────────────────────────────────────────────────────────────────────┤    │
│  │ + filter_configurations(query, user) → query  [static]              │    │
│  │ + filter_quotes(query, user) → query  [static]                      │    │
│  │ + filter_orders(query, user) → query  [static]                      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                              UI ACTIONS                                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────┐       ┌─────────────────────────┐             │
│  │      PageAction         │       │      TableAction        │             │
│  │      <<dataclass>>      │       │      <<dataclass>>      │             │
│  ├─────────────────────────┤       ├─────────────────────────┤             │
│  │ text: str               │       │ title: str              │             │
│  │ href: str               │       │ icon: str               │             │
│  │ permission: str | None  │       │ url: str | Callable     │             │
│  │ role: str | None        │       │ permission: str | None  │             │
│  │ class_: str             │       │ role: str | None        │             │
│  │ icon: str | None        │       ├─────────────────────────┤             │
│  ├─────────────────────────┤       │ + get_url(item) → str   │             │
│  │ + to_dict() → dict      │       │ + to_dict() → dict      │             │
│  └─────────────────────────┘       └─────────────────────────┘             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Current Decorator Flow

```
                                    @require(Role.ADMIN)
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │   decorator factory   │
                               │   require(*reqs)      │
                               └───────────┬───────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │   wrapper function    │
                               │                       │
                               │ 1. Extract user       │
                               │ 2. Evaluate groups    │
                               │ 3. Allow or deny      │
                               └───────────┬───────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
         ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
         │ Role Check      │    │ Permission Check│    │ Ownership Check │
         │                 │    │                 │    │                 │
         │ Compare user.   │    │ Call Casbin     │    │ Extract ID,     │
         │ role to required│    │ enforcer        │    │ check ownership │
         └─────────────────┘    └─────────────────┘    └─────────────────┘
                    │                      │                      │
                    └──────────────────────┼──────────────────────┘
                                           │
                                           ▼
                               ┌───────────────────────┐
                               │   Result: Allow/Deny  │
                               │                       │
                               │ Allow → Execute func  │
                               │ Deny → HTTPException  │
                               └───────────────────────┘
```

---

## 2. Target System Design

### 2.1 Target System Overview

The target design removes all business coupling while preserving functionality.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PyPI Package: fastapi-role                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                        │  │
│  │  ┌───────────────────────────────────────────────────────────────┐    │  │
│  │  │                        Core Module                             │    │  │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │    │  │
│  │  │  │Role Factory │ │ Permission  │ │ Ownership   │ │Privilege │ │    │  │
│  │  │  │(Dynamic)    │ │             │ │             │ │          │ │    │  │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │    │  │
│  │  └───────────────────────────────────────────────────────────────┘    │  │
│  │                                │                                       │  │
│  │  ┌─────────────────────────────┴─────────────────────────────────┐    │  │
│  │  │                       Protocols Module                         │    │  │
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │    │  │
│  │  │  │UserProtocol │ │RoleProvider │ │Ownership    │ │Subject   │ │    │  │
│  │  │  │             │ │Protocol     │ │Provider     │ │Provider  │ │    │  │
│  │  │  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │    │  │
│  │  └───────────────────────────────────────────────────────────────┘    │  │
│  │                                │                                       │  │
│  │  ┌─────────────────────────────┴─────────────────────────────────┐    │  │
│  │  │                       Service Module                           │    │  │
│  │  │  ┌─────────────────────────────────────────────────────────┐  │    │  │
│  │  │  │                    RBACService                           │  │    │  │
│  │  │  │  - Uses configured providers                             │  │    │  │
│  │  │  │  - No business model imports                             │  │    │  │
│  │  │  │  - Configurable caching                                  │  │    │  │
│  │  │  └─────────────────────────────────────────────────────────┘  │    │  │
│  │  └───────────────────────────────────────────────────────────────┘    │  │
│  │                                │                                       │  │
│  │  ┌─────────────────────────────┴─────────────────────────────────┐    │  │
│  │  │                     Decorators Module                          │    │  │
│  │  │  ┌──────────────────────────────────────────────────────────┐ │    │  │
│  │  │  │            @require() decorator                           │ │    │  │
│  │  │  └──────────────────────────────────────────────────────────┘ │    │  │
│  │  └───────────────────────────────────────────────────────────────┘    │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        Configuration Module                           │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐  │   │
│  │  │  RBACConfig    │  │ Default Model  │  │ Environment Loader     │  │   │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ User implements
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           User's FastAPI Application                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      User-Provided Implementations                     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │  │
│  │  │  User Model     │  │ Custom Providers │  │ Policy Files        │   │  │
│  │  │ (UserProtocol)  │  │ (Optional)       │  │ (rbac_policy.csv)   │   │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Target Package Structure

```
fastapi_rbac/
├── __init__.py                 # Public API exports
│   └── exports: create_roles, require, Permission, Privilege,
│       ResourceOwnership, RBACConfig, RBACService, UserProtocol
│
├── core/
│   ├── __init__.py
│   ├── roles.py                # Role factory and RoleComposition
│   │   └── create_roles(names: list[str]) → Type[Enum]
│   ├── permissions.py          # Permission class
│   ├── ownership.py            # ResourceOwnership class
│   ├── privilege.py            # Privilege class
│   └── composition.py          # RoleComposition class
│
├── protocols/
│   ├── __init__.py
│   ├── user.py                 # UserProtocol
│   │   └── @runtime_checkable Protocol with id, email, role
│   ├── providers.py            # Provider protocols
│   │   ├── SubjectProvider
│   │   ├── RoleProvider
│   │   └── OwnershipProvider
│   └── adapters.py             # Adapter protocols for Casbin
│
├── service/
│   ├── __init__.py
│   ├── rbac_service.py         # Core service (generalized)
│   │   └── RBACService using providers
│   └── cache.py                # Cache implementations
│       ├── MemoryCache
│       └── CacheProtocol
│
├── providers/
│   ├── __init__.py
│   ├── default_subject.py      # Default: use user.email
│   ├── default_role.py         # Default: use user.role
│   └── default_ownership.py    # Default: superadmin bypass
│
├── decorators/
│   ├── __init__.py
│   └── require.py              # The @require decorator
│
├── config/
│   ├── __init__.py
│   ├── settings.py             # RBACConfig dataclass
│   ├── defaults.py             # Default values and model
│   └── loaders.py              # Environment and file loaders
│
├── templates/                  # Optional template helpers
│   ├── __init__.py
│   └── helpers.py              # Can, Has, RBACHelper
│
├── actions/                    # UI action configurations
│   ├── __init__.py
│   └── ui_actions.py           # PageAction, TableAction
│
├── exceptions.py               # Package exceptions
│   └── AuthorizationError, ConfigurationError, etc.
│
└── py.typed                    # PEP 561 marker
```

### 2.3 Target Class Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              PROTOCOLS                                          │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌────────────────────────┐      ┌────────────────────────────────────────┐    │
│  │     UserProtocol       │      │         SubjectProvider                │    │
│  │   <<protocol>>         │      │            <<protocol>>                │    │
│  ├────────────────────────┤      ├────────────────────────────────────────┤    │
│  │ id: Any                │      │ + get_subject(user: UserProtocol) → str│    │
│  │ email: str             │      └────────────────────────────────────────┘    │
│  │ role: str              │                                                     │
│  ├────────────────────────┤      ┌────────────────────────────────────────┐    │
│  │ has_role(name) → bool  │      │         RoleProvider                   │    │
│  │        [optional]      │      │         <<protocol>>                   │    │
│  └────────────────────────┘      ├────────────────────────────────────────┤    │
│                                  │ + get_roles(user: UserProtocol)        │    │
│                                  │   → list[str]                          │    │
│                                  │ + has_role(user, role_name) → bool     │    │
│                                  └────────────────────────────────────────┘    │
│                                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                         OwnershipProvider                               │    │
│  │                            <<protocol>>                                 │    │
│  ├────────────────────────────────────────────────────────────────────────┤    │
│  │ + check_ownership(user: UserProtocol, resource_type: str,              │    │
│  │                   resource_id: Any) → Awaitable[bool]                  │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                              CORE CLASSES (Generalized)                         │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                          create_roles()                               │      │
│  ├──────────────────────────────────────────────────────────────────────┤      │
│  │ + create_roles(names: list[str],                                      │      │
│  │                superadmin_name: str = None) → Type[RoleEnum]          │      │
│  │                                                                       │      │
│  │ Returns dynamically generated Enum with:                              │      │
│  │   - __or__() for composition                                          │      │
│  │   - __ror__() for reverse composition                                 │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                          RoleRegistry                                 │      │
│  ├──────────────────────────────────────────────────────────────────────┤      │
│  │ _roles: Type[Enum] | None                                             │      │
│  │ _superadmin_role: str | None                                          │      │
│  ├──────────────────────────────────────────────────────────────────────┤      │
│  │ + register(role_type: Type[Enum], superadmin: str = None)             │      │
│  │ + get_roles() → Type[Enum]                                            │      │
│  │ + is_superadmin(role_value: str) → bool                               │      │
│  │ + validate(role_value: str) → bool                                    │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
│  (Permission, ResourceOwnership, Privilege classes remain similar              │
│   but with generalized type hints)                                             │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE (Generalized)                              │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                          RBACService                                  │      │
│  ├──────────────────────────────────────────────────────────────────────┤      │
│  │ config: RBACConfig                                                    │      │
│  │ enforcer: casbin.Enforcer                                             │      │
│  │ subject_provider: SubjectProvider                                     │      │
│  │ role_provider: RoleProvider                                           │      │
│  │ ownership_providers: dict[str, OwnershipProvider]                     │      │
│  │ cache: CacheProtocol                                                  │      │
│  ├──────────────────────────────────────────────────────────────────────┤      │
│  │ + __init__(config: RBACConfig)                                        │      │
│  │ + check_permission(user, resource, action, context) → bool            │      │
│  │ + check_role(user, required_role) → bool                              │      │
│  │ + check_ownership(user, resource_type, resource_id) → bool            │      │
│  │ + check_privilege(user, privilege) → bool                             │      │
│  │ + register_ownership_provider(resource_type, provider)                │      │
│  │ + clear_cache()                                                       │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────┐
│                              CONFIGURATION                                      │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                          RBACConfig                                   │      │
│  │                         <<dataclass>>                                 │      │
│  ├──────────────────────────────────────────────────────────────────────┤      │
│  │ # Policy configuration                                                │      │
│  │ model_path: str | None = None                                         │      │
│  │ model_text: str | None = None                                         │      │
│  │ policy_path: str | None = None                                        │      │
│  │ policy_adapter: Any | None = None                                     │      │
│  │                                                                       │      │
│  │ # Role configuration                                                  │      │
│  │ roles: list[str] | None = None                                        │      │
│  │ superadmin_role: str | None = None                                    │      │
│  │                                                                       │      │
│  │ # User configuration                                                  │      │
│  │ subject_field: str = "email"                                          │      │
│  │ subject_provider: SubjectProvider | None = None                       │      │
│  │                                                                       │      │
│  │ # Behavior configuration                                              │      │
│  │ cache_enabled: bool = True                                            │      │
│  │ cache_ttl_seconds: int = 300                                          │      │
│  │ default_deny: bool = True                                             │      │
│  │ log_denials: bool = True                                              │      │
│  ├──────────────────────────────────────────────────────────────────────┤      │
│  │ + from_env() → RBACConfig  [classmethod]                              │      │
│  │ + from_file(path: str) → RBACConfig  [classmethod]                    │      │
│  │ + validate() → None                                                   │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Designs

### 3.1 Role Factory Design

**Purpose:** Generate dynamic Role enums at runtime with full type support.

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Role Factory Flow                               │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│    User Code                     Library                                │
│    ──────────                    ───────                                │
│                                                                         │
│    role_names = [              ┌─────────────────────────────┐          │
│      "admin",                  │     create_roles()          │          │
│      "moderator",       ────▶  │                             │          │
│      "user",                   │ 1. Validate names           │          │
│      "guest"                   │ 2. Create Enum class        │          │
│    ]                           │ 3. Inject __or__ method     │          │
│                                │ 4. Register superadmin      │          │
│                                │ 5. Return Type[Enum]        │          │
│    Role = create_roles(        └──────────┬──────────────────┘          │
│      role_names,                          │                             │
│      superadmin="admin"        ◀──────────┘                             │
│    )                                                                    │
│                                                                         │
│    # Result: Role is a real Enum                                        │
│    Role.ADMIN    → "admin"                                              │
│    Role.USER     → "user"                                               │
│    Role.ADMIN | Role.MODERATOR → RoleComposition                        │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Provider Architecture

**Purpose:** Enable pluggable implementations for subject extraction, role checking, and ownership validation.

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Provider Architecture                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        RBACService                               │   │
│  │                                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │   │
│  │  │ Subject      │  │ Role         │  │ Ownership          │    │   │
│  │  │ Provider     │  │ Provider     │  │ Registry           │    │   │
│  │  │              │  │              │  │                    │    │   │
│  │  │ get_subject()│  │ get_roles()  │  │ providers: dict    │    │   │
│  │  │              │  │ has_role()   │  │ get(resource_type) │    │   │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘    │   │
│  └─────────┼─────────────────┼──────────────────┼─────────────────┘   │
│            │                 │                  │                      │
│            ▼                 ▼                  ▼                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────────┐  │
│  │ Default:        │  │ Default:        │  │ User Implementations: │  │
│  │ user.email      │  │ user.role       │  │                       │  │
│  └─────────────────┘  │ + superadmin    │  │ OrderOwnership        │  │
│                       │   bypass        │  │ ProjectOwnership      │  │
│  ┌─────────────────┐  └─────────────────┘  │ TenantOwnership       │  │
│  │ Custom:         │                       │ ...                   │  │
│  │ user.id or      │  ┌─────────────────┐  └───────────────────────┘  │
│  │ composite key   │  │ Custom:         │                             │
│  └─────────────────┘  │ Multi-role      │                             │
│                       │ from database   │                             │
│                       └─────────────────┘                             │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Configuration System Design

**Purpose:** Provide flexible, layered configuration with sensible defaults.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Configuration Loading Priority                     │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│    Priority 1 (Highest)          Priority 2            Priority 3      │
│    ─────────────────────         ──────────            ──────────      │
│                                                                         │
│    ┌───────────────────┐    ┌───────────────────┐   ┌────────────────┐ │
│    │ Programmatic      │    │ Environment       │   │ Config File    │ │
│    │                   │    │ Variables         │   │                │ │
│    │ RBACConfig(       │    │                   │   │ rbac.yaml      │ │
│    │   model_path=...  │    │ RBAC_MODEL_PATH   │   │ rbac.toml      │ │
│    │ )                 │    │ RBAC_POLICY_PATH  │   │ rbac.json      │ │
│    └─────────┬─────────┘    │ RBAC_SUPERADMIN   │   └────────┬───────┘ │
│              │              └─────────┬─────────┘            │         │
│              │                        │                      │         │
│              └────────────────────────┼──────────────────────┘         │
│                                       │                                 │
│                                       ▼                                 │
│                            ┌───────────────────┐                       │
│                            │ Merged Config     │                       │
│                            │                   │                       │
│                            │ (programmatic     │                       │
│                            │  overrides env    │                       │
│                            │  overrides file   │                       │
│                            │  overrides defaults)                      │
│                            └───────────────────┘                       │
│                                       │                                 │
│                                       ▼                                 │
│    Priority 4 (Lowest)                                                  │
│    ──────────────────                                                   │
│                                                                         │
│    ┌───────────────────────────────────────────────────────────────┐   │
│    │                       Library Defaults                         │   │
│    │                                                                │   │
│    │  model_text: DEFAULT_RBAC_MODEL (embedded)                     │   │
│    │  cache_enabled: True                                           │   │
│    │  cache_ttl: 300                                                │   │
│    │  default_deny: True                                            │   │
│    │  subject_field: "email"                                        │   │
│    └───────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow Diagrams

### 4.1 Authorization Request Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         Authorization Request Flow                          │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   HTTP Request                                                              │
│       │                                                                     │
│       ▼                                                                     │
│   ┌───────────────┐                                                         │
│   │   FastAPI     │                                                         │
│   │   Router      │                                                         │
│   └───────┬───────┘                                                         │
│           │                                                                 │
│           ▼                                                                 │
│   ┌───────────────┐                                                         │
│   │   Auth        │    ┌─── If not authenticated ───▶ 401 Unauthorized     │
│   │   Dependency  │    │                                                    │
│   └───────┬───────┘    │                                                    │
│           │            │                                                    │
│           ▼            │                                                    │
│   ┌───────────────┐    │                                                    │
│   │   @require    │────┘                                                    │
│   │   Decorator   │                                                         │
│   └───────┬───────┘                                                         │
│           │                                                                 │
│           ▼                                                                 │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                    Requirement Evaluation                          │    │
│   │                                                                    │    │
│   │   For each requirement group (OR logic between groups):           │    │
│   │                                                                    │    │
│   │   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐ │    │
│   │   │ Check Role      │   │ Check Permission│   │ Check Ownership │ │    │
│   │   │                 │   │                 │   │                 │ │    │
│   │   │ Role Provider:  │   │ Casbin Enforcer:│   │ Ownership       │ │    │
│   │   │ user.role ==    │   │ enforce(        │   │ Provider:       │ │    │
│   │   │ required?       │   │   subject,      │   │ check_ownership │ │    │
│   │   │                 │   │   resource,     │   │ (user, type, id)│ │    │
│   │   │ Superadmin      │   │   action        │   │                 │ │    │
│   │   │ bypass?         │   │ )               │   │                 │ │    │
│   │   └────────┬────────┘   └────────┬────────┘   └────────┬────────┘ │    │
│   │            │                     │                     │          │    │
│   │            └─────────────────────┼─────────────────────┘          │    │
│   │                                  │                                 │    │
│   │                                  ▼                                 │    │
│   │   Within group: AND logic (all must pass)                         │    │
│   │   Between groups: OR logic (any group passing is success)         │    │
│   │                                                                    │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│           │                                                                 │
│           ▼                                                                 │
│   ┌───────────────────┐        ┌───────────────────┐                       │
│   │     SUCCESS       │        │      FAILURE      │                       │
│   │                   │        │                   │                       │
│   │ Execute endpoint  │        │ HTTPException 403 │                       │
│   │ Return response   │        │ "Access denied"   │                       │
│   └───────────────────┘        └───────────────────┘                       │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Cache Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              Cache Flow                                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   check_permission(user, resource, action)                                  │
│                │                                                            │
│                ▼                                                            │
│   ┌────────────────────────┐                                               │
│   │   Generate Cache Key   │                                               │
│   │                        │                                               │
│   │   key = f"{user.id}:   │                                               │
│   │          {resource}:   │                                               │
│   │          {action}"     │                                               │
│   └───────────┬────────────┘                                               │
│               │                                                             │
│               ▼                                                             │
│   ┌────────────────────────┐     ┌────────────────────────────────┐        │
│   │   Check Cache          │     │      Cache Hit                  │        │
│   │                        │────▶│                                 │        │
│   │   cache.get(key)       │     │   Return cached result         │        │
│   └───────────┬────────────┘     │   ──────────────────▶ Result   │        │
│               │                  └────────────────────────────────┘        │
│               │ Cache Miss                                                  │
│               ▼                                                             │
│   ┌────────────────────────┐                                               │
│   │   Evaluate Permission  │                                               │
│   │                        │                                               │
│   │   enforcer.enforce(    │                                               │
│   │     subject, resource, │                                               │
│   │     action             │                                               │
│   │   )                    │                                               │
│   └───────────┬────────────┘                                               │
│               │                                                             │
│               ▼                                                             │
│   ┌────────────────────────┐                                               │
│   │   Store in Cache       │                                               │
│   │                        │                                               │
│   │   cache.set(           │                                               │
│   │     key,               │                                               │
│   │     result,            │                                               │
│   │     ttl=config.ttl     │                                               │
│   │   )                    │                                               │
│   └───────────┬────────────┘                                               │
│               │                                                             │
│               ▼                                                             │
│            Result                                                           │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. API Design

### 5.1 Public API Surface

**Initialization:**
```python
# Minimal setup
from fastapi_rbac import create_roles, RBACConfig, RBACService

Role = create_roles(["admin", "user", "guest"], superadmin="admin")
config = RBACConfig()
rbac = RBACService(config)
```

**Decorator Usage:**
```python
from fastapi_rbac import require, Permission, ResourceOwnership

@app.get("/admin")
@require(Role.ADMIN)
async def admin_only(user: User):
    ...

@app.get("/data")
@require(Permission("data", "read"))
async def read_data(user: User):
    ...

@app.get("/items/{item_id}")
@require(ResourceOwnership("item"))
async def get_item(item_id: int, user: User):
    ...
```

**Provider Registration:**
```python
class MyOwnershipProvider:
    async def check_ownership(self, user, resource_type, resource_id):
        return user.id == resource_id  # Example logic

rbac.register_ownership_provider("item", MyOwnershipProvider())
```

### 5.2 Error Response Design

**Standard Error Format:**
```json
{
  "detail": "Access denied: insufficient privileges for admin_only",
  "error_code": "AUTHORIZATION_DENIED",
  "required": ["admin"],
  "user_role": "user"
}
```

**Exception Hierarchy:**
```
RBACError (base)
├── AuthorizationDenied
│   ├── RoleDenied
│   ├── PermissionDenied
│   └── OwnershipDenied
├── ConfigurationError
│   ├── InvalidPolicyError
│   ├── InvalidModelError
│   └── MissingConfigError
└── ProviderError
    ├── SubjectExtractionError
    └── OwnershipCheckError
```

---

## 6. Extension Architecture

### 6.1 Extension Points Summary

| Extension Point | Protocol | Default Implementation | Use Case |
|-----------------|----------|----------------------|----------|
| Subject Provider | `SubjectProvider` | Returns `user.email` | Custom subject identifiers |
| Role Provider | `RoleProvider` | Reads `user.role` | Multi-role support, database roles |
| Ownership Provider | `OwnershipProvider` | Superadmin bypass | Resource-specific ownership |
| Policy Adapter | `casbin.Adapter` | File adapter | Database policies |
| Cache Provider | `CacheProtocol` | Memory cache | Redis, distributed cache |

### 6.2 Provider Lifecycle

```
Application Startup
       │
       ▼
┌──────────────────────┐
│  Create Providers    │
│                      │
│  provider = MyProv() │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Register Providers  │
│                      │
│  rbac.register_*()   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Initialize RBAC     │
│                      │
│  rbac.initialize()   │
│  (loads policies)    │
└──────────┬───────────┘
           │
           ▼
       Application
       Running
           │
       Each Request
           │
           ▼
┌──────────────────────┐
│  Provider Called     │
│                      │
│  provider.check_*()  │
└──────────────────────┘
```

---

## 7. Configuration Design

### 7.1 Configuration Schema

```yaml
# Example rbac.yaml configuration
rbac:
  # Policy files
  model_path: "./config/rbac_model.conf"
  policy_path: "./config/rbac_policy.csv"
  
  # Role configuration
  roles:
    - admin
    - moderator
    - user
    - guest
  superadmin_role: admin
  
  # User mapping
  subject_field: email  # or id, username
  
  # Behavior
  cache:
    enabled: true
    ttl_seconds: 300
  
  default_deny: true
  log_denials: true
  log_level: INFO
```

### 7.2 Environment Variable Mapping

| Variable | Config Field | Default |
|----------|--------------|---------|
| `RBAC_MODEL_PATH` | `model_path` | None |
| `RBAC_POLICY_PATH` | `policy_path` | None |
| `RBAC_SUPERADMIN_ROLE` | `superadmin_role` | None |
| `RBAC_CACHE_ENABLED` | `cache_enabled` | `true` |
| `RBAC_CACHE_TTL` | `cache_ttl_seconds` | `300` |
| `RBAC_DEFAULT_DENY` | `default_deny` | `true` |
| `RBAC_LOG_DENIALS` | `log_denials` | `true` |

---

## 8. Migration Architecture

### 8.1 Compatibility Layer Design

For users migrating from the business-coupled version:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Compatibility Layer                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Old Import                        New Import + Compatibility          │
│   ──────────                        ───────────────────────────         │
│                                                                         │
│   from app.core.rbac import Role    from fastapi_rbac.compat import (   │
│                                         create_legacy_roles              │
│                                     )                                    │
│                                     Role = create_legacy_roles()        │
│                                     # Creates SUPERADMIN, SALESMAN,     │
│                                     # DATA_ENTRY, PARTNER, CUSTOMER     │
│                                                                         │
│   from app.core.rbac import (       from fastapi_rbac import (          │
│       require, Permission               require, Permission             │
│   )                                 )                                    │
│   # Syntax unchanged                # Syntax unchanged                  │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Migration Steps

```
Step 1: Install new package
        pip install fastapi-role

Step 2: Create role configuration
        Role = create_roles([...your roles...])

Step 3: Update imports
        - from app.core.rbac → from fastapi_rbac
        - Remove User import from rbac

Step 4: Initialize RBAC at startup
        config = RBACConfig(...)
        rbac = RBACService(config)

Step 5: Register custom providers (if needed)
        rbac.register_ownership_provider(...)

Step 6: Run tests to verify behavior
```

---

This design document provides the complete architectural blueprint for transforming the business-coupled `fastapi-role` code into a general-purpose PyPI package while maintaining all existing functionality and enabling extensive customization.
