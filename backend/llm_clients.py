import asyncio
import aiohttp
import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from openai import AsyncOpenAI
import anthropic
import replicate


class LLMClient:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))
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

5. **1.3.4 Orientation (Level AA):**
   - Check content isn't restricted to specific orientation
   - For infotainment: Check landscape/portrait mode support

6. **1.4.1 Use of Color (Level A):**
   - Check information isn't conveyed by color alone
   - Check form validation errors use more than just color
   - For infotainment: Check status indicators (green/red) have additional cues

7. **1.4.3 Contrast (Level AA):**
   - Check text contrast ratios (4.5:1 for normal text, 3:1 for large text)
   - Check UI component contrast (3:1 minimum)
   - For infotainment: Critical for readability while driving

8. **1.4.11 Non-text Contrast (Level AA):**
   - Check UI components and graphical objects have 3:1 contrast
   - For infotainment: Check button borders, focus indicators

**B. OPERABLE ISSUES (Level A/AA/AAA)**
9. **2.1.1 Keyboard (Level A):**
   - Check ALL interactive elements can be reached by keyboard
   - Check for onclick without onkeydown/onkeypress handlers
   - Check custom controls have proper keyboard support
   - For infotainment: Critical for hands-free operation

10. **2.1.2 No Keyboard Trap (Level A):**
    - Check users can navigate away from any focused element
    - Check modal dialogs have proper escape mechanisms
    - For infotainment: Check menu navigation allows exit

11. **2.1.4 Character Key Shortcuts (Level A):**
    - Check single-key shortcuts can be disabled/remapped
    - For infotainment: Check voice command conflicts

12. **2.4.1 Bypass Blocks (Level A):**
    - Check for skip links or landmark navigation
    - For infotainment: Check quick access to main functions

13. **2.4.2 Page Titled (Level A):**
    - Check <title> elements are descriptive and unique
    - For infotainment: Check screen/view titles

14. **2.4.3 Focus Order (Level A):**
    - Check tab order is logical and meaningful
    - Check custom tabindex values are appropriate
    - For infotainment: Critical for safe sequential navigation

15. **2.4.7 Focus Visible (Level AA):**
    - Check ALL focusable elements have visible focus indicators
    - Check focus indicators have sufficient contrast
    - For infotainment: Essential for eyes-free operation

16. **2.5.1 Pointer Gestures (Level A):**
    - Check complex gestures have simple alternatives
    - For infotainment: Check swipe gestures have button alternatives

17. **2.5.2 Pointer Cancellation (Level A):**
    - Check touch/click actions can be cancelled
    - For infotainment: Prevent accidental activations while driving

18. **2.5.3 Label in Name (Level A):**
    - Check accessible names include visible text labels
    - For infotainment: Check voice control can use visible labels

19. **2.5.4 Motion Actuation (Level A):**
    - Check device motion triggers can be disabled
    - For infotainment: Check shake/tilt controls have alternatives

20. **2.5.8 Target Size (Level AA):**
    - Check touch targets are at least 44x44 CSS pixels
    - For infotainment: Critical for vehicle vibration/movement

**C. UNDERSTANDABLE ISSUES (Level A/AA/AAA)**
21. **3.1.1 Language of Page (Level A):**
    - Check <html> element has lang attribute
    - For infotainment: Check multilingual support

22. **3.2.1 On Focus (Level A):**
    - Check focusing elements doesn't trigger unexpected changes
    - For infotainment: Prevent context switches while driving

23. **3.2.2 On Input (Level A):**
    - Check input changes don't cause unexpected context changes
    - For infotainment: Check form auto-submission

24. **3.3.1 Error Identification (Level A):**
    - Check form errors are clearly identified
    - Check error messages are associated with fields
    - For infotainment: Check voice error announcements

25. **3.3.2 Labels or Instructions (Level A):**
    - Check ALL form fields have labels or instructions
    - Check required fields are clearly marked
    - For infotainment: Check voice input prompts

**D. ROBUST ISSUES (Level A/AA/AAA)**
26. **4.1.1 Parsing (Level A):**
    - Check HTML is valid and well-formed
    - Check unique IDs, proper nesting, closing tags
    - For infotainment: Critical for screen reader compatibility

27. **4.1.2 Name, Role, Value (Level A):**
    - Check ALL UI components have accessible names
    - Check custom controls have proper ARIA roles
    - Check state changes are programmatically determinable
    - For infotainment: Check media controls, navigation states

28. **4.1.3 Status Messages (Level AA):**
    - Check important status updates use aria-live regions
    - For infotainment: Check notifications, alerts, progress updates

