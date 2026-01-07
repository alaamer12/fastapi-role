#!/usr/bin/env python3
"""
File-Based Configuration RBAC Example

This example demonstrates the pure general RBAC system with:
- Configuration-driven role and policy definition
- Multiple generic resource types
- Custom ownership providers
- File-based policy storage
- YAML configuration files

Run with: python examples/file_based_rbac_example.py
Then visit: http://localhost:8000/docs
"""

import os
import yaml
import jso