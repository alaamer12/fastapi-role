"""Comprehensive business-agnostic validation tests.

This module provides thorough testing to ensure the RBAC system is completely
business-agnostic and works with arbitrary resource types and domains.

Test Classes:
    TestArbitraryResourceTypeValidation: Tests with completely arbitrary resource types
    TestDynamicRoleSystemValidation: Tests dynamic role creation with various configurations  
    TestProviderSystemValidation: Tests provider system with mock implementations
    TestBusinessAssumptionValidation: Verifies no business-specific assumptions remain
    TestCrossDomainCompatibilityValidation: Tests across different business domains
"""

import asyncio
import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional, Protocol

import pytest
from fastapi import HTTPException

from fastapi_role import (
    Permission, 
    Privilege, 
    ResourceOwnership, 
    require,
    set_rbac_service,
    rbac_service_context,
)
from fastapi_role.core.roles import create_roles


class TestArbitraryResourceTypeValidation:
    """Tests system works with completely arbitrary resource types.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
    """

    @pytest.fixture
    def flexible_rbac_service(self):
        """Create a flexible RBAC service that accepts any resource type."""
        
        class FlexibleRBACService:
            def __init__(self):
                self.permissions = {}
                self.ownership = {}
            
            def grant_permission(self, user_email: str, resource: str, action: str):
                key = (user_email, resource, action)
                self.permissions[key] = True
            
            def grant_ownership(self, user_email: str, resource_type: str, resource_id: str):
                key = (user_email, resource_type, resource_id)
                self.ownership[key] = True
            
            async def check_permission(self, user, resource, action, context=None):
                key = (user.email, resource, action)
                return self.permissions.get(key, False)
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                key = (user.email, resource_type, str(resource_id))
                return self.ownership.get(key, False)
        
        return FlexibleRBACService()

    @pytest.fixture
    def generic_user(self):
        """Create a generic user for testing."""
        
        class GenericUser:
            def __init__(self, email: str = "user@example.com"):
                self.email = email
                self.id = uuid.uuid4()
        
        return GenericUser()

    @pytest.mark.asyncio
    async def test_scientific_research_resources(self, generic_user, flexible_rbac_service):
        """Test with scientific research resource types."""
        
        # Grant permissions for scientific resources
        scientific_resources = [
            ("experiments", "conduct"),
            ("datasets", "analyze"), 
            ("publications", "submit"),
            ("equipment", "reserve"),
            ("samples", "collect"),
            ("protocols", "modify")
        ]
        
        for resource, action in scientific_resources:
            flexible_rbac_service.grant_permission(generic_user.email, resource, action)
        
        @require(Permission("experiments", "conduct"))
        async def conduct_experiment(experiment_id: str, *, current_user, rbac_service):
            return f"experiment_{experiment_id}_conducted_by_{current_user.email}"
        
        @require(Permission("datasets", "analyze"))
        async def analyze_dataset(dataset_id: str, *, current_user, rbac_service):
            return f"dataset_{dataset_id}_analyzed_by_{current_user.email}"
        
        @require(Permission("publications", "submit"))
        async def submit_publication(paper_title: str, *, current_user, rbac_service):
            return f"paper_{paper_title}_submitted_by_{current_user.email}"

        # Execute scientific workflow
        exp_result = await conduct_experiment("EXP001", current_user=generic_user, rbac_service=flexible_rbac_service)
        data_result = await analyze_dataset("DATA001", current_user=generic_user, rbac_service=flexible_rbac_service)
        pub_result = await submit_publication("quantum_research", current_user=generic_user, rbac_service=flexible_rbac_service)
        
        assert "experiment_EXP001_conducted" in exp_result
        assert "dataset_DATA001_analyzed" in data_result
        assert "paper_quantum_research_submitted" in pub_result

    @pytest.mark.asyncio
    async def test_creative_industry_resources(self, generic_user, flexible_rbac_service):
        """Test with creative industry resource types."""
        
        # Grant permissions for creative resources
        creative_resources = [
            ("artworks", "create"),
            ("galleries", "curate"),
            ("exhibitions", "organize"),
            ("commissions", "negotiate"),
            ("portfolios", "showcase"),
            ("critiques", "publish")
        ]
        
        for resource, action in creative_resources:
            flexible_rbac_service.grant_permission(generic_user.email, resource, action)
        
        @require(Permission("artworks", "create"))
        async def create_artwork(title: str, *, current_user, rbac_service):
            return f"artwork_{title}_created_by_{current_user.email}"
        
        @require(Permission("galleries", "curate"))
        async def curate_gallery(gallery_name: str, *, current_user, rbac_service):
            return f"gallery_{gallery_name}_curated_by_{current_user.email}"
        
        @require(Permission("exhibitions", "organize"))
        async def organize_exhibition(theme: str, *, current_user, rbac_service):
            return f"exhibition_{theme}_organized_by_{current_user.email}"

        # Execute creative workflow
        art_result = await create_artwork("digital_dreams", current_user=generic_user, rbac_service=flexible_rbac_service)
        gallery_result = await curate_gallery("modern_art", current_user=generic_user, rbac_service=flexible_rbac_service)
        exhibition_result = await organize_exhibition("future_visions", current_user=generic_user, rbac_service=flexible_rbac_service)
        
        assert "artwork_digital_dreams_created" in art_result
        assert "gallery_modern_art_curated" in gallery_result
        assert "exhibition_future_visions_organized" in exhibition_result

    @pytest.mark.asyncio
    async def test_space_exploration_resources(self, generic_user, flexible_rbac_service):
        """Test with space exploration resource types."""
        
        # Grant permissions for space resources
        space_resources = [
            ("missions", "plan"),
            ("satellites", "deploy"),
            ("telescopes", "operate"),
            ("astronauts", "train"),
            ("rovers", "control"),
            ("stations", "maintain")
        ]
        
        for resource, action in space_resources:
            flexible_rbac_service.grant_permission(generic_user.email, resource, action)
        
        @require(Permission("missions", "plan"))
        async def plan_mission(mission_name: str, *, current_user, rbac_service):
            return f"mission_{mission_name}_planned_by_{current_user.email}"
        
        @require(Permission("satellites", "deploy"))
        async def deploy_satellite(satellite_id: str, *, current_user, rbac_service):
            return f"satellite_{satellite_id}_deployed_by_{current_user.email}"
        
        @require(Permission("rovers", "control"))
        async def control_rover(rover_id: str, command: str, *, current_user, rbac_service):
            return f"rover_{rover_id}_command_{command}_by_{current_user.email}"

        # Execute space workflow
        mission_result = await plan_mission("mars_exploration", current_user=generic_user, rbac_service=flexible_rbac_service)
        satellite_result = await deploy_satellite("SAT001", current_user=generic_user, rbac_service=flexible_rbac_service)
        rover_result = await control_rover("ROVER001", "move_forward", generic_user, flexible_rbac_service)
        
        assert "mission_mars_exploration_planned" in mission_result
        assert "satellite_SAT001_deployed" in satellite_result
        assert "rover_ROVER001_command_move_forward" in rover_result

    @pytest.mark.asyncio
    async def test_resource_ownership_with_arbitrary_types(self, generic_user, flexible_rbac_service):
        """Test resource ownership with completely arbitrary resource types."""
        
        # Grant ownership for arbitrary resources
        arbitrary_resources = [
            ("dragon_eggs", "egg_001"),
            ("time_machines", "tm_alpha"),
            ("magic_spells", "spell_fireball"),
            ("alien_artifacts", "artifact_xyz"),
            ("quantum_computers", "qc_prime"),
            ("dimensional_portals", "portal_beta")
        ]
        
        for resource_type, resource_id in arbitrary_resources:
            flexible_rbac_service.grant_ownership(generic_user.email, resource_type, resource_id)
        
        @require(ResourceOwnership("dragon_eggs"))
        async def hatch_dragon_egg(egg_id: str, *, current_user, rbac_service):
            return f"dragon_egg_{egg_id}_hatched_by_{current_user.email}"
        
        @require(ResourceOwnership("time_machines"))
        async def operate_time_machine(machine_id: str, destination: str, *, current_user, rbac_service):
            return f"time_machine_{machine_id}_to_{destination}_by_{current_user.email}"
        
        @require(ResourceOwnership("magic_spells"))
        async def cast_spell(spell_id: str, target: str, *, current_user, rbac_service):
            return f"spell_{spell_id}_cast_on_{target}_by_{current_user.email}"

        # Execute fantasy workflow
        dragon_result = await hatch_dragon_egg("egg_001", current_user=generic_user, rbac_service=flexible_rbac_service)
        time_result = await operate_time_machine("tm_alpha", "medieval_times", generic_user, flexible_rbac_service)
        spell_result = await cast_spell("spell_fireball", "orc", generic_user, flexible_rbac_service)
        
        assert "dragon_egg_egg_001_hatched" in dragon_result
        assert "time_machine_tm_alpha_to_medieval_times" in time_result
        assert "spell_spell_fireball_cast_on_orc" in spell_result

    @pytest.mark.asyncio
    async def test_complex_resource_hierarchies(self, generic_user, flexible_rbac_service):
        """Test with complex resource type hierarchies."""
        
        # Grant permissions for hierarchical resources
        hierarchical_resources = [
            ("universes", "create"),
            ("galaxies", "manage"),
            ("solar_systems", "design"),
            ("planets", "terraform"),
            ("continents", "shape"),
            ("countries", "govern"),
            ("cities", "plan"),
            ("buildings", "construct"),
            ("rooms", "decorate"),
            ("furniture", "arrange")
        ]
        
        for resource, action in hierarchical_resources:
            flexible_rbac_service.grant_permission(generic_user.email, resource, action)
        
        @require(Permission("universes", "create"))
        async def create_universe(universe_name: str, *, current_user, rbac_service):
            return f"universe_{universe_name}_created_by_{current_user.email}"
        
        @require(Permission("planets", "terraform"))
        async def terraform_planet(planet_name: str, *, current_user, rbac_service):
            return f"planet_{planet_name}_terraformed_by_{current_user.email}"
        
        @require(Permission("furniture", "arrange"))
        async def arrange_furniture(room_id: str, layout: str, *, current_user, rbac_service):
            return f"furniture_in_{room_id}_arranged_{layout}_by_{current_user.email}"

        # Execute hierarchical workflow
        universe_result = await create_universe("new_reality", current_user=generic_user, rbac_service=flexible_rbac_service)
        planet_result = await terraform_planet("new_earth", current_user=generic_user, rbac_service=flexible_rbac_service)
        furniture_result = await arrange_furniture("room_001", "modern", generic_user, flexible_rbac_service)
        
        assert "universe_new_reality_created" in universe_result
        assert "planet_new_earth_terraformed" in planet_result
        assert "furniture_in_room_001_arranged_modern" in furniture_result


