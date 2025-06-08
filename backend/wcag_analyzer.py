import re
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
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
        """Process and enhance LLM analysis results"""
        if llm_result.get("error"):
            return llm_result

        # Enhanced processing of detected issues
        enhanced_issues = []

        for issue in llm_result.get("issues", []):
            enhanced_issue = self._enhance_issue(issue, file_info, original_code)
            enhanced_issues.append(enhanced_issue)

        # Add static analysis results
        static_issues = self._perform_static_analysis(original_code, file_info)
        enhanced_issues.extend(static_issues)

        # Calculate metrics
        metrics = self._calculate_metrics(enhanced_issues)

        return {
            "file_info": file_info,
            "total_issues": len(enhanced_issues),
            "issues": enhanced_issues,
            "metrics": metrics,
            "llm_result": llm_result
        }

    def _enhance_issue(self, issue: Dict[str, Any], file_info: Dict[str, Any],
                       original_code: str) -> Dict[str, Any]:
        """Enhance individual issue with additional context"""
        enhanced = issue.copy()

        # Add WCAG guideline details
        guideline_id = self._extract_guideline_id(issue.get("wcag_guideline", ""))
        if guideline_id in self.wcag_guidelines:
            enhanced["wcag_details"] = self.wcag_guidelines[guideline_id]

        # Extract and validate code snippet
        line_numbers = issue.get("line_numbers", [])
        if line_numbers:
            enhanced["code_context"] = self._extract_code_context(
                original_code, line_numbers
            )

        # Add infotainment-specific context
        enhanced["infotainment_context"] = self._analyze_infotainment_context(
            issue.get("code_snippet", ""), file_info
        )

        # Generate preview data for UI rendering
        enhanced["ui_preview"] = self._generate_ui_preview(issue, file_info)

        # Add fix confidence score
        enhanced["fix_confidence"] = self._calculate_fix_confidence(issue)

        return enhanced

    def _perform_static_analysis(self, code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform static analysis for common accessibility issues"""
        issues = []
        file_type = self._determine_file_type(file_info["name"])

        if file_type == "html":
            issues.extend(self._analyze_html(code, file_info))
        elif file_type == "css":
            issues.extend(self._analyze_css(code, file_info))
        elif file_type == "xml":
            issues.extend(self._analyze_xml(code, file_info))
        elif file_type in ["jsx", "tsx"]:
            issues.extend(self._analyze_react(code, file_info))

        return issues

    def _analyze_html(self, html_code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze HTML for accessibility issues"""
        issues = []

        try:
            soup = BeautifulSoup(html_code, 'html.parser')

            # Check for missing alt attributes
            images = soup.find_all('img')
            for i, img in enumerate(images):
                if not img.get('alt'):
                    issues.append({
                        "issue_id": f"STATIC_1_1_1_{i:03d}",
                        "wcag_guideline": "1.1.1 Non-text Content",
                        "severity": "A",
                        "description": "Image missing alt attribute",
                        "line_numbers": [self._find_element_line(html_code, str(img))],
                        "code_snippet": str(img),
                        "recommendation": "Add descriptive alt attribute to image",
                        "category": "perceivable",
                        "source": "static_analysis"
                    })

            # Check for missing form labels
            inputs = soup.find_all('input')
            for i, input_elem in enumerate(inputs):
                if input_elem.get('type') not in ['hidden', 'submit', 'button']:
                    if not input_elem.get('aria-label') and not input_elem.get('aria-labelledby'):
                        # Check if there's an associated label
                        input_id = input_elem.get('id')
                        if not input_id or not soup.find('label', {'for': input_id}):
                            issues.append({
                                "issue_id": f"STATIC_3_3_2_{i:03d}",
                                "wcag_guideline": "3.3.2 Labels or Instructions",
                                "severity": "A",
                                "description": "Form input missing associated label",
                                "line_numbers": [self._find_element_line(html_code, str(input_elem))],
                                "code_snippet": str(input_elem),
                                "recommendation": "Add label element or aria-label attribute",
                                "category": "understandable",
                                "source": "static_analysis"
                            })

            # Check for missing heading structure
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if len(headings) == 0:
                issues.append({
                    "issue_id": "STATIC_2_4_6_001",
                    "wcag_guideline": "2.4.6 Headings and Labels",
                    "severity": "AA",
                    "description": "No heading elements found - poor document structure",
                    "line_numbers": [1],
                    "code_snippet": "<!-- No headings found in document -->",
                    "recommendation": "Add appropriate heading elements (h1-h6) to structure content",
                    "category": "operable",
                    "source": "static_analysis"
                })

        except Exception as e:
            # If parsing fails, add a general issue
            issues.append({
                "issue_id": "STATIC_4_1_1_001",
                "wcag_guideline": "4.1.1 Parsing",
                "severity": "A",
                "description": f"HTML parsing error: {str(e)}",
                "line_numbers": [1],
                "code_snippet": "<!-- Parsing error -->",
                "recommendation": "Fix HTML syntax errors",
                "category": "robust",
                "source": "static_analysis"
            })

        return issues

    def _analyze_css(self, css_code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze CSS for accessibility issues"""
        issues = []

        try:
            # Parse CSS
            sheet = cssutils.parseString(css_code)

            # Check for potential contrast issues
            color_rules = []
            for rule in sheet:
                if rule.type == rule.STYLE_RULE:
                    for prop in rule.style:
                        if prop.name in ['color', 'background-color']:
                            color_rules.append({
                                'selector': rule.selectorText,
                                'property': prop.name,
                                'value': prop.value,
                                'line': getattr(prop, 'line', 0)
                            })

            # Check for missing focus indicators
            focus_rules = [rule for rule in sheet if rule.type == rule.STYLE_RULE
                           and ':focus' in rule.selectorText]

            if len(focus_rules) == 0:
                issues.append({
                    "issue_id": "STATIC_2_4_7_001",
                    "wcag_guideline": "2.4.7 Focus Visible",
                    "severity": "AA",
                    "description": "No focus indicators defined in CSS",
                    "line_numbers": [1],
                    "code_snippet": "/* No :focus styles found */",
                    "recommendation": "Add visible focus indicators for interactive elements",
                    "category": "operable",
                    "source": "static_analysis"
                })

        except Exception as e:
            pass  # CSS parsing can be finicky, skip errors

        return issues

    def _analyze_xml(self, xml_code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze XML (Android layouts) for accessibility issues"""
        issues = []

        try:
            root = ET.fromstring(xml_code)

            # Check for missing contentDescription in ImageView
            for elem in root.iter():
                if elem.tag == 'ImageView' or elem.tag.endswith('ImageView'):
                    if 'contentDescription' not in elem.attrib:
                        issues.append({
                            "issue_id": f"STATIC_1_1_1_XML_{elem.tag}",
                            "wcag_guideline": "1.1.1 Non-text Content",
                            "severity": "A",
                            "description": "ImageView missing contentDescription",
                            "line_numbers": [self._find_xml_element_line(xml_code, elem)],
                            "code_snippet": ET.tostring(elem, encoding='unicode'),
                            "recommendation": "Add android:contentDescription attribute",
                            "category": "perceivable",
                            "source": "static_analysis"
                        })

                # Check for small touch targets
                if any(elem.tag.endswith(t) for t in ['Button', 'ImageButton', 'CheckBox']):
                    width = elem.get('android:layout_width', '')
                    height = elem.get('android:layout_height', '')
                    if ('48dp' not in width and 'match_parent' not in width and
                            '48dp' not in height and 'match_parent' not in height):
                        issues.append({
                            "issue_id": f"STATIC_2_5_8_XML_{elem.tag}",
                            "wcag_guideline": "2.5.8 Target Size (Minimum)",
                            "severity": "AA",
                            "description": "Touch target may be too small",
                            "line_numbers": [self._find_xml_element_line(xml_code, elem)],
                            "code_snippet": ET.tostring(elem, encoding='unicode'),
                            "recommendation": "Ensure touch targets are at least 48dp",
                            "category": "operable",
                            "source": "static_analysis"
                        })

        except ET.ParseError as e:
            issues.append({
                "issue_id": "STATIC_4_1_1_XML_001",
                "wcag_guideline": "4.1.1 Parsing",
                "severity": "A",
                "description": f"XML parsing error: {str(e)}",
                "line_numbers": [1],
                "code_snippet": "<!-- XML parsing error -->",
                "recommendation": "Fix XML syntax errors",
                "category": "robust",
                "source": "static_analysis"
            })

        return issues

    def _analyze_react(self, code: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze React/JSX code for accessibility issues"""
        issues = []

        # Check for missing key props in lists
        if 'map(' in code and '.map(' in code:
            map_matches = re.finditer(r'\.map\([^)]*\)', code)
            for match in map_matches:
                context = code[match.start():match.end() + 100]
                if 'key=' not in context:
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append({
                        "issue_id": f"STATIC_REACT_KEY_{line_num}",
                        "wcag_guideline": "4.1.2 Name, Role, Value",
                        "severity": "A",
                        "description": "Missing key prop in list rendering",
                        "line_numbers": [line_num],
                        "code_snippet": context[:50] + "...",
                        "recommendation": "Add unique key prop to each list item",
                        "category": "robust",
                        "source": "static_analysis"
                    })

        # Check for onClick without onKeyDown
        onclick_matches = re.finditer(r'onClick\s*=', code)
        for match in onclick_matches:
            line_start = code.rfind('\n', 0, match.start()) + 1
            line_end = code.find('\n', match.end())
            if line_end == -1:
                line_end = len(code)

            line_content = code[line_start:line_end]
            if 'onKeyDown' not in line_content and 'onKeyPress' not in line_content:
                line_num = code[:match.start()].count('\n') + 1
                issues.append({
                    "issue_id": f"STATIC_2_1_1_REACT_{line_num}",
                    "wcag_guideline": "2.1.1 Keyboard",
                    "severity": "A",
                    "description": "Interactive element missing keyboard event handler",
                    "line_numbers": [line_num],
                    "code_snippet": line_content.strip(),
                    "recommendation": "Add onKeyDown handler for keyboard accessibility",
                    "category": "operable",
                    "source": "static_analysis"
                })

        return issues

    def _calculate_metrics(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate accessibility metrics"""
        total_issues = len(issues)

        if total_issues == 0:
            return {
                "total_issues": 0,
                "severity_breakdown": {"A": 0, "AA": 0, "AAA": 0},
                "category_breakdown": {"perceivable": 0, "operable": 0, "understandable": 0, "robust": 0},
                "compliance_score": 100
            }

        severity_counts = {"A": 0, "AA": 0, "AAA": 0}
        category_counts = {"perceivable": 0, "operable": 0, "understandable": 0, "robust": 0}

        for issue in issues:
            severity = issue.get("severity", "A")
            category = issue.get("category", "unknown")

            if severity in severity_counts:
                severity_counts[severity] += 1
            if category in category_counts:
                category_counts[category] += 1

        # Calculate compliance score (simple heuristic)
        critical_issues = severity_counts["A"] + severity_counts["AA"]
        compliance_score = max(0, 100 - (critical_issues * 5))

        return {
            "total_issues": total_issues,
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "compliance_score": compliance_score
        }

    def _determine_file_type(self, filename: str) -> str:
        """Determine file type from filename"""
        ext = Path(filename).suffix.lower()

        type_map = {
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.xml': 'xml',
            '.jsx': 'jsx',
            '.tsx': 'tsx',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.cpp': 'cpp',
            '.c': 'c'
        }

        return type_map.get(ext, 'unknown')

    def _extract_guideline_id(self, guideline_text: str) -> str:
        """Extract WCAG guideline ID from text"""
        match = re.search(r'(\d+\.\d+\.\d+)', guideline_text)
        return match.group(1) if match else ""

    def _extract_code_context(self, code: str, line_numbers: List[int]) -> Dict[str, Any]:
        """Extract code context around specified lines"""
        lines = code.split('\n')

        if not line_numbers:
            return {"lines": [], "start_line": 0, "end_line": 0}

        min_line = max(0, min(line_numbers) - 3)
        max_line = min(len(lines), max(line_numbers) + 3)

        context_lines = []
        for i in range(min_line, max_line):
            context_lines.append({
                "number": i + 1,
                "content": lines[i] if i < len(lines) else "",
                "highlighted": (i + 1) in line_numbers
            })

        return {
            "lines": context_lines,
            "start_line": min_line + 1,
            "end_line": max_line
        }

    def _analyze_infotainment_context(self, code_snippet: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze infotainment-specific context"""
        context = {
            "patterns_found": [],
            "infotainment_relevance": "low",
            "driver_distraction_risk": "low"
        }

        # Check for infotainment patterns
        for pattern_name, pattern in self.infotainment_patterns.items():
            if re.search(pattern, code_snippet, re.IGNORECASE):
                context["patterns_found"].append(pattern_name)

        # Assess relevance and risk
        if len(context["patterns_found"]) > 0:
            context["infotainment_relevance"] = "high"

            if any(p in context["patterns_found"] for p in ["media_controls", "navigation"]):
                context["driver_distraction_risk"] = "high"
            elif any(p in context["patterns_found"] for p in ["touch_targets", "interactive"]):
                context["driver_distraction_risk"] = "medium"

        return context

    def _generate_ui_preview(self, issue: Dict[str, Any], file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UI preview data for the issue"""
        return {
            "element_type": self._extract_element_type(issue.get("code_snippet", "")),
            "bounding_box": self._estimate_bounding_box(issue),
            "preview_html": self._generate_preview_html(issue, file_info),
            "annotations": self._generate_annotations(issue)
        }

    def _extract_element_type(self, code_snippet: str) -> str:
        """Extract element type from code snippet"""
        # Simple heuristic to identify element types
        if re.search(r'<(button|input|a|img)', code_snippet, re.IGNORECASE):
            match = re.search(r'<(\w+)', code_snippet)
            return match.group(1) if match else "unknown"
        return "unknown"

    def _estimate_bounding_box(self, issue: Dict[str, Any]) -> Dict[str, int]:
        """Estimate bounding box for UI preview"""
        # This is a simplified estimation - in a real implementation,
        # you might use browser automation to get actual element positions
        return {
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 50
        }

    def _generate_preview_html(self, issue: Dict[str, Any], file_info: Dict[str, Any]) -> str:
        """Generate HTML preview for the issue"""
        code_snippet = issue.get("code_snippet", "")

        # Create a simplified preview
        preview = f"""
        <div class="accessibility-preview">
            <div class="issue-highlight">
                {code_snippet}
            </div>
            <div class="issue-annotation">
                <strong>{issue.get('wcag_guideline', 'Unknown')}</strong>
                <p>{issue.get('description', 'No description')}</p>
            </div>
        </div>
        """

        return preview

    def _generate_annotations(self, issue: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate annotations for the UI preview"""
        return [
            {
                "type": "error",
                "position": {"x": 10, "y": 10},
                "message": issue.get("description", "Accessibility issue"),
                "severity": issue.get("severity", "A")
            }
        ]

    def _calculate_fix_confidence(self, issue: Dict[str, Any]) -> float:
        """Calculate confidence score for fix suggestions"""
        # Simple heuristic based on issue type and available information
        base_confidence = 0.7

        # Adjust based on severity
        severity = issue.get("severity", "A")
        if severity == "A":
            base_confidence += 0.2
        elif severity == "AA":
            base_confidence += 0.1

        # Adjust based on available context
        if issue.get("code_snippet") and issue.get("line_numbers"):
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def _find_element_line(self, html_code: str, element_str: str) -> int:
        """Find line number of HTML element"""
        lines = html_code.split('\n')
        for i, line in enumerate(lines):
            if element_str in line:
                return i + 1
        return 1

    def _find_xml_element_line(self, xml_code: str, element: ET.Element) -> int:
        """Find line number of XML element"""
        # This is a simplified approach - in practice, you'd need to track line numbers during parsing
        tag_name = element.tag
        lines = xml_code.split('\n')
        for i, line in enumerate(lines):
            if f'<{tag_name}' in line:
                return i + 1
        return 1