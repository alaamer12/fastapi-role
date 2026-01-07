# File-Based Configuration RBAC Example

This example demonstrates the pure general RBAC system with file-based configuration, showcasing:

- **Configuration-driven role and policy definition** via YAML files
- **Multiple generic resource types** (documents, projects, tasks)
- **Custom ownership providers** with different business logic per resource type
- **File-based policy storage** that can be modified without code changes
- **Runtime configuration reloading** (admin feature)

## Features Demonstrated

### 1. Configuration-Driven Roles
- Roles defined in `config/roles.yaml`
- Dynamic role creation from configuration
- Configurable superadmin role
- Permission mapping per role

### 2. File-Based Policies
- Policies defined in `config/policies.yaml`
- Subject-Object-Action pattern
- Allow/deny effects
- Runtime policy modification

### 3. Resource Type Configuration
- Resource types defined in `config/resources.yaml`
- Configurable actions per resource type
- Custom ownership providers per type
- Default permission templates

### 4. Custom Ownership Providers
- **DocumentOwnershipProvider**: Owner + public access + manager override
- **ProjectOwnershipProvider**: Owner + membership + public access
- **TaskOwnershipProvider**: Owner + assignee + role-based access

### 5. User Configuration
- Users defined in `config/users.yaml`
- User attributes and metadata
- Role assignments
- Extensible user properties

## Quick Start

### 1. Install Dependencies
```bash
pip install pyyaml pyjwt fastapi uvicorn
```

### 2. Run the Example
```bash
python examples/file_based_rbac_example.py
```

The server will start at `http://localhost:8001` with API documentation at `http://localhost:8001/docs`.

### 3. Configuration Files
On first run, default configuration files are created in `examples/config/`:

- `roles.yaml` - Role definitions and permissions
- `policies.yaml` - Access control policies  
- `resources.yaml` - Resource type configurations
- `users.yaml` - User definitions and attributes

## Test Users

| Email | Role | Password | Description |
|-------|------|----------|-------------|
| admin@example.com | admin | password | System administrator |
| manager@example.com | manager | password | Project manager |
| editor@example.com | editor | password | Content editor |
| viewer@example.com | viewer | password | Read-only user |

## API Endpoints

### Authentication
- `POST /login` - Login with email/password
- `GET /me` - Get current user info

### Configuration
- `GET /config` - View current RBAC configuration
- `GET /config/reload` - Reload configuration from files (admin only)

### Resources
- `GET /resources` - List accessible resources (with filtering)
- `GET /resources/{type}/{id}` - Get specific resource
- `POST /resources/{type}` - Create new resource
- `PUT /resources/{type}/{id}` - Update resource
- `DELETE /resources/{type}/{id}` - Delete resource

### Administration
- `GET /admin/users` - List all users (admin only)
- `GET /admin/stats` - System statistics (admin only)

## Configuration Examples

### Adding a New Role

Edit `config/roles.yaml`:
```yaml
roles:
  - name: contributor
    description: External contributor with limited access
    permissions:
      - document:read
      - task:read
      - task:create
```

### Adding a New Policy

Edit `config/policies.yaml`:
```yaml
policies:
  - subject: contributor
    object: document
    action: read
    effect: allow
```

### Adding a New Resource Type

Edit `config/resources.yaml`:
```yaml
resource_types:
  - name: comment
    description: Comments and discussions
    actions: [read, create, update, delete, moderate]
    ownership_provider: comment_ownership
    default_permissions:
      owner: [read, update, delete]
      public: [read]
```

## Custom Ownership Providers

The example includes three custom ownership providers demonstrating different access patterns:

### DocumentOwnershipProvider
```python
# Access Logic:
# 1. Superadmin bypass
# 2. Owner access
# 3. Public document access
# 4. Manager role override
```

### ProjectOwnershipProvider  
```python
# Access Logic:
# 1. Superadmin bypass
# 2. Owner access
# 3. Project member access
# 4. Public project access
# 5. Manager role override
```

### TaskOwnershipProvider
```python
# Access Logic:
# 1. Superadmin bypass
# 2. Owner access
# 3. Task assignee access
# 4. Manager/Editor role access
```

## Testing the Example

### 1. Login as Admin
```bash
curl -X POST "http://localhost:8001/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "password"}'
```

### 2. List Resources
```bash
curl -X GET "http://localhost:8001/resources" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Create a Document
```bash
curl -X POST "http://localhost:8001/resources/document" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Document", "is_public": false}'
```

### 4. View Configuration
```bash
curl -X GET "http://localhost:8001/config" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Key Benefits

1. **No Code Changes**: Modify roles and policies via configuration files
2. **Runtime Flexibility**: Add new resource types without redeployment
3. **Business Logic Separation**: Custom ownership providers handle domain-specific rules
4. **Audit Trail**: Configuration changes are tracked in version control
5. **Environment-Specific**: Different configurations for dev/staging/production

## Production Considerations

1. **Configuration Validation**: Add schema validation for YAML files
2. **Hot Reloading**: Implement file watchers for automatic config reloading
3. **Database Storage**: Move configuration to database for multi-instance deployments
4. **Caching**: Add configuration caching with TTL
5. **Security**: Encrypt sensitive configuration data
6. **Backup**: Implement configuration backup and restore

## Extending the Example

### Add New Resource Types
1. Define in `config/resources.yaml`
2. Create custom ownership provider
3. Register provider in `setup_rbac()`
4. Add sample data to `RESOURCES`

### Add New Roles
1. Define in `config/roles.yaml`
2. Add policies in `config/policies.yaml`
3. Create test users in `config/users.yaml`

### Add Custom Attributes
1. Extend user attributes in `config/users.yaml`
2. Use attributes in custom ownership providers
3. Add attribute-based policy conditions

This example demonstrates how the pure general RBAC system can be completely configured through files, making it suitable for complex enterprise scenarios where business rules change frequently.