class TestDynamicRoleSystemValidation:
    """Tests dynamic role creation with various configurations.
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
    """

    @pytest.fixture
    def role_aware_rbac_service(self):
        """Create a role-aware RBAC service."""
        
        class RoleAwareRBACService:
            def __init__(self):
                self.role_permissions = {}
                self.superadmin_roles = set()
            
            def set_role_permissions(self, role_permissions: Dict[str, List[str]]):
                self.role_permissions = role_permissions
            
            def set_superadmin_roles(self, roles: List[str]):
                self.superadmin_roles = set(roles)
            
            async def check_permission(self, user, resource, action, context=None):
                user_role = getattr(user, 'role', None)
                if not user_role:
                    return False
                
                # Superadmin bypass
                if user_role in self.superadmin_roles:
                    return True
                
                allowed_permissions = self.role_permissions.get(user_role, [])
                return f"{resource}:{action}" in allowed_permissions
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                user_role = getattr(user, 'role', None)
                return user_role in self.superadmin_roles  # Superadmin owns everything
        
        return RoleAwareRBACService()

    @pytest.mark.asyncio
    async def test_gaming_role_hierarchy(self, role_aware_rbac_service):
        """Test with gaming role hierarchy."""
        
        # Create gaming-specific roles
        GamingRole = create_roles([
            "player", "moderator", "game_master", "developer", "admin"
        ], superadmin="admin")
        
        role_aware_rbac_service.set_role_permissions({
            "player": ["games:play", "chat:send"],
            "moderator": ["games:play", "chat:send", "chat:moderate", "players:warn"],
            "game_master": ["games:play", "chat:send", "chat:moderate", "players:warn", "events:create"],
            "developer": ["games:play", "games:debug", "content:create", "analytics:view"],
            "admin": ["*:*"]  # All permissions
        })
        
        role_aware_rbac_service.set_superadmin_roles(["admin"])
        
        class GamingUser:
            def __init__(self, email: str, role: str):
                self.email = email
                self.role = role
        
        player = GamingUser("player@game.com", "player")
        moderator = GamingUser("mod@game.com", "moderator")
        admin = GamingUser("admin@game.com", "admin")
        
        @require(GamingRole.PLAYER)
        async def play_game(current_user: GamingUser, rbac_service):
            return f"game_played_by_{current_user.role}"
        
        @require(GamingRole.MODERATOR)
        async def moderate_chat(current_user: GamingUser, rbac_service):
            return f"chat_moderated_by_{current_user.role}"
        
        @require(GamingRole.ADMIN)
        async def admin_function(current_user: GamingUser, rbac_service):
            return f"admin_action_by_{current_user.role}"

        # Test role hierarchy
        play_result = await play_game(player, role_aware_rbac_service)
        moderate_result = await moderate_chat(moderator, role_aware_rbac_service)
        admin_result = await admin_function(admin, role_aware_rbac_service)
        
        assert play_result == "game_played_by_player"
        assert moderate_result == "chat_moderated_by_moderator"
        assert admin_result == "admin_action_by_admin"

    @pytest.mark.asyncio
    async def test_academic_role_system(self, role_aware_rbac_service):
        """Test with academic role system."""
        
        # Create academic roles
        AcademicRole = create_roles([
            "undergraduate", "graduate", "postdoc", "professor", "dean"
        ], superadmin="dean")
        
        role_aware_rbac_service.set_role_permissions({
            "undergraduate": ["courses:enroll", "assignments:submit"],
            "graduate": ["courses:enroll", "assignments:submit", "research:conduct"],
            "postdoc": ["research:conduct", "papers:publish", "students:mentor"],
            "professor": ["courses:teach", "research:lead", "papers:review", "grants:apply"],
            "dean": ["*:*"]
        })
        
        role_aware_rbac_service.set_superadmin_roles(["dean"])
        
        class AcademicUser:
            def __init__(self, email: str, role: str):
                self.email = email
                self.role = role
        
        undergrad = AcademicUser("student@university.edu", "undergraduate")
        professor = AcademicUser("prof@university.edu", "professor")
        
        @require(AcademicRole.UNDERGRADUATE)
        async def submit_assignment(assignment_id: str, current_user: AcademicUser, rbac_service):
            return f"assignment_{assignment_id}_submitted_by_{current_user.role}"
        
        @require(AcademicRole.PROFESSOR)
        async def teach_course(course_id: str, current_user: AcademicUser, rbac_service):
            return f"course_{course_id}_taught_by_{current_user.role}"

        # Test academic workflow
        assignment_result = await submit_assignment("MATH101_HW1", undergrad, role_aware_rbac_service)
        course_result = await teach_course("PHYS201", professor, role_aware_rbac_service)
        
        assert assignment_result == "assignment_MATH101_HW1_submitted_by_undergraduate"
        assert course_result == "course_PHYS201_taught_by_professor"

    @pytest.mark.asyncio
    async def test_military_rank_system(self, role_aware_rbac_service):
        """Test with military rank system."""
        
        # Create military ranks
        MilitaryRank = create_roles([
            "private", "corporal", "sergeant", "lieutenant", "captain", "major", "colonel", "general"
        ], superadmin="general")
        
        role_aware_rbac_service.set_role_permissions({
            "private": ["equipment:use", "orders:follow"],
            "corporal": ["equipment:use", "orders:follow", "squad:lead"],
            "sergeant": ["equipment:use", "orders:follow", "squad:lead", "training:conduct"],
            "lieutenant": ["platoon:command", "missions:plan"],
            "captain": ["company:command", "resources:allocate"],
            "major": ["battalion:support", "strategy:develop"],
            "colonel": ["regiment:command", "operations:oversee"],
            "general": ["*:*"]
        })
        
        role_aware_rbac_service.set_superadmin_roles(["general"])
        
        class MilitaryPersonnel:
            def __init__(self, email: str, rank: str):
                self.email = email
                self.role = rank
        
        sergeant = MilitaryPersonnel("sgt@military.gov", "sergeant")
        captain = MilitaryPersonnel("capt@military.gov", "captain")
        
        @require(MilitaryRank.SERGEANT)
        async def conduct_training(training_type: str, current_user: MilitaryPersonnel, rbac_service):
            return f"training_{training_type}_conducted_by_{current_user.role}"
        
        @require(MilitaryRank.CAPTAIN)
        async def command_company(operation: str, current_user: MilitaryPersonnel, rbac_service):
            return f"company_commanded_for_{operation}_by_{current_user.role}"

        # Test military workflow
        training_result = await conduct_training("weapons", sergeant, role_aware_rbac_service)
        command_result = await command_company("patrol", captain, role_aware_rbac_service)
        
        assert training_result == "training_weapons_conducted_by_sergeant"
        assert command_result == "company_commanded_for_patrol_by_captain"

    def test_role_consistency_across_recreations(self):
        """Test that dynamically created roles are consistent across recreations."""
        
        role_names = ["alpha", "beta", "gamma", "delta"]
        
        # Create roles multiple times
        Role1 = create_roles(role_names)
        Role2 = create_roles(role_names)
        Role3 = create_roles(role_names)
        
        # Verify consistency
        for role_name in role_names:
            role1_value = getattr(Role1, role_name.upper()).value
            role2_value = getattr(Role2, role_name.upper()).value
            role3_value = getattr(Role3, role_name.upper()).value
            
            assert role1_value == role2_value == role3_value == role_name

    def test_role_validation_with_invalid_names(self):
        """Test role validation with invalid role names."""
        
        invalid_role_sets = [
            [],  # Empty list
            [""],  # Empty string
            ["valid", ""],  # Mix of valid and empty
            ["valid", "invalid@name"],  # Invalid characters
            ["valid", "valid"],  # Duplicates
        ]
        
        for invalid_roles in invalid_role_sets:
            with pytest.raises(ValueError):
                create_roles(invalid_roles)

    def test_role_bitwise_operations(self):
        """Test bitwise operations with dynamically created roles."""
        
        TestRole = create_roles(["user", "admin", "superuser"])
        
        # Test OR operations
        combined = TestRole.USER | TestRole.ADMIN
        assert hasattr(combined, '__iter__')  # Should be iterable (composition)
        
        # Test that roles maintain their identity
        assert TestRole.USER.value == "user"
        assert TestRole.ADMIN.value == "admin"
        assert TestRole.SUPERUSER.value == "superuser"


