### Review Feedback for WP04

The implementation is functionally correct and passes the integration tests. However, there are a few missing pieces and improvements needed:

1. **System Prompt Update Missing**: Subtask T016 specifically requested updating the system prompts to explain when to use `LocateEmployeeTool` and `CheckETATool`. While the tools are registered in `llm_client.py`, the `src/assets/prompts.yaml` (where the system instruction actually resides) was not updated. Without this, the LLM may not consistently trigger these tools for user queries like "Where is my tech?" or "Where are my employees?".
   - **Action**: Add intent parsing guidelines and tool descriptions for `LocateEmployeeTool` and `CheckETATool` to `src/assets/prompts.yaml`.

2. **Error Message Consistency**: The `CheckETATool` logic uses `self.user_phone` as the default customer phone. While this works for WhatsApp, it might be worth explicitly verifying if the user is a customer or an admin before allowing `customer_query` overrides, as per the spec's intent to restrict some data.

3. **Routing Service Import**: In `src/tool_executor.py`, `OpenRouteServiceAdapter` is imported and instantiated inside `_execute_check_eta`. It might be better to inject it or use the `RoutingServiceProvider` pattern if we want to support the mock service in production for any reason.

Please update the `prompts.yaml` and re-submit for review.
