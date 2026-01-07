"""Module for code-first Casbin configuration.

This module provides the CasbinConfig class, which allows the Casbin model
and policies to be defined programmatically, removing the need for external
configuration files like .conf or .csv.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

import casbin  # type: ignore
import casbin.model  # type: ignore
from platformdirs import user_data_path


@dataclass
class Policy:
    """Represents a Casbin permission policy (p).

    Attributes:
        sub (str): The subject (role or user).
        obj (str): The object (resource).
        act (str): The action (read, write, etc.).
        eft (str): The effect (allow, deny). Defaults to "allow".
    """

    sub: str
    obj: str
    act: str
    eft: str = "allow"

    def to_list(self) -> List[str]:
        """Converts the policy to a list of strings for Casbin.

        Returns:
            List[str]: The policy representation as [sub, obj, act, eft].
        """
        return [self.sub, self.obj, self.act, self.eft]


@dataclass
class GroupingPolicy:
    """Represents a Casbin grouping policy (g) for role inheritance.

    Attributes:
        child (str): The role or user inheriting permissions.
        parent (str): The role providing permissions.
        domain (Optional[str]): The optional domain context.
    """

    child: str
    parent: str
    domain: Optional[str] = None

    def to_list(self) -> List[str]:
        """Converts the grouping policy to a list of strings for Casbin.

        Returns:
            List[str]: The policy representation as [child, parent] or [child, parent, domain].
        """
        if self.domain:
            return [self.child, self.parent, self.domain]
        return [self.child, self.parent]


class CasbinConfig:
    """Single source of truth for Casbin RBAC configuration.

    Allows programmatic definition of the Casbin model and policies,
    eliminating the need for external configuration files.

    Attributes:
        model (casbin.model.Model): The Casbin model definition.
        policies (List[Policy]): List of permission policies.
        grouping_policies (List[GroupingPolicy]): List of role inheritance policies.
        superadmin_role (Optional[str]): The role name that bypasses all access checks.
    """

    def __init__(
        self, 
        app_name: str = "rbac-app", 
        filepath: Optional[Path] = None,
        superadmin_role: Optional[str] = None,
        model_content: Optional[str] = None,
        model_definitions: Optional[Dict[str, Dict[str, str]]] = None,
        base_directory: Optional[str] = None,
        model_filename: str = "rbac_model.conf",
        policy_filename: str = "rbac_policy.csv"
    ):
        """Initializes the CasbinConfig with configurable RBAC model.
        
        Args:
            app_name: Application name used for hashing directory path. Defaults to "rbac-app".
            filepath: Custom file path for config files. If None, uses platformdirs with hashed app_name.
            superadmin_role: Optional role name that bypasses all access checks. If None, no superadmin bypass.
            model_content: Optional custom model content as string. If None, uses default or model_definitions.
            model_definitions: Optional custom model definitions dict. If None, uses default RBAC model.
            base_directory: Optional base directory name for platformdirs. Defaults to app_name.
            model_filename: Filename for model configuration. Defaults to "rbac_model.conf".
            policy_filename: Filename for policy file. Defaults to "rbac_policy.csv".
        """
        self.app_name = app_name
        self.base_directory = base_directory or app_name
        self.model_filename = model_filename
        self.policy_filename = policy_filename
        self.filepath = filepath if filepath else self._get_default_filepath()
        self.superadmin_role = superadmin_role
        self.model = casbin.model.Model()
        self.policies: List[Policy] = []
        self.grouping_policies: List[GroupingPolicy] = []
        
        # Setup model based on provided configuration
        if model_content:
            self._setup_model_from_content(model_content)
        elif model_definitions:
            self._setup_model_from_definitions(model_definitions)
        else:
            self._setup_default_model()

    def _setup_default_model(self) -> None:
        """Initializes a standard RBAC model definition.

        Sets up request, policy, role, effect, and matcher definitions
        conforming to a standard RBAC pattern.
        """
        default_definitions = {
            "r": {"r": "sub, obj, act"},
            "p": {"p": "sub, obj, act, eft"},
            "g": {"g": "_, _"},
            "e": {"e": "some(where (p.eft == allow)) && !some(where (p.eft == deny))"},
            "m": {"m": "g(r.sub, p.sub) && keyMatch2(r.obj, p.obj) && keyMatch2(r.act, p.act)"}
        }
        self._setup_model_from_definitions(default_definitions)

    def _setup_model_from_definitions(self, definitions: Dict[str, Dict[str, str]]) -> None:
        """Setup model from definitions dictionary.
        
        Args:
            definitions: Dictionary of section -> {key: value} mappings
        """
        for section, section_defs in definitions.items():
            for key, value in section_defs.items():
                self.model.add_def(section, key, value)

    def _setup_model_from_content(self, content: str) -> None:
        """Setup model from raw content string.
        
        Args:
            content: Raw model content in Casbin format
        """
        # Parse the content and add definitions
        lines = content.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('[') and line.endswith(']'):
                # Extract section name (e.g., "request_definition" -> "r")
                section_name = line[1:-1]
                if section_name == "request_definition":
                    current_section = "r"
                elif section_name == "policy_definition":
                    current_section = "p"
                elif section_name == "role_definition":
                    current_section = "g"
                elif section_name == "policy_effect":
                    current_section = "e"
                elif section_name == "matchers":
                    current_section = "m"
                else:
                    # Use first character for unknown sections
                    current_section = section_name[0] if section_name else None
                continue
                
            if current_section and '=' in line:
                key, value = line.split('=', 1)
                self.model.add_def(current_section, key.strip(), value.strip())

    def add_policy(
        self, subject: Union[str, Enum], resource: str, action: str, effect: str = "allow"
    ) -> None:
        """Adds a permission policy (p).

        Args:
            subject (Union[str, Enum]): The role or user.
            resource (str): The resource being accessed.
            action (str): The action being performed.
            effect (str): Either 'allow' or 'deny'. Defaults to 'allow'.
        """
        sub_str = subject.value if isinstance(subject, Enum) else subject
        self.policies.append(Policy(sub_str, resource, action, effect))

    def add_role_inheritance(
        self, child_role: Union[str, Enum], parent_role: Union[str, Enum]
    ) -> None:
        """Adds a role inheritance policy (g).

        Args:
            child_role (Union[str, Enum]): The role inheriting permissions.
            parent_role (Union[str, Enum]): The role granting permissions.
        """
        child_str = child_role.value if isinstance(child_role, Enum) else child_role
        parent_str = parent_role.value if isinstance(parent_role, Enum) else parent_role
        self.grouping_policies.append(GroupingPolicy(child_str, parent_str))

    def _get_default_filepath(self) -> Path:
        """Generate default filepath using platformdirs and app_name hash.
        
        Returns:
            Path: Directory path for config files based on hashed app_name.
        """
        app_hash = hashlib.md5(self.app_name.encode()).hexdigest()
        return user_data_path(self.base_directory) / "roles" / app_hash
    
    def _ensure_files_exist(self) -> None:
        """Ensure config directory and default files exist."""
        self.filepath.mkdir(parents=True, exist_ok=True)
        
        model_path = self.get_model_path()
        policy_path = self.get_policy_path()
        
        # Write default model file if missing
        if not model_path.exists():
            model_content = self._get_default_model_content()
            model_path.write_text(model_content, encoding="utf-8")
        
        # Write default policy file if missing
        if not policy_path.exists():
            policy_content = self._get_default_policy_content()
            policy_path.write_text(policy_content, encoding="utf-8")

    def _get_default_model_content(self) -> str:
        """Get default model content.
        
        Returns:
            str: Default model configuration content
        """
        return """[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act, eft

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow)) && !some(where (p.eft == deny))

