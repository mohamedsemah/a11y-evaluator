import re
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, Tag
import cssutils
import logging

# Suppress CSS parsing warnings
cssutils.log.setLevel(logging.CRITICAL)


class WCAGAnalyzer:
    def __init__(self):
        self.wcag_guidelines = {
            "1.1.1": {"name": "Non-text Content", "level": "A", "category": "perceivable"},
            "1.2.1": {"name": "Audio-only and Video-only", "level": "A", "category": "perceivable"},
            "1.2.2": {"name": "Captions (Prerecorded)", "level": "A", "category": "perceivable"},
            "1.2.3": {"name": "Audio Description or Media Alternative", "level": "A", "category": "perceivable"},
            "1.3.1": {"name": "Info and Relationships", "level": "A", "category": "perceivable"},
            "1.3.2": {"name": "Meaningful Sequence", "level": "A", "category": "perceivable"},
            "1.3.3": {"name": "Sensory Characteristics", "level": "A", "category": "perceivable"},
            "1.3.4": {"name": "Orientation", "level": "AA", "category": "perceivable"},
            "1.3.5": {"name": "Identify Input Purpose", "level": "AA", "category": "perceivable"},
            "1.4.1": {"name": "Use of Color", "level": "A", "category": "perceivable"},
            "1.4.2": {"name": "Audio Control", "level": "A", "category": "perceivable"},
            "1.4.3": {"name": "Contrast (Minimum)", "level": "AA", "category": "perceivable"},
            "1.4.4": {"name": "Resize text", "level": "AA", "category": "perceivable"},
            "1.4.5": {"name": "Images of Text", "level": "AA", "category": "perceivable"},
            "1.4.10": {"name": "Reflow", "level": "AA", "category": "perceivable"},
            "1.4.11": {"name": "Non-text Contrast", "level": "AA", "category": "perceivable"},
            "1.4.12": {"name": "Text Spacing", "level": "AA", "category": "perceivable"},
            "1.4.13": {"name": "Content on Hover or Focus", "level": "AA", "category": "perceivable"},
            "2.1.1": {"name": "Keyboard", "level": "A", "category": "operable"},
            "2.1.2": {"name": "No Keyboard Trap", "level": "A", "category": "operable"},
            "2.1.4": {"name": "Character Key Shortcuts", "level": "A", "category": "operable"},
            "2.2.1": {"name": "Timing Adjustable", "level": "A", "category": "operable"},
            "2.2.2": {"name": "Pause, Stop, Hide", "level": "A", "category": "operable"},
            "2.3.1": {"name": "Three Flashes or Below Threshold", "level": "A", "category": "operable"},
            "2.4.1": {"name": "Bypass Blocks", "level": "A", "category": "operable"},
            "2.4.2": {"name": "Page Titled", "level": "A", "category": "operable"},
            "2.4.3": {"name": "Focus Order", "level": "A", "category": "operable"},
            "2.4.4": {"name": "Link Purpose (In Context)", "level": "A", "category": "operable"},
            "2.4.5": {"name": "Multiple Ways", "level": "AA", "category": "operable"},
            "2.4.6": {"name": "Headings and Labels", "level": "AA", "category": "operable"},
            "2.4.7": {"name": "Focus Visible", "level": "AA", "category": "operable"},
            "2.5.1": {"name": "Pointer Gestures", "level": "A", "category": "operable"},
            "2.5.2": {"name": "Pointer Cancellation", "level": "A", "category": "operable"},
            "2.5.3": {"name": "Label in Name", "level": "A", "category": "operable"},
            "2.5.4": {"name": "Motion Actuation", "level": "A", "category": "operable"},
            "2.5.7": {"name": "Dragging Movements", "level": "AA", "category": "operable"},
            "2.5.8": {"name": "Target Size (Minimum)", "level": "AA", "category": "operable"},
            "3.1.1": {"name": "Language of Page", "level": "A", "category": "understandable"},
            "3.1.2": {"name": "Language of Parts", "level": "AA", "category": "understandable"},
            "3.2.1": {"name": "On Focus", "level": "A", "category": "understandable"},
            "3.2.2": {"name": "On Input", "level": "A", "category": "understandable"},
            "3.2.3": {"name": "Consistent Navigation", "level": "AA", "category": "understandable"},
            "3.2.4": {"name": "Consistent Identification", "level": "AA", "category": "understandable"},
            "3.2.6": {"name": "Consistent Help", "level": "A", "category": "understandable"},
            "3.3.1": {"name": "Error Identification", "level": "A", "category": "understandable"},
            "3.3.2": {"name": "Labels or Instructions", "level": "A", "category": "understandable"},
            "3.3.3": {"name": "Error Suggestion", "level": "AA", "category": "understandable"},
            "3.3.4": {"name": "Error Prevention (Legal, Financial, Data)", "level": "AA", "category": "understandable"},
            "3.3.7": {"name": "Redundant Entry", "level": "A", "category": "understandable"},
            "3.3.8": {"name": "Accessible Authentication (Minimum)", "level": "AA", "category": "understandable"},
            "4.1.1": {"name": "Parsing", "level": "A", "category": "robust"},
            "4.1.2": {"name": "Name, Role, Value", "level": "A", "category": "robust"},
            "4.1.3": {"name": "Status Messages", "level": "AA", "category": "robust"}
        }

        self.infotainment_patterns = {
            "touch_targets": r'(button|clickable|touchable|pressable)',
            "navigation": r'(menu|nav|breadcrumb|tab)',
            "media_controls": r'(play|pause|stop|volume|mute)',
            "form_inputs": r'(input|textfield|dropdown|checkbox|radio)',
            "alerts": r'(alert|notification|warning|error)',
            "interactive": r'(onclick|ontouch|onpress|gesture)'
        }

    def process_llm_result(self, llm_result: Dict[str, Any], file_info: Dict[str, Any],
                           original_code: str) -> Dict[str, Any]:
        """Process and enhance LLM analysis results with improved validation"""
        if llm_result.get("error"):
            return llm_result

        # Enhanced processing of detected issues
        enhanced_issues = []

        for issue in llm_result.get("issues", []):
            enhanced_issue = self._enhance_issue(issue, file_info, original_code)

            # Validate issue accuracy before including
            if self._validate_issue_existence(enhanced_issue, original_code):
                enhanced_issues.append(enhanced_issue)
            else:
                print(f"Rejected invalid issue: {issue.get('issue_id', 'Unknown')}")

        # Add static analysis results
        try:
            static_issues = self._perform_static_analysis(original_code, file_info)
            enhanced_issues.extend(static_issues)
        except Exception as e:
            print(f"Static analysis failed: {str(e)}")
            # Continue without static analysis

        # Calculate metrics
        metrics = self._calculate_metrics(enhanced_issues)

        return {
            "file_info": file_info,
            "total_issues": len(enhanced_issues),
            "issues": enhanced_issues,
            "metrics": metrics,
            "llm_result": llm_result
        }

    def _validate_issue_existence(self, issue: Dict[str, Any], original_code: str) -> bool:
        """Validate that an issue actually exists in the code"""
        lines = original_code.split('\n')
        line_numbers = issue.get('line_numbers', [])
        code_snippet = issue.get('code_snippet', '').strip()

        if not line_numbers or not code_snippet:
            return False

        # Check if at least one line number contains relevant code
        matches = 0
        for line_num in line_numbers:
            if 1 <= line_num <= len(lines):
                line_content = lines[line_num - 1].strip()

                # Multiple validation strategies
                if (code_snippet in line_content or
                        self._fuzzy_match_code(code_snippet, line_content) or
                        self._semantic_match_code(issue, line_content)):
                    matches += 1

        # Issue is valid if at least 50% of line numbers match
        return matches >= max(1, len(line_numbers) * 0.5)

    def _fuzzy_match_code(self, snippet: str, line_content: str) -> bool:
        """Fuzzy matching for code snippets"""
        # Remove whitespace and normalize
        snippet_clean = re.sub(r'\s+', '', snippet.lower())
        line_clean = re.sub(r'\s+', '', line_content.lower())

        # Check if significant parts match
        if len(snippet_clean) > 10:
            # For longer snippets, check if major parts are present
            snippet_words = snippet_clean.split()
            return sum(word in line_clean for word in snippet_words if len(word) > 3) >= len(snippet_words) * 0.6
        else:
            # For shorter snippets, be more strict
            return snippet_clean in line_clean

    def _semantic_match_code(self, issue: Dict[str, Any], line_content: str) -> bool:
        """Semantic matching based on issue type"""
        wcag_guideline = issue.get('wcag_guideline', '')

        # Define patterns for different WCAG guidelines
        semantic_patterns = {
            '1.1.1': [r'<img\b', r'<input[^>]+type\s*=\s*["\']image["\']', r'background-image'],
            '2.1.1': [r'onclick\s*=', r'ontouch\s*=', r'button\b', r'<a\b'],
            '2.4.7': [r':focus\b', r'focus-visible', r'outline\s*:'],
            '3.3.2': [r'<input\b', r'<select\b', r'<textarea\b', r'<label\b'],
            '4.1.2': [r'role\s*=', r'aria-\w+', r'<button\b', r'<input\b']
        }

        # Extract guideline number (e.g., "1.1.1" from "1.1.1 Non-text Content")
        guideline_match = re.match(r'(\d+\.\d+\.\d+)', wcag_guideline)
        if guideline_match:
            guideline_num = guideline_match.group(1)
            if guideline_num in semantic_patterns:
                return any(re.search(pattern, line_content, re.IGNORECASE)
                           for pattern in semantic_patterns[guideline_num])

        return False

    def _enhance_issue(self, issue: Dict[str, Any], file_info: Dict[str, Any],
                       original_code: str) -> Dict[str, Any]:
        """Enhance individual issue with additional context and accurate line detection"""
        enhanced = issue.copy()

        # Improve line number accuracy
        enhanced["line_numbers"] = self._improve_line_accuracy(issue, original_code)

        # Add WCAG guideline details
        guideline_id = self._extract_guideline_id(issue.get("wcag_guideline", ""))
        if guideline_id in self.wcag_guidelines:
            enhanced["wcag_details"] = self.wcag_guidelines[guideline_id]

        # Extract and validate code snippet with improved accuracy
        line_numbers = enhanced["line_numbers"]
        if line_numbers:
            enhanced["code_context"] = self._extract_accurate_code_context(
                original_code, line_numbers
            )
            # Update code snippet with actual code from validated lines
            enhanced["code_snippet"] = self._extract_precise_code_snippet(
                original_code, line_numbers, issue.get("code_snippet", "")
            )

        # Add infotainment-specific context
        enhanced["infotainment_context"] = self._analyze_infotainment_context(
            enhanced.get("code_snippet", ""), file_info
        )

        # Generate preview data for UI rendering
        enhanced["ui_preview"] = self._generate_ui_preview(enhanced, file_info)

        # Add fix confidence score
        enhanced["fix_confidence"] = self._calculate_fix_confidence(enhanced)

        # Add validation score
        enhanced["validation_score"] = self._calculate_validation_score(enhanced, original_code)

        return enhanced

    def _improve_line_accuracy(self, issue: Dict[str, Any], original_code: str) -> List[int]:
        """Improve line number accuracy using multiple strategies"""
        lines = original_code.split('\n')
        code_snippet = issue.get('code_snippet', '').strip()
        original_line_numbers = issue.get('line_numbers', [])

        if not code_snippet:
            return original_line_numbers

        # Strategy 1: Exact match search
        exact_matches = []
        for i, line in enumerate(lines, 1):
            if code_snippet in line:
                exact_matches.append(i)

        if exact_matches:
            return exact_matches[:3]  # Limit to first 3 matches

        # Strategy 2: Fuzzy search for similar content
        fuzzy_matches = []
        for i, line in enumerate(lines, 1):
            if self._fuzzy_match_code(code_snippet, line):
                fuzzy_matches.append(i)

        if fuzzy_matches:
            return fuzzy_matches[:3]

        # Strategy 3: Search for key elements mentioned in the issue
        element_matches = self._find_related_elements(issue, original_code)
        if element_matches:
            return element_matches[:3]

        # Strategy 4: Return validated original line numbers or search nearby
        validated_lines = []
        for line_num in original_line_numbers:
            if 1 <= line_num <= len(lines):
                # Check a range around the original line number
                for offset in range(-2, 3):  # Check ±2 lines
                    check_line = line_num + offset
                    if 1 <= check_line <= len(lines):
                        if any(keyword in lines[check_line - 1].lower()
                               for keyword in self._extract_keywords_from_issue(issue)):
                            validated_lines.append(check_line)
                            break
                else:
                    validated_lines.append(line_num)  # Keep original if no better match

        return validated_lines if validated_lines else [1]

    def _find_related_elements(self, issue: Dict[str, Any], original_code: str) -> List[int]:
        """Find lines containing elements related to the issue"""
        lines = original_code.split('\n')
        wcag_guideline = issue.get('wcag_guideline', '')

        # Define search patterns for different WCAG guidelines
        search_patterns = {
            '1.1.1': [r'<img\b', r'<input[^>]+type\s*=\s*["\']image["\']'],
            '2.1.1': [r'onclick\s*=', r'<button\b', r'<a\b'],
            '2.4.7': [r':focus\b', r'tabindex\s*='],
            '3.3.2': [r'<input\b(?![^>]*type\s*=\s*["\'](?:hidden|submit|button)["\'])', r'<select\b', r'<textarea\b'],
            '4.1.2': [r'role\s*=', r'aria-\w+', r'<button\b']
        }

        guideline_match = re.match(r'(\d+\.\d+\.\d+)', wcag_guideline)
        if guideline_match:
            guideline_num = guideline_match.group(1)
            if guideline_num in search_patterns:
                matching_lines = []
                for i, line in enumerate(lines, 1):
                    for pattern in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            return i
        except:
        pass

    # Strategy 3: Look for tag name
    try:
        soup = BeautifulSoup(element_str, 'html.parser')
        element = soup.find()
        if element:
            tag_name = element.name
            for i, line in enumerate(lines, 1):
                if f'<{tag_name}' in line.lower():
                    return i
    except:
        pass

    return 1  # Fallback


