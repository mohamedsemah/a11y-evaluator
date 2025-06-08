import asyncio
import aiohttp
import json
import os
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
import anthropic
import replicate


class LLMClient:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

        # WCAG 2.2 Detection Prompt Template - FIXED
        self.detection_prompt = """
You are an expert accessibility auditor specializing in WCAG 2.2 compliance for infotainment systems. 

Analyze the following code file and identify ALL accessibility violations according to WCAG 2.2 guidelines.

File: {filename}
Code:
```
{code}
```

For each violation found, provide:
1. **Issue ID**: Unique identifier (e.g., "WCAG_1_1_1_001")
2. **WCAG Guideline**: Specific guideline violated (e.g., "1.1.1 Non-text Content")
3. **Severity**: A, AA, or AAA level
4. **Line Numbers**: Exact line(s) where the issue occurs
5. **Description**: Clear explanation of the violation
6. **Impact**: How this affects users with disabilities
7. **Code Snippet**: The problematic code section
8. **Recommendation**: Specific fix needed

Focus on detecting:
- Missing alt text and labels
- Insufficient color contrast
- Keyboard navigation issues
- Focus management problems
- Timing and motion issues
- Cognitive load concerns
- Touch target size issues
- Error identification and handling
- Semantic markup violations
- ARIA misuse or missing ARIA

Return results as JSON in this exact format:
{{
  "total_issues": 0,
  "issues": [
    {{
      "issue_id": "string",
      "wcag_guideline": "string",
      "severity": "A|AA|AAA",
      "line_numbers": [1],
      "description": "string",
      "impact": "string",
      "code_snippet": "string",
      "recommendation": "string",
      "category": "perceivable|operable|understandable|robust"
    }}
  ],
  "file_info": {{
    "filename": "string",
    "total_lines": 0,
    "file_type": "string"
  }}
}}
"""

        # WCAG 2.2 Remediation Prompt Template - FIXED
        self.remediation_prompt = """
You are an expert accessibility developer specializing in WCAG 2.2 compliance fixes for infotainment systems.

Fix the following accessibility violation in the code:

File: {filename}
Original Code:
```
{code}
```

Issue to Fix:
- **Issue ID**: {issue_id}
- **WCAG Guideline**: {wcag_guideline}
- **Description**: {description}
- **Line Numbers**: {line_numbers}

Requirements:
1. Fix ONLY the specified accessibility issue
2. Preserve all existing functionality
3. Add comments with "// PATCHED" for all changes
4. Follow WCAG 2.2 best practices
5. Ensure the fix works across different infotainment platforms
6. Maintain code style and structure

Return the result as JSON:
{{
  "fixed_code": "string (complete fixed file content)",
  "changes": [
    {{
      "line_number": 0,
      "original": "string",
      "fixed": "string",
      "explanation": "string"
    }}
  ],
  "validation": {{
    "wcag_compliance": "string",
    "testing_notes": "string"
  }}
}}
"""

    async def detect_accessibility_issues(self, code: str, filename: str, model: str) -> Dict[str, Any]:
        """Detect accessibility issues using specified LLM model"""
        try:
            prompt = self.detection_prompt.format(code=code, filename=filename)
        except KeyError as e:
            return {
                "error": f"Prompt formatting error: {str(e)}",
                "total_issues": 0,
                "issues": [],
                "file_info": {"filename": filename, "total_lines": len(code.split('\n')), "file_type": "unknown"}
            }

        try:
            if model == "gpt-4o":
                return await self._call_openai(prompt, model)
            elif model == "claude-opus-4":
                return await self._call_anthropic(prompt)
            elif model == "deepseek-v3":
                return await self._call_deepseek(prompt)
            elif model == "llama-maverick":
                return await self._call_replicate(prompt)
            else:
                raise ValueError(f"Unsupported model: {model}")
        except Exception as e:
            return {
                "error": str(e),
                "total_issues": 0,
                "issues": [],
                "file_info": {"filename": filename, "total_lines": len(code.split('\n')), "file_type": "unknown"}
            }

    async def fix_accessibility_issues(self, code: str, filename: str, model: str) -> Dict[str, Any]:
        """Fix accessibility issues using specified LLM model"""
        # First detect issues, then fix them
        detection_result = await self.detect_accessibility_issues(code, filename, model)

        if detection_result.get("error") or not detection_result.get("issues"):
            return detection_result

        # Fix all detected issues
        fixed_code = code
        all_changes = []

        for issue in detection_result["issues"]:
            try:
                fix_prompt = self.remediation_prompt.format(
                    code=fixed_code,
                    filename=filename,
                    issue_id=issue["issue_id"],
                    wcag_guideline=issue["wcag_guideline"],
                    description=issue["description"],
                    line_numbers=issue["line_numbers"]
                )
            except KeyError as e:
                continue  # Skip this issue if prompt formatting fails

            try:
                fix_result = await self._call_model_for_fix(fix_prompt, model)
                if fix_result.get("fixed_code"):
                    fixed_code = fix_result["fixed_code"]
                    all_changes.extend(fix_result.get("changes", []))
            except Exception as e:
                continue

        return {
            "original_code": code,
            "fixed_code": fixed_code,
            "total_changes": len(all_changes),
            "changes": all_changes,
            "issues_fixed": len(detection_result["issues"])
        }

    async def fix_specific_issue(self, code: str, issue_id: str, model: str) -> Dict[str, Any]:
        """Fix a specific accessibility issue"""
        fix_prompt = f"""
Fix the accessibility issue with ID: {issue_id} in the following code:

```
{code}
```

Return the fixed code with // PATCHED comments for all changes.
Return as JSON: {{"fixed_code": "...", "changes": []}}
"""

        try:
            return await self._call_model_for_fix(fix_prompt, model)
        except Exception as e:
            return {"error": str(e), "fixed_code": code, "changes": []}

    async def _call_openai(self, prompt: str, model: str = "gpt-4o") -> Dict[str, Any]:
        """Call OpenAI API"""
        try:
            # Use gpt-4o-mini if gpt-4o fails or quota exceeded
            models_to_try = ["gpt-4o-mini", "gpt-3.5-turbo"] if model == "gpt-4o" else [model]

            for model_name in models_to_try:
                try:
                    response = await self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system",
                             "content": "You are an expert accessibility auditor for infotainment systems."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=4000
                    )

                    content = response.choices[0].message.content
                    return self._parse_json_response(content)
                except Exception as e:
                    if "insufficient_quota" in str(e) or "rate_limit" in str(e):
                        continue  # Try next model
                    else:
                        raise e

            # If all models fail
            raise Exception("All OpenAI models failed or quota exceeded")

        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    async def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic Claude API"""
        try:
            # Check if we have the right Anthropic client version
            if hasattr(self.anthropic_client, 'messages'):
                # New API version
                response = await self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4000
                )
                content = response.content[0].text
            else:
                # Older API version - try alternative approach
                response = await self.anthropic_client.completions.create(
                    model="claude-2.1",
                    prompt=f"Human: {prompt}\n\nAssistant:",
                    max_tokens_to_sample=4000
                )
                content = response.completion

            return self._parse_json_response(content)

        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")

    async def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        """Call DeepSeek API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system",
                         "content": "You are an expert accessibility auditor for infotainment systems."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4000
                }

                async with session.post(
                        "https://api.deepseek.com/chat/completions",
                        headers=headers,
                        json=payload
                ) as response:
                    result = await response.json()

                    if response.status != 200:
                        raise Exception(f"DeepSeek API error: {result}")

                    content = result["choices"][0]["message"]["content"]
                    return self._parse_json_response(content)
        except Exception as e:
            raise Exception(f"DeepSeek API error: {str(e)}")

    async def _call_replicate(self, prompt: str) -> Dict[str, Any]:
        """Call Replicate API for LLaMA"""
        try:
            # Using LLaMA 2 or 3 model on Replicate
            output = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.replicate_client.run(
                    "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3",
                    input={
                        "prompt": prompt,
                        "temperature": 0.1,
                        "max_new_tokens": 4000,
                        "system_prompt": "You are an expert accessibility auditor for infotainment systems."
                    }
                )
            )

            # Replicate returns a list of strings, join them
            content = "".join(output) if isinstance(output, list) else str(output)
            return self._parse_json_response(content)
        except Exception as e:
            raise Exception(f"Replicate API error: {str(e)}")

    async def _call_model_for_fix(self, prompt: str, model: str) -> Dict[str, Any]:
        """Call appropriate model for fixing issues"""
        if model == "gpt-4o":
            return await self._call_openai(prompt, model)
        elif model == "claude-opus-4":
            return await self._call_anthropic(prompt)
        elif model == "deepseek-v3":
            return await self._call_deepseek(prompt)
        elif model == "llama-maverick":
            return await self._call_replicate(prompt)
        else:
            raise ValueError(f"Unsupported model: {model}")

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response from LLM, handling markdown code blocks"""
        try:
            # Remove markdown code blocks if present
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end != -1:
                    content = content[start:end].strip()

            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback: create a basic structure
            return {
                "total_issues": 0,
                "issues": [],
                "error": "Failed to parse LLM response as JSON",
                "raw_response": content
            }

    def get_supported_models(self) -> List[str]:
        """Get list of supported LLM models"""
        return ["gpt-4o", "claude-opus-4", "deepseek-v3", "llama-maverick"]