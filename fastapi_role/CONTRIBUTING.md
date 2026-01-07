# Contributing to fastapi-role

Thank you for your interest in contributing to fastapi-role! We welcome contributions that help maintain our core principle: **Pure General RBAC with zero business assumptions**.

## 🎯 Core Principles

Before contributing, please understand our core principles:

1. **Pure General RBAC**: No business domain assumptions (no hardcoded customers, orders, etc.)
2. **Framework Agnostic**: Must work with FastAPI, Flask, Django, CLI, etc.
3. **Resource Agnostic**: Use `(type, id)` patterns, never hardcode resource types
4. **Provider-Based**: All business logic through pluggable providers
5. **Configuration-Driven**: Behavior defined by data, not code
6. **Zero Dependencies**: Minimal dependencies, maximum compatibility

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- uv (recommended) or pip

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/alaamer12/fastapi-role.git
cd fastapi-role/fastapi_role

# Install dependencies with uv (recommended)
uv sync --dev

# Or with pip
pip install -e ".[dev]"

# Run tests to ensure everything works
pytest
```

### Project Structure

```
fastapi_role/
├── fastapi_role/           # Core package
│   ├── core/              # Core RBAC engine
│   ├── protocols/         # Provider protocols
│   ├── providers/         # Default provider implementations
│   ├── helpers/           # Utility functions
│   ├── rbac_service.py    # Main RBAC service
│   └── rbac.py           # Decorators and public API
├── tests/                 # Test suite
├── examples/             # Usage examples
└── docs/                 # Documentation
```

## 🔧 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Follow TDD (Test-Driven Development)

We practice strict TDD for all changes:

```bash
# 1. Write failing tests first
pytest tests/test_your_feature.py -v

# 2. Implement the minimum code to make tests pass
# 3. Refactor while keeping tests green
# 4. Repeat
```

### 3. Maintain Pure General RBAC

Ensure your changes maintain our core principles:

```python
# ❌ DON'T: Business-specific code
def get_customer_orders(customer_id: int):
    pass

# ✅ DO: Resource-agnostic code  
def get_resources(resource_type: str, resource_id: Any):
    pass

