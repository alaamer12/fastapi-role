# Analysis and Code Audit

**Date:** 2026-01-02
**Phase:** 1 (Analysis & Preparation)

## 1. File Inventory & Size

| File | Size (Lines) | Purpose |
|------|-------------|---------|
| [fastapi_role/__init__.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/__init__.py) | ~39 | Package exports and version integration. |
| [fastapi_role/rbac.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py) | ~785 | Core RBAC classes ([Role](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#56-88), [Permission](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#137-163), [Privilege](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#191-230)), [require](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#500-570) decorator, [RBACQueryFilter](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#389-494). |
| [fastapi_role/rbac_actions.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_actions.py) | ~129 | UI Action configuration classes ([PageAction](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_actions.py#26-70), [TableAction](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_actions.py#72-129)). |
| [fastapi_role/rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | ~553 | Core Service using `casbin`, ownership checks, caching, customer relationship logic. |
| [config/rbac_model.conf](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/config/rbac_model.conf) | 14 | Casbin model definition (request, policy, role, matchers). |
| [config/rbac_policy.csv](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/config/rbac_policy.csv) | 7 | Default policy definitions using hardcoded roles. |

**Total Code Volume:** ~1520 Lines

## 2. Dependency Map & Coupling Analysis

### A. Standard Library (Safe)
- `logging`, `datetime`, `collections.abc`, `enum`, `functools`, `typing`, `inspect`.

### B. Third-Party (Keep)
- `casbin`: Core policy engine.
- `fastapi`: `HTTPException` for access control.
- `sqlalchemy`: Query construction (used in filters and service).

### C. Business-Specific (MUST REMOVE/ABSTRACT)
These imports represent hard coupling to the specific "WindX" (or "ResPect") business domain.

| File | Line(s) | Import / Usage | Reason for Removal |
|------|---------|----------------|-------------------|
| [rbac.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py) | 40 | `from app.models.user import User` | Couples to specific User model. |
| [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | 31-35 | `from app.core.exceptions import ...` | Couples to specific exception hierarchy. |
| [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | 36 | `from app.core.rbac import Privilege, Role` | Circular/legacy import. |
| [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | 37 | `from app.models.customer import Customer` | Couples to "Customer" concept. |
| [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | 38 | `from app.models.user import User` | Couples to specific User model. |
| [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | 39 | `from app.services.base import BaseService` | Couples to application service layer. |
| [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | 412 | `from app.database.connection ...` | Couples to database session factory. |
| [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) | 161, 174, 187 | `from app.models.[configuration/quote/order]` | Couples ownership logic to specific entities. |

## 3. Hardcoded Values & Logic Audit

### A. Roles ([rbac.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py))
- Hardcoded `Enum`: `SUPERADMIN`, `SALESMAN`, `DATA_ENTRY`, `PARTNER`, `CUSTOMER`.
- **Transformation Target:** Dynamic `RoleFactory`.

### B. Resource Types ([rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py))
- Explicit checks for: `"customer"`, `"configuration"`, `"quote"`, `"order"`.
- **Transformation Target:** Pluggable `OwnershipProvider` registry.

### C. Configuration Paths ([rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py))
- Hardcoded: `casbin.Enforcer("config/rbac_model.conf", "config/rbac_policy.csv")`.
- **Transformation Target:** `RBACConfig` object with file/env loading.

### D. Business Logic "Side Effects"
- [get_or_create_customer_for_user](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py#244-274): Creates a "Customer" record when a "User" is processed. This is pure business logic (CRM feature) mixed into RBAC.
- **Recommendations:** Remove from generic library. This should be implemented by the using application, possibly via an event hook or just outside the RBAC service.

### E. Query Filters ([rbac.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py))
- [filter_configurations](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#396-428), [filter_quotes](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#429-461), [filter_orders](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#462-494).
- **Transformation Target:** [RBACQueryFilter](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac.py#389-494) should provide generic helpers (e.g., `filter_by_ownership(params)`), but specialized entity filters must move to the application code or a specific `SQLAlchemyProvider` extension.

## 4. Requirement Gap Analysis

Based on the audit, the [requirements.md](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/.repertoire/milestone/requirements.md) generally covers the transformation well.

- **Gap Identified:** The [get_or_create_customer_for_user](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py#244-274) logic.
    - [requirements.md](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/.repertoire/milestone/requirements.md) does not explicitly state "Remove business side-effects".
    - **Resolution:** Implicit in "Decouple Business Logic", but worth noting that this feature will *disappear* from the core library service.

- **Gap Identified:** Database Dependencies.
    - [rbac_service.py](file:///f:/Projects/Languages/Python/WorkingOnIt/fastapi-role/fastapi_role/rbac_service.py) inherits `BaseService` and uses `AsyncSession`.
    - **Resolution:** Generic library should likely be agnostic of the DB session type, or provide a specific `SQLAlchemyRBACService`. usage of `db` attribute is pervasive.

## 5. Next Steps
Proceed with **Phase 2: Core Generalization**.
1. Implement `RoleFactory`.
2. Define `UserProtocol`.
3. Create `RBACConfig`.
