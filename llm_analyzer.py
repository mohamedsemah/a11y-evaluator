import os
import json
import asyncio
import re
from typing import List, Dict, Any
from openai import AsyncOpenAI
import anthropic
from dotenv import load_dotenv

load_dotenv()


class InfotainmentLLMAnalyzer:
    def __init__(self):
        # Initialize API clients
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.replicate_api_key = os.getenv("REPLICATE_API_TOKEN")  # For Llama Maverick

        print(f"OpenAI API Key: {'✓ Set' if self.openai_api_key else '✗ Missing'}")
        print(f"Anthropic API Key: {'✓ Set' if self.anthropic_api_key else '✗ Missing'}")
        print(f"DeepSeek API Key: {'✓ Set' if self.deepseek_api_key else '✗ Missing'}")
        print(f"Replicate API Key: {'✓ Set' if self.replicate_api_key else '✗ Missing'}")

        # Initialize clients only if API keys are provided
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key) if self.anthropic_api_key else None

        # Enhanced file filtering for large projects
        self.MAX_FILES_PER_MODEL = 50  # Limit files per model to prevent timeouts
        self.MAX_LINES_PER_FILE = 1000  # Skip very large files
        self.PRIORITY_EXTENSIONS = {'.jsx', '.tsx', '.js', '.ts', '.html', '.qml', '.ui'}

        # Files to definitely skip (beyond what backend already filters)
        self.SKIP_PATTERNS = [
            r'\.min\.(js|css)$',  # Minified files
            r'bundle\.(js|css)$',  # Bundle files
            r'chunk\.\w+\.(js|css)$',  # Webpack chunks
            r'vendor\.(js|css)$',  # Vendor files
            r'polyfill\.(js|css)$',  # Polyfills
            r'\.d\.ts$',  # TypeScript definition files
            r'test\.(js|ts|jsx|tsx)$',  # Test files
            r'spec\.(js|ts|jsx|tsx)$',  # Spec files
            r'__tests__/',  # Test directories
            r'\.stories\.(js|jsx|ts|tsx)$',  # Storybook files
            r'\.config\.(js|ts)$',  # Config files
        ]

        # Base system prompt (will be customized based on selected standards)
        self.base_system_prompt = """You are an expert in infotainment system accessibility, specializing in automotive HMI design and comprehensive accessibility standards. Analyze the provided code for accessibility issues following the SELECTED standards only.

CRITICAL: You must respond with valid JSON in exactly this format:
{
  "issues": [
    {
      "file": "filename.ext",
      "line": 42,
      "type": "missing_alt_text",
      "severity": "safety_critical",
      "safety_critical": true,
      "wcag_criteria": ["1.1.1"],
      "wcag_level": "A",
      "wcag_principle": "Perceivable",
      "iso15008_criteria": ["visual_presentation", "character_height"],
      "nhtsa_criteria": ["eyes_off_road_time"],
      "sae_criteria": ["task_completion_time"],
      "gtr8_criteria": ["safety_critical_hmi"],
      "description": "Clear description of the accessibility issue",
      "original_code": "The problematic code snippet",
      "suggested_fix": "The corrected code snippet with accessibility improvements",
      "automotive_metrics": {
        "eyes_off_road_time": 2.5,
        "glance_count": 3,
        "task_time": 8.2
      },
      "context_conditions": {
        "lighting": "daylight",
        "driving_mode": true,
        "interaction_method": "touch"
      },
      "interaction_method": "touch"
    }
  ]
}

IMPORTANT: Only populate the criteria fields for standards that are being analyzed. If a standard is not selected, set its criteria field to null or omit it entirely.

"""

        # Infotainment-specific issue types
        self.infotainment_issue_types = [
            # Visual & Display
            'inadequate_daylight_contrast', 'inadequate_night_contrast', 'character_too_small_driving',
            'excessive_visual_complexity', 'poor_glare_control', 'color_dependency_driving',
            'animation_distraction', 'missing_alt_text', 'low_contrast',

            # Interaction & Control
            'complex_gesture_while_driving', 'inadequate_touch_targets', 'missing_physical_backup',
            'steering_wheel_inaccessible', 'voice_command_mismatch', 'accidental_activation',
            'poor_haptic_feedback', 'missing_label', 'keyboard_trap',

            # Timing & Attention
            'excessive_task_time', 'excessive_glance_time', 'excessive_glance_count',
            'no_progress_indication', 'timeout_too_short', 'cognitive_overload',

            # Audio & Voice
            'inadequate_voice_feedback', 'speech_interference', 'missing_audio_alternatives',
            'inconsistent_voice_commands', 'no_audio_ducking', 'poor_speech_recognition',

            # Safety & Emergency
            'blocked_critical_info', 'emergency_function_buried', 'system_failure_unsafe',
            'driver_trap', 'attention_capture',

            # Context & Adaptation
            'no_driving_mode_adaptation', 'poor_lighting_adaptation', 'missing_context_awareness',
            'passenger_driver_confusion',

            # Traditional Web Issues (Enhanced for Infotainment)
            'aria_issue', 'focus_issue', 'semantic_issue', 'heading_structure', 'table_headers'
        ]

    def _should_skip_file(self, filename: str, content: str) -> bool:
        """Enhanced file filtering to skip irrelevant files."""

        # Check against skip patterns
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                print(f"Skipping {filename} - matches skip pattern: {pattern}")
                return True

        # Skip very large files (likely generated/bundled)
        line_count = len(content.split('\n'))
        if line_count > self.MAX_LINES_PER_FILE:
            print(f"Skipping {filename} - too large ({line_count} lines)")
            return True

        # Skip files with mostly whitespace or comments
        non_empty_lines = [line.strip() for line in content.split('\n') if line.strip()]
        if len(non_empty_lines) < 10:  # Very small files probably not important
            print(f"Skipping {filename} - too few content lines ({len(non_empty_lines)})")
            return True

        # Check for generated file indicators
        first_lines = content[:500].lower()
        generated_indicators = [
            'this file is automatically generated',
            'auto-generated',
            'do not edit',
            'generated by webpack',
            'compiled by babel',
            'this file was procedurally generated'
        ]

        if any(indicator in first_lines for indicator in generated_indicators):
            print(f"Skipping {filename} - appears to be auto-generated")
            return True

        return False

    def _prioritize_files(self, file_contents: Dict[str, str]) -> List[str]:
        """Prioritize files for analysis based on relevance and importance."""
        files_with_scores = []

        for filename, content in file_contents.items():
            if self._should_skip_file(filename, content):
                continue

            score = 0
            filename_lower = filename.lower()

            # Priority by extension
            for ext in self.PRIORITY_EXTENSIONS:
                if filename_lower.endswith(ext):
                    score += 50
                    break

            # Priority by infotainment keywords
            infotainment_keywords = [
                'dashboard', 'navigation', 'media', 'climate', 'phone', 'settings',
                'hmi', 'cluster', 'instrument', 'display', 'screen', 'dialog',
                'component', 'widget', 'view', 'page', 'layout', 'interface'
            ]

            for keyword in infotainment_keywords:
                if keyword in filename_lower:
                    score += 30
                if keyword in content.lower()[:1000]:  # Check first 1000 chars
                    score += 10

            # Priority by accessibility-related content
            accessibility_keywords = [
                'aria-', 'role=', 'alt=', 'label', 'button', 'input', 'form',
                'accessible', 'accessibility', 'a11y', 'wcag', 'tabindex'
            ]

            content_sample = content.lower()[:2000]  # Check first 2000 chars
            for keyword in accessibility_keywords:
                if keyword in content_sample:
                    score += 15

            # Bonus for smaller, manageable files
            line_count = len(content.split('\n'))
            if 50 <= line_count <= 500:  # Sweet spot for analysis
                score += 20
            elif line_count <= 50:
                score += 10

            # Penalty for very large files
            if line_count > 800:
                score -= 30

            files_with_scores.append((filename, score))

        # Sort by score and return top files
        files_with_scores.sort(key=lambda x: x[1], reverse=True)
        prioritized_files = [f[0] for f in files_with_scores[:self.MAX_FILES_PER_MODEL]]

        print(f"Prioritized {len(prioritized_files)} files out of {len(file_contents)} for analysis")
        if len(prioritized_files) < len(file_contents):
            skipped_count = len(file_contents) - len(prioritized_files)
            print(f"Skipped {skipped_count} files (low priority/irrelevant)")

        return prioritized_files

    def _get_system_prompt_for_standards(self, selected_standards: List[str]) -> str:
        """Generate system prompt with only selected standards."""
        prompt = self.base_system_prompt

        # Add standard-specific sections based on selection
        standards_content = "\n=== STANDARDS TO ANALYZE AGAINST ===\n\n"

        if "WCAG 2.2" in selected_standards or "WCAG" in selected_standards:
            standards_content += """
🌐 WCAG 2.1/2.2 SUCCESS CRITERIA (Primary Focus):
Level A (Essential):
- 1.1.1 Non-text Content: All images, icons, media need text alternatives for voice control
- 1.2.1 Audio/Video alternatives: Traffic alerts need visual indicators, music needs visual metadata
- 1.3.1 Info/Relationships: Screen readers must understand infotainment structure
- 1.3.2 Meaningful Sequence: Voice navigation must follow logical order
- 1.3.3 Sensory Characteristics: Cannot rely only on "red button" or sound cues
- 1.4.1 Use of Color: Status indicators need more than color (patterns, text, icons)
- 1.4.2 Audio Control: All audio must have pause/volume controls
- 2.1.1 Keyboard: All functions accessible via steering wheel controls/physical buttons
- 2.1.2 No Keyboard Trap: Drivers must never be trapped in interface (SAFETY CRITICAL)
- 2.2.1 Timing Adjustable: Drivers need time to safely interact while driving
- 2.2.2 Pause/Stop: Moving content causes distraction (SAFETY CRITICAL)
- 2.3.1 Three Flashes: No rapid flashing in confined vehicle space (SAFETY CRITICAL)
- 2.4.1 Bypass Blocks: Skip to main content for voice navigation efficiency
- 2.4.2 Page Titled: Screen titles must be announced clearly
- 2.4.3 Focus Order: Critical for safe operation while driving
- 2.4.4 Link Purpose: Links/buttons clear for voice control and quick scanning
- 2.5.1 Pointer Gestures: Complex gestures dangerous while driving - need alternatives
- 2.5.2 Pointer Cancellation: Can cancel accidental touches while driving
- 2.5.3 Label in Name: Voice commands must match visible labels exactly
- 2.5.4 Motion Actuation: Vehicle motion could trigger unintended actions
- 3.1.1 Language: Important for multilingual drivers and voice systems
- 3.2.1 On Focus: Focus changes cannot cause unexpected navigation (SAFETY CRITICAL)
- 3.2.2 On Input: Form changes cannot auto-navigate (SAFETY CRITICAL)
- 3.3.1 Error Identification: Critical for voice input and quick glances
- 3.3.2 Labels/Instructions: Essential for voice control
- 4.1.1 Parsing: Valid markup for reliable screen reader operation
- 4.1.2 Name/Role/Value: Critical for assistive technology integration

Level AA (Standard):
- 1.4.3 Contrast: More critical in vehicles due to varying lighting/viewing angles
- 1.4.4 Resize Text: Important for aging drivers and varied seating positions
- 1.4.5 Images of Text: Critical for multilingual infotainment systems
- 2.4.6 Headings/Labels: Critical for quick scanning while driving
- 2.4.7 Focus Visible: Essential for mixed input methods, all lighting conditions
- 3.2.3 Consistent Navigation: Predictable navigation critical for driver safety
- 3.2.4 Consistent Identification: Same functions must work the same way
- 3.3.3 Error Suggestion: Provide suggestions for fixing input errors
- 3.3.4 Error Prevention: Prevent errors in legal/financial/data deletion contexts
- 4.1.3 Status Messages: Status updates must be announced to screen readers
"""

        if "ISO15008" in selected_standards:
            standards_content += """
🚗 ISO 15008:2017 - Visual Presentation in Vehicles:
- Character Height: Minimum 16 arc minutes for driving tasks
- Contrast Ratio: Enhanced requirements for automotive lighting conditions
- Viewing Distance: Account for typical driver seating positions (600-700mm)
- Luminance: Adapt to interior lighting conditions (day/night modes)
- Color Coding: Maximum 6 colors for categorical information
- Glare Control: Minimize reflections and glare in all lighting
- Font Requirements: Sans-serif fonts recommended for vehicle displays
"""

        if "NHTSA" in selected_standards:
            standards_content += """
🚨 NHTSA Driver Distraction Guidelines:
- 12-Second Rule: Tasks must be completable in 12 seconds of glances
- 2-Second Rule: Individual glances must not exceed 2 seconds
- Eyes-Off-Road: Total eyes-off-road time minimized
- Manual Task Limits: Restrict manual input while driving
- Voice Priority: Encourage voice interaction for complex tasks
- Emergency Access: Critical functions always accessible
- Lock-Out Features: Some functions disabled while driving
"""

        if "SAE J3016" in selected_standards or "SAE" in selected_standards:
            standards_content += """
⚡ SAE J2364 & J2365 - Task Time & Speech Interface:
- 15-Second Rule: Driver information tasks under 15 seconds
- Task Complexity: Minimize cognitive load during driving
- Speech Interface: Clear prompts and feedback
- Error Recovery: Quick recovery from speech recognition errors
- Confirmation: Critical actions require confirmation
- Context Awareness: Adapt interface based on driving conditions
"""

        if "GTR8" in selected_standards:
            standards_content += """
🛡️ GTR No. 8 - Safety & Human-Machine Interface:
- Safety-Critical Functions: Must remain accessible during system failures
- Redundancy: Critical information available through multiple channels  
- Fail-Safe Design: System failures must not compromise safety
- Driver State Monitoring: Adapt to driver attention/workload
- Emergency Override: Driver can always override automated systems
"""

        # Add the rest of the original prompt content
        standards_content += """

=== INFOTAINMENT-SPECIFIC ISSUE TYPES ===

Visual & Display Issues:
- inadequate_daylight_contrast: Text/icons not visible in bright sunlight
- inadequate_night_contrast: Poor visibility in dark conditions
- character_too_small_driving: Text too small for safe reading while driving
- excessive_visual_complexity: Too much information causing cognitive overload
- poor_glare_control: Reflections interfering with display visibility
- color_dependency_driving: Critical info relies only on color differentiation
- animation_distraction: Moving elements cause dangerous distraction

Interaction & Control Issues:
- complex_gesture_while_driving: Multi-touch gestures unsafe for drivers
- inadequate_touch_targets: Touch areas too small for vehicle vibration/movement
- missing_physical_backup: No physical button alternative for touch controls
- steering_wheel_inaccessible: Functions not reachable from steering wheel
- voice_command_mismatch: Voice commands don't match visible labels
- accidental_activation: Easy to trigger unintended actions while driving
- poor_haptic_feedback: Insufficient tactile confirmation of actions

Timing & Attention Issues:
- excessive_task_time: Tasks take too long, causing extended distraction
- excessive_glance_time: Single glances exceed safe 2-second limit
- excessive_glance_count: Too many glances needed to complete task
- no_progress_indication: User can't estimate remaining task time
- timeout_too_short: Interface times out before driver can safely respond
- cognitive_overload: Too much mental processing required while driving

Audio & Voice Issues:
- inadequate_voice_feedback: Poor or missing audio confirmation
- speech_interference: Background noise interferes with voice commands
- missing_audio_alternatives: Visual-only feedback inaccessible while driving
- inconsistent_voice_commands: Voice interface behaves unpredictably
- no_audio_ducking: Media doesn't reduce volume for navigation/alerts
- poor_speech_recognition: Voice system frequently misunderstands

Safety & Emergency Issues:
- blocked_critical_info: Safety info obscured by other interface elements
- emergency_function_buried: Emergency features not quickly accessible
- system_failure_unsafe: Interface fails unsafely or without warning
- driver_trap: Interface state prevents return to safe operation
- attention_capture: Interface demands attention at unsafe moments

Context & Adaptation Issues:
- no_driving_mode_adaptation: Interface identical whether driving or parked
- poor_lighting_adaptation: No automatic day/night mode switching
- missing_context_awareness: Interface doesn't adapt to driving conditions
- passenger_driver_confusion: Interface doesn't distinguish target user

=== SEVERITY CLASSIFICATION (Enhanced for Infotainment) ===

SAFETY_CRITICAL: Could cause accident or prevent access to safety functions
- Driver trapped in interface unable to access critical controls
- Emergency functions inaccessible or blocked
- Interface causes dangerous distraction (>2s glances, >12s total task time)
- Critical safety information blocked or unclear
- System failure creates unsafe condition

CRITICAL: Significantly impacts driver safety or system usability
- Excessive task completion time (8-12 seconds)
- Poor contrast making interface difficult to read while driving
- Complex interactions requiring too much attention
- Missing voice alternatives for visual-only information
- Inaccessible emergency or frequently-used functions

HIGH: Important accessibility issues affecting user experience
- WCAG AA violations that impact driver comfort/efficiency
- Moderate contrast or sizing issues
- Missing alternative input methods
- Voice command inconsistencies
- Poor error feedback

MEDIUM: Noticeable accessibility issues with workarounds
- WCAG A violations with alternative access methods
- Minor contrast or interaction issues
- Inconsistent interface behavior
- Missing helpful features

LOW: Minor accessibility improvements
- WCAG AAA enhancements
- Convenience features for accessibility
- Minor usability improvements

=== CONTEXT CONDITIONS TO CONSIDER ===

Lighting Conditions:
- "daylight": Bright sunlight, high ambient light
- "night": Dark conditions, low ambient light  
- "twilight": Mixed lighting conditions
- "tunnel": Rapidly changing light conditions

Driving States:
- driving_mode: true/false - Is vehicle in motion?
- speed_range: "0", "1-30", "31-60", "61+" - Speed affects attention availability
- traffic_conditions: "heavy", "moderate", "light" - Affects cognitive load

User Context:
- attention_level: "full", "divided", "minimal" - Available attention for interface
- user_state: "alert", "tired", "stressed" - User condition affects interaction ability
- experience_level: "novice", "experienced" - Familiarity with system

Interaction Methods:
- "touch": Touchscreen interaction
- "voice": Voice commands and feedback
- "gesture": Hand gestures, air gestures
- "physical_button": Hardware buttons, knobs, switches
- "steering_wheel": Steering wheel mounted controls
- "eye_tracking": Gaze-based interaction
- "mixed": Multiple interaction methods combined

Your analysis should:
1. Identify violations ONLY for the selected standards: """ + ", ".join(selected_standards) + """
2. Consider automotive context and safety implications
3. Provide specific metrics for eyes-off-road time, glance count, task time
4. Suggest fixes appropriate for infotainment systems
5. Classify safety criticality appropriately
6. Consider multiple interaction methods and contexts
7. Only populate criteria fields for the selected standards - set others to null
8. Focus on the most important accessibility issues in each file"""

        return prompt + standards_content

    async def analyze_with_openai(self, file_contents: Dict[str, str], model: str) -> List[Dict]:
        """Analyze code using OpenAI models with enhanced filtering."""
        if not self.openai_client:
            raise Exception("OpenAI API key not configured")

        all_issues = []

        # Prioritize files for analysis
        prioritized_files = self._prioritize_files(file_contents)
        print(f"OpenAI {model}: Analyzing {len(prioritized_files)} prioritized files")

        # Get the appropriate system prompt based on selected standards
        system_prompt = self._get_system_prompt_for_standards(self.current_selected_standards)

        for filename in prioritized_files:
            content = file_contents[filename]
            try:
                print(f"Analyzing {filename} with OpenAI {model}... ({len(content.split())} words)")

                # Prepare the code for analysis
                code_with_lines = self._add_line_numbers(content)
                context_prompt = self._get_context_prompt(filename)

                response = await self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",
                         "content": f"Analyze this {filename} file for infotainment accessibility issues. Focus on the most critical issues only:\n\n{context_prompt}\n\n{code_with_lines}"}
                    ],
                    temperature=0.1,
                    max_tokens=4000,  # Limit response size
                    response_format={"type": "json_object"}
                )

                # Parse the response
                result = json.loads(response.choices[0].message.content)
                issues = result.get("issues", [])

                print(f"Found {len(issues)} issues in {filename}")

                # Add filename and enhance each issue
                for issue in issues:
                    if "file" not in issue:
                        issue["file"] = filename
                    self._enhance_issue_data(issue, filename)
                    all_issues.append(issue)

            except Exception as e:
                print(f"Error analyzing {filename} with OpenAI: {str(e)}")
                continue

        print(f"OpenAI {model} analysis complete: {len(all_issues)} total issues found")
        return all_issues

    def analyze_with_anthropic_sync(self, file_contents: Dict[str, str], model: str) -> List[Dict]:
        """Analyze code using Anthropic models with enhanced filtering."""
        if not self.anthropic_client:
            raise Exception("Anthropic API key not configured")

        all_issues = []

        # Prioritize files for analysis
        prioritized_files = self._prioritize_files(file_contents)
        print(f"Anthropic {model}: Analyzing {len(prioritized_files)} prioritized files")

        # Get the appropriate system prompt based on selected standards
        system_prompt = self._get_system_prompt_for_standards(self.current_selected_standards)

        # Map requested model to actual Anthropic model
        anthropic_model_map = {
            "claude-opus-4": "claude-3-5-sonnet-20241022",
            "claude-3-opus": "claude-3-opus-20240229",
            "claude-3-sonnet": "claude-3-5-sonnet-20241022"
        }

        actual_model = anthropic_model_map.get(model, "claude-3-5-sonnet-20241022")
        print(f"Using Anthropic model: {actual_model}")

        for filename in prioritized_files:
            content = file_contents[filename]
            try:
                print(f"Analyzing {filename} with Anthropic {actual_model}... ({len(content.split())} words)")

                # Prepare the code for analysis
                code_with_lines = self._add_line_numbers(content)
                context_prompt = self._get_context_prompt(filename)

                response = self.anthropic_client.messages.create(
                    model=actual_model,
                    max_tokens=4000,  # Limit response size
                    temperature=0.1,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": f"Analyze this {filename} file for critical infotainment accessibility issues and return ONLY valid JSON:\n\n{context_prompt}\n\n{code_with_lines}"
                        }
                    ]
                )

                # Extract content from response
                content_text = response.content[0].text
                print(f"Raw response for {filename}: {content_text[:200]}...")

                # Parse JSON from the response
                issues = self._extract_json_from_response(content_text, filename)

                print(f"Found {len(issues)} issues in {filename}")

                # Add filename and enhance each issue
                for issue in issues:
                    if "file" not in issue:
                        issue["file"] = filename
                    self._enhance_issue_data(issue, filename)
                    all_issues.append(issue)

            except Exception as e:
                print(f"Error analyzing {filename} with Anthropic: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        print(f"Anthropic {model} analysis complete: {len(all_issues)} total issues found")
        return all_issues

    async def analyze_with_deepseek(self, file_contents: Dict[str, str]) -> List[Dict]:
        """Analyze code using DeepSeek V3 model with enhanced filtering."""
        import httpx

        if not self.deepseek_api_key:
            print("DeepSeek API key not configured")
            return []

        print(f"Starting DeepSeek V3 infotainment analysis...")
        all_issues = []

        # Prioritize files for analysis
        prioritized_files = self._prioritize_files(file_contents)
        print(f"DeepSeek V3: Analyzing {len(prioritized_files)} prioritized files")

        # Get the appropriate system prompt based on selected standards
        system_prompt = self._get_system_prompt_for_standards(self.current_selected_standards)

        async with httpx.AsyncClient(timeout=120.0) as client:  # Reduced timeout
            for filename in prioritized_files:
                content = file_contents[filename]
                print(f"Analyzing {filename} with DeepSeek V3... ({len(content.split())} words)")
                code_with_lines = self._add_line_numbers(content)
                context_prompt = self._get_context_prompt(filename)

                try:
                    response = await client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.deepseek_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user",
                                 "content": f"Analyze this {filename} file for critical infotainment accessibility issues:\n\n{context_prompt}\n\n{code_with_lines}"}
                            ],
                            "temperature": 0.1,
                            "max_tokens": 4000,  # Limit response size
                            "stream": False
                        }
                    )

                    print(f"DeepSeek V3 API response status: {response.status_code}")

                    if response.status_code != 200:
                        error_text = response.text
                        print(f"DeepSeek V3 API error: {response.status_code} - {error_text}")
                        continue

                    result = response.json()

                    if "choices" not in result or not result["choices"]:
                        print(f"No choices in DeepSeek V3 response for {filename}")
                        continue

                    content_text = result["choices"][0]["message"]["content"]
                    print(f"DeepSeek V3 response for {filename}: {content_text[:300]}...")

                    # Enhanced JSON extraction for DeepSeek V3
                    issues = self._extract_json_from_deepseek_v3(content_text, filename)
                    print(f"Extracted {len(issues)} issues from DeepSeek V3 for {filename}")

                    # Add filename and enhance each issue
                    for issue in issues:
                        if "file" not in issue:
                            issue["file"] = filename
                        self._enhance_issue_data(issue, filename)
                        all_issues.append(issue)

                except httpx.TimeoutException:
                    print(f"DeepSeek V3 API timeout for {filename}")
                    continue
                except Exception as e:
                    print(f"DeepSeek V3 analysis error for {filename}: {str(e)}")
                    continue

        print(f"DeepSeek V3 infotainment analysis complete. Total issues found: {len(all_issues)}")
        return all_issues

    async def analyze_with_llama_maverick(self, file_contents: Dict[str, str]) -> List[Dict]:
        """Analyze code using Llama Maverick model via Replicate API with enhanced filtering."""
        import httpx

        if not self.replicate_api_key:
            print("Replicate API key not configured for Llama Maverick")
            return []

        print(f"Starting Llama Maverick infotainment analysis...")
        all_issues = []

        # Prioritize files for analysis
        prioritized_files = self._prioritize_files(file_contents)
        print(f"Llama Maverick: Analyzing {len(prioritized_files)} prioritized files")

        # Get the appropriate system prompt based on selected standards
        system_prompt = self._get_system_prompt_for_standards(self.current_selected_standards)

        async with httpx.AsyncClient(timeout=180.0) as client:  # Longer timeout for Llama
            for filename in prioritized_files:
                content = file_contents[filename]
                print(f"Analyzing {filename} with Llama Maverick... ({len(content.split())} words)")
                code_with_lines = self._add_line_numbers(content)
                context_prompt = self._get_context_prompt(filename)

                try:
                    # Replicate API call for Llama Maverick
                    response = await client.post(
                        "https://api.replicate.com/v1/predictions",
                        headers={
                            "Authorization": f"Token {self.replicate_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "version": "02e509c789964a7ea8736978a43525956ef40397be9033abf9fd2badfe68c9e3",
                            "input": {
                                "system_prompt": system_prompt,
                                "prompt": f"Analyze this {filename} file for critical infotainment accessibility issues and return valid JSON:\n\n{context_prompt}\n\n{code_with_lines}",
                                "max_new_tokens": 2048,  # Limit response size
                                "temperature": 0.1,
                                "top_p": 0.9,
                                "repetition_penalty": 1.15
                            }
                        }
                    )

                    print(f"Llama Maverick API response status: {response.status_code}")

                    if response.status_code != 201:
                        error_text = response.text
                        print(f"Llama Maverick API error: {response.status_code} - {error_text}")
                        continue

                    prediction = response.json()
                    prediction_id = prediction["id"]

                    # Poll for completion with shorter timeout
                    max_polls = 30  # Reduced from 60 - 2.5 minutes max
                    for poll_count in range(max_polls):
                        await asyncio.sleep(5)  # Wait 5 seconds between polls

                        status_response = await client.get(
                            f"https://api.replicate.com/v1/predictions/{prediction_id}",
                            headers={"Authorization": f"Token {self.replicate_api_key}"}
                        )

                        if status_response.status_code == 200:
                            status_data = status_response.json()

                            if status_data["status"] == "succeeded":
                                output = status_data["output"]
                                if isinstance(output, list):
                                    content_text = "".join(output)
                                else:
                                    content_text = str(output)

                                print(f"Llama Maverick response for {filename}: {content_text[:300]}...")

                                # Extract JSON from Llama response
                                issues = self._extract_json_from_llama_maverick(content_text, filename)
                                print(f"Extracted {len(issues)} issues from Llama Maverick for {filename}")

                                # Add filename and enhance each issue
                                for issue in issues:
                                    if "file" not in issue:
                                        issue["file"] = filename
                                    self._enhance_issue_data(issue, filename)
                                    all_issues.append(issue)
                                break

                            elif status_data["status"] == "failed":
                                print(
                                    f"Llama Maverick prediction failed for {filename}: {status_data.get('error', 'Unknown error')}")
                                break

                    else:
                        print(f"Llama Maverick analysis timeout for {filename}")

                except httpx.TimeoutException:
                    print(f"Llama Maverick API timeout for {filename}")
                    continue
                except Exception as e:
                    print(f"Llama Maverick analysis error for {filename}: {str(e)}")
                    continue

        print(f"Llama Maverick infotainment analysis complete. Total issues found: {len(all_issues)}")
        return all_issues

    def _is_infotainment_file(self, filename: str) -> bool:
        """Check if file is relevant for infotainment accessibility analysis."""
        # Web-based infotainment files
        web_extensions = ['.html', '.htm', '.jsx', '.tsx', '.js', '.ts', '.css', '.vue', '.svelte']

        # Embedded infotainment files
        embedded_extensions = ['.qml', '.ui', '.xml', '.cpp', '.c', '.h', '.hpp', '.swift', '.kt', '.java']

        # Configuration and resource files
        config_extensions = ['.json', '.yaml', '.yml', '.plist', '.properties', '.cfg']

        # Check file extension
        if any(filename.lower().endswith(ext) for ext in web_extensions + embedded_extensions + config_extensions):
            return True

        # Check for infotainment-specific keywords in filename
        infotainment_keywords = [
            'hmi', 'dashboard', 'cluster', 'infotainment', 'vehicle', 'automotive',
            'carplay', 'androidauto', 'navigation', 'media', 'climate', 'settings',
            'radio', 'music', 'phone', 'contacts', 'maps', 'traffic', 'voice'
        ]

        return any(keyword in filename.lower() for keyword in infotainment_keywords)

    def _get_context_prompt(self, filename: str) -> str:
        """Generate context-specific analysis prompt based on filename."""
        filename_lower = filename.lower()

        if any(word in filename_lower for word in ['dashboard', 'cluster', 'gauge']):
            return """CONTEXT: This appears to be an instrument cluster/dashboard interface file. 
Focus on: Safety-critical information display, glance time minimization, high contrast for all lighting conditions, 
clear hierarchy of information, and accessibility during driving."""

        elif any(word in filename_lower for word in ['navigation', 'maps', 'gps']):
            return """CONTEXT: This appears to be a navigation/maps interface file.
Focus on: Voice guidance accessibility, touch target sizes for in-motion use, clear visual hierarchy, 
turn-by-turn instruction clarity, and emergency/alternative route accessibility."""

        elif any(word in filename_lower for word in ['media', 'music', 'radio', 'audio']):
            return """CONTEXT: This appears to be a media/audio interface file.
Focus on: Voice control for all functions, audio feedback, large touch targets, 
quick access to frequently used controls, and audio ducking for safety announcements."""

        elif any(word in filename_lower for word in ['phone', 'contacts', 'call']):
            return """CONTEXT: This appears to be a phone/communication interface file.
Focus on: Hands-free operation, voice dialing, emergency contact accessibility, 
call management during driving, and integration with steering wheel controls."""

        elif any(word in filename_lower for word in ['climate', 'hvac', 'temperature']):
            return """CONTEXT: This appears to be a climate control interface file.
Focus on: Quick access to common adjustments, voice control for temperature, 
physical backup controls, clear visual feedback, and minimal distraction design."""

        elif any(word in filename_lower for word in ['settings', 'config', 'preferences']):
            return """CONTEXT: This appears to be a settings/configuration interface file.
Focus on: Parked-only complex settings, clear navigation hierarchy, voice guidance through menus, 
undo functionality, and prevention of accidental changes while driving."""

        else:
            return """CONTEXT: This appears to be a general infotainment interface file.
Focus on: Overall system accessibility, consistent interaction patterns, 
voice control integration, and comprehensive WCAG compliance for automotive context."""

    def _filter_issue_by_standards(self, issue: Dict) -> None:
        """Filter issue criteria based on selected standards."""
        if not hasattr(self, 'current_selected_standards'):
            return

        selected = self.current_selected_standards

        # Only keep criteria for selected standards
        if "WCAG 2.2" not in selected and "WCAG" not in selected:
            issue["wcag_criteria"] = None
            issue["wcag_level"] = None
            issue["wcag_principle"] = None

        if "ISO15008" not in selected:
            issue["iso15008_criteria"] = None

        if "NHTSA" not in selected:
            issue["nhtsa_criteria"] = None

        if "SAE" not in selected and "SAE J3016" not in selected:
            issue["sae_criteria"] = None

        if "GTR8" not in selected:
            issue["gtr8_criteria"] = None

    def _enhance_issue_data(self, issue: Dict, filename: str) -> None:
        """Enhance issue data with additional infotainment-specific information."""
        # Ensure required fields exist with defaults
        if "safety_critical" not in issue:
            issue["safety_critical"] = issue.get("severity") == "safety_critical"

        if "wcag_criteria" not in issue:
            issue["wcag_criteria"] = []

        if "automotive_metrics" not in issue:
            issue["automotive_metrics"] = {
                "eyes_off_road_time": self._estimate_eyes_off_road_time(issue),
                "glance_count": self._estimate_glance_count(issue),
                "task_time": self._estimate_task_time(issue)
            }

        if "context_conditions" not in issue:
            issue["context_conditions"] = {
                "lighting": "variable",
                "driving_mode": True,
                "interaction_method": self._determine_interaction_method(issue, filename)
            }

        if "interaction_method" not in issue:
            issue["interaction_method"] = self._determine_interaction_method(issue, filename)

        # Filter based on selected standards
        self._filter_issue_by_standards(issue)

    def _estimate_eyes_off_road_time(self, issue: Dict) -> float:
        """Estimate eyes-off-road time based on issue type and complexity."""
        issue_type = issue.get("type", "")
        severity = issue.get("severity", "medium")

        base_times = {
            "inadequate_daylight_contrast": 3.0,
            "character_too_small_driving": 4.0,
            "excessive_visual_complexity": 5.0,
            "missing_alt_text": 2.5,
            "complex_gesture_while_driving": 6.0,
            "inadequate_touch_targets": 3.5,
            "poor_haptic_feedback": 2.0,
            "excessive_task_time": 8.0,
            "cognitive_overload": 7.0
        }

        base_time = base_times.get(issue_type, 2.0)

        # Adjust based on severity
        severity_multipliers = {
            "safety_critical": 2.0,
            "critical": 1.5,
            "high": 1.2,
            "medium": 1.0,
            "low": 0.8
        }

        return base_time * severity_multipliers.get(severity, 1.0)

    def _estimate_glance_count(self, issue: Dict) -> int:
        """Estimate number of glances required based on issue complexity."""
        issue_type = issue.get("type", "")

        glance_counts = {
            "excessive_visual_complexity": 5,
            "poor_glare_control": 4,
            "inadequate_touch_targets": 3,
            "missing_label": 2,
            "character_too_small_driving": 3,
            "cognitive_overload": 6
        }

        return glance_counts.get(issue_type, 2)

    def _estimate_task_time(self, issue: Dict) -> float:
        """Estimate total task completion time based on issue impact."""
        issue_type = issue.get("type", "")

        task_times = {
            "complex_gesture_while_driving": 15.0,
            "excessive_task_time": 20.0,
            "cognitive_overload": 18.0,
            "missing_physical_backup": 12.0,
            "voice_command_mismatch": 10.0,
            "inadequate_touch_targets": 8.0,
            "poor_haptic_feedback": 6.0
        }

        return task_times.get(issue_type, 5.0)

    def _determine_interaction_method(self, issue: Dict, filename: str) -> str:
        """Determine primary interaction method based on issue and file context."""
        issue_type = issue.get("type", "")
        filename_lower = filename.lower()

        # Voice-related issues
        if any(word in issue_type for word in ["voice", "speech", "audio"]):
            return "voice"

        # Touch-related issues
        if any(word in issue_type for word in ["touch", "gesture", "tap"]):
            return "touch"

        # Physical control issues
        if any(word in issue_type for word in ["physical", "button", "steering"]):
            return "physical_button"

        # File-based determination
        if any(word in filename_lower for word in ["voice", "speech", "audio"]):
            return "voice"
        elif any(word in filename_lower for word in ["touch", "gesture"]):
            return "touch"
        elif any(word in filename_lower for word in ["button", "physical", "steering"]):
            return "steering_wheel"
        else:
            return "mixed"

    def _extract_json_from_response(self, content_text: str, filename: str) -> List[Dict]:
        """Extract and parse JSON from Claude's response."""
        try:
            # First, try to parse the entire response as JSON
            result = json.loads(content_text)
            return result.get("issues", [])
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in the response
        json_patterns = [
            r'\{[\s\S]*\}',  # Find JSON object
            r'```json\s*(\{[\s\S]*?\})\s*```',  # JSON in code block
            r'```\s*(\{[\s\S]*?\})\s*```',  # JSON in generic code block
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content_text, re.DOTALL)
            for match in matches:
                try:
                    # Clean up the JSON string
                    json_str = match.strip()
                    result = json.loads(json_str)
                    return result.get("issues", [])
                except json.JSONDecodeError:
                    continue

        # If no valid JSON found, try to create a simple issue from the text
        print(f"Could not parse JSON from Claude response for {filename}. Creating fallback issue.")

        # Create a fallback issue if Claude found something but couldn't format it properly
        if any(keyword in content_text.lower() for keyword in
               ['accessibility', 'issue', 'problem', 'missing', 'alt', 'label', 'contrast', 'infotainment']):
            return [{
                "file": filename,
                "line": 1,
                "type": "semantic_issue",
                "severity": "medium",
                "safety_critical": False,
                "wcag_criteria": [],
                "description": "Claude detected potential accessibility issues but response format was invalid. Please review manually.",
                "original_code": "Response parsing failed",
                "suggested_fix": "Manual review required",
                "automotive_metrics": {"eyes_off_road_time": 2.0, "glance_count": 2, "task_time": 5.0},
                "context_conditions": {"lighting": "variable", "driving_mode": True, "interaction_method": "mixed"},
                "interaction_method": "mixed"
            }]

        return []

    def _extract_json_from_deepseek_v3(self, content_text: str, filename: str) -> List[Dict]:
        """Enhanced JSON extraction specifically for DeepSeek V3 responses."""
        try:
            # First, try to parse the entire response as JSON
            result = json.loads(content_text.strip())
            return result.get("issues", [])
        except json.JSONDecodeError:
            pass

        # Try to find JSON block patterns common in DeepSeek V3 responses
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[^}]*"issues"[^}]*\[.*?\]\s*\})',
            r'(\{.*?"issues".*?\})',
            r'(\{[\s\S]*\})',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    # Clean up the JSON string
                    json_str = match.strip()
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)

                    result = json.loads(json_str)
                    if isinstance(result, dict) and "issues" in result:
                        return result["issues"]
                    elif isinstance(result, list):
                        return result
                except json.JSONDecodeError:
                    continue

        # If no valid JSON found, create fallback
        print(f"Could not parse JSON from DeepSeek V3 response for {filename}")

        # Look for infotainment accessibility-related keywords
        infotainment_keywords = [
            'accessibility', 'wcag', 'contrast', 'voice control', 'touch target',
            'driver distraction', 'safety critical', 'eyes off road', 'infotainment'
        ]

        if any(keyword.lower() in content_text.lower() for keyword in infotainment_keywords):
            return [{
                "file": filename,
                "line": 1,
                "type": "accessibility_issue",
                "severity": "medium",
                "safety_critical": False,
                "wcag_criteria": [],
                "description": "DeepSeek V3 detected potential infotainment accessibility issues but response format was invalid. Please review manually.",
                "original_code": "See description",
                "suggested_fix": "Review infotainment accessibility guidelines",
                "automotive_metrics": {"eyes_off_road_time": 2.5, "glance_count": 2, "task_time": 6.0},
                "context_conditions": {"lighting": "variable", "driving_mode": True, "interaction_method": "mixed"},
                "interaction_method": "mixed"
            }]

        return []

    def _extract_json_from_llama_maverick(self, content_text: str, filename: str) -> List[Dict]:
        """Enhanced JSON extraction specifically for Llama Maverick responses."""
        try:
            # First, try to parse the entire response as JSON
            result = json.loads(content_text.strip())
            return result.get("issues", [])
        except json.JSONDecodeError:
            pass

        # Try to find JSON block patterns common in Llama responses
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[^}]*"issues"[^}]*\[.*?\]\s*\})',
            r'(\{.*?"issues".*?\})',
            r'(\{[\s\S]*\})',
            # Llama sometimes returns without proper JSON formatting
            r'"issues":\s*\[(.*?)\]',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, content_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    # Clean up the JSON string for Llama responses
                    json_str = match.strip()

                    # Handle Llama-specific formatting issues
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    json_str = re.sub(r'}\s*{', '},{', json_str)  # Fix missing commas between objects

                    # Try to wrap in proper JSON structure if it's just the issues array
                    if json_str.startswith('[') and json_str.endswith(']'):
                        json_str = f'{{"issues": {json_str}}}'

                    result = json.loads(json_str)
                    if isinstance(result, dict) and "issues" in result:
                        return result["issues"]
                    elif isinstance(result, list):
                        return result
                except json.JSONDecodeError:
                    continue

        # If no valid JSON found, create fallback
        print(f"Could not parse JSON from Llama Maverick response for {filename}")

        # Look for infotainment accessibility-related keywords
        infotainment_keywords = [
            'accessibility', 'wcag', 'contrast', 'voice control', 'touch target',
            'driver distraction', 'safety critical', 'eyes off road', 'infotainment'
        ]

        if any(keyword.lower() in content_text.lower() for keyword in infotainment_keywords):
            return [{
                "file": filename,
                "line": 1,
                "type": "accessibility_issue",
                "severity": "medium",
                "safety_critical": False,
                "wcag_criteria": [],
                "description": "Llama Maverick detected potential infotainment accessibility issues but response format was invalid. Please review manually.",
                "original_code": "See description",
                "suggested_fix": "Review infotainment accessibility guidelines and automotive standards",
                "automotive_metrics": {"eyes_off_road_time": 2.3, "glance_count": 2, "task_time": 5.8},
                "context_conditions": {"lighting": "variable", "driving_mode": True, "interaction_method": "mixed"},
                "interaction_method": "mixed"
            }]

        return []

    def _add_line_numbers(self, content: str) -> str:
        """Add line numbers to code for easier reference."""
        lines = content.split('\n')
        numbered_lines = []
        for i, line in enumerate(lines, 1):
            numbered_lines.append(f"{i:4d}: {line}")
        return '\n'.join(numbered_lines)

    async def analyze_with_anthropic(self, file_contents: Dict[str, str], model: str) -> List[Dict]:
        """Async wrapper for Anthropic analysis."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.analyze_with_anthropic_sync, file_contents, model)

    async def analyze_code(self, file_contents: Dict[str, str], model: str, analysis_id: str,
                           selected_standards: List[str] = None) -> List[Dict]:
        """
        Analyze code for infotainment accessibility issues using specified LLM model.

        Args:
            file_contents: Dictionary mapping filenames to their content
            model: LLM model to use ('gpt-4o', 'claude-opus-4', 'Deepseek-V3', 'llama-maverick')
            analysis_id: Unique identifier for this analysis
            selected_standards: List of standards to check against

        Returns:
            List of infotainment accessibility issues found
        """
        try:
            print(f"Starting infotainment accessibility analysis with {model} for analysis {analysis_id}")
            print(f"Total files uploaded: {len(file_contents)}")
            print(f"Selected standards: {selected_standards}")

            # Store selected standards for filtering
            self.current_selected_standards = selected_standards or ["WCAG 2.2", "ISO15008", "NHTSA"]

            if model == "gpt-4o":
                return await self.analyze_with_openai(file_contents, "gpt-4o")
            elif model == "claude-opus-4":
                return await self.analyze_with_anthropic(file_contents, "claude-opus-4")
            elif model in ["Deepseek-V3", "deepseek-v3", "deepseek-chat"]:
                return await self.analyze_with_deepseek(file_contents)
            elif model == "llama-maverick":
                return await self.analyze_with_llama_maverick(file_contents)
            else:
                raise ValueError(f"Unsupported model: {model}")

        except Exception as e:
            print(f"Error in analyze_code with {model}: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return empty list on error to allow other models to continue
            return []

    async def compare_infotainment_results(self, all_results: Dict[str, List[Dict]]) -> Dict:
        """
        Compare results from different LLM models for infotainment A/B testing.

        Args:
            all_results: Dictionary mapping model names to their results

        Returns:
            Comprehensive comparison statistics for infotainment systems
        """
        comparison = {
            "total_issues_by_model": {},
            "safety_critical_by_model": {},
            "common_issues": [],
            "unique_issues_by_model": {},
            "severity_distribution": {},
            "wcag_compliance_by_model": {},
            "automotive_metrics_by_model": {},
            "interaction_method_distribution": {},
            "standard_coverage_comparison": {}
        }

        # Calculate statistics for each model
        for model, issues in all_results.items():
            comparison["total_issues_by_model"][model] = len(issues)
            comparison["safety_critical_by_model"][model] = len([i for i in issues if i.get("safety_critical", False)])

            # Severity distribution
            severity_counts = {}
            for issue in issues:
                severity = issue.get("severity", "unknown")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            comparison["severity_distribution"][model] = severity_counts

            # WCAG compliance analysis
            wcag_stats = {
                "A_violations": len([i for i in issues if i.get("wcag_level") == "A"]),
                "AA_violations": len([i for i in issues if i.get("wcag_level") == "AA"]),
                "AAA_violations": len([i for i in issues if i.get("wcag_level") == "AAA"]),
                "principles": {}
            }

            for principle in ["Perceivable", "Operable", "Understandable", "Robust"]:
                wcag_stats["principles"][principle] = len([i for i in issues if i.get("wcag_principle") == principle])

            comparison["wcag_compliance_by_model"][model] = wcag_stats

            # Automotive metrics analysis
            if issues:
                eyes_off_times = [i.get("automotive_metrics", {}).get("eyes_off_road_time", 0) for i in issues if
                                  i.get("automotive_metrics")]
                glance_counts = [i.get("automotive_metrics", {}).get("glance_count", 0) for i in issues if
                                 i.get("automotive_metrics")]
                task_times = [i.get("automotive_metrics", {}).get("task_time", 0) for i in issues if
                              i.get("automotive_metrics")]

                comparison["automotive_metrics_by_model"][model] = {
                    "avg_eyes_off_road_time": sum(eyes_off_times) / len(eyes_off_times) if eyes_off_times else 0,
                    "max_eyes_off_road_time": max(eyes_off_times) if eyes_off_times else 0,
                    "avg_glance_count": sum(glance_counts) / len(glance_counts) if glance_counts else 0,
                    "avg_task_time": sum(task_times) / len(task_times) if task_times else 0,
                    "safety_violations": len([t for t in eyes_off_times if t > 2.0])  # >2s individual glances
                }

            # Interaction method distribution
            interaction_counts = {}
            for issue in issues:
                method = issue.get("interaction_method", "unknown")
                interaction_counts[method] = interaction_counts.get(method, 0) + 1
            comparison["interaction_method_distribution"][model] = interaction_counts

            # Standard coverage comparison
            standard_coverage = {
                "wcag_issues": len([i for i in issues if i.get("wcag_criteria")]),
                "iso15008_issues": len([i for i in issues if i.get("iso15008_criteria")]),
                "nhtsa_issues": len([i for i in issues if i.get("nhtsa_criteria")]),
                "sae_issues": len([i for i in issues if i.get("sae_criteria")]),
                "gtr8_issues": len([i for i in issues if i.get("gtr8_criteria")])
            }
            comparison["standard_coverage_comparison"][model] = standard_coverage

        # Find common issues (same file, line, and type across models)
        if len(all_results) > 1:
            models = list(all_results.keys())
            first_model_issues = all_results[models[0]]

            for issue in first_model_issues:
                is_common = True
                consensus_data = {
                    "file": issue.get("file"),
                    "line": issue.get("line"),
                    "type": issue.get("type"),
                    "models_found": [models[0]],
                    "severity_consensus": {models[0]: issue.get("severity")},
                    "safety_critical_consensus": {models[0]: issue.get("safety_critical", False)}
                }

                for other_model in models[1:]:
                    found = False
                    for other_issue in all_results[other_model]:
                        if (issue.get("file") == other_issue.get("file") and
                                issue.get("line") == other_issue.get("line") and
                                issue.get("type") == other_issue.get("type")):
                            found = True
                            consensus_data["models_found"].append(other_model)
                            consensus_data["severity_consensus"][other_model] = other_issue.get("severity")
                            consensus_data["safety_critical_consensus"][other_model] = other_issue.get(
                                "safety_critical", False)
                            break

                    if not found:
                        is_common = False
                        break

                if is_common:
                    comparison["common_issues"].append(consensus_data)

        return comparison