# ❌ DON'T: Hardcoded roles
class Role(Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"

# ✅ DO: Dynamic roles
Role = create_roles(["admin", "user"], superadmin="admin")
```

### 4. Run Quality Checks

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fastapi_role --cov-report=html

# Type checking
mypy fastapi_role

# Linting and formatting
ruff check .
ruff format .

# Property-based tests (important!)
pytest tests/test_*_properties.py -v
```

## 🧪 Testing Guidelines

### Test Categories

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test component interactions
3. **Property Tests**: Test universal properties (critical for RBAC)
4. **Framework Tests**: Test compatibility with different frameworks

### Property-Based Testing

We use property-based testing to ensure universal correctness:

```python
from hypothesis import given, strategies as st

@given(st.lists(st.text(min_size=1), min_size=1))
def test_role_creation_consistency(role_names):
    """For any valid role names, creating roles multiple times produces equivalent results"""
    Role1 = create_roles(role_names)
    Role2 = create_roles(role_names)
    
    assert list(Role1) == list(Role2)
    assert Role1.__name__ == Role2.__name__
```

### Test Requirements

- **Coverage**: Maintain >90% test coverage
- **Property Tests**: All core functionality must have property tests
- **Framework Tests**: Test with FastAPI, Flask, and CLI scenarios
- **Edge Cases**: Test error conditions and boundary cases
- **Performance**: Include performance regression tests

## 📝 Code Style

### Python Style

```python
# Use type hints for all public APIs
async def can_access(
    self, 
    user: UserProtocol, 
    resource: ResourceRef, 
    action: str
) -> bool:
    """Check if user can access resource with action."""
    pass

# Use descriptive variable names
resource_type = "document"  # ✅
rt = "document"            # ❌

# Prefer composition over inheritance
class RBACService:
    def __init__(self, providers: ProviderRegistry):
        self.providers = providers  # ✅ Composition
```

### Documentation Style

```python
def create_roles(
    role_names: List[str], 
    superadmin: Optional[str] = None
) -> Type[Enum]:
    """Create a dynamic role enum from role names.
    
    Args:
        role_names: List of role names to create
        superadmin: Optional superadmin role name
        
    Returns:
        Dynamic enum class with role values
        
    Raises:
        ValueError: If role names are invalid or duplicated
        
    Example:
        >>> Role = create_roles(["admin", "user"], superadmin="admin")
        >>> Role.ADMIN.value
        'admin'
    """
```

## 🔌 Adding New Providers

When adding new provider types:

1. **Define Protocol**: Create a clear protocol interface
2. **Default Implementation**: Provide a sensible default
3. **Documentation**: Include usage examples
4. **Tests**: Test protocol compliance and edge cases

```python
# 1. Define protocol
class NewProvider(Protocol):
    @abstractmethod
    async def do_something(self, param: Any) -> bool:
        """Do something with the parameter."""
        ...

# 2. Default implementation
class DefaultNewProvider:
    async def do_something(self, param: Any) -> bool:
        return True  # Sensible default

# 3. Tests
def test_new_provider_protocol():
    """Test that custom providers work correctly"""
    pass
```

## 🚫 What NOT to Contribute

Please avoid these types of contributions:

- **Business-Specific Features**: Customer management, order processing, etc.
- **Framework-Specific Code**: Code that only works with one framework
- **Hardcoded Assumptions**: Hardcoded roles, resources, or business logic
- **Breaking Changes**: Changes that break the pure general RBAC principle
- **Performance Optimizations**: Without benchmarks and tests

## 📋 Pull Request Process

### Before Submitting

- [ ] All tests pass (`pytest`)
- [ ] Code coverage maintained (`pytest --cov`)
- [ ] Type checking passes (`mypy`)
- [ ] Linting passes (`ruff check`)
- [ ] Property tests pass (critical for RBAC correctness)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Pure General RBAC Compliance
- [ ] No business domain assumptions added
- [ ] Works with arbitrary resource types
- [ ] Framework agnostic
- [ ] Provider-based architecture maintained
- [ ] Configuration-driven behavior

## Testing
- [ ] Unit tests added/updated
- [ ] Property tests added/updated
- [ ] Integration tests pass
- [ ] Framework compatibility tested

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added for new functionality
- [ ] All tests pass
```

### Review Process

1. **Automated Checks**: CI/CD pipeline runs all tests
2. **Code Review**: Maintainer reviews for RBAC principles
3. **Testing**: Manual testing of examples and integration
4. **Documentation**: Ensure docs are updated
5. **Merge**: Squash and merge with descriptive commit message

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment**: Python version, framework, OS
2. **Minimal Reproduction**: Smallest code that reproduces the issue
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **RBAC Context**: Roles, permissions, resources involved

```python
# Example bug report code
from fastapi_role import create_roles, RBACService, require

Role = create_roles(["admin", "user"])
rbac = RBACService()

@require(Role.ADMIN)
async def test_function(user: User, rbac: RBACService):
    return "success"

# This should work but doesn't...
```

## 💡 Feature Requests

For new features, please:

1. **Check Existing Issues**: Avoid duplicates
2. **Describe Use Case**: Real-world scenario
3. **Maintain Principles**: Ensure it fits pure general RBAC
4. **Provide Examples**: Show how it would work
5. **Consider Alternatives**: Other ways to achieve the goal

## 🏆 Recognition

Contributors will be recognized in:

- CHANGELOG.md for their contributions
- README.md contributors section
- GitHub contributors page

## 📞 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Email**: For security issues (ahmedmuhmmed239@gmail.com)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make fastapi-role the best pure general RBAC engine! 🚀