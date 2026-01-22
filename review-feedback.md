**Issue 1**: Test Suite Failures
The following test modules have failures that need to be addressed before merging:

- tests/integration/test_location_eta_flow.py
- tests/integration/test_scheduler_flow.py
- tests/test_crm_pipeline_logic.py
- tests/test_event_emission.py
- tests/test_messaging_integration.py
- tests/test_messaging_service.py
- tests/test_security.py
- tests/test_service_settings.py
- tests/test_services_core.py

**Issue 2**: Definition of Done not met
The work package requires "All tests pass" as part of the Definition of Done. Please investigate and fix the regression or environment issues causing these failures.
