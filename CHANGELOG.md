# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-03

### Added
- Initial release of `fastapi-role` (formerly internal `fastapi-role`).
- Core `RBACService` for Casbin policy enforcement.
- `@require` decorator for declarative endpoint protection.
- Support for both synchronous and asynchronous SQLAlchemy sessions.
- `UserProtocol` for loose coupling with user models.
- Pluggable `Provider` architecture:
    - `SubjectProvider` (customizable user ID extraction).
    - `RoleProvider` (customizable role fetching).
    - `CacheProvider` (customizable permission caching).
    - `OwnershipProvider` (extensible resource ownership logic).
- Zero-config default setup with `platformdirs`.
- Helper utilities for query filtering.

### Changed
- Refactored internal `fastapi-role` code to be generic and reusable.
- Moved from hardcoded Roles enum to dynamic/configurable roles.
- Decoupled from specific business models (User, Customer, etc.).
