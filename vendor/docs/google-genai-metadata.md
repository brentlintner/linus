# genai.types.GenerateContentResponse

Bases: BaseModel

Response message for PredictionService.GenerateContent.

Create a new model by parsing and validating input data from keyword arguments.

Raises [ValidationError][pydantic_core.ValidationError] if the input data cannot be validated to form a valid model.

self is explicitly positional-only to allow self as a field name.

FIELDS:
automatic_function_calling_history (list[genai.types.Content] | None)
candidates (list[genai.types.Candidate] | None)
model_version (str | None)
parsed (pydantic.main.BaseModel | dict | enum.Enum)
prompt_feedback (genai.types.GenerateContentResponsePromptFeedback | None)
usage_metadata (genai.types.GenerateContentResponseUsageMetadata | None)
field automatic_function_calling_history: Optional[list[Content]] = None (alias 'automaticFunctionCallingHistory')
field candidates: Optional[list[Candidate]] = None
Response variations returned by the model.

field model_version: Optional[str] = None (alias 'modelVersion')
Output only. The model version used to generate the response.

field parsed: Union[BaseModel, dict, Enum] = None
Parsed response if response_schema is provided. Not available for streaming.

field prompt_feedback: Optional[GenerateContentResponsePromptFeedback] = None (alias 'promptFeedback')
Output only. Content filter results for a prompt sent in the request. Note: Sent only in the first stream chunk. Only happens when no candidates were generated due to content violations.

field usage_metadata: Optional[GenerateContentResponseUsageMetadata] = None (alias 'usageMetadata')
Usage metadata about the response(s).

property function_calls: list[FunctionCall] | None
Returns the list of function calls in the response.

property text: str | None
Returns the concatenation of all text parts in the response.

# genai.types.GenerateContentResponseUsageMetadata

Bases: BaseModel

Usage metadata about response(s).

Create a new model by parsing and validating input data from keyword arguments.

Raises [ValidationError][pydantic_core.ValidationError] if the input data cannot be validated to form a valid model.

self is explicitly positional-only to allow self as a field name.

FIELDS:

cached_content_token_count (int | None)
candidates_token_count (int | None)
prompt_token_count (int | None)
total_token_count (int | None)
field cached_content_token_count: Optional[int] = None (alias 'cachedContentTokenCount')
Output only. Number of tokens in the cached part in the input (the cached content).

field candidates_token_count: Optional[int] = None (alias 'candidatesTokenCount')
Number of tokens in the response(s).

field prompt_token_count: Optional[int] = None (alias 'promptTokenCount')
Number of tokens in the request. When cached_content is set, this is still the total effective prompt size meaning this includes the number of tokens in the cached content.

field total_token_count: Optional[int] = None (alias 'totalTokenCount')
Total token count for prompt and response candidates.
