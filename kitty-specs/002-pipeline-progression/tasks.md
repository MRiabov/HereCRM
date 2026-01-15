# Tasks: Pipeline Progression Logic

## Work Packages

### WP01: Foundational Pipeline Infrastructure

- **Goal**: Set up the data model and the EventBus for decoupled state changes.
- **Priority**: P1
- **Success Criteria**: `PipelineStage` enum exists, `Customer` has the field, `EventBus` can register and emit events.
- **Subtasks**:
  - [x] **T001**: Define `PipelineStage` Enum in `src/models.py`. [P]
  - [x] **T002**: Add `pipeline_stage` field to `Customer` model in `src/models.py` (default `NOT_CONTACTED`). [P]
  - [x] **T003**: Implement a simple `EventBus` in `src/events.py`. [P]
  - [x] **T004**: Initialize `EventBus` and register handlers in `src/main.py`.
- **Implementation Sketch**: Start with model updates, then build the EventBus to be used for decoupled service communication.
- **Prompt**: [tasks/WP01-foundational-infrastructure.md](file:///home/maksym/Work/proj/HereCRM/.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/tasks/WP01-foundational-infrastructure.md)

### WP02: Automatic State Progression

- **Goal**: Implement the core logic that moves customers between stages based on job creation.
- **Priority**: P1
- **Success Criteria**: Adding first/second jobs automatically updates the customer's pipeline stage.
- **Subtasks**:
  - [x] **T005**: Create `src/services/pipeline_handlers.py` for event listeners. [P]
  - [x] **T006**: Emit `JOB_CREATED` event from `CRMService`.
  - [x] **T007**: Implement stage update logic in `pipeline_handlers.py` (Not Contacted -> Converted Once -> Converted Recurrent).
  - [x] **T008**: Implement automatic "Contacted" trigger on first interaction.
- **Implementation Sketch**: Hook into Job creation to trigger customer state updates via the EventBus.
- **Dependencies**: WP01
- **Prompt**: [tasks/WP02-automatic-progression.md](file:///home/maksym/Work/proj/HereCRM/.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/tasks/WP02-automatic-progression.md)

### WP03: Pipeline Querying and Reporting

- **Goal**: Enable users to see their sales funnel with counts and details.
- **Priority**: P2
- **Success Criteria**: Command "show pipeline" returns a formatted text summary of customers in each stage.
- **Subtasks**:
  - [x] **T009**: Add `get_pipeline_summary` to `CRMService`. [P]
  - [x] **T010**: Implement text-based visualization for the pipeline summary.
  - [x] **T011**: Update LLM client/tools to support pipeline queries.
- **Implementation Sketch**: Create a reporting method in CRM service and expose it via the LLM toolset.
- **Dependencies**: WP01
- **Prompt**: [tasks/WP03-pipeline-querying.md](file:///home/maksym/Work/proj/HereCRM/.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/tasks/WP03-pipeline-querying.md)

### WP04: Search Filtering and Manual Updates

- **Goal**: Allow filtering customers by stage and manual status overrides.
- **Priority**: P2
- **Success Criteria**: Search can filter by "Lost" or "Converted Once", and "mark as Lost" works.
- **Subtasks**:
  - [x] **T012**: Update `CustomerRepository.search` to support `pipeline_stage` filter. [P]
  - [x] **T013**: Update LLM tools to pass `pipeline_stage` filter.
  - [x] **T014**: Implement manual stage update tool in `CRMService`.
  - [x] **T015**: Update LLM prompts for manual overrides (Lost, Not Interested).
- **Implementation Sketch**: Extend repository search and add a specific tool for manual state changes.
- **Dependencies**: WP01, WP02
- **Prompt**: [tasks/WP04-search-and-manual-updates.md](file:///home/maksym/Work/proj/HereCRM/.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/tasks/WP04-search-and-manual-updates.md)

### WP05: Verification and Polish

- **Goal**: Ensure all logic is tested and the UI/LLM interactions are smooth.
- **Priority**: P2
- **Success Criteria**: All unit and integration tests pass; pipeline behavior matches Spec 002.
- **Subtasks**:
  - [ ] **T016**: Create `tests/test_pipeline_logic.py` for unit testing state transitions. [P]
  - [ ] **T017**: Create integration tests for end-to-end user stories. [P]
  - [ ] **T018**: Create tests for search filtering by stage. [P]
- **Implementation Sketch**: Comprehensive test suite covering both automatic and manual transitions.
- **Dependencies**: All previous
- **Prompt**: [tasks/WP05-verification.md](file:///home/maksym/Work/proj/HereCRM/.worktrees/002-pipeline-progression/kitty-specs/002-pipeline-progression/tasks/WP05-verification.md)