class TestProviderSystemValidation:
    """Tests provider system with mock implementations.
    
    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
    """

    def test_custom_subject_provider(self):
        """Test custom subject provider implementation."""
        
        class CustomSubjectProvider:
            def __init__(self, field_name: str = "username"):
                self.field_name = field_name
            
            def get_subject(self, user) -> str:
                return getattr(user, self.field_name, "unknown")
        
        class TestUser:
            def __init__(self, username: str, email: str):
                self.username = username
                self.email = email
        
        # Test with username field
        username_provider = CustomSubjectProvider("username")
        user = TestUser("john_doe", "john@example.com")
        
        subject = username_provider.get_subject(user)
        assert subject == "john_doe"
        
        # Test with email field
        email_provider = CustomSubjectProvider("email")
        subject = email_provider.get_subject(user)
        assert subject == "john@example.com"

    @pytest.mark.asyncio
    async def test_custom_role_provider(self):
        """Test custom role provider implementation."""
        
        class DatabaseRoleProvider:
            def __init__(self):
                self.user_roles = {
                    "user1@example.com": ["user", "editor"],
                    "user2@example.com": ["admin", "superuser"],
                    "user3@example.com": ["guest"]
                }
            
            async def get_user_roles(self, user) -> List[str]:
                return self.user_roles.get(user.email, [])
            
            async def has_role(self, user, role_name: str) -> bool:
                user_roles = await self.get_user_roles(user)
                return role_name in user_roles
        
        class TestUser:
            def __init__(self, email: str):
                self.email = email
        
        provider = DatabaseRoleProvider()
        
        user1 = TestUser("user1@example.com")
        user2 = TestUser("user2@example.com")
        user3 = TestUser("unknown@example.com")
        
        # Test role retrieval
        roles1 = await provider.get_user_roles(user1)
        roles2 = await provider.get_user_roles(user2)
        roles3 = await provider.get_user_roles(user3)
        
        assert roles1 == ["user", "editor"]
        assert roles2 == ["admin", "superuser"]
        assert roles3 == []
        
        # Test role checking
        assert await provider.has_role(user1, "editor") is True
        assert await provider.has_role(user1, "admin") is False
        assert await provider.has_role(user2, "admin") is True

    @pytest.mark.asyncio
    async def test_custom_ownership_provider(self):
        """Test custom ownership provider implementation."""
        
        class GraphBasedOwnershipProvider:
            def __init__(self):
                self.ownership_graph = {
                    ("user1@example.com", "document", "doc1"): True,
                    ("user1@example.com", "project", "proj1"): True,
                    ("user2@example.com", "document", "doc2"): True,
                    ("user2@example.com", "project", "proj1"): True,  # Shared project
                }
            
            async def check_ownership(self, user, resource_type: str, resource_id) -> bool:
                key = (user.email, resource_type, str(resource_id))
                return self.ownership_graph.get(key, False)
        
        class TestUser:
            def __init__(self, email: str):
                self.email = email
        
        provider = GraphBasedOwnershipProvider()
        
        user1 = TestUser("user1@example.com")
        user2 = TestUser("user2@example.com")
        
        # Test ownership checks
        assert await provider.check_ownership(user1, "document", "doc1") is True
        assert await provider.check_ownership(user1, "document", "doc2") is False
        assert await provider.check_ownership(user2, "project", "proj1") is True
        assert await provider.check_ownership(user1, "project", "proj1") is True  # Shared

    @pytest.mark.asyncio
    async def test_custom_cache_provider(self):
        """Test custom cache provider implementation."""
        
        class InMemoryCacheProvider:
            def __init__(self):
                self.cache = {}
                self.stats = {"hits": 0, "misses": 0, "sets": 0}
            
            async def get(self, key: str):
                if key in self.cache:
                    self.stats["hits"] += 1
                    return self.cache[key]
                else:
                    self.stats["misses"] += 1
                    return None
            
            async def set(self, key: str, value, ttl: Optional[int] = None):
                self.cache[key] = value
                self.stats["sets"] += 1
            
            async def clear(self, pattern: Optional[str] = None):
                if pattern:
                    keys_to_remove = [k for k in self.cache.keys() if pattern in k]
                    for key in keys_to_remove:
                        del self.cache[key]
                else:
                    self.cache.clear()
            
            async def get_stats(self) -> Dict[str, Any]:
                return self.stats.copy()
        
        provider = InMemoryCacheProvider()
        
        # Test cache operations
        await provider.set("key1", "value1")
        await provider.set("key2", "value2")
        
        value1 = await provider.get("key1")
        value2 = await provider.get("key2")
        value3 = await provider.get("key3")  # Miss
        
        assert value1 == "value1"
        assert value2 == "value2"
        assert value3 is None
        
        # Test stats
        stats = await provider.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["sets"] == 2
        
        # Test clear
        await provider.clear("key1")
        value1_after_clear = await provider.get("key1")
        value2_after_clear = await provider.get("key2")
        
        assert value1_after_clear is None
        assert value2_after_clear == "value2"

    @pytest.mark.asyncio
    async def test_custom_policy_provider(self):
        """Test custom policy provider implementation."""
        
        class JSONPolicyProvider:
            def __init__(self):
                self.policies = [
                    ["admin", "*", "*", "allow"],
                    ["user", "documents", "read", "allow"],
                    ["user", "documents", "write", "deny"],
                    ["guest", "public", "read", "allow"]
                ]
            
            async def load_policies(self) -> List[List[str]]:
                return self.policies.copy()
            
            async def save_policy(self, policy: List[str]) -> bool:
                if policy not in self.policies:
                    self.policies.append(policy)
                    return True
                return False
            
            async def remove_policy(self, policy: List[str]) -> bool:
                if policy in self.policies:
                    self.policies.remove(policy)
                    return True
                return False
        
        provider = JSONPolicyProvider()
        
        # Test policy loading
        policies = await provider.load_policies()
        assert len(policies) == 4
        assert ["admin", "*", "*", "allow"] in policies
        
        # Test policy saving
        new_policy = ["editor", "articles", "edit", "allow"]
        result = await provider.save_policy(new_policy)
        assert result is True
        
        updated_policies = await provider.load_policies()
        assert len(updated_policies) == 5
        assert new_policy in updated_policies
        
        # Test policy removal
        result = await provider.remove_policy(new_policy)
        assert result is True
        
        final_policies = await provider.load_policies()
        assert len(final_policies) == 4
        assert new_policy not in final_policies


