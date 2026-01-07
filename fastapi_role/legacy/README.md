# Legacy Components

This directory contains components that were removed from the core RBAC package to achieve pure general RBAC functionality.

## base.py

The `BaseService` class was moved here because it represents business-specific database session management that couples the RBAC engine to specific database technologies and patterns.

### Why it was removed:

1. **Business Coupling**: Assumes specific SQLAlchemy session management patterns
2. **Database Dependency**: Forces RBAC core to depend on database connections
3. **Framework Coupling**: Ties RBAC to specific ORM technology

### If you need database integration:

Use the new provider pattern instead:

```python
from fastapi_role.providers import DatabaseProvider

class MyDatabaseProvider(DatabaseProvider):
    def __init__(self, session):
        self.session = session
    
    async def persist_user_role(self, user_id, role):
        # Your database logic here
        pass

# Register with RBAC service
rbac_service.register_database_provider(MyDatabaseProvider(session))
```

This approach keeps the RBAC core pure while allowing flexible database integration.