[matchers]
m = g(r.sub, p.sub) && keyMatch2(r.obj, p.obj) && keyMatch2(r.act, p.act)
"""

    def _get_default_policy_content(self) -> str:
        """Get default policy content.
        
        Returns:
            str: Default policy file content
        """
        return """# Default RBAC policies
# Format: p, subject, object, action, effect
# Example: p, admin, *, *, allow
"""
    
    def get_model_path(self) -> Path:
        """Get path to model configuration file.
        
        Returns:
            Path: Full path to model configuration file.
        """
        return self.filepath / self.model_filename
    
    def get_policy_path(self) -> Path:
        """Get path to policy file.
        
        Returns:
            Path: Full path to policy file.
        """
        return self.filepath / self.policy_filename

    def get_casbin_enforcer(self) -> casbin.Enforcer:
        """Constructs and returns a fully initialized Casbin Enforcer.

        Returns:
            casbin.Enforcer: The initialized enforcer ready for access checks.
        """
        # Initialize Enforcer with the configured model
        enforcer = casbin.Enforcer(self.model)

        # Load policies into the enforcer memory
        for p in self.policies:
            enforcer.add_policy(*p.to_list())

        for g in self.grouping_policies:
            enforcer.add_grouping_policy(*g.to_list())

        return enforcer