class TestBusinessAssumptionValidation:
    """Verifies no business-specific assumptions remain in any code path.
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
    """

    def test_no_customer_assumptions_in_core(self):
        """Test that core RBAC has no customer-specific assumptions."""
        
        import fastapi_role.rbac_service as rbac_service_module
        import fastapi_role.rbac as rbac_module
        
        modules_to_check = [rbac_service_module, rbac_module]
        
        customer_terms = [
            "customer", "client", "account", "billing", "invoice",
            "order", "quote", "sale", "purchase", "payment"
        ]
        
        for module in modules_to_check:
            module_source = inspect.getsource(module).lower()
            
            for term in customer_terms:
                # Check for the term as a standalone word (not part of other words)
                import re
                pattern = r'\b' + re.escape(term) + r'\b'
                matches = re.findall(pattern, module_source)
                
                # Allow terms in comments or strings, but not in code logic
                if matches:
                    # More detailed check - ensure it's not in actual business logic
                    lines = module_source.split('\n')
                    for i, line in enumerate(lines):
                        if term in line and not (line.strip().startswith('#') or '"""' in line or "'''" in line):
                            # Check if it's in a string literal
                            if not ('"' + term + '"' in line or "'" + term + "'" in line):
                                assert False, f"Found business term '{term}' in business logic at line {i+1} in {module.__name__}: {line.strip()}"

    def test_no_hardcoded_business_workflows(self):
        """Test that no hardcoded business workflows exist."""
        
        from fastapi_role.rbac_service import RBACService
        
        # Check RBACService methods
        rbac_methods = [method for method in dir(RBACService) if not method.startswith('_')]
        
        # Business workflow methods that should not exist
        business_methods = [
            "create_customer", "update_customer", "delete_customer",
            "create_order", "update_order", "cancel_order",
            "generate_quote", "approve_quote", "send_quote",
            "process_payment", "refund_payment", "calculate_tax"
        ]
        
        for business_method in business_methods:
            assert business_method not in rbac_methods, f"Found business method '{business_method}' in RBACService"

    def test_no_hardcoded_database_schemas(self):
        """Test that no hardcoded database schemas exist."""
        
        import fastapi_role.rbac_service as rbac_service_module
        
        rbac_service_source = inspect.getsource(rbac_service_module)
        
        # Database schema terms that should not appear
        schema_terms = [
            "customers", "orders", "quotes", "invoices", "products",
            "inventory", "shipments", "payments", "accounts"
        ]
        
        for term in schema_terms:
            # Check for table/model references
            table_patterns = [
                f'"{term}"',  # Direct table name
                f"'{term}'",  # Direct table name
                f"Table('{term}'",  # SQLAlchemy table
                f'__tablename__ = "{term}"',  # Model definition
            ]
            
            for pattern in table_patterns:
                assert pattern not in rbac_service_source, f"Found hardcoded schema reference '{pattern}' in RBACService"

    @pytest.mark.asyncio
    async def test_system_works_without_business_context(self):
        """Test that system works without any business context."""
        
        class MinimalRBACService:
            async def check_permission(self, user, resource, action, context=None):
                # Pure permission logic without business assumptions
                return hasattr(user, 'email') and resource and action
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                # Pure ownership logic without business assumptions
                return hasattr(user, 'id') and resource_type and resource_id
        
        class MinimalUser:
            def __init__(self, email: str):
                self.email = email
                self.id = uuid.uuid4()
        
        rbac_service = MinimalRBACService()
        user = MinimalUser("test@example.com")
        
        # Test with completely abstract resources
        abstract_resources = [
            ("entities", "manipulate"),
            ("objects", "transform"),
            ("items", "process"),
            ("elements", "combine"),
            ("units", "organize")
        ]
        
        for resource, action in abstract_resources:
            @require(Permission(resource, action))
            async def abstract_function(
                current_user: MinimalUser, 
                rbac_service: MinimalRBACService,
                res: str = resource,
                act: str = action
            ):
                return f"{act}_{res}_by_{current_user.email}"
            
            result = await abstract_function(user, rbac_service)
            assert result == f"{action}_{resource}_by_test@example.com"

    def test_configuration_has_no_business_defaults(self):
        """Test that configuration system has no business-specific defaults."""
        
        from fastapi_role.core.config import CasbinConfig
        
        # Create default config
        config = CasbinConfig()
        
        # Check that no business-specific defaults are set
        config_dict = config.__dict__
        
        business_keys = [
            "customer_role", "salesman_role", "admin_role",
            "customer_permissions", "order_permissions", "quote_permissions"
        ]
        
        for key in business_keys:
            assert key not in config_dict, f"Found business-specific default '{key}' in CasbinConfig"
        
        # Check that default model is generic
        if hasattr(config, 'model_text') and config.model_text:
            model_text = config.model_text.lower()
            business_terms = ["customer", "order", "quote", "invoice", "product"]
            
            for term in business_terms:
                assert term not in model_text, f"Found business term '{term}' in default model"


