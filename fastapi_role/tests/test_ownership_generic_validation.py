"""Tests to validate ownership system is truly generic.

Tests for task 5.2: Remove any remaining hardcoded ownership logic
- Verify no hardcoded resource types remain in ownership checks
- Ensure ownership system works with arbitrary resource types
- Test ownership providers with mock implementations
- Validate ownership system is truly generic
"""

import pytest
from typing import Any
from unittest.mock import AsyncMock

from fastapi_role.core.ownership import OwnershipRegistry
from fastapi_role.providers import DefaultOwnershipProvider
from fastapi_role import RBACService
from fastapi_role.core.config import CasbinConfig
from fastapi_role.core.resource import ResourceRef
from tests.conftest import TestUser as User


class TestGenericResourceTypes:
    """Test ownership system with completely arbitrary resource types."""

    @pytest.mark.asyncio
    async def test_arbitrary_resource_type_names(self):
        """Test ownership system works with any resource type names."""
        registry = OwnershipRegistry(default_allow=False)
        
        class GenericProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                # Allow access if resource_id matches user_id
                return resource_id == user.id
                
        provider = GenericProvider()
        
        # Test with completely arbitrary resource type names
        arbitrary_types = [
            "xyzzy",                    # Nonsense word
            "🚀",                      # Emoji
            "resource-with-dashes",     # Dashes
            "resource_with_underscores", # Underscores
            "ResourceWithCamelCase",    # CamelCase
            "resource.with.dots",       # Dots
            "resource/with/slashes",    # Slashes
            "resource:with:colons",     # Colons
            "123numeric",               # Starting with number
            "a" * 100,                  # Very long name
            "",                         # Empty string (edge case)
        ]
        
        user = User(id=42, role="user")
        
        for resource_type in arbitrary_types:
            if resource_type:  # Skip empty string for registration
                registry.register(resource_type, provider)
                
                # Test ownership check
                result_owned = await registry.check(user, resource_type, 42)
                result_not_owned = await registry.check(user, resource_type, 99)
                
                assert result_owned is True, f"Failed for resource type: {resource_type}"
                assert result_not_owned is False, f"Failed for resource type: {resource_type}"

    @pytest.mark.asyncio
    async def test_arbitrary_resource_id_types(self):
        """Test ownership system works with any resource ID types."""
        registry = OwnershipRegistry(default_allow=False)
        
        class FlexibleProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                # Different logic based on resource_id type
                if isinstance(resource_id, int):
                    return resource_id == user.id
                elif isinstance(resource_id, str):
                    return str(user.id) in resource_id
                elif isinstance(resource_id, dict):
                    return resource_id.get("owner_id") == user.id
                elif isinstance(resource_id, list):
                    return user.id in resource_id
                elif isinstance(resource_id, tuple):
                    return user.id in resource_id
                else:
                    return False
                    
        registry.register("flexible", FlexibleProvider())
        user = User(id=123, role="user")
        
        # Test different resource ID types
        test_cases = [
            (123, True),                                    # int - matching
            (456, False),                                   # int - not matching
            ("user_123_file", True),                        # str - containing user ID
            ("user_456_file", False),                       # str - not containing user ID
            ({"owner_id": 123, "name": "test"}, True),     # dict - matching owner
            ({"owner_id": 456, "name": "test"}, False),    # dict - not matching owner
            ([100, 123, 200], True),                       # list - containing user ID
            ([100, 456, 200], False),                      # list - not containing user ID
            ((100, 123, 200), True),                       # tuple - containing user ID
            ((100, 456, 200), False),                      # tuple - not containing user ID
            (None, False),                                  # None
            (object(), False),                              # arbitrary object
        ]
        
        for resource_id, expected in test_cases:
            result = await registry.check(user, "flexible", resource_id)
            assert result == expected, f"Failed for resource_id: {resource_id} (type: {type(resource_id)})"

    @pytest.mark.asyncio
    async def test_domain_agnostic_ownership(self):
        """Test ownership system works across different business domains."""
        registry = OwnershipRegistry(default_allow=False)
        
        class DomainAgnosticProvider:
            def __init__(self):
                # Simulate different business domains
                self.domain_rules = {
                    # E-commerce domain
                    "product": lambda user, rid: user.role == "merchant" and rid < 1000,
                    "cart": lambda user, rid: rid == user.id,
                    "order": lambda user, rid: rid % 10 == user.id % 10,
                    
                    # Healthcare domain
                    "patient": lambda user, rid: user.role == "doctor" or rid == user.id,
                    "appointment": lambda user, rid: user.role in ["doctor", "nurse"],
                    "prescription": lambda user, rid: user.role == "doctor",
                    
                    # Education domain
                    "course": lambda user, rid: user.role == "teacher",
                    "assignment": lambda user, rid: user.role in ["teacher", "student"],
                    "grade": lambda user, rid: user.role == "teacher" or rid == user.id,
                    
                    # Finance domain
                    "account": lambda user, rid: rid == user.id or user.role == "manager",
                    "transaction": lambda user, rid: user.role in ["manager", "accountant"],
                    "report": lambda user, rid: user.role == "manager",
                    
                    # Generic/Unknown domains
                    "unknown_resource": lambda user, rid: user.role == "admin",
                }
                
            async def check_ownership(self, user, resource_type, resource_id):
                rule = self.domain_rules.get(resource_type)
                if rule:
                    return rule(user, resource_id)
                return False  # Unknown resource types denied
                
        provider = DomainAgnosticProvider()
        
        # Register for all resource types
        for resource_type in provider.domain_rules.keys():
            registry.register(resource_type, provider)
            
        # Test users from different domains
        merchant = User(id=5, role="merchant")
        doctor = User(id=10, role="doctor")
        teacher = User(id=15, role="teacher")
        manager = User(id=20, role="manager")
        student = User(id=25, role="student")
        admin = User(id=30, role="admin")
        
        # E-commerce tests
        assert await registry.check(merchant, "product", 500) is True   # merchant + id < 1000
        assert await registry.check(merchant, "product", 1500) is False # merchant + id >= 1000
        assert await registry.check(doctor, "product", 500) is False    # not merchant
        
        assert await registry.check(merchant, "cart", 5) is True        # cart id matches user id
        assert await registry.check(merchant, "cart", 10) is False      # cart id doesn't match
        
        # Healthcare tests
        assert await registry.check(doctor, "patient", 999) is True     # doctor can access any patient
        assert await registry.check(student, "patient", 25) is True     # patient can access own record
        assert await registry.check(student, "patient", 10) is False    # patient can't access other records
        
        assert await registry.check(doctor, "prescription", 123) is True    # doctor can prescribe
        assert await registry.check(student, "prescription", 123) is False  # student cannot prescribe
        
        # Education tests
        assert await registry.check(teacher, "course", 456) is True     # teacher can access courses
        assert await registry.check(student, "course", 456) is False    # student cannot access courses
        
        assert await registry.check(teacher, "assignment", 789) is True     # teacher can access assignments
        assert await registry.check(student, "assignment", 789) is True     # student can access assignments
        assert await registry.check(doctor, "assignment", 789) is False     # doctor cannot access assignments
        
        # Finance tests
        assert await registry.check(manager, "account", 999) is True    # manager can access any account
        assert await registry.check(student, "account", 25) is True     # user can access own account
        assert await registry.check(student, "account", 20) is False    # user cannot access other accounts
        
        # Generic/Unknown tests
        assert await registry.check(admin, "unknown_resource", 123) is True     # admin can access unknown
        assert await registry.check(student, "unknown_resource", 123) is False  # others cannot


