# Feature Lifecycle

### **Step 1 — Feature Definition**

- Define **what the feature does** and **why it exists**.
- Write **Acceptance Criteria** (clear, testable outcomes).
- Link to the **corresponding milestone step**.

**Goal:** Everyone knows **what we are building and when it is “done”**.

---

### **Step 2 — Planning**

- Decide **how it will be implemented** (high-level plan).
- Identify **dependencies**: modules, APIs, data structures, or other milestone steps.
- Define Decisions
- Construct Phases for work

**Goal:** Reduce surprises during coding.

---

### **Step 3 — Technical Design**

- **System Design:** How modules interact.
- **Module Design:** Classes, functions, data structures.
- **Data Changes:** DB schema or in-memory changes.
- **Failure Modes:** How the feature could fail, recovery plan.

**Goal:** Developers have a clear **blueprint before writing code**.

---

### **Step 4 — Testing Strategy (ATDD)**

- Write **Acceptance Tests first** (user-facing or system-facing).
- Define **edge cases**, **number of test cases**, **execution plan**.
- Include **safe refactoring checks** to ensure milestone steps don’t break.

**Goal:** Testing guides coding and ensures feature safety.

---

### **Step 5 — Implementation**

- Code the feature following the **technical design**.
- Run **Blind Inspection Framework** to catch code/design issues.
- Integrate with system and ensure **existing milestone steps remain intact**.

**Goal:** Build the feature **quickly but safely**.

---

### **Step 6 — Verification / Definition of Done**

- Ensure all **Acceptance Tests pass**.
- **Blind Inspection** completed.
- **System unchanged** for previous milestone steps.
- Update **documentation**.

**Goal:** Feature is officially “done” and ready for next steps.

---

### **Optional / Ongoing**

- Safe refactoring can continue after initial delivery.
- Future polish or optimizations can be added after urgent delivery.

---

### 🔑 **Summary of Step Order**

1. **Feature Definition** → what & acceptance criteria
2. **Planning** → how, dependencies, decisions, components, phases
3. **Technical Design** → modules, system, data, failures
4. **Testing Strategy (ATDD)** → tests, edge cases, refactoring safety
5. **Implementation** → code + blind inspection
6. **Verification / Definition of Done** → pass tests, no regressions, docs updated

---