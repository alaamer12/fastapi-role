# Repertoire Framework Metadata

> **Updated**: December 27, 2025  
> **Version**: 3.0 - New Level-Based Milestone Structure

This directory contains the complete documentation for Symphony's Repertoire development framework - a systematic approach to building complex software systems through structured milestone decomposition and feature-driven development.

---

## 📋 Framework Overview

The Repertoire framework addresses critical weaknesses in traditional development approaches:

1. **Unclear Requirements** → Solved with level-based requirements.md files
2. **Poor Architecture Documentation** → Solved with design.md ASCII diagrams
3. **Lost Implementation Knowledge** → Solved with incremental notes.md files
4. **Inconsistent Quality** → Solved with BIF evaluation framework

---

## 🏗️ NEW: Level-Based Milestone Structure

### Improved Organization

```
milestones/
├── level0/                    # System-wide architecture
│   ├── requirements.md        # High-level goals and properties
│   ├── design.md             # Main architecture diagram
│   └── notes.md              # Decisions and insights
├── level1/                    # Component breakdown
│   ├── requirements.md        # Component responsibilities
│   ├── design.md             # Component diagrams
│   └── notes.md              # Implementation notes
└── level2/                    # Detailed implementation
    ├── level2_m1/            # Milestone group M1
    │   ├── requirements.md    # M1 specific requirements
    │   ├── design.md         # M1 implementation diagrams
    │   └── notes.md          # M1 decisions
    └── level2_m2/            # Milestone group M2
        └── ...
```

### File Purposes

**requirements.md**:
- What this level is responsible for
- High-level goals and acceptance criteria
- **Correctness Properties**: Formal behavioral guarantees
- Glossary of key terms
- ATDD-compatible requirements

**design.md**:
- Architecture and structure
- **ASCII diagrams** (recommended) or Mermaid
- Component relationships
- Simple and readable designs

**notes.md**:
- Empty by default
- Filled incrementally with decisions, issues, insights
- Implementation discoveries
- Performance observations

---

## 📁 Documentation Structure

### Core Framework Documents

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Development.md](./Development.md)** | Complete framework specification and workflow | All team members |
| **[How To Use.md](./How%20To%20Use.md)** | AI mode system prompts and usage guide | AI operators, developers |
| **[BIF.md](./BIF.md)** | Blind Inspection Framework for quality evaluation | Code reviewers, QA |
| **[Feature Lifecycle.md](./Feature%20Lifecycle.md)** | 7-document lifecycle process | Feature implementers |

### Technical Standards

| Document | Purpose | Location |
|----------|---------|----------|
| **[technical_pattern.md](../practice/technical_pattern.md)** | Technical implementation patterns and standards | `.repertoire/practice/` |

---

## 🎯 Level Meanings

### Level 0: System Architecture
- **The highest-level architecture**
- **One main architecture diagram**
- **Describes the system as a whole**

Example: Symphony AIDE system overview showing Symphony Binary ↔ XI-editor Binary

### Level 1: Component Breakdown
- **Breaks down Level 0 into major components**
- **Multiple diagrams allowed**
- **Component responsibilities and interfaces**

Example: Break down Symphony Binary into Domain Core, Ports, Adapters, The Pit, etc.

### Level 2: Implementation Details
- **Breaks down Level 1 components into specific implementations**
- **One diagram per sub-milestone**
- **Concrete implementation strategies**

Example: Break down each Level 1 component into specific features and implementations

---

## 🔄 Migration Benefits

### From Old Structure
```
.repertoire/milestones/
├── LEVEL0.md              # Monolithic file
├── LEVEL1/LEVEL1.md       # Single large file
└── LEVEL2/LEVEL2_M*.md    # Multiple files
```

### To New Structure
```
milestones/
├── level0/                # Separated concerns
│   ├── requirements.md    # What we're building
│   ├── design.md         # How it's structured
│   └── notes.md          # Why decisions were made
├── level1/               # Component focus
└── level2/               # Implementation focus
```

### Improvements
- **Better Separation of Concerns**: What vs How vs Why
- **Clearer Documentation Purpose**: Each file has specific role
- **Improved Navigation**: Easier to find relevant information
- **Systematic Knowledge Evolution**: Incremental notes capture learning

---

## 🎯 AI Mode System

### Four Specialized AI Modes

1. **CONSTRUCTOR** → Strategic planning and milestone creation
2. **TRANSFORMER** → Feature extraction and specification
3. **IMPLEMENTER** → Code implementation and verification
4. **ANALYZER** → Technical consultation and system analysis

Each mode has specific responsibilities and handoff protocols documented in [How To Use.md](./How%20To%20Use.md).

---

## 📊 Quality Assurance: Enhanced BIF Framework

### Reasoning-Based Evaluation

All BIF evaluations require **reasoning** for every rating:

| Dimension | Rating | **Reasoning Required** |
|-----------|--------|----------------------|
| Feature Completeness | 0-100% | Why this percentage? What's missing? |
| Code Quality | Poor/Basic/Good/Excellent | What specific evidence supports this rating? |
| Documentation | None/Basic/Good/Excellent | What documentation exists and why is it rated this way? |
| Reliability | Low/Medium/High/Enterprise | What error handling exists? What are the risks? |
| Performance | Poor/Acceptable/Good/Excellent | What are the performance characteristics? |
| Integration | Not Compatible/Partial/Full/Enterprise | How well does it integrate? What are limitations? |
| Maintenance | Low/Medium/High/Enterprise | What makes it maintainable or not? |
| Stress Collapse | Prediction with numbers | What analysis led to this prediction? |

### BIF Readiness Levels

- ✅ **Production Ready**: 80%+ features at Full or Enterprise level
- 🟡 **Staging Ready**: 60-79% features at Full or Enterprise level  
- ⚠️ **Development**: 40-59% features at Full or Enterprise level
- ❌ **Not Ready**: <40% features at Full or Enterprise level

---

## 🔧 Technical Implementation Standards

### Technical Pattern Requirements

All implementations must follow patterns defined in `technical_pattern.md`:

#### Code Quality Standards
- **Rust**: Use thiserror for errors, comprehensive rustdoc, property-based testing
- **Testing**: TDD approach (Red → Green → Refactor)
- **Documentation**: Every public API documented with examples
- **Performance**: Benchmarks for all performance-critical code

#### Debugging Standards
- **Loud Smart Duck Debugging**: `[DUCK DEBUGGING]: message` format
- Only active in debug builds (`#[cfg(debug_assertions)]`)
- Easy to search and remove for production

#### Quality Gates
- All acceptance criteria met (✅)
- All tests passing (100%)
- BIF evaluation complete with HIGH priority issues resolved
- Documentation complete and accurate

---

## 📈 Status Tracking System

### Checkbox Status Meanings

- `[ ]` → **Not Started** (idle)
- `[ - ]` → **In Progress** (actively being worked)
- `[ 1 ]` → **Completed** (first attempt successful)
- `[ 2 ]` → **Completed** (reopened once, then completed)
- `[ N ]` → **Completed** (reopened N-1 times)

### Status Propagation Rules

```
Feature Complete → Level 2 Step → Level 1 Section → Level 0 Milestone
F001 [1] → M1.1.1 [1] → M1.1 [1] → M1 [1]
```

---

## 🚀 Getting Started

### For New Projects

1. **Use CONSTRUCTOR mode** to create level-based milestone hierarchy
2. **Use TRANSFORMER mode** to extract features from Level 2 steps
3. **Use IMPLEMENTER mode** to build features with quality assurance

### For Existing Projects

1. **Use ANALYZER mode** to assess current state
2. **Migrate to new structure** using provided migration steps
3. **Apply technical patterns** to existing code
4. **Run BIF evaluation** with enhanced reasoning requirements

---

## 📚 Quick Reference

### Essential Commands

```bash
# Start new project with new structure
"Switch to CONSTRUCTOR mode and help me plan [project description]"

# Convert milestones to features  
"Switch to TRANSFORMER mode and process these milestones"

# Implement features
"Switch to IMPLEMENTER mode and start with F001"

# Analyze existing system
"Switch to ANALYZER mode and review my project"
```

### Key Files to Create

1. **Milestones**: Level-based structure with requirements.md, design.md, notes.md
2. **Features**: 7 lifecycle documents per feature
3. **Technical Standards**: `practice/technical_pattern.md`

### Quality Checklist

- [ ] Level-based milestone structure implemented
- [ ] Requirements include correctness properties
- [ ] Design uses ASCII diagrams
- [ ] Notes capture incremental learning
- [ ] BIF evaluation includes reasoning
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Status tracking accurate

---

## 🔄 Framework Evolution

### Version 3.0 Improvements (December 2025)

1. **Level-Based Milestone Structure** → Better separation of concerns
2. **Requirements with Properties** → Formal correctness guarantees
3. **ASCII Diagram Standards** → Readable, maintainable architecture docs
4. **Incremental Notes System** → Capture learning and decisions

### Migration Path

The framework supports migration from LEVEL0/LEVEL1/LEVEL2 structure to the new level-based organization. This provides:

- Better separation of concerns (what vs how vs why)
- Clearer documentation purpose
- Improved navigation and maintenance
- Systematic knowledge evolution

---

## 🆘 Support and Troubleshooting

### Common Issues

1. **Unclear requirements** → Use correctness properties and ATDD format
2. **Complex diagrams** → Keep ASCII diagrams simple and focused
3. **Lost decisions** → Use notes.md to capture incremental learning
4. **Low BIF scores** → Address HIGH priority issues with reasoning

### Getting Help

- **Framework Questions**: Review [Development.md](./Development.md)
- **AI Mode Issues**: Check [How To Use.md](./How%20To%20Use.md)
- **Quality Problems**: Consult [BIF.md](./BIF.md)
- **Implementation Patterns**: Reference [technical_pattern.md](../practice/technical_pattern.md)

---

*The Repertoire framework transforms software development from ad-hoc coding to systematic, quality-driven engineering. The new level-based structure makes complex projects more understandable and maintainable.* 🎼