class TestMockImplementations:
    """Test ownership providers with mock implementations."""

    @pytest.mark.asyncio
    async def test_mock_ownership_provider_behavior(self):
        """Test ownership system with completely mocked provider implementations."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Create mock providers with different behaviors
        mock_providers = {
            "always_allow": AsyncMock(return_value=True),
            "always_deny": AsyncMock(return_value=False),
            "conditional": AsyncMock(side_effect=lambda u, rt, rid: rid % 2 == 0),
            "error_prone": AsyncMock(side_effect=ValueError("Mock error")),
        }
        
        # Register mock providers
        for resource_type, provider in mock_providers.items():
            # Wrap the mock to match the expected interface
            class MockWrapper:
                def __init__(self, mock_func):
                    self.mock_func = mock_func
                    
                async def check_ownership(self, user, resource_type, resource_id):
                    return await self.mock_func(user, resource_type, resource_id)
                    
            registry.register(resource_type, MockWrapper(provider))
            
        user = User(id=1, role="user")
        
        # Test always_allow provider
        result = await registry.check(user, "always_allow", 123)
        assert result is True
        mock_providers["always_allow"].assert_called_once()
        
        # Test always_deny provider
        result = await registry.check(user, "always_deny", 456)
        assert result is False
        mock_providers["always_deny"].assert_called_once()
        
        # Test conditional provider
        result1 = await registry.check(user, "conditional", 2)  # Even
        result2 = await registry.check(user, "conditional", 3)  # Odd
        assert result1 is True
        assert result2 is False
        assert mock_providers["conditional"].call_count == 2
        
        # Test error_prone provider
        with pytest.raises(ValueError, match="Mock error"):
            await registry.check(user, "error_prone", 789)

    @pytest.mark.asyncio
    async def test_provider_call_tracking(self):
        """Test that provider calls are tracked correctly."""
        registry = OwnershipRegistry(default_allow=False)
        
        class TrackingProvider:
            def __init__(self):
                self.calls = []
                
            async def check_ownership(self, user, resource_type, resource_id):
                self.calls.append((user.id, resource_type, resource_id))
                return len(self.calls) % 2 == 1  # Alternate True/False
                
        provider = TrackingProvider()
        registry.register("tracked", provider)
        
        users = [User(id=i, role="user") for i in range(3)]
        
        # Make multiple calls
        results = []
        for i, user in enumerate(users):
            for j in range(2):
                result = await registry.check(user, "tracked", i * 10 + j)
                results.append(result)
                
        # Verify call tracking
        expected_calls = [
            (0, "tracked", 0), (0, "tracked", 1),
            (1, "tracked", 10), (1, "tracked", 11),
            (2, "tracked", 20), (2, "tracked", 21),
        ]
        
        assert provider.calls == expected_calls
        assert results == [True, False, True, False, True, False]  # Alternating


class TestRBACServiceGenericIntegration:
    """Test RBACService integration with generic ownership system."""

    @pytest.fixture
    def rbac_service(self):
        """Create RBACService with mocked dependencies."""
        from unittest.mock import patch, MagicMock
        
        config = CasbinConfig(superadmin_role="superadmin")
        with patch("casbin.Enforcer"):
            service = RBACService(config=config)
            service.enforcer = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_rbac_service_with_arbitrary_resources(self, rbac_service):
        """Test RBACService works with completely arbitrary resource types."""
        # Mock permission check to always return True
        rbac_service.check_permission = AsyncMock(return_value=True)
        
        # Register generic ownership provider
        class ArbitraryResourceProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                # Simple rule: user owns resources where ID matches their ID
                return resource_id == user.id
                
        provider = ArbitraryResourceProvider()
        
        # Test with completely arbitrary resource types
        arbitrary_resources = [
            "🎯", "quantum_flux_capacitor", "interdimensional_portal",
            "time_machine", "unicorn", "dragon_egg", "magic_wand",
            "teleporter", "invisibility_cloak", "philosopher_stone"
        ]
        
        for resource_type in arbitrary_resources:
            rbac_service.ownership_registry.register(resource_type, provider)
            
        user = User(id=42, role="user")
        
        # Test can_access with arbitrary resources
        for resource_type in arbitrary_resources:
            owned_resource = ResourceRef(resource_type, 42)
            not_owned_resource = ResourceRef(resource_type, 99)
            
            # Should allow access to owned resource
            result1 = await rbac_service.can_access(user, owned_resource, "use")
            assert result1 is True, f"Failed for owned {resource_type}"
            
            # Should deny access to non-owned resource
            result2 = await rbac_service.can_access(user, not_owned_resource, "use")
            assert result2 is False, f"Failed for non-owned {resource_type}"

    @pytest.mark.asyncio
    async def test_rbac_service_without_hardcoded_assumptions(self, rbac_service):
        """Test that RBACService makes no hardcoded assumptions about resource types."""
        # Mock permission check to always return True
        rbac_service.check_permission = AsyncMock(return_value=True)
        
        # Create provider that works with any resource type
        class UniversalProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                # No hardcoded resource type checks - purely generic logic
                if isinstance(resource_id, str):
                    return user.role in resource_id
                elif isinstance(resource_id, int):
                    return resource_id % 10 == user.id % 10
                elif isinstance(resource_id, dict):
                    return resource_id.get("accessible_by") == user.role
                else:
                    return False
                    
        rbac_service.ownership_registry.register("*", UniversalProvider())
        
        # Test users with different roles
        admin = User(id=1, role="admin")
        user = User(id=7, role="user")
        guest = User(id=3, role="guest")
        
        # Test with various resource types and IDs
        test_cases = [
            # String IDs containing role names
            ("any_type", "admin_resource", admin, True),
            ("any_type", "admin_resource", user, False),
            ("another_type", "user_data", user, True),
            ("another_type", "user_data", guest, False),
            
            # Integer IDs with modulo logic
            ("numeric_type", 11, admin, True),   # 11 % 10 == 1, admin.id % 10 == 1
            ("numeric_type", 17, user, True),    # 17 % 10 == 7, user.id % 10 == 7
            ("numeric_type", 13, guest, True),   # 13 % 10 == 3, guest.id % 10 == 3
            ("numeric_type", 15, admin, False),  # 15 % 10 == 5, admin.id % 10 == 1
            
            # Dict IDs with role-based access
            ("dict_type", {"accessible_by": "admin"}, admin, True),
            ("dict_type", {"accessible_by": "admin"}, user, False),
            ("dict_type", {"accessible_by": "user"}, user, True),
            ("dict_type", {"accessible_by": "guest"}, guest, True),
        ]
        
        for resource_type, resource_id, test_user, expected in test_cases:
            resource = ResourceRef(resource_type, resource_id)
            result = await rbac_service.can_access(test_user, resource, "access")
            assert result == expected, f"Failed for {test_user.role} accessing {resource_type}:{resource_id}"


class TestOwnershipSystemCompleteness:
    """Test that ownership system is complete and truly generic."""

    @pytest.mark.asyncio
    async def test_no_business_domain_assumptions(self):
        """Test that ownership system makes no assumptions about business domains."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Test with resource types from completely different domains
        domains = {
            # Gaming
            "weapon": lambda u, rid: u.role == "warrior" and rid < 100,
            "spell": lambda u, rid: u.role == "mage",
            "potion": lambda u, rid: rid == u.id,
            
            # Space exploration
            "spaceship": lambda u, rid: u.role == "captain",
            "planet": lambda u, rid: u.role in ["explorer", "scientist"],
            "alien_artifact": lambda u, rid: u.role == "xenoarchaeologist",
            
            # Cooking
            "recipe": lambda u, rid: u.role == "chef",
            "ingredient": lambda u, rid: True,  # Everyone can access ingredients
            "kitchen_tool": lambda u, rid: u.role in ["chef", "sous_chef"],
            
            # Abstract concepts
            "idea": lambda u, rid: rid % 2 == u.id % 2,
            "dream": lambda u, rid: u.role == "dreamer",
            "memory": lambda u, rid: rid == u.id,
        }
        
        class DomainAgnosticProvider:
            async def check_ownership(self, user, resource_type, resource_id):
                rule = domains.get(resource_type)
                return rule(user, resource_id) if rule else False
                
        provider = DomainAgnosticProvider()
        
        # Register for all domains
        for resource_type in domains.keys():
            registry.register(resource_type, provider)
            
        # Test users with domain-specific roles
        warrior = User(id=1, role="warrior")
        mage = User(id=2, role="mage")
        captain = User(id=3, role="captain")
        chef = User(id=4, role="chef")
        dreamer = User(id=5, role="dreamer")
        
        # Test cross-domain access patterns
        test_cases = [
            # Gaming domain
            (warrior, "weapon", 50, True),      # Warrior can use low-level weapons
            (warrior, "weapon", 150, False),    # Warrior cannot use high-level weapons
            (mage, "weapon", 50, False),        # Mage cannot use weapons
            (mage, "spell", 123, True),         # Mage can use spells
            (warrior, "spell", 123, False),     # Warrior cannot use spells
            
            # Space domain
            (captain, "spaceship", 456, True),  # Captain can pilot spaceships
            (chef, "spaceship", 456, False),    # Chef cannot pilot spaceships
            
            # Cooking domain
            (chef, "recipe", 789, True),        # Chef can access recipes
            (captain, "recipe", 789, False),    # Captain cannot access recipes
            (warrior, "ingredient", 999, True), # Anyone can access ingredients
            (mage, "ingredient", 999, True),    # Anyone can access ingredients
            
            # Abstract domain
            (dreamer, "dream", 111, True),      # Dreamer can access dreams
            (chef, "dream", 111, False),        # Chef cannot access dreams
            (warrior, "memory", 1, True),       # User can access own memories
            (mage, "memory", 1, False),         # User cannot access others' memories
        ]
        
        for user, resource_type, resource_id, expected in test_cases:
            result = await registry.check(user, resource_type, resource_id)
            assert result == expected, f"Failed: {user.role} accessing {resource_type}:{resource_id}"

    def test_ownership_system_extensibility(self):
        """Test that ownership system can be extended without modifying core code."""
        registry = OwnershipRegistry(default_allow=False)
        
        # Demonstrate that new provider types can be added without changing core
        class FutureProvider:
            """A provider for resources that don't exist yet."""
            
            async def check_ownership(self, user, resource_type, resource_id):
                # Future logic that we can't predict now
                return hash(f"{user.id}:{resource_type}:{resource_id}") % 2 == 0
                
        class QuantumProvider:
            """A provider with quantum-inspired logic."""
            
            def __init__(self):
                self.quantum_state = True
                
            async def check_ownership(self, user, resource_type, resource_id):
                # Quantum superposition: result depends on observation
                self.quantum_state = not self.quantum_state
                return self.quantum_state and (resource_id % 3 == user.id % 3)
                
        # These providers can be registered without any core changes
        registry.register("future_resource", FutureProvider())
        registry.register("quantum_resource", QuantumProvider())
        
        # Verify they work
        assert registry.has_provider("future_resource")
        assert registry.has_provider("quantum_resource")
        
        # The system is extensible - new provider types can be added
        # without modifying the core OwnershipRegistry implementation
        assert len(registry._providers) == 2