def _analyze_css_enhanced(self, css_code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enhanced CSS analysis"""
    issues = []
    lines = css_code.split('\n')

    # Check for focus indicators
    focus_selectors = re.findall(r'[^{]*:focus[^{]*{[^}]*}', css_code, re.IGNORECASE | re.DOTALL)

    if not focus_selectors:
        issues.append({
            "issue_id": "STATIC_2_4_7_CSS_001",
            "wcag_guideline": "2.4.7 Focus Visible",
            "severity": "AA",
            "description": "No focus styles defined in CSS",
            "line_numbers": [1],
            "code_snippet": "/* No :focus styles found */",
            "recommendation": "Add focus styles: button:focus, a:focus { outline: 2px solid #0066cc; outline-offset: 2px; }",
            "category": "operable",
            "source": "static_analysis",
            "infotainment_risk": "critical",
            "driver_safety_impact": "critical"
        })

    # Check for insufficient color contrast (basic pattern detection)
    color_pairs = self._find_color_contrast_issues(css_code)
    for i, (selector, issue_line) in enumerate(color_pairs):
        issues.append({
            "issue_id": f"STATIC_1_4_3_CSS_{i:03d}",
            "wcag_guideline": "1.4.3 Contrast (Minimum)",
            "severity": "AA",
            "description": f"Potential color contrast issue in selector '{selector}' on line {issue_line}",
            "line_numbers": [issue_line],
            "code_snippet": lines[issue_line - 1] if issue_line <= len(lines) else "",
            "recommendation": "Ensure color contrast ratio is at least 4.5:1 for normal text, 3:1 for large text",
            "category": "perceivable",
            "source": "static_analysis",
            "infotainment_risk": "high",
            "driver_safety_impact": "moderate"
        })

    return issues


def _find_color_contrast_issues(self, css_code: str) -> List[Tuple[str, int]]:
    """Find potential color contrast issues in CSS"""
    lines = css_code.split('\n')
    issues = []

    # Look for common problematic color combinations
    problematic_patterns = [
        (r'color\s*:\s*#?(?:white|#fff|#ffffff)', r'background(?:-color)?\s*:\s*#?(?:yellow|#ff0|#ffff00)'),
        (r'color\s*:\s*#?(?:gray|grey|#808080)', r'background(?:-color)?\s*:\s*#?(?:white|#fff|#ffffff)'),
        (r'color\s*:\s*#?(?:light|#ccc|#cccccc)', r'background(?:-color)?\s*:\s*#?(?:white|#fff|#ffffff)')
    ]

    current_selector = ""
    for i, line in enumerate(lines, 1):
        # Track current selector
        if '{' in line and not line.strip().startswith('/*'):
            current_selector = line.split('{')[0].strip()

        # Check for problematic color combinations
        for color_pattern, bg_pattern in problematic_patterns:
            if (re.search(color_pattern, line, re.IGNORECASE) and
                    re.search(bg_pattern, line, re.IGNORECASE)):
                issues.append((current_selector, i))
                break

    return issues


def _analyze_xml_enhanced(self, xml_code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enhanced XML analysis for Android layouts"""
    issues = []

    try:
        # Basic XML validation
        ET.fromstring(xml_code)
    except ET.ParseError as e:
        issues.append({
            "issue_id": "STATIC_XML_PARSE_001",
            "wcag_guideline": "4.1.1 Parsing",
            "severity": "A",
            "description": f"XML parsing error: {str(e)}",
            "line_numbers": [1],
            "code_snippet": "<!-- XML parsing failed -->",
            "recommendation": "Fix XML syntax errors",
            "category": "robust",
            "source": "static_analysis",
            "infotainment_risk": "high",
            "driver_safety_impact": "moderate"
        })

    return issues


def _analyze_react_enhanced(self, code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enhanced React/JSX analysis with fixed regex patterns"""
    issues = []
    lines = code.split('\n')

    try:
        # Fixed pattern: Check for missing key props in map operations
        # Using a simpler approach that doesn't rely on problematic lookbehind
        map_matches = re.finditer(r'\.map\s*\(\s*[^)]*\)\s*=>\s*[^}]*<[^>]*>', code, re.MULTILINE | re.DOTALL)

        for match in map_matches:
            line_num = code[:match.start()].count('\n') + 1
            context = code[match.start():match.end()]

            # Check if 'key=' is NOT present in the context
            if 'key=' not in context:
                issues.append({
                    "issue_id": f"STATIC_REACT_KEY_{line_num}",
                    "wcag_guideline": "4.1.2 Name, Role, Value",
                    "severity": "A",
                    "description": f"Missing key prop in list rendering on line {line_num}",
                    "line_numbers": [line_num],
                    "code_snippet": context[:100] + "...",
                    "recommendation": "Add unique key prop: key={item.id} or key={index}",
                    "category": "robust",
                    "source": "static_analysis",
                    "infotainment_risk": "medium",
                    "driver_safety_impact": "minor"
                })

        # Check for onClick without keyboard handlers
        onclick_pattern = r'onClick\s*=\s*{[^}]*}'
        for match in re.finditer(onclick_pattern, code):
            line_num = code[:match.start()].count('\n') + 1
            line_content = lines[line_num - 1] if line_num <= len(lines) else ""

            if 'onKeyDown' not in line_content and 'onKeyPress' not in line_content:
                issues.append({
                    "issue_id": f"STATIC_2_1_1_REACT_{line_num}",
                    "wcag_guideline": "2.1.1 Keyboard",
                    "severity": "A",
                    "description": f"Interactive element with onClick but no keyboard handler on line {line_num}",
                    "line_numbers": [line_num],
                    "code_snippet": line_content.strip(),
                    "recommendation": "Add keyboard handler: onKeyDown={(e) => e.key === 'Enter' && handleClick()}",
                    "category": "operable",
                    "source": "static_analysis",
                    "infotainment_risk": "critical",
                    "driver_safety_impact": "critical"
                })

    except Exception as e:
        print(f"React analysis error: {str(e)}")
        # Continue without React-specific analysis

    return issues


def _calculate_metrics(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate enhanced accessibility metrics"""
    total_issues = len(issues)

    if total_issues == 0:
        return {
            "total_issues": 0,
            "severity_breakdown": {"A": 0, "AA": 0, "AAA": 0},
            "category_breakdown": {"perceivable": 0, "operable": 0, "understandable": 0, "robust": 0},
            "infotainment_risk_breakdown": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "driver_safety_breakdown": {"none": 0, "minor": 0, "moderate": 0, "critical": 0},
            "compliance_score": 100,
            "validation_quality": 1.0
        }

    severity_counts = {"A": 0, "AA": 0, "AAA": 0}
    category_counts = {"perceivable": 0, "operable": 0, "understandable": 0, "robust": 0}
    infotainment_risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    driver_safety_counts = {"none": 0, "minor": 0, "moderate": 0, "critical": 0}

    validation_scores = []

    for issue in issues:
        severity = issue.get("severity", "A")
        category = issue.get("category", "unknown")
        infotainment_risk = issue.get("infotainment_risk", "medium")
        driver_safety = issue.get("driver_safety_impact", "minor")
        validation_score = issue.get("validation_score", 0.5)

        if severity in severity_counts:
            severity_counts[severity] += 1
        if category in category_counts:
            category_counts[category] += 1
        if infotainment_risk in infotainment_risk_counts:
            infotainment_risk_counts[infotainment_risk] += 1
        if driver_safety in driver_safety_counts:
            driver_safety_counts[driver_safety] += 1

        validation_scores.append(validation_score)

    # Calculate compliance score with infotainment weighting
    critical_issues = severity_counts["A"] + severity_counts["AA"]
    safety_critical = driver_safety_counts.get("critical", 0)
    compliance_score = max(0, 100 - (critical_issues * 5) - (safety_critical * 10))

    # Calculate average validation quality
    avg_validation = sum(validation_scores) / len(validation_scores) if validation_scores else 1.0

    return {
        "total_issues": total_issues,
        "severity_breakdown": severity_counts,
        "category_breakdown": category_counts,
        "infotainment_risk_breakdown": infotainment_risk_counts,
        "driver_safety_breakdown": driver_safety_counts,
        "compliance_score": compliance_score,
        "validation_quality": avg_validation
    }


def _determine_file_type(self, filename: str) -> str:
    """Determine file type from filename"""
    ext = Path(filename).suffix.lower()

    type_map = {
        '.html': 'html', '.htm': 'html',
        '.css': 'css',
        '.xml': 'xml',
        '.jsx': 'jsx', '.tsx': 'tsx',
        '.js': 'javascript', '.ts': 'typescript',
        '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
        '.c': 'c', '.h': 'c'
    }

    return type_map.get(ext, 'unknown')


def _extract_guideline_id(self, guideline_text: str) -> str:
    """Extract WCAG guideline ID from text"""
    match = re.search(r'(\d+\.\d+\.\d+)', guideline_text)
    return match.group(1) if match else ""


def _analyze_infotainment_context(self, code_snippet: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze infotainment-specific context"""
    context = {
        "patterns_found": [],
        "infotainment_relevance": "low",
        "driver_distraction_risk": "low",
        "safety_critical_functions": []
    }

    # Check for infotainment patterns
    for pattern_name, pattern in self.infotainment_patterns.items():
        if re.search(pattern, code_snippet, re.IGNORECASE):
            context["patterns_found"].append(pattern_name)

    # Check for safety-critical functions
    safety_patterns = [
        r'emergency|911|sos',
        r'navigation|gps|route',
        r'phone|call|dial',
        r'media|music|radio',
        r'climate|hvac|temperature'
    ]

    for pattern in safety_patterns:
        if re.search(pattern, code_snippet, re.IGNORECASE):
            context["safety_critical_functions"].append(pattern)

    # Assess relevance and risk
    if len(context["patterns_found"]) > 0:
        context["infotainment_relevance"] = "high"

        if any(p in context["patterns_found"] for p in ["media_controls", "navigation"]):
            context["driver_distraction_risk"] = "high"
        elif any(p in context["patterns_found"] for p in ["touch_targets", "interactive"]):
            context["driver_distraction_risk"] = "medium"

    return context


def _generate_ui_preview(self, issue: Dict[str, Any], file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Generate enhanced UI preview data"""
    return {
        "element_type": self._extract_element_type(issue.get("code_snippet", "")),
        "bounding_box": self._estimate_bounding_box(issue),
        "preview_html": self._generate_preview_html(issue, file_info),
        "annotations": self._generate_annotations(issue),
        "accessibility_tree": self._generate_accessibility_tree(issue)
    }


def _generate_accessibility_tree(self, issue: Dict[str, Any]) -> Dict[str, Any]:
    """Generate accessibility tree representation"""
    code_snippet = issue.get("code_snippet", "")

    try:
        soup = BeautifulSoup(code_snippet, 'html.parser')
        element = soup.find()

        if element:
            return {
                "role": element.get('role', element.name),
                "name": (element.get('aria-label') or
                         element.get('alt') or
                         element.get_text(strip=True) or
                         "Unnamed element"),
                "description": element.get('aria-describedby', ''),
                "state": {
                    "focused": False,
                    "expanded": element.get('aria-expanded') == 'true',
                    "selected": element.get('aria-selected') == 'true'
                }
            }
    except:
        pass

    return {"role": "unknown", "name": "Could not parse element", "description": "", "state": {}}


def _extract_element_type(self, code_snippet: str) -> str:
    """Extract element type from code snippet"""
    # Enhanced element type detection
    patterns = [
        (r'<(button|input|a|img|select|textarea|label)\b', lambda m: m.group(1)),
        (r'role\s*=\s*["\']([^"\']+)["\']', lambda m: m.group(1)),
        (r'<(\w+)', lambda m: m.group(1))
    ]

    for pattern, extractor in patterns:
        match = re.search(pattern, code_snippet, re.IGNORECASE)
        if match:
            return extractor(match)

    return "unknown"


def _estimate_bounding_box(self, issue: Dict[str, Any]) -> Dict[str, int]:
    """Estimate bounding box with infotainment considerations"""
    element_type = issue.get("ui_preview", {}).get("element_type", "unknown")

    # Infotainment-specific sizing
    size_map = {
        "button": {"width": 120, "height": 60},  # Larger for touch
        "input": {"width": 200, "height": 50},
        "img": {"width": 100, "height": 100},
        "select": {"width": 180, "height": 50},
        "unknown": {"width": 100, "height": 40}
    }

    size = size_map.get(element_type, size_map["unknown"])

    return {
        "x": 100,
        "y": 100,
        "width": size["width"],
        "height": size["height"]
    }


def _generate_preview_html(self, issue: Dict[str, Any], file_info: Dict[str, Any]) -> str:
    """Generate enhanced HTML preview"""
    code_snippet = issue.get("code_snippet", "")
    wcag_guideline = issue.get("wcag_guideline", "")

    preview = f"""
        <div class="accessibility-preview infotainment-theme">
            <div class="issue-highlight">
                <div class="code-snippet">{code_snippet}</div>
                <div class="violation-marker" data-severity="{issue.get('severity', 'A')}">
                    <span class="wcag-reference">{wcag_guideline}</span>
                </div>
            </div>
            <div class="issue-annotation">
                <h4>{wcag_guideline}</h4>
                <p>{issue.get('description', 'No description')}</p>
                <div class="infotainment-impact">
                    <span class="risk-level">{issue.get('infotainment_risk', 'medium')}</span>
                    <span class="safety-impact">{issue.get('driver_safety_impact', 'minor')}</span>
                </div>
            </div>
        </div>
        """

    return preview


def _generate_annotations(self, issue: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate enhanced annotations"""
    annotations = [
        {
            "type": "error",
            "position": {"x": 10, "y": 10},
            "message": issue.get("description", "Accessibility issue"),
            "severity": issue.get("severity", "A"),
            "infotainment_risk": issue.get("infotainment_risk", "medium"),
            "driver_safety": issue.get("driver_safety_impact", "minor")
        }
    ]

    # Add infotainment-specific annotations
    if issue.get("infotainment_risk") == "critical":
        annotations.append({
            "type": "warning",
            "position": {"x": 50, "y": 10},
            "message": "Critical for driver safety",
            "severity": "critical"
        })

    return annotations


def _calculate_fix_confidence(self, issue: Dict[str, Any]) -> float:
    """Calculate enhanced fix confidence score"""
    base_confidence = 0.7

    # Adjust based on validation score
    validation_score = issue.get("validation_score", 0.5)
    base_confidence *= validation_score

    # Adjust based on severity
    severity = issue.get("severity", "A")
    if severity == "A":
        base_confidence += 0.2
    elif severity == "AA":
        base_confidence += 0.1

    # Adjust based on static vs LLM analysis
    if issue.get("source") == "static_analysis":
        base_confidence += 0.1

    # Adjust based on code snippet quality
    code_snippet = issue.get("code_snippet", "")
    if len(code_snippet) > 10 and "<" in code_snippet:
        base_confidence += 0.1

    return min(1.0, base_confidence)
    for pattern in search_patterns[guideline_num]:
        if re.search(pattern, line, re.IGNORECASE):
            matching_lines.append(i)
            break


return matching_lines

return []


def _extract_keywords_from_issue(self, issue: Dict[str, Any]) -> List[str]:
    """Extract relevant keywords from issue description"""
    description = issue.get('description', '').lower()
    code_snippet = issue.get('code_snippet', '').lower()

    # Common HTML/CSS/JS keywords to look for
    keywords = []

    # Extract HTML tags
    html_tags = re.findall(r'<(\w+)', code_snippet)
    keywords.extend(html_tags)

    # Extract attribute names
    attributes = re.findall(r'(\w+)\s*=', code_snippet)
    keywords.extend(attributes)

    # Extract keywords from description
    keyword_patterns = [
        r'\b(alt|src|href|role|aria-\w+|tabindex|onclick|onkeydown)\b',
        r'\b(button|input|img|label|select|textarea)\b',
        r'\b(focus|hover|active|visited)\b'
    ]

    for pattern in keyword_patterns:
        matches = re.findall(pattern, description)
        keywords.extend(matches)

    return list(set(keywords))  # Remove duplicates


def _extract_accurate_code_context(self, code: str, line_numbers: List[int]) -> Dict[str, Any]:
    """Extract code context with improved accuracy"""
    lines = code.split('\n')

    if not line_numbers:
        return {"lines": [], "start_line": 0, "end_line": 0}

    # Expand context window based on code complexity
    context_window = 3  # Default context
    min_line = max(0, min(line_numbers) - context_window)
    max_line = min(len(lines), max(line_numbers) + context_window)

    context_lines = []
    for i in range(min_line, max_line):
        is_highlighted = (i + 1) in line_numbers
        line_content = lines[i] if i < len(lines) else ""

        context_lines.append({
            "number": i + 1,
            "content": line_content,
            "highlighted": is_highlighted,
            "indentation": len(line_content) - len(line_content.lstrip()),
            "is_empty": not line_content.strip()
        })

    return {
        "lines": context_lines,
        "start_line": min_line + 1,
        "end_line": max_line,
        "highlighted_lines": line_numbers
    }


def _extract_precise_code_snippet(self, code: str, line_numbers: List[int],
                                  original_snippet: str) -> str:
    """Extract precise code snippet from validated line numbers"""
    lines = code.split('\n')

    if not line_numbers:
        return original_snippet

    # Get the actual lines
    actual_lines = []
    for line_num in line_numbers:
        if 1 <= line_num <= len(lines):
            actual_lines.append(lines[line_num - 1])

    if actual_lines:
        # If we have multiple lines, join them intelligently
        if len(actual_lines) == 1:
            return actual_lines[0].strip()
        else:
            # For multiple lines, preserve important structure
            return '\n'.join(line.rstrip() for line in actual_lines)

    return original_snippet


def _calculate_validation_score(self, issue: Dict[str, Any], original_code: str) -> float:
    """Calculate a validation score for the issue"""
    score = 0.0

    # Line number accuracy (40% of score)
    line_numbers = issue.get('line_numbers', [])
    if line_numbers:
        lines = original_code.split('\n')
        valid_lines = sum(1 for ln in line_numbers if 1 <= ln <= len(lines))
        score += 0.4 * (valid_lines / len(line_numbers))

    # Code snippet relevance (30% of score)
    code_snippet = issue.get('code_snippet', '')
    if code_snippet and line_numbers:
        if any(code_snippet.strip() in original_code.split('\n')[ln - 1]
               for ln in line_numbers if 1 <= ln <= len(original_code.split('\n'))):
            score += 0.3

    # WCAG guideline specificity (20% of score)
    wcag_guideline = issue.get('wcag_guideline', '')
    if re.match(r'\d+\.\d+\.\d+', wcag_guideline):
        score += 0.2

    # Description quality (10% of score)
    description = issue.get('description', '')
    if len(description) > 20 and any(keyword in description.lower()
                                     for keyword in
                                     ['accessibility', 'wcag', 'screen reader', 'keyboard', 'focus']):
        score += 0.1

    return min(score, 1.0)


def _perform_static_analysis(self, code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enhanced static analysis with precise line detection"""
    issues = []
    file_type = self._determine_file_type(file_info["name"])

    try:
        if file_type == "html":
            issues.extend(self._analyze_html_enhanced(code, file_info))
        elif file_type == "css":
            issues.extend(self._analyze_css_enhanced(code, file_info))
        elif file_type == "xml":
            issues.extend(self._analyze_xml_enhanced(code, file_info))
        elif file_type in ["jsx", "tsx", "javascript"]:
            issues.extend(self._analyze_react_enhanced(code, file_info))
    except Exception as e:
        print(f"Static analysis error for {file_type}: {str(e)}")
        # Continue without this specific analysis

    return issues


def _analyze_html_enhanced(self, html_code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Enhanced HTML analysis with precise line detection"""
    issues = []
    lines = html_code.split('\n')

    try:
        soup = BeautifulSoup(html_code, 'html.parser')

        # Check for missing alt attributes with precise line detection
        images = soup.find_all('img')
        for i, img in enumerate(images):
            if not img.get('alt'):
                # Find exact line number
                img_line = self._find_element_line_precise(html_code, str(img))
                issues.append({
                    "issue_id": f"STATIC_1_1_1_{i:03d}",
                    "wcag_guideline": "1.1.1 Non-text Content",
                    "severity": "A",
                    "description": f"Image element missing alt attribute on line {img_line}",
                    "line_numbers": [img_line],
                    "code_snippet": str(img),
                    "recommendation": "Add descriptive alt attribute: alt='description of image content'",
                    "category": "perceivable",
                    "source": "static_analysis",
                    "infotainment_risk": "high" if any(keyword in str(img).lower()
                                                       for keyword in ['icon', 'button', 'control']) else "medium",
                    "driver_safety_impact": "moderate"
                })

        # Check for missing form labels with enhanced detection
        inputs = soup.find_all('input')
        for i, input_elem in enumerate(inputs):
            input_type = input_elem.get('type', 'text').lower()
            if input_type not in ['hidden', 'submit', 'button']:
                has_label = (input_elem.get('aria-label') or
                             input_elem.get('aria-labelledby') or
                             input_elem.get('title'))

                # Check for associated label element
                input_id = input_elem.get('id')
                if input_id:
                    associated_label = soup.find('label', {'for': input_id})
                    if associated_label:
                        has_label = True

                if not has_label:
                    input_line = self._find_element_line_precise(html_code, str(input_elem))
                    issues.append({
                        "issue_id": f"STATIC_3_3_2_{i:03d}",
                        "wcag_guideline": "3.3.2 Labels or Instructions",
                        "severity": "A",
                        "description": f"Form input missing accessible label on line {input_line}",
                        "line_numbers": [input_line],
                        "code_snippet": str(input_elem),
                        "recommendation": "Add label: <label for='inputId'>Label text</label> or aria-label='Label text'",
                        "category": "understandable",
                        "source": "static_analysis",
                        "infotainment_risk": "high",
                        "driver_safety_impact": "critical"
                    })

        # Check for missing focus styles
        if not re.search(r':focus\s*{[^}]*outline\s*:[^}]*}', html_code, re.IGNORECASE):
            issues.append({
                "issue_id": "STATIC_2_4_7_001",
                "wcag_guideline": "2.4.7 Focus Visible",
                "severity": "AA",
                "description": "No visible focus indicators found in document",
                "line_numbers": [1],
                "code_snippet": "<!-- Add focus styles for interactive elements -->",
                "recommendation": "Add CSS focus styles: button:focus { outline: 2px solid #0066cc; }",
                "category": "operable",
                "source": "static_analysis",
                "infotainment_risk": "critical",
                "driver_safety_impact": "critical"
            })

        # Check for keyboard event handlers
        interactive_elements = soup.find_all(['button', 'a', 'input'])
        for elem in interactive_elements:
            if elem.get('onclick') and not (elem.get('onkeydown') or elem.get('onkeypress')):
                elem_line = self._find_element_line_precise(html_code, str(elem))
                issues.append({
                    "issue_id": f"STATIC_2_1_1_KEYBOARD_{elem.name}_{elem_line}",
                    "wcag_guideline": "2.1.1 Keyboard",
                    "severity": "A",
                    "description": f"Interactive element with onclick but no keyboard support on line {elem_line}",
                    "line_numbers": [elem_line],
                    "code_snippet": str(elem),
                    "recommendation": "Add keyboard event handler: onkeydown='if(event.key===\"Enter\"||event.key===\" \")clickHandler()'",
                    "category": "operable",
                    "source": "static_analysis",
                    "infotainment_risk": "critical",
                    "driver_safety_impact": "critical"
                })

    except Exception as e:
        issues.append({
            "issue_id": "STATIC_4_1_1_001",
            "wcag_guideline": "4.1.1 Parsing",
            "severity": "A",
            "description": f"HTML parsing error: {str(e)}",
            "line_numbers": [1],
            "code_snippet": "<!-- HTML parsing failed -->",
            "recommendation": "Fix HTML syntax errors",
            "category": "robust",
            "source": "static_analysis",
            "infotainment_risk": "high",
            "driver_safety_impact": "moderate"
        })

    return issues


def _find_element_line_precise(self, html_code: str, element_str: str) -> int:
    """Find precise line number of HTML element using multiple strategies"""
    lines = html_code.split('\n')

    # Strategy 1: Exact match
    for i, line in enumerate(lines, 1):
        if element_str.strip() in line:
            return i

    # Strategy 2: Parse element and look for key attributes
    try:
        soup = BeautifulSoup(element_str, 'html.parser')
        element = soup.find()
        if element:
            tag_name = element.name

            # Look for opening tag with attributes
            attributes = []
            for attr, value in element.attrs.items():
                if isinstance(value, list):
                    value = ' '.join(value)
                attributes.append(f'{attr}="{value}"')

            # Create search patterns
            patterns = [
                f'<{tag_name}\\b[^>]*>',  # Any opening tag
                f'<{tag_name}\\s+'  # Tag with space (likely has attributes)
            ]

            # Add attribute-specific patterns
            for attr in attributes:
                patterns.append(re.escape(attr))

            for i, line in enumerate(lines, 1):