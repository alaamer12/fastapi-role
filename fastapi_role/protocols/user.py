from typing import Protocol,runtime_checkable

@runtime_checkable
class UserProtocol(Protocol):
    """Protocol defining the minimal user interface required by fastapi-role."""
    
    id: int | str
    email: str
    role: str

    def has_role(self, role_name: str) -> bool:
        """Check if user has this specific role.
        
        This method is optional - if not present, the library will 
        compare the 'role' attribute against the role_name.
        """
        ...
