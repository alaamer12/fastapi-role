# fastapi-role

[![PyPI version](https://badge.fury.io/py/fastapi-role.svg)](https://badge.fury.io/py/fastapi-role)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastapi-role.svg)](https://pypi.org/project/fastapi-role/)

**fastapi-role** is a flexible, pluggable Role-Based Access Control library for FastAPI applications, powered by [Casbin](https://casbin.org/). It provides a robust decorator-based permission system, automatic resource ownership validation, and seamless integration with your existing user models and databases.

> 🚀 **Transform your business logic into secure, role-aware operations in minutes.**

## Features

*   **🔒 Decorator-based Security**: Secure endpoints with `@require(roles=["admin"])` or `@require(permissions=["item", "read"])`.
*   **🛠️ Framework Agnostic**: Works with *any* User model via a simple Protocol (duck-typing).
*   **🧩 Pluggable Architecture**: Customize everything - Policy Storage, Role Extraction, Subject Definition, Permissions Caching.
*   **🔄 Sync & Async Support**: Full support for both synchronous and asynchronous SQLAlchemy sessions.
*   **📦 Zero-Config Defaults**: Works out of the box with sensible defaults (file-based default policies).
*   **🧱 Ownership Validation**: Built-in support for resource ownership checks ("can this user edit *this* specific item?").

## Installation

```bash
pip install fastapi-role
```

## Quick Start

```python
from fastapi import FastAPI, Depends
from fastapi_role import RBACService, require
from fastapi_role.core.config import CasbinConfig
from pydantic import BaseModel
from typing import Annotated

# 1. Define your User (must have id, email, role)
class User(BaseModel):
    id: int = 1
    email: str = "alice@admin.com"
    role: str = "admin"

app = FastAPI()

# 2. Configure Service
config = CasbinConfig(app_name="my_app")
# Real apps should inject a DB session here
def get_rbac():
    return RBACService(db=None, config=config)

# 3. Protect Endpoint
@app.get("/secure")
@require(roles=["admin"])
async def secure_data(
    service: Annotated[RBACService, Depends(get_rbac)]
):
    return {"status": "secure access granted"}
```

## Documentation

Full documentation is available in the `docs/` directory:

- [Getting Started](docs/getting-started.md)
- [Configuration Reference](docs/configuration.md)
- [Architecture Overview](docs/architecture.md)

## Examples

Check the `examples/` directory for ready-to-run projects:
- `examples/minimal`: Simple one-file application.
- `examples/database`: SQLAlchemy integration with ownership checks.
- `examples/file_based`: Custom policy file loading.

## License

This project is licensed under the terms of the MIT license.