**INFOTAINMENT-SPECIFIC CONSIDERATIONS:**
- **Driver Safety:** Issues that could cause distraction while driving
- **Voice Integration:** Compatibility with voice assistants
- **Vibration Resilience:** Touch targets robust enough for vehicle movement
- **Emergency Access:** Critical functions accessible in emergency situations
- **Multi-modal Input:** Support for touch, voice, and physical controls

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

**FIX REQUIREMENTS:**
1. **Preserve Functionality:** Don't break existing behavior
2. **WCAG 2.2 Compliance:** Ensure fix meets specific guideline requirements
3. **Infotainment Optimized:** Consider driver safety and vehicle environment
4. **Code Quality:** Maintain existing code style and patterns
5. **Performance:** Ensure fix doesn't degrade performance
6. **Cross-Platform:** Work across different infotainment platforms

**WCAG-SPECIFIC FIX GUIDANCE:**

**For 1.1.1 Non-text Content:**
- Add descriptive alt attributes: alt="descriptive text"
- For decorative images: alt="" or role="presentation"
- For complex images: use aria-describedby pointing to detailed description

**For 2.1.1 Keyboard Access:**
- Add tabindex="0" for custom interactive elements
- Add onkeydown handlers: if(event.key === 'Enter' || event.key === ' ')
- Ensure logical tab order

**For 2.4.7 Focus Visible:**
- Add CSS focus styles: :focus {{ outline: 2px solid #0066cc; }}
- Ensure focus indicators are visible against all backgrounds

**For 2.5.8 Target Size:**
- Minimum 44x44 CSS pixels for touch targets
- Add CSS: min-height: 44px; min-width: 44px;

**For 3.3.2 Labels or Instructions:**
- Add <label for="inputId">Label Text</label>
- Or add aria-label="Label Text"
- Or add aria-labelledby="labelElementId"

**For 4.1.2 Name, Role, Value:**
- Add appropriate ARIA roles: role="button", role="tab", etc.
- Add aria-label for accessible names
- Add aria-expanded, aria-selected for state

**INFOTAINMENT BEST PRACTICES:**
- Voice Control: Ensure labels work with voice commands
- Large Touch Targets: Account for vehicle vibration
- High Contrast: Readable in various lighting conditions
- Quick Access: Critical functions easily reachable
- Error Recovery: Clear error states and recovery paths

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
            # Create numbered code for accurate line reference
            numbered_code = self._create_numbered_code(code)

            prompt = self.detection_prompt.format(
                code=code,
                numbered_code=numbered_code,
                filename=filename
            )

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
                        print(f"Rejected low-confidence issue: {issue.get('issue_id', 'Unknown')}")

                raw_result["issues"] = validated_issues
                raw_result["total_issues"] = len(validated_issues)

            return raw_result

        except Exception as e:
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
                            print(f"Rejected low-quality fix for issue: {issue['issue_id']}")

                except Exception as e:
                    print(f"Failed to fix issue {issue.get('issue_id', 'Unknown')}: {str(e)}")
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
        """Unified model calling with better error handling"""
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
            raise Exception(f"OpenAI API error: {str(e)}")

    async def _call_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Call Anthropic Claude API"""
        try:
            response = await self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000
            )
            content = response.content[0].text
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
            raise Exception(f"DeepSeek API error: {str(e)}")

    async def _call_replicate(self, prompt: str) -> Dict[str, Any]:
        """Call Replicate API for LLaMA"""
        try:
            output = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.replicate_client.run(
                    "meta/llama-2-70b-chat:02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3",
                    input={
                        "prompt": prompt,
                        "temperature": 0.1,
                        "max_new_tokens": 4000,
                        "system_prompt": "You are an expert accessibility auditor specializing in WCAG 2.2 compliance for infotainment systems."
                    }
                )
            )

            content = "".join(output) if isinstance(output, list) else str(output)
            return self._parse_json_response(content)

        except Exception as e:
            raise Exception(f"Replicate API error: {str(e)}")

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Enhanced JSON parsing with better error handling"""
        try:
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

            # Try to parse JSON
            parsed = json.loads(content)

            # Validate required fields
            if not isinstance(parsed.get("issues"), list):
                parsed["issues"] = []
            if not isinstance(parsed.get("total_issues"), int):
                parsed["total_issues"] = len(parsed.get("issues", []))

            return parsed

        except json.JSONDecodeError as e:
            # Extract any JSON-like content if possible
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass

            # Fallback response
            return {
                "total_issues": 0,
                "issues": [],
                "error": f"Failed to parse LLM response as JSON: {str(e)}",
                "raw_response": content[:500] + "..." if len(content) > 500 else content
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