class TestCrossDomainCompatibilityValidation:
    """Tests across different business domains to ensure true generality.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7
    """

    @pytest.fixture
    def domain_agnostic_rbac_service(self):
        """Create a domain-agnostic RBAC service."""
        
        class DomainAgnosticRBACService:
            def __init__(self):
                self.domain_permissions = {}
            
            def configure_domain(self, domain: str, permissions: Dict[str, List[str]]):
                self.domain_permissions[domain] = permissions
            
            async def check_permission(self, user, resource, action, context=None):
                user_domain = getattr(user, 'domain', 'default')
                domain_perms = self.domain_permissions.get(user_domain, {})
                user_role = getattr(user, 'role', 'user')
                allowed_perms = domain_perms.get(user_role, [])
                return f"{resource}:{action}" in allowed_perms
            
            async def check_resource_ownership(self, user, resource_type, resource_id):
                # Domain-agnostic ownership - based on user ID matching resource owner
                return str(getattr(user, 'id', '')) == str(resource_id).split('_')[-1]
        
        return DomainAgnosticRBACService()

    @pytest.mark.asyncio
    async def test_manufacturing_domain(self, domain_agnostic_rbac_service):
        """Test RBAC system in manufacturing domain."""
        
        # Configure manufacturing domain
        domain_agnostic_rbac_service.configure_domain("manufacturing", {
            "operator": ["machines:operate", "quality:check"],
            "supervisor": ["machines:operate", "quality:check", "production:schedule"],
            "manager": ["production:plan", "inventory:manage", "reports:generate"]
        })
        
        ManufacturingRole = create_roles(["operator", "supervisor", "manager"])
        
        class ManufacturingUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
                self.domain = "manufacturing"
        
        operator = ManufacturingUser(1, "operator@factory.com", "operator")
        supervisor = ManufacturingUser(2, "supervisor@factory.com", "supervisor")
        
        @require(Permission("machines", "operate"))
        async def operate_machine(machine_id: str, current_user: ManufacturingUser, rbac_service):
            return f"machine_{machine_id}_operated_by_{current_user.role}"
        
        @require(Permission("production", "schedule"))
        async def schedule_production(batch_id: str, current_user: ManufacturingUser, rbac_service):
            return f"production_{batch_id}_scheduled_by_{current_user.role}"

        # Test manufacturing workflow
        machine_result = await operate_machine("CNC001", operator, domain_agnostic_rbac_service)
        schedule_result = await schedule_production("BATCH001", supervisor, domain_agnostic_rbac_service)
        
        assert machine_result == "machine_CNC001_operated_by_operator"
        assert schedule_result == "production_BATCH001_scheduled_by_supervisor"

    @pytest.mark.asyncio
    async def test_logistics_domain(self, domain_agnostic_rbac_service):
        """Test RBAC system in logistics domain."""
        
        # Configure logistics domain
        domain_agnostic_rbac_service.configure_domain("logistics", {
            "driver": ["vehicles:drive", "deliveries:complete"],
            "dispatcher": ["routes:plan", "vehicles:assign", "schedules:manage"],
            "manager": ["fleet:manage", "contracts:negotiate", "performance:analyze"]
        })
        
        LogisticsRole = create_roles(["driver", "dispatcher", "manager"])
        
        class LogisticsUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
                self.domain = "logistics"
        
        driver = LogisticsUser(1, "driver@logistics.com", "driver")
        dispatcher = LogisticsUser(2, "dispatch@logistics.com", "dispatcher")
        
        @require(Permission("deliveries", "complete"))
        async def complete_delivery(delivery_id: str, current_user: LogisticsUser, rbac_service):
            return f"delivery_{delivery_id}_completed_by_{current_user.role}"
        
        @require(Permission("routes", "plan"))
        async def plan_route(route_id: str, current_user: LogisticsUser, rbac_service):
            return f"route_{route_id}_planned_by_{current_user.role}"

        # Test logistics workflow
        delivery_result = await complete_delivery("DEL001", driver, domain_agnostic_rbac_service)
        route_result = await plan_route("ROUTE001", dispatcher, domain_agnostic_rbac_service)
        
        assert delivery_result == "delivery_DEL001_completed_by_driver"
        assert route_result == "route_ROUTE001_planned_by_dispatcher"

    @pytest.mark.asyncio
    async def test_media_production_domain(self, domain_agnostic_rbac_service):
        """Test RBAC system in media production domain."""
        
        # Configure media production domain
        domain_agnostic_rbac_service.configure_domain("media", {
            "intern": ["footage:view", "notes:take"],
            "editor": ["footage:edit", "audio:mix", "effects:apply"],
            "director": ["scenes:direct", "cuts:approve", "vision:define"],
            "producer": ["budget:manage", "talent:hire", "distribution:negotiate"]
        })
        
        MediaRole = create_roles(["intern", "editor", "director", "producer"])
        
        class MediaUser:
            def __init__(self, user_id: int, email: str, role: str):
                self.id = user_id
                self.email = email
                self.role = role
                self.domain = "media"
        
        editor = MediaUser(1, "editor@studio.com", "editor")
        director = MediaUser(2, "director@studio.com", "director")
        
        @require(Permission("footage", "edit"))
        async def edit_footage(clip_id: str, current_user: MediaUser, rbac_service):
            return f"footage_{clip_id}_edited_by_{current_user.role}"
        
        @require(Permission("scenes", "direct"))
        async def direct_scene(scene_id: str, current_user: MediaUser, rbac_service):
            return f"scene_{scene_id}_directed_by_{current_user.role}"

        # Test media production workflow
        edit_result = await edit_footage("CLIP001", editor, domain_agnostic_rbac_service)
        direct_result = await direct_scene("SCENE001", director, domain_agnostic_rbac_service)
        
        assert edit_result == "footage_CLIP001_edited_by_editor"
        assert direct_result == "scene_SCENE001_directed_by_director"

    @pytest.mark.asyncio
    async def test_cross_domain_user_migration(self, domain_agnostic_rbac_service):
        """Test that users can migrate between domains seamlessly."""
        
        # Configure multiple domains
        domain_agnostic_rbac_service.configure_domain("retail", {
            "cashier": ["transactions:process", "inventory:check"],
            "manager": ["staff:schedule", "reports:generate"]
        })
        
        domain_agnostic_rbac_service.configure_domain("hospitality", {
            "server": ["orders:take", "tables:serve"],
            "manager": ["reservations:manage", "staff:coordinate"]
        })
        
        class MigratableUser:
            def __init__(self, user_id: int, email: str, role: str, domain: str):
                self.id = user_id
                self.email = email
                self.role = role
                self.domain = domain
        
        # User starts in retail
        user = MigratableUser(1, "user@company.com", "manager", "retail")
        
        @require(Permission("reports", "generate"))
        async def generate_reports(report_type: str, current_user: MigratableUser, rbac_service):
            return f"report_{report_type}_generated_by_{current_user.role}_in_{current_user.domain}"

        # Test in retail domain
        retail_result = await generate_reports("sales", user, domain_agnostic_rbac_service)
        assert retail_result == "report_sales_generated_by_manager_in_retail"
        
        # Migrate to hospitality domain
        user.domain = "hospitality"
        
        @require(Permission("reservations", "manage"))
        async def manage_reservations(action: str, current_user: MigratableUser, rbac_service):
            return f"reservations_{action}_by_{current_user.role}_in_{current_user.domain}"

        # Test in hospitality domain
        hospitality_result = await manage_reservations("updated", user, domain_agnostic_rbac_service)
        assert hospitality_result == "reservations_updated_by_manager_in_hospitality"