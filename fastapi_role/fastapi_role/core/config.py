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
from typing import List, Optional, Union

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
    """

    def __init__(self, app_name: str = "fastapi-role", filepath: Optional[Path] = None):
        """Initializes the CasbinConfig with a default RBAC model.
        
        Args:
            app_name: Application name used for hashing directory path. Defaults to "fastapi-role".
            filepath: Custom file path for config files. If None, uses platformdirs with hashed app_name.
        """
        self.app_name = app_name
        self.filepath = filepath if filepath else self._get_default_filepath()
        self.model = casbin.model.Model()
        self.policies: List[Policy] = []
        self.grouping_policies: List[GroupingPolicy] = []
        self._setup_default_model()

    def _setup_default_model(self) -> None:
        """Initializes a standard RBAC model definition.

        Sets up request, policy, role, effect, and matcher definitions
        conforming to a standard RBAC pattern.
        """
        m = self.model
        m.add_def("r", "r", "sub, obj, act")
        m.add_def("p", "p", "sub, obj, act, eft")
        m.add_def("g", "g", "_, _")
        m.add_def("e", "e", "some(where (p.eft == allow)) && !some(where (p.eft == deny))")
        m.add_def("m", "m", "g(r.sub, p.sub) && keyMatch2(r.obj, p.obj) && keyMatch2(r.act, p.act)")

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
        return user_data_path("fastapi-role") / "roles" / app_hash
    
    def _ensure_files_exist(self) -> None:
        """Ensure config directory and default files exist."""
        self.filepath.mkdir(parents=True, exist_ok=True)
        
        model_path = self.get_model_path()
        policy_path = self.get_policy_path()
        
        # Write default model file if missing
        if not model_path.exists():
            model_content = """[request_definition]
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
            model_path.write_text(model_content, encoding="utf-8")
        
        # Write default policy file if missing
        if not policy_path.exists():
            policy_content = """# Default RBAC policies
# Format: p, subject, object, action, effect
# Example: p, admin, *, *, allow
"""
            policy_path.write_text(policy_content, encoding="utf-8")
    
    def get_model_path(self) -> Path:
        """Get path to rbac_model.conf file.
        
        Returns:
            Path: Full path to model configuration file.
        """
        return self.filepath / "rbac_model.conf"
    
    def get_policy_path(self) -> Path:
        """Get path to rbac_policy.csv file.
        
        Returns:
            Path: Full path to policy file.
        """
        return self.filepath / "rbac_policy.csv"

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
