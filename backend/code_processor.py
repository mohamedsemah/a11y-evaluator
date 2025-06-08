import os
import mimetypes
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import zipfile
import tempfile
import shutil
import difflib
from datetime import datetime


class CodeProcessor:
    def __init__(self):
        self.supported_extensions = {
            '.html', '.htm', '.xhtml',
            '.css', '.scss', '.sass', '.less',
            '.js', '.jsx', '.ts', '.tsx',
            '.xml', '.xaml',
            '.cpp', '.cc', '.cxx', '.c', '.h', '.hpp',
            '.java', '.kt', '.swift',
            '.py', '.rb', '.php',
            '.json', '.yaml', '.yml',
            '.vue', '.svelte',
            '.qml',  # Qt/QML for automotive
            '.ui'  # Qt Designer files
        }

        self.infotainment_frameworks = {
            'android_auto': ['.xml', '.java', '.kt'],
            'carplay': ['.swift', '.m', '.h'],
            'qnx': ['.cpp', '.cc', '.h', '.qml'],
            'linux_ivi': ['.cpp', '.c', '.h', '.js', '.html'],
            'flutter': ['.dart'],
            'react_native': ['.js', '.jsx', '.ts', '.tsx']
        }

    @classmethod
    def is_supported_file(cls, file_path: Path) -> bool:
        """Check if file is supported for accessibility analysis"""
        processor = cls()
        return file_path.suffix.lower() in processor.supported_extensions

    def extract_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from a file"""
        try:
            stat = file_path.stat()

            metadata = {
                'name': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'extension': file_path.suffix.lower(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'mime_type': mimetypes.guess_type(str(file_path))[0],
                'framework': self._detect_framework(file_path),
                'complexity': self._estimate_complexity(file_path)
            }

            return metadata
        except Exception as e:
            return {
                'name': file_path.name,
                'path': str(file_path),
                'error': str(e)
            }

    def read_file_content(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Read file content with error handling and encoding detection"""
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()

                return content, {
                    'encoding': encoding,
                    'lines': len(content.split('\n')),
                    'chars': len(content),
                    'words': len(content.split())
                }
            except UnicodeDecodeError:
                continue
            except Exception as e:
                return "", {'error': str(e)}

        # If all encodings fail, try binary read
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return content.decode('utf-8', errors='ignore'), {
                'encoding': 'binary_fallback',
                'note': 'Some characters may be corrupted'
            }
        except Exception as e:
            return "", {'error': str(e)}

    def create_backup(self, file_path: Path, backup_dir: Path) -> Path:
        """Create a backup of the original file"""
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name

        shutil.copy2(file_path, backup_path)
        return backup_path

    def apply_fixes(self, original_content: str, fixes: List[Dict[str, Any]],
                    file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """Apply accessibility fixes to file content"""
        modified_content = original_content
        applied_fixes = []
        failed_fixes = []

        # Sort fixes by line number (descending) to avoid line number shifts
        sorted_fixes = sorted(fixes, key=lambda x: x.get('line_number', 0), reverse=True)

        for fix in sorted_fixes:
            try:
                if 'line_number' in fix and 'original' in fix and 'fixed' in fix:
                    # Line-based replacement
                    lines = modified_content.split('\n')
                    line_idx = fix['line_number'] - 1

                    if 0 <= line_idx < len(lines):
                        original_line = lines[line_idx]

                        # Verify the original content matches
                        if fix['original'].strip() in original_line:
                            # Replace the content
                            lines[line_idx] = original_line.replace(
                                fix['original'],
                                fix['fixed'] + "  // PATCHED"
                            )
                            modified_content = '\n'.join(lines)
                            applied_fixes.append(fix)
                        else:
                            failed_fixes.append({
                                **fix,
                                'reason': 'Original content not found at specified line'
                            })
                    else:
                        failed_fixes.append({
                            **fix,
                            'reason': 'Line number out of range'
                        })

                elif 'search' in fix and 'replace' in fix:
                    # Content-based replacement
                    if fix['search'] in modified_content:
                        modified_content = modified_content.replace(
                            fix['search'],
                            fix['replace'] + "  // PATCHED"
                        )
                        applied_fixes.append(fix)
                    else:
                        failed_fixes.append({
                            **fix,
                            'reason': 'Search content not found'
                        })

            except Exception as e:
                failed_fixes.append({
                    **fix,
                    'reason': str(e)
                })

        # Generate summary
        summary = {
            'total_fixes_attempted': len(fixes),
            'successful_fixes': len(applied_fixes),
            'failed_fixes': len(failed_fixes),
            'applied_fixes': applied_fixes,
            'failed_fixes': failed_fixes,
            'modification_timestamp': datetime.now().isoformat()
        }

        return modified_content, summary

    def generate_diff(self, original_content: str, modified_content: str,
                      file_path: Path) -> Dict[str, Any]:
        """Generate detailed diff between original and modified content"""
        original_lines = original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)

        # Generate unified diff
        unified_diff = list(difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
            lineterm=''
        ))

        # Generate side-by-side diff
        side_by_side = list(difflib.context_diff(
            original_lines,
            modified_lines,
            fromfile=f"Original {file_path.name}",
            tofile=f"Modified {file_path.name}",
            lineterm=''
        ))

        # Calculate statistics
        stats = self._calculate_diff_stats(original_lines, modified_lines)

        # Extract changed lines with context
        changes = self._extract_changes(original_lines, modified_lines)

        return {
            'file_path': str(file_path),
            'unified_diff': ''.join(unified_diff),
            'side_by_side_diff': ''.join(side_by_side),
            'changes': changes,
            'statistics': stats,
            'has_changes': len(changes) > 0
        }

    def create_fixed_archive(self, session_dir: Path, fixed_files: Dict[str, str]) -> Path:
        """Create ZIP archive with fixed files"""
        archive_path = session_dir / "fixed_files.zip"

        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path, content in fixed_files.items():
                # Preserve directory structure
                relative_path = Path(file_path).name
                zipf.writestr(f"fixed/{relative_path}", content)

                # Add a summary file
                summary = f"""
File: {relative_path}
Fixed: {datetime.now().isoformat()}
Changes: Applied accessibility fixes with // PATCHED comments
Original preserved in: original/{relative_path}
                """.strip()
                zipf.writestr(f"fixed/{relative_path}.summary.txt", summary)

        return archive_path

    def validate_fixed_code(self, original_content: str, fixed_content: str,
                            file_path: Path) -> Dict[str, Any]:
        """Validate that fixed code maintains functionality"""
        validation_results = {
            'syntax_valid': True,
            'structure_preserved': True,
            'fixes_applied': False,
            'issues': [],
            'warnings': []
        }

        try:
            # Check for PATCHED comments
            if "// PATCHED" in fixed_content:
                validation_results['fixes_applied'] = True

            # Basic syntax validation based on file type
            file_ext = file_path.suffix.lower()

            if file_ext in ['.html', '.htm', '.xhtml']:
                validation_results.update(self._validate_html(fixed_content))
            elif file_ext == '.css':
                validation_results.update(self._validate_css(fixed_content))
            elif file_ext == '.xml':
                validation_results.update(self._validate_xml(fixed_content))
            elif file_ext in ['.js', '.jsx']:
                validation_results.update(self._validate_javascript(fixed_content))
            elif file_ext == '.json':
                validation_results.update(self._validate_json(fixed_content))

            # Check for structural changes
            original_structure = self._extract_structure(original_content, file_ext)
            fixed_structure = self._extract_structure(fixed_content, file_ext)

            if original_structure != fixed_structure:
                validation_results['structure_preserved'] = False
                validation_results['warnings'].append(
                    "Code structure may have been significantly altered"
                )

        except Exception as e:
            validation_results['syntax_valid'] = False
            validation_results['issues'].append(f"Validation error: {str(e)}")

        return validation_results

    def _detect_framework(self, file_path: Path) -> Optional[str]:
        """Detect infotainment framework based on file patterns"""
        file_ext = file_path.suffix.lower()
        file_name = file_path.name.lower()

        # Check file content for framework indicators
        try:
            content, _ = self.read_file_content(file_path)

            # Android Auto indicators
            if any(indicator in content for indicator in [
                'android.car', 'CarAppService', 'androidx.car',
                'android:layout_width', 'android:layout_height'
            ]):
                return 'android_auto'

            # CarPlay indicators
            if any(indicator in content for indicator in [
                'CarPlay', 'CPTemplate', 'CPListTemplate',
                '#import <CarPlay/', '@import CarPlay'
            ]):
                return 'carplay'

            # QNX indicators
            if any(indicator in content for indicator in [
                'QNX', 'qnx/', 'QtQuick', 'QML',
                '#include <qnx', 'import QtQuick'
            ]):
                return 'qnx'

            # React Native indicators
            if any(indicator in content for indicator in [
                'react-native', 'import React', 'from \'react\'',
                'StyleSheet.create', 'View, Text'
            ]):
                return 'react_native'

            # Flutter indicators
            if 'flutter' in content or 'dart:' in content:
                return 'flutter'

            # Generic web-based
            if any(indicator in content for indicator in [
                '<!DOCTYPE html>', '<html', 'document.', 'window.'
            ]):
                return 'web_based'

        except Exception:
            pass

        # Fallback to extension-based detection
        for framework, extensions in self.infotainment_frameworks.items():
            if file_ext in extensions:
                return framework

        return None

    def _estimate_complexity(self, file_path: Path) -> Dict[str, Any]:
        """Estimate code complexity for prioritization"""
        try:
            content, _ = self.read_file_content(file_path)

            complexity = {
                'lines_of_code': len([line for line in content.split('\n') if line.strip()]),
                'total_lines': len(content.split('\n')),
                'cyclomatic_complexity': self._calculate_cyclomatic_complexity(content),
                'ui_elements': self._count_ui_elements(content, file_path.suffix),
                'accessibility_features': self._count_accessibility_features(content),
                'complexity_score': 'low'
            }

            # Calculate overall complexity score
            score = 0
            if complexity['lines_of_code'] > 100:
                score += 1
            if complexity['cyclomatic_complexity'] > 10:
                score += 2
            if complexity['ui_elements'] > 20:
                score += 1

            if score >= 3:
                complexity['complexity_score'] = 'high'
            elif score >= 1:
                complexity['complexity_score'] = 'medium'

            return complexity

        except Exception:
            return {'complexity_score': 'unknown', 'error': 'Failed to analyze'}

    def _calculate_cyclomatic_complexity(self, content: str) -> int:
        """Calculate basic cyclomatic complexity"""
        # Simple heuristic based on control flow keywords
        keywords = ['if', 'else', 'for', 'while', 'switch', 'case', 'catch', '&&', '||', '?']
        complexity = 1  # Base complexity

        for keyword in keywords:
            complexity += content.count(keyword)

        return complexity

    def _count_ui_elements(self, content: str, file_extension: str) -> int:
        """Count UI elements in the code"""
        if file_extension.lower() in ['.html', '.htm', '.xhtml']:
            # HTML elements
            import re
            return len(re.findall(r'<(button|input|select|textarea|a|img|video|audio)', content, re.IGNORECASE))
        elif file_extension.lower() == '.xml':
            # Android XML elements
            import re
            return len(re.findall(r'<(Button|ImageView|TextView|EditText|CheckBox|RadioButton)', content))
        elif file_extension.lower() in ['.js', '.jsx', '.ts', '.tsx']:
            # React/JS components
            import re
            return len(
                re.findall(r'<(button|input|select|textarea|a|img|video|audio|div|span)', content, re.IGNORECASE))

        return 0

    def _count_accessibility_features(self, content: str) -> int:
        """Count existing accessibility features"""
        accessibility_patterns = [
            r'alt\s*=', r'aria-\w+', r'role\s*=', r'tabindex\s*=',
            r'contentDescription', r'accessibilityLabel', r'accessibilityHint'
        ]

        count = 0
        for pattern in accessibility_patterns:
            import re
            count += len(re.findall(pattern, content, re.IGNORECASE))

        return count

    def _calculate_diff_stats(self, original_lines: List[str], modified_lines: List[str]) -> Dict[str, int]:
        """Calculate diff statistics"""
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)

        added = 0
        deleted = 0
        modified = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                added += j2 - j1
            elif tag == 'delete':
                deleted += i2 - i1
            elif tag == 'replace':
                modified += max(i2 - i1, j2 - j1)

        return {
            'lines_added': added,
            'lines_deleted': deleted,
            'lines_modified': modified,
            'total_changes': added + deleted + modified
        }

    def _extract_changes(self, original_lines: List[str], modified_lines: List[str]) -> List[Dict[str, Any]]:
        """Extract individual changes with context"""
        matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)
        changes = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                change = {
                    'type': tag,
                    'original_start': i1 + 1,
                    'original_end': i2,
                    'modified_start': j1 + 1,
                    'modified_end': j2,
                    'original_content': original_lines[i1:i2],
                    'modified_content': modified_lines[j1:j2]
                }
                changes.append(change)

        return changes

    def _extract_structure(self, content: str, file_ext: str) -> List[str]:
        """Extract structural elements for comparison"""
        if file_ext in ['.html', '.htm']:
            # Extract HTML structure
            import re
            return re.findall(r'<(\w+)', content)
        elif file_ext == '.xml':
            # Extract XML structure
            import re
            return re.findall(r'<(\w+)', content)
        elif file_ext in ['.js', '.jsx']:
            # Extract function/component structure
            import re
            functions = re.findall(r'function\s+(\w+)', content)
            components = re.findall(r'const\s+(\w+)\s*=', content)
            return functions + components

        return []

    def _validate_html(self, content: str) -> Dict[str, Any]:
        """Validate HTML syntax"""
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(content, 'html.parser')
            return {'syntax_valid': True}
        except Exception as e:
            return {'syntax_valid': False, 'issues': [f"HTML syntax error: {str(e)}"]}

    def _validate_css(self, content: str) -> Dict[str, Any]:
        """Validate CSS syntax"""
        import cssutils
        import logging

        # Suppress CSS warnings
        cssutils.log.setLevel(logging.CRITICAL)

        try:
            cssutils.parseString(content)
            return {'syntax_valid': True}
        except Exception as e:
            return {'syntax_valid': False, 'issues': [f"CSS syntax error: {str(e)}"]}

    def _validate_xml(self, content: str) -> Dict[str, Any]:
        """Validate XML syntax"""
        import xml.etree.ElementTree as ET
        try:
            ET.fromstring(content)
            return {'syntax_valid': True}
        except ET.ParseError as e:
            return {'syntax_valid': False, 'issues': [f"XML syntax error: {str(e)}"]}

    def _validate_javascript(self, content: str) -> Dict[str, Any]:
        """Basic JavaScript validation"""
        # Simple bracket matching
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []

        for char in content:
            if char in brackets:
                stack.append(brackets[char])
            elif char in brackets.values():
                if not stack or stack.pop() != char:
                    return {'syntax_valid': False, 'issues': ['Mismatched brackets']}

        if stack:
            return {'syntax_valid': False, 'issues': ['Unclosed brackets']}

        return {'syntax_valid': True}

    def _validate_json(self, content: str) -> Dict[str, Any]:
        """Validate JSON syntax"""
        import json
        try:
            json.loads(content)
            return {'syntax_valid': True}
        except json.JSONDecodeError as e:
            return {'syntax_valid': False, 'issues': [f"JSON syntax error: {str(e)}"]}

    def get_file_preview(self, file_path: Path, max_lines: int = 50) -> Dict[str, Any]:
        """Get a preview of the file content"""
        try:
            content, metadata = self.read_file_content(file_path)
            lines = content.split('\n')

            preview = {
                'filename': file_path.name,
                'total_lines': len(lines),
                'preview_lines': lines[:max_lines],
                'truncated': len(lines) > max_lines,
                'metadata': metadata
            }

            return preview

        except Exception as e:
            return {
                'filename': file_path.name,
                'error': str(e)
            }