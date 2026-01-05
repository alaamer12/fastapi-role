# Architecture Overview

`fastapi-role` is designed to be modular, extensible, and framework-agnostic (within the FastAPI ecosystem). It decouples policy enforcement, role management, and data access.

## High-Level Diagram

```mermaid
graph TD
    Request[Incoming Request] --> Middleware[FastAPI Middleware/Dependency]
    Middleware --> Decorator[@require]
    Decorator --> RBACService[RBACService]
    
    subgraph "fastapi-role Core"
        RBACService --> SubjectProvider[Subject Provider]
        RBACService --> RoleProvider[Role Provider]
        RBACService --> Cache[Cache Provider]
        RBACService --> Enforcer[Casbin Enforcer]
        RBACService --> Ownership[Ownership Registry]
    end
    
    subgraph "Data & Policy"
        Enforcer --> Model[Model.conf]
        Enforcer --> Policy[Policy.csv / DB]
        Ownership --> DB[(Database)]
    end
    
    SubjectProvider -- "Extract User ID" --> User[User Object]
    RoleProvider -- "Extract Roles" --> User
```

## Core Components

### 1. RBACService
The central entry point. It coordinates all other components. It initializes the Casbin enforcer, checks caches, delegates ownership checks, and manages the transaction lifecycle if a DB session is provided.

### 2. Providers (Extension Points)
To avoid coupling with specific business logic (like your specific User model or Database schema), the library uses the **Provider Pattern**.

*   **SubjectProtocol**: Defines "Who is this user?".
*   **RoleProtocol**: Defines "What roles does this user have?".
*   **CacheProtocol**: Defines "How do we store/retrieve permission results?".
*   **OwnershipProtocol**: Defines "Does this user own this specific resource ID?".

### 3. Protocols
We use Python `typing.Protocol` for structural subtyping. This means your `User` model doesn't need to inherit from our base class; it just needs to have `id`, `email`, and `role` attributes.

### 4. Casbin Integration
The library wraps [PyCasbin](https://github.com/casbin/pycasbin).
*   **Model**: Defines the mathematical verification logic (Request, Policy, Matchers).
*   **Policy**: The actual rules (`p, admin, data, read`).
*   **Enforcer**: The engine that takes a request `(sub, obj, act)` and returns `True/False`.

### 5. Sync & Async Support
The library supports both synchronous (`Session`) and asynchronous (`AsyncSession`) SQLAlchemy sessions.
*   **Sync**: `commit_sync()`, `rollback_sync()`
*   **Async**: `await commit()`, `await rollback()`

Internal RBAC checks (`check_permission`) are `async` by default to support non-blocking I/O (like Redis caches or DB lookups) but don't strictly require an async DB session.

## Request Flow

1.  **Endpoint Hit**: Request reaches a protected endpoint.
2.  **Dependency Injection**: `RBACService` is injected.
3.  **Decorator Check**: `@require(roles=["admin"])` intercepts execution.
4.  **Service Validation**:
    *   Extracts subject from user (`SubjectProvider`).
    *   Checks Cache.
    *   If miss, calls Casbin `enforce()`.
    *   If resource ID provided, calls `check_resource_ownership()`.
5.  **Result**: Access granted or `403 Forbidden` raised.
