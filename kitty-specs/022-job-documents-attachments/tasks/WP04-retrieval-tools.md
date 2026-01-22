---
work_package_id: "WP04"
title: "Retrieval Tools"
lane: "planned"
dependencies: ["WP02"]
subtasks: ["T012", "T013", "T014"]
---
# Work Package 04: Retrieval Tools

**Goal**: Allow users to ask "Show me documents" and receive a list of secure links.

## Context

We need a tool that the Agent (or rule-based system) can use to list documents for a job. Note: Secure links have short expiration.

## Subtasks

### T012: Create `GetJobDocumentsTool`

**Purpose**: Expose document listing capability.

**Steps**:

1. Create `src/tools/document_tools.py`.
2. Define `GetJobDocumentsTool(BaseTool)`:
    * Input: `job_id` (optional), `customer_id` (optional).
    * Logic:
        * If `job_id`: Call `DocumentService.get_documents_for_job`.
        * Else if `customer_id`: Call `DocumentService.get_documents_for_customer`.
        * Else: Infer from context or error.
    * This might need integration into `tool_executor.py` registry.

**Files**:
* `src/tools/document_tools.py` (NEW)
* `src/tool_executor.py` (UPDATE - register tool)

### T013: Format Response with Presigned URLs

**Purpose**: Present the documents nicely.

**Steps**:

1. In the Tool's `run` method (or output formatter):
    * Iterate over documents.
    * For internal docs: Call `StorageService.get_presigned_url(doc.storage_path)`.
    * For external docs: Use `doc.storage_path` (the external URL).
2. Construct output string:
    * "Found X documents:"
    * 1. [Filename](url) (Type: Img/PDF)
    * 1. [Link](url) (External)

### T014: E2E Tests for Retrieval

**Purpose**: Verify the tool works.

**Steps**:

1. Create `tests/integration/test_document_tools.py`.
2. Seed DB with documents.
3. Run the Tool.
4. Verify output contains valid URLs (mock signature generation).

**Validation**:
* Tool returns formatted list.
* URLs are present.
