import asyncio
import aiohttp
import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from openai import AsyncOpenAI
import anthropic
import replicate
import logging

# Set up logging
logger = logging.getLogger(__name__)

# P1: Retry logic and error tracking
try:
    from retry_logic import retry_async, RetryConfig, RetryStrategy, circuit_breakers
    from error_tracking import capture_exception
    RETRY_AVAILABLE = True
except ImportError:
    RETRY_AVAILABLE = False
    logger.warning("Retry logic not available. Install required dependencies.")


class LLMClient:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Fix for Anthropic API - use the correct async client initialization
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_key)
        else:
            self.anthropic_client = None

        replicate_token = os.getenv("REPLICATE_API_TOKEN")
        if replicate_token:
            self.replicate_client = replicate.Client(api_token=replicate_token)
        else:
            self.replicate_client = None

        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

        # Enhanced WCAG 2.2 Detection Prompt - Comprehensive and Systematic
        self.detection_prompt = """
You are an expert accessibility auditor specializing in WCAG 2.2 compliance for infotainment systems. 

CRITICAL INSTRUCTIONS:
1. Analyze EVERY line of code systematically
2. Report EXACT line numbers where issues occur
3. Only report issues that actually exist in the provided code
4. Use the numbered line references provided below

File: {filename}
Code with line numbers:
```
{numbered_code}
```

SYSTEMATIC WCAG 2.2 ANALYSIS CHECKLIST:

**A. PERCEIVABLE ISSUES (Level A/AA/AAA)**
1. **1.1.1 Non-text Content (Level A):**
   - Check ALL <img> tags for missing/empty alt attributes
   - Check <input type="image"> for missing alt attributes
   - Check <area> tags in image maps for missing alt attributes
   - Check CSS background-images used for content (not decoration)
   - For infotainment: Check icon buttons, media thumbnails, status indicators

2. **1.3.1 Info and Relationships (Level A):**
   - Check form inputs missing <label> elements or aria-label
   - Check headings (h1-h6) are properly nested
   - Check data tables have <th> elements with scope attributes
   - Check lists use proper <ul>, <ol>, <li> structure
   - For infotainment: Check menu hierarchies, navigation structures

3. **1.3.2 Meaningful Sequence (Level A):**
   - Check logical reading order matches visual order
   - Check tab order makes sense (tabindex issues)
   - For infotainment: Check sequential navigation through controls

4. **1.3.3 Sensory Characteristics (Level A):**
   - Check instructions don't rely solely on color/shape/position
   - Example: "Click the red button" should include other identifiers
   - For infotainment: Check voice prompts don't rely on visual-only cues

5. **1.4.1 Use of Color (Level A):**
   - Check information isn't conveyed by color alone
   - Check form validation errors use more than just color
   - For infotainment: Check status indicators (green/red) have additional cues

6. **1.4.3 Contrast (Level AA):**
   - Check text contrast ratios (4.5:1 for normal text, 3:1 for large text)
   - Check UI component contrast (3:1 minimum)
   - For infotainment: Critical for readability while driving

**B. OPERABLE ISSUES (Level A/AA/AAA)**
7. **2.1.1 Keyboard (Level A):**
   - Check ALL interactive elements can be reached by keyboard
   - Check for onclick without onkeydown/onkeypress handlers
   - Check custom controls have proper keyboard support
   - For infotainment: Critical for hands-free operation

8. **2.4.7 Focus Visible (Level AA):**
   - Check ALL focusable elements have visible focus indicators
   - Check focus indicators have sufficient contrast
   - For infotainment: Essential for eyes-free operation

9. **2.5.8 Target Size (Level AA):**
   - Check touch targets are at least 44x44 CSS pixels
   - For infotainment: Critical for vehicle vibration/movement

**C. UNDERSTANDABLE ISSUES (Level A/AA/AAA)**
10. **3.3.2 Labels or Instructions (Level A):**
    - Check ALL form fields have labels or instructions
    - Check required fields are clearly marked
    - For infotainment: Check voice input prompts

**D. ROBUST ISSUES (Level A/AA/AAA)**
11. **4.1.2 Name, Role, Value (Level A):**
    - Check ALL UI components have accessible names
    - Check custom controls have proper ARIA roles
    - Check state changes are programmatically determinable
    - For infotainment: Check media controls, navigation states

**ANALYSIS METHODOLOGY:**
1. Go through code line by line
2. For each WCAG criterion above, check if violations exist
3. Record EXACT line numbers where issues are found
4. Validate that reported code snippets match actual lines
5. Prioritize by severity and driver safety impact

**OUTPUT FORMAT:**
Return ONLY valid JSON with this exact structure:
{{
  "total_issues": 0,
  "issues": [
    {{
      "issue_id": "WCAG_X_X_X_NNN",
      "wcag_guideline": "X.X.X Guideline Name",
      "severity": "A|AA|AAA",
      "line_numbers": [actual_line_number],
      "description": "Specific issue description",
      "impact": "How this affects users with disabilities",
      "code_snippet": "Exact code from the specified lines",
      "recommendation": "Specific fix with code example",
      "category": "perceivable|operable|understandable|robust",
      "infotainment_risk": "low|medium|high",
      "driver_safety_impact": "none|minor|moderate|critical"
    }}
  ],
  "file_info": {{
    "filename": "{filename}",
    "total_lines": 0,
    "file_type": "html|css|javascript|xml|other"
  }}
}}

IMPORTANT: Only report issues that actually exist in the provided code. Verify line numbers are accurate before reporting.
"""

        # Enhanced Remediation Prompt
        self.remediation_prompt = """
You are an expert accessibility developer specializing in WCAG 2.2 compliance fixes for infotainment systems.

TASK: Fix the specific accessibility violation below while preserving all existing functionality.

File: {filename}
Current Code:
```
{numbered_code}
```

**ISSUE TO FIX:**
- Issue ID: {issue_id}
- WCAG Guideline: {wcag_guideline}  
- Description: {description}
- Line Numbers: {line_numbers}
- Current Code Snippet: {code_snippet}

**OUTPUT FORMAT:**
Return ONLY valid JSON:
{{
  "fixed_code": "Complete file content with fixes applied and // FIXED comments",
  "changes": [
    {{
      "line_number": actual_line_number,
      "original": "original code line",
      "fixed": "fixed code line", 
      "explanation": "Why this change fixes the WCAG violation",
      "wcag_principle": "Which WCAG principle this addresses"
    }}
  ],
  "validation": {{
    "wcag_compliance": "How this fix ensures WCAG 2.2 compliance",
    "testing_notes": "How to test that the fix works",
    "driver_safety": "How this improves safety for drivers"
  }}
}}

CRITICAL: Provide complete fixed file content with // FIXED comments marking all changes.
"""

    def _create_numbered_code(self, code: str) -> str:
        """Create code with accurate line numbers for LLM analysis"""
        lines = code.split('\n')
        numbered_lines = []

        for i, line in enumerate(lines, 1):
            # Add line numbers with consistent formatting
            numbered_lines.append(f"{i:4d}: {line}")

        return '\n'.join(numbered_lines)

    def _extract_line_numbers_from_response(self, response_text: str, original_code: str) -> List[int]:
        """Extract and validate line numbers from LLM response"""
        # Look for line number patterns in the response
        line_patterns = [
            r'line[s]?\s*(\d+)',
            r'Line[s]?\s*(\d+)',
            r'lines?\s*(\d+)',
            r'(?:at|on)\s+line\s*(\d+)',
            r'"line_numbers?":\s*\[([^\]]+)\]'
        ]

        found_lines = set()
        total_lines = len(original_code.split('\n'))

        for pattern in line_patterns:
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            for match in matches:
                if ',' in match:  # Handle arrays like [1,2,3]
                    line_nums = re.findall(r'\d+', match)
                else:
                    line_nums = [match]

                for line_str in line_nums:
                    try:
                        line_num = int(line_str)
                        if 1 <= line_num <= total_lines:
                            found_lines.add(line_num)
                    except ValueError:
                        continue

        return sorted(list(found_lines))

    def _validate_issue_accuracy(self, issue: Dict[str, Any], original_code: str) -> Dict[str, Any]:
        """Validate that reported issues actually exist at specified lines"""
        lines = original_code.split('\n')
        validation_result = {
            "is_valid": False,
            "confidence": 0.0,
            "validation_notes": []
        }

        # Check if line numbers are within bounds
        line_numbers = issue.get('line_numbers', [])
        if not line_numbers:
            validation_result["validation_notes"].append("No line numbers provided")
            return validation_result

        valid_line_count = 0
        for line_num in line_numbers:
            if 1 <= line_num <= len(lines):
                line_content = lines[line_num - 1].strip()
                code_snippet = issue.get('code_snippet', '').strip()

                # Check if code snippet matches or is contained in the line
                if code_snippet and (code_snippet in line_content or
                                     any(word in line_content for word in code_snippet.split() if len(word) > 3)):
                    valid_line_count += 1
                    validation_result["validation_notes"].append(f"Line {line_num}: Code snippet matches")
                else:
                    validation_result["validation_notes"].append(f"Line {line_num}: Code snippet mismatch")
            else:
                validation_result["validation_notes"].append(f"Line {line_num}: Out of bounds")

        # Calculate confidence based on validation
        if line_numbers:
            validation_result["confidence"] = valid_line_count / len(line_numbers)
            validation_result["is_valid"] = validation_result["confidence"] >= 0.5

        return validation_result

    async def detect_accessibility_issues(self, code: str, filename: str, model: str) -> Dict[str, Any]:
        """Enhanced accessibility detection with accurate line tracking"""
        try:
            # Check if we need to chunk the code for models with small context windows
            if model == "llama-maverick" and len(code) > 2000:  # LLaMA has small context window
                logger.info(f"Code too large for {model}, chunking...")
                return await self._detect_issues_chunked(code, filename, model)

            # Create numbered code for accurate line reference
            numbered_code = self._create_numbered_code(code)

            prompt = self.detection_prompt.format(
                code=code,
                numbered_code=numbered_code,
                filename=filename
            )

            logger.info(f"Prompt length: {len(prompt)} characters")

            # Call the appropriate model
            raw_result = await self._call_model(prompt, model)

            # Enhance and validate results
            if raw_result.get("issues"):
                validated_issues = []
                for issue in raw_result["issues"]:
                    # Validate issue accuracy
                    validation = self._validate_issue_accuracy(issue, code)
                    issue["validation"] = validation

                    # Only include high-confidence issues
                    if validation["confidence"] >= 0.3:  # Adjust threshold as needed
                        validated_issues.append(issue)
                    else:
                        logger.warning(f"Rejected low-confidence issue: {issue.get('issue_id', 'Unknown')}")

                raw_result["issues"] = validated_issues
                raw_result["total_issues"] = len(validated_issues)

            return raw_result

        except Exception as e:
            logger.error(f"Error in detect_accessibility_issues: {str(e)}")
            return {
                "error": str(e),
                "total_issues": 0,
                "issues": [],
                "file_info": {
                    "filename": filename,
                    "total_lines": len(code.split('\n')),
                    "file_type": self._detect_file_type(filename)
                }
            }

    async def _detect_issues_chunked(self, code: str, filename: str, model: str) -> Dict[str, Any]:
        """Detect accessibility issues by processing code in chunks for models with small context windows"""
        logger.info("Starting chunked analysis for large file...")

        lines = code.split('\n')
        chunk_size = 100  # Process 100 lines at a time
        all_issues = []

        # Create a shorter, focused prompt for chunked analysis
        chunk_prompt_template = """
You are an accessibility expert. Analyze this code chunk for WCAG 2.2 violations.

File: {filename} (Lines {start_line}-{end_line})
Code:
```
{chunk_code}
```

Find accessibility issues and return JSON:
{{
  "issues": [
    {{
      "issue_id": "WCAG_X_X_X_NNN",
      "wcag_guideline": "X.X.X Guideline Name", 
      "severity": "A|AA|AAA",
      "line_numbers": [line_number],
      "description": "Issue description",
      "code_snippet": "problematic code",
      "recommendation": "how to fix",
      "category": "perceivable|operable|understandable|robust"
    }}
  ]
}}

Focus on:
- Missing alt attributes on images
- Missing labels on form inputs  
- Missing keyboard support (onclick without onkeydown)
- Missing focus styles
- Missing ARIA attributes
"""

        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_code = '\n'.join(chunk_lines)

            start_line = i + 1
            end_line = min(i + chunk_size, len(lines))

            logger.info(f"Processing chunk: lines {start_line}-{end_line}")

            # Skip empty chunks
            if not chunk_code.strip():
                continue

            prompt = chunk_prompt_template.format(
                filename=filename,
                start_line=start_line,
                end_line=end_line,
                chunk_code=chunk_code
            )

            logger.info(f"Chunk prompt length: {len(prompt)} characters")

            try:
                chunk_result = await self._call_model(prompt, model)

                if chunk_result.get("issues"):
                    # Adjust line numbers to be relative to the full file
                    for issue in chunk_result["issues"]:
                        if "line_numbers" in issue:
                            # Adjust line numbers by adding the chunk offset
                            adjusted_lines = []
                            for line_num in issue["line_numbers"]:
                                if isinstance(line_num, int):
                                    adjusted_lines.append(line_num + i)
                                else:
                                    adjusted_lines.append(line_num)
                            issue["line_numbers"] = adjusted_lines

                        # Add chunk info for debugging
                        issue["chunk_info"] = f"Lines {start_line}-{end_line}"

                    all_issues.extend(chunk_result["issues"])
                    logger.info(f"Found {len(chunk_result['issues'])} issues in chunk")

            except Exception as e:
                logger.error(f"Error processing chunk {start_line}-{end_line}: {str(e)}")
                continue

        logger.info(f"Chunked analysis complete. Total issues found: {len(all_issues)}")

        return {
            "total_issues": len(all_issues),
            "issues": all_issues,
            "file_info": {
                "filename": filename,
                "total_lines": len(lines),
                "file_type": self._detect_file_type(filename)
            },
            "analysis_method": "chunked"
        }

    async def fix_accessibility_issues(self, code: str, filename: str, model: str) -> Dict[str, Any]:
        """Enhanced remediation with validation"""
        # First detect issues
        detection_result = await self.detect_accessibility_issues(code, filename, model)

        if detection_result.get("error") or not detection_result.get("issues"):
            return detection_result

        # Fix each validated issue
        fixed_code = code
        all_changes = []
        successful_fixes = 0

        for issue in detection_result["issues"]:
            # Only attempt to fix high-confidence issues
            if issue.get("validation", {}).get("confidence", 0) >= 0.5:
                try:
                    numbered_code = self._create_numbered_code(fixed_code)

                    fix_prompt = self.remediation_prompt.format(
                        numbered_code=numbered_code,
                        filename=filename,
                        issue_id=issue["issue_id"],
                        wcag_guideline=issue["wcag_guideline"],
                        description=issue["description"],
                        line_numbers=issue["line_numbers"],
                        code_snippet=issue.get("code_snippet", "")
                    )

                    fix_result = await self._call_model(fix_prompt, model)

                    if fix_result.get("fixed_code"):
                        # Validate that the fix actually addresses the issue
                        if self._validate_fix_quality(fixed_code, fix_result["fixed_code"], issue):
                            fixed_code = fix_result["fixed_code"]
                            all_changes.extend(fix_result.get("changes", []))
                            successful_fixes += 1
                        else:
                            logger.warning(f"Rejected low-quality fix for issue: {issue['issue_id']}")

                except Exception as e:
                    logger.error(f"Failed to fix issue {issue.get('issue_id', 'Unknown')}: {str(e)}")
                    continue

        return {
            "original_code": code,
            "fixed_code": fixed_code,
            "total_changes": len(all_changes),
            "changes": all_changes,
            "issues_detected": len(detection_result["issues"]),
            "issues_fixed": successful_fixes,
            "fix_success_rate": successful_fixes / len(detection_result["issues"]) if detection_result["issues"] else 0
        }

    def _validate_fix_quality(self, original_code: str, fixed_code: str, issue: Dict[str, Any]) -> bool:
        """Validate that a fix actually improves the code"""
        # Basic validation - ensure fix contains expected improvements
        issue_type = issue.get("wcag_guideline", "").split()[0] if issue.get("wcag_guideline") else ""

        validation_patterns = {
            "1.1.1": [r'alt\s*=\s*["\'][^"\']+["\']'],  # Alt text added
            "2.1.1": [r'onkeydown', r'onkeypress', r'tabindex'],  # Keyboard support
            "2.4.7": [r':focus\s*{', r'focus-visible'],  # Focus styles
            "3.3.2": [r'<label', r'aria-label', r'aria-labelledby'],  # Labels
            "4.1.2": [r'role\s*=', r'aria-\w+'],  # ARIA attributes
        }

        # Check if relevant improvements are present
        if issue_type in validation_patterns:
            for pattern in validation_patterns[issue_type]:
                if re.search(pattern, fixed_code, re.IGNORECASE) and not re.search(pattern, original_code,
                                                                                   re.IGNORECASE):
                    return True

        # If we can't validate specifically, check for general improvements
        return "// FIXED" in fixed_code or len(fixed_code) > len(original_code)

    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from filename"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        type_mapping = {
            'html': 'html', 'htm': 'html',
            'css': 'css',
            'js': 'javascript', 'jsx': 'javascript',
            'ts': 'typescript', 'tsx': 'typescript',
            'xml': 'xml',
            'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp',
            'c': 'c', 'h': 'c',
            'java': 'java',
            'kt': 'kotlin',
            'swift': 'swift'
        }

        return type_mapping.get(ext, 'other')

    async def _call_model(self, prompt: str, model: str) -> Dict[str, Any]:
        """Unified model calling with retry logic and error handling (P1)"""
        # Determine provider for circuit breaker
        provider = None
        if model == "gpt-4o":
            provider = "openai"
        elif model == "claude-opus-4":
            provider = "anthropic"
        elif model == "deepseek-v3":
            provider = "deepseek"
        elif model == "llama-maverick":
            provider = "replicate"
        
        # Get circuit breaker for this provider
        circuit_breaker = circuit_breakers.get(provider) if provider else None
        
        # Configure retry logic
        retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retryable_exceptions=[Exception, ConnectionError, TimeoutError, asyncio.TimeoutError],
            jitter=True,
            circuit_breaker=circuit_breaker
        )
        
        async def call_provider():
            """Inner function to call the appropriate provider"""
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
        
        try:
            # Use retry logic with circuit breaker if available
            if RETRY_AVAILABLE:
                result = await retry_async(call_provider, config=retry_config)
            else:
                # Fallback to direct call without retry
                result = await call_provider()
            return result
        except Exception as e:
            logger.error(f"Model {model} failed after retries: {str(e)}")
            # Capture to error tracking if available
            if RETRY_AVAILABLE:
                try:
                    capture_exception(
                        e,
                        level="error",
                        context={
                            "model": model,
                            "provider": provider,
                            "prompt_length": len(prompt)
                        },
                        tags={"component": "llm_client", "model": model}
                    )
                except Exception:
                    pass  # Don't fail if error tracking fails
            raise Exception(f"Model {model} failed: {str(e)}")

    async def _call_openai(self, prompt: str, model: str = "gpt-4o") -> Dict[str, Any]:
        """Call OpenAI API with enhanced error handling"""
        try:
            models_to_try = ["gpt-4o-mini", "gpt-3.5-turbo"] if model == "gpt-4o" else [model]

            for model_name in models_to_try:
                try:
                    response = await self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert accessibility auditor specializing in WCAG 2.2 compliance for infotainment systems. You provide accurate, detailed analysis with precise line numbers."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=4000
                    )

                    content = response.choices[0].message.content
                    return self._parse_json_response(content)

                except Exception as e:
                    if "insufficient_quota" in str(e) or "rate_limit" in str(e):
                        continue
                    else:
                        raise e

            raise Exception("All OpenAI models failed or quota exceeded")

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise Exception(f"OpenAI API error: {str(e)}")

    async def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic Claude API with proper async handling"""
        try:
            if not self.anthropic_client:
                raise Exception("Anthropic API key not configured")

            # Use the correct async method for the newer Anthropic library
            response = await self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Using Haiku as it's more available
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract content from the response
            content = response.content[0].text
            return self._parse_json_response(content)

        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise Exception(f"Anthropic API error: {str(e)}")

    async def _call_deepseek(self, prompt: str) -> Dict[str, Any]:
        """Call DeepSeek API"""
        try:
            if not self.deepseek_api_key:
                raise Exception("DeepSeek API key not configured")

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert accessibility auditor specializing in WCAG 2.2 compliance for infotainment systems."
                        },
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
            logger.error(f"DeepSeek API error: {str(e)}")
            raise Exception(f"DeepSeek API error: {str(e)}")

    async def _call_replicate(self, prompt: str) -> Dict[str, Any]:
        """Call Replicate API for LLaMA with enhanced error handling and debugging"""
        try:
            if not self.replicate_client:
                raise Exception("Replicate API token not configured")

            logger.info("Starting Replicate API call...")

            # Use async executor to handle the synchronous replicate client
            loop = asyncio.get_event_loop()

            def run_replicate():
                try:
                    # Check prompt length and choose appropriate model
                    prompt_length = len(prompt)
                    logger.info(f"Prompt length: {prompt_length} characters")

                    if prompt_length > 12000:  # Too long even for chunking
                        raise Exception(f"Prompt too long ({prompt_length} chars) - use chunking")
                    elif prompt_length > 8000:
                        # Use a model with larger context window
                        model_version = "meta/llama-2-13b-chat:f4e2de70d66816a838a89eeeb621910adffb0dd0baba3976c96980970978018d"
                        logger.info("Using LLaMA-2-13B for large prompt")
                    else:
                        # Use standard model
                        model_version = "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3"
                        logger.info("Using LLaMA-2-70B standard model")

                    logger.info(f"Using model: {model_version}")

                    # Create prediction
                    prediction = self.replicate_client.run(
                        model_version,
                        input={
                            "prompt": prompt,
                            "temperature": 0.1,
                            "max_new_tokens": 2000,  # Reduced to leave room for input
                            "top_p": 0.9,
                            "repetition_penalty": 1.15,
                            "system_prompt": "You are an expert accessibility auditor. Always respond with valid JSON format."
                        }
                    )

                    logger.info(f"Prediction type: {type(prediction)}")

                    # Handle generator objects properly
                    if hasattr(prediction, '__iter__') and not isinstance(prediction, str):
                        # It's a generator or iterator - consume it
                        prediction_list = list(prediction)
                        logger.info(f"Generator consumed, got {len(prediction_list)} items")

                        # Join all items
                        content = "".join(str(item) for item in prediction_list)
                        logger.info(f"Joined content length: {len(content)}")
                        logger.info(f"Joined content preview: {content[:200]}...")

                        return content
                    else:
                        # It's already a string or other object
                        content = str(prediction)
                        logger.info(f"Direct content length: {len(content)}")
                        logger.info(f"Direct content preview: {content[:200]}...")

                        return content

                except Exception as e:
                    logger.error(f"Replicate execution error: {str(e)}")
                    raise e

            # Run in executor with timeout
            try:
                content = await asyncio.wait_for(
                    loop.run_in_executor(None, run_replicate),
                    timeout=180  # 3 minute timeout for large prompts
                )

                logger.info("Replicate call completed successfully")

            except asyncio.TimeoutError:
                logger.error("Replicate API call timed out")
                raise Exception("Replicate API call timed out after 3 minutes")

            logger.info(f"Final content length: {len(content)}")
            logger.info(f"Final content preview: {content[:500]}...")

            # Clean up the content
            content = content.strip()

            if not content:
                logger.error("Empty response from Replicate")
                raise Exception("Empty response from Replicate API")

            # Check if content looks like a generator string representation
            if content.startswith('<generator object') or 'generator' in content:
                logger.error("Received generator string representation instead of actual content")
                raise Exception("Replicate returned generator object string representation")

            # Try to parse as JSON
            try:
                parsed_result = self._parse_json_response(content)
                logger.info("Successfully parsed JSON response")
                return parsed_result

            except Exception as parse_error:
                logger.error(f"JSON parsing failed: {str(parse_error)}")
                logger.error(f"Content that failed to parse: {content[:1000]}...")

                # Return a fallback response with error details
                return {
                    "total_issues": 0,
                    "issues": [],
                    "error": f"Failed to parse LLM response as JSON: {str(parse_error)}",
                    "raw_response": content[:1000] + "..." if len(content) > 1000 else content,
                    "file_info": {
                        "filename": "unknown",
                        "total_lines": 0,
                        "file_type": "unknown"
                    }
                }

        except Exception as e:
            logger.error(f"Replicate API error: {str(e)}")
            return {
                "total_issues": 0,
                "issues": [],
                "error": f"Replicate API error: {str(e)}",
                "raw_response": "",
                "file_info": {
                    "filename": "unknown",
                    "total_lines": 0,
                    "file_type": "unknown"
                }
            }

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Enhanced JSON parsing with better error handling"""
        try:
            # Log the content for debugging
            logger.debug(f"Parsing content: {content[:200]}...")

            # Remove markdown code blocks
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

            # Try to find JSON object in the response
            json_start = content.find('{')
            json_end = content.rfind('}')

            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_content = content[json_start:json_end + 1]
                logger.debug(f"Extracted JSON: {json_content[:200]}...")

                try:
                    parsed = json.loads(json_content)
                    logger.info("Successfully parsed JSON")

                    # Validate required fields
                    if not isinstance(parsed.get("issues"), list):
                        parsed["issues"] = []
                    if not isinstance(parsed.get("total_issues"), int):
                        parsed["total_issues"] = len(parsed.get("issues", []))

                    return parsed

                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON decode error: {str(json_error)}")
                    logger.error(f"JSON content: {json_content}")

            # If JSON parsing fails, try to extract any valid JSON-like content
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    logger.info("Successfully parsed JSON from regex match")
                    return parsed
                except json.JSONDecodeError:
                    pass

            # Fallback response
            logger.warning("Could not parse response as JSON, returning fallback")
            return {
                "total_issues": 0,
                "issues": [],
                "error": f"Failed to parse LLM response as JSON: Content does not contain valid JSON",
                "raw_response": content[:500] + "..." if len(content) > 500 else content,
                "file_info": {
                    "filename": "unknown",
                    "total_lines": 0,
                    "file_type": "unknown"
                }
            }

        except Exception as e:
            logger.error(f"Error in _parse_json_response: {str(e)}")
            return {
                "total_issues": 0,
                "issues": [],
                "error": f"Failed to parse LLM response: {str(e)}",
                "raw_response": content[:500] + "..." if len(content) > 500 else content,
                "file_info": {
                    "filename": "unknown",
                    "total_lines": 0,
                    "file_type": "unknown"
                }
            }

    def get_supported_models(self) -> List[str]:
        """Get list of supported LLM models"""
        return ["gpt-4o", "claude-opus-4", "deepseek-v3", "llama-maverick"]

    async def fix_specific_issue(self, code: str, issue_id: str, model: str) -> Dict[str, Any]:
        """Fix a specific accessibility issue with enhanced validation"""
        try:
            # Simple fix prompt for specific issues
            numbered_code = self._create_numbered_code(code)

            fix_prompt = f"""
Fix the accessibility issue with ID: {issue_id} in the following code:

Code with line numbers:
```
{numbered_code}
```

Return the fixed code with // FIXED comments for all changes.
Follow WCAG 2.2 guidelines and infotainment best practices.

Return as JSON:
{{
  "fixed_code": "complete fixed file content",
  "changes": [
    {{
      "line_number": number,
      "original": "original line",
      "fixed": "fixed line",
      "explanation": "explanation of fix"
    }}
  ]
}}
"""

            result = await self._call_model(fix_prompt, model)

            # Validate the fix
            if result.get("fixed_code"):
                result["validation_score"] = self._calculate_fix_validation_score(code, result["fixed_code"])

            return result

        except Exception as e:
            logger.error(f"Error in fix_specific_issue: {str(e)}")
            return {
                "error": str(e),
                "fixed_code": code,
                "changes": [],
                "validation_score": 0.0
            }

    def _calculate_fix_validation_score(self, original: str, fixed: str) -> float:
        """Calculate a validation score for the fix quality"""
        score = 0.0

        # Check for common accessibility improvements
        improvements = [
            (r'alt\s*=\s*["\'][^"\']+["\']', 0.2),  # Alt text
            (r'aria-label\s*=', 0.15),  # ARIA labels
            (r'role\s*=', 0.15),  # ARIA roles
            (r':focus\s*{', 0.1),  # Focus styles
            (r'tabindex\s*=', 0.1),  # Tab order
            (r'onkeydown|onkeypress', 0.15),  # Keyboard support
            (r'<label', 0.15),  # Form labels
        ]

        for pattern, weight in improvements:
            if re.search(pattern, fixed, re.IGNORECASE) and not re.search(pattern, original, re.IGNORECASE):
                score += weight

        # Bonus for FIXED comments
        if "// FIXED" in fixed:
            score += 0.1

        return min(score, 1.0)