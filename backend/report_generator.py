import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import base64
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
import matplotlib.pyplot as plt
import seaborn as sns


class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom styles for the report"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.lightgrey,
            borderPadding=5
        ))

        self.styles.add(ParagraphStyle(
            name='IssueTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=6,
            textColor=colors.red
        ))

        self.styles.add(ParagraphStyle(
            name='CodeBlock',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Courier',
            backgroundColor=colors.lightgrey,
            borderWidth=1,
            borderColor=colors.grey,
            borderPadding=5,
            leftIndent=10,
            rightIndent=10
        ))

    async def generate_pdf_report(self, session_data: Dict[str, Any]) -> Path:
        """Generate comprehensive PDF report"""
        session_id = session_data["id"]
        output_path = Path(f"temp_sessions/{session_id}_report.pdf")

        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Build story (content)
        story = []

        # Title page
        story.extend(self._create_title_page(session_data))
        story.append(PageBreak())

        # Executive summary
        story.extend(self._create_executive_summary(session_data))
        story.append(PageBreak())

        # Analysis results by model
        story.extend(self._create_analysis_section(session_data))
        story.append(PageBreak())

        # Detailed findings
        story.extend(self._create_detailed_findings(session_data))
        story.append(PageBreak())

        # Remediation results
        story.extend(self._create_remediation_section(session_data))
        story.append(PageBreak())

        # Recommendations
        story.extend(self._create_recommendations_section(session_data))
        story.append(PageBreak())

        # Appendices
        story.extend(self._create_appendices(session_data))

        # Build PDF
        doc.build(story)

        return output_path

    def _create_title_page(self, session_data: Dict[str, Any]) -> List:
        """Create title page"""
        story = []

        # Main title
        story.append(Paragraph(
            "Infotainment Accessibility Analysis Report",
            self.styles['CustomTitle']
        ))
        story.append(Spacer(1, 0.5 * inch))

        # Session info
        session_info = f"""
        <b>Session ID:</b> {session_data['id']}<br/>
        <b>Analysis Date:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
        <b>Files Analyzed:</b> {len(session_data.get('files', []))}<br/>
        <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        story.append(Paragraph(session_info, self.styles['Normal']))
        story.append(Spacer(1, 1 * inch))

        # Summary table
        analysis_results = session_data.get('analysis_results', {})
        total_issues = sum(
            len(model_results) for model_results in analysis_results.values()
            if isinstance(model_results, list)
        )

        summary_data = [
            ['Metric', 'Value'],
            ['Total Files', str(len(session_data.get('files', [])))],
            ['LLM Models Used', str(len(analysis_results.keys()))],
            ['Total Issues Found', str(total_issues)],
            ['Analysis Duration', 'Varies by model'],
        ]

        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(summary_table)

        return story

    def _create_executive_summary(self, session_data: Dict[str, Any]) -> List:
        """Create executive summary section"""
        story = []

        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))

        # Calculate overall metrics
        analysis_results = session_data.get('analysis_results', {})
        all_issues = []

        for model, model_results in analysis_results.items():
            if isinstance(model_results, list):
                for file_result in model_results:
                    if 'issues' in file_result:
                        all_issues.extend(file_result['issues'])

        # Severity breakdown
        severity_counts = {'A': 0, 'AA': 0, 'AAA': 0}
        category_counts = {'perceivable': 0, 'operable': 0, 'understandable': 0, 'robust': 0}

        for issue in all_issues:
            severity = issue.get('severity', 'A')
            category = issue.get('category', 'unknown')

            if severity in severity_counts:
                severity_counts[severity] += 1
            if category in category_counts:
                category_counts[category] += 1

        # Summary text
        total_issues = len(all_issues)
        critical_issues = severity_counts['A'] + severity_counts['AA']

        summary_text = f"""
        This report presents the results of an automated accessibility analysis performed on 
        {len(session_data.get('files', []))} infotainment system files using multiple Large Language Models (LLMs). 

        <b>Key Findings:</b><br/>
        • Total accessibility issues identified: {total_issues}<br/>
        • Critical issues (Level A & AA): {critical_issues}<br/>
        • Most common category: {max(category_counts, key=category_counts.get) if category_counts else 'N/A'}<br/>
        • LLM models compared: {', '.join(analysis_results.keys())}<br/>

        <b>Compliance Status:</b><br/>
        The analysis reveals varying degrees of WCAG 2.2 compliance across the analyzed files. 
        Immediate attention is recommended for Level A and AA violations, which represent 
        fundamental accessibility barriers for users with disabilities.
        """

        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        # Create charts
        if total_issues > 0:
            # Severity chart
            story.append(self._create_severity_chart(severity_counts))
            story.append(Spacer(1, 0.2 * inch))

            # Category chart
            story.append(self._create_category_chart(category_counts))

        return story

    def _create_analysis_section(self, session_data: Dict[str, Any]) -> List:
        """Create LLM analysis comparison section"""
        story = []

        story.append(Paragraph("LLM Model Analysis Comparison", self.styles['SectionHeader']))

        analysis_results = session_data.get('analysis_results', {})

        # Model comparison table
        comparison_data = [['Model', 'Files Analyzed', 'Total Issues', 'Avg Issues/File', 'Performance']]

        for model, model_results in analysis_results.items():
            if isinstance(model_results, list):
                files_count = len(model_results)
                total_issues = sum(len(result.get('issues', [])) for result in model_results)
                avg_issues = round(total_issues / files_count, 1) if files_count > 0 else 0

                # Simple performance rating
                if avg_issues < 2:
                    performance = "Excellent"
                elif avg_issues < 5:
                    performance = "Good"
                elif avg_issues < 10:
                    performance = "Fair"
                else:
                    performance = "Needs Review"

                comparison_data.append([
                    model,
                    str(files_count),
                    str(total_issues),
                    str(avg_issues),
                    performance
                ])

        comparison_table = Table(comparison_data, colWidths=[1.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1.2 * inch])
        comparison_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(comparison_table)
        story.append(Spacer(1, 0.3 * inch))

        # Model-specific details
        for model, model_results in analysis_results.items():
            story.append(Paragraph(f"{model} Analysis", self.styles['Heading3']))

            if isinstance(model_results, list) and model_results:
                model_text = f"""
                <b>Files Processed:</b> {len(model_results)}<br/>
                <b>Analysis Method:</b> WCAG 2.2 compliance detection<br/>
                <b>Key Strengths:</b> {self._get_model_strengths(model, model_results)}<br/>
                <b>Areas for Improvement:</b> {self._get_model_weaknesses(model, model_results)}
                """
                story.append(Paragraph(model_text, self.styles['Normal']))
            else:
                story.append(Paragraph("No analysis results available for this model.", self.styles['Normal']))

            story.append(Spacer(1, 0.2 * inch))

        return story

    def _create_detailed_findings(self, session_data: Dict[str, Any]) -> List:
        """Create detailed findings section"""
        story = []

        story.append(Paragraph("Detailed Accessibility Findings", self.styles['SectionHeader']))

        analysis_results = session_data.get('analysis_results', {})

        # Group issues by WCAG guideline
        guideline_issues = {}

        for model, model_results in analysis_results.items():
            if isinstance(model_results, list):
                for file_result in model_results:
                    for issue in file_result.get('issues', []):
                        guideline = issue.get('wcag_guideline', 'Unknown')
                        if guideline not in guideline_issues:
                            guideline_issues[guideline] = []

                        issue_copy = issue.copy()
                        issue_copy['model'] = model
                        issue_copy['file'] = file_result.get('file_info', {}).get('name', 'Unknown')
                        guideline_issues[guideline].append(issue_copy)

        # Present issues by guideline
        for guideline, issues in sorted(guideline_issues.items()):
            story.append(Paragraph(f"{guideline}", self.styles['IssueTitle']))

            # Guideline summary
            severity_dist = {}
            for issue in issues:
                sev = issue.get('severity', 'A')
                severity_dist[sev] = severity_dist.get(sev, 0) + 1

            summary_text = f"""
            <b>Occurrences:</b> {len(issues)}<br/>
            <b>Severity Distribution:</b> {', '.join(f'{k}: {v}' for k, v in severity_dist.items())}<br/>
            <b>Files Affected:</b> {len(set(issue['file'] for issue in issues))}
            """
            story.append(Paragraph(summary_text, self.styles['Normal']))

            # Sample issue details
            if issues:
                sample_issue = issues[0]
                issue_details = f"""
                <b>Description:</b> {sample_issue.get('description', 'No description available')}<br/>
                <b>Impact:</b> {sample_issue.get('impact', 'Impact not specified')}<br/>
                <b>Recommendation:</b> {sample_issue.get('recommendation', 'No recommendation provided')}
                """
                story.append(Paragraph(issue_details, self.styles['Normal']))

                # Code snippet
                if sample_issue.get('code_snippet'):
                    story.append(Paragraph("<b>Example Code:</b>", self.styles['Normal']))
                    story.append(Paragraph(
                        sample_issue['code_snippet'][:200] + "...",
                        self.styles['CodeBlock']
                    ))

            story.append(Spacer(1, 0.2 * inch))

        return story

    def _create_remediation_section(self, session_data: Dict[str, Any]) -> List:
        """Create remediation results section"""
        story = []

    def _create_remediation_section(self, session_data: Dict[str, Any]) -> List:
        """Create remediation results section"""
        story = []

        story.append(Paragraph("Remediation Results", self.styles['SectionHeader']))

        remediation_results = session_data.get('remediation_results', {})
        remediations = session_data.get('remediations', {})

        if not remediation_results and not remediations:
            story.append(Paragraph("No remediation has been performed yet.", self.styles['Normal']))
            return story

        # Remediation summary
        total_fixes = len(remediations)
        successful_fixes = sum(1 for r in remediations.values() if 'fixed_code' in r.get('result', {}))

        summary_text = f"""
        <b>Remediation Summary:</b><br/>
        • Total fixes attempted: {total_fixes}<br/>
        • Successful fixes: {successful_fixes}<br/>
        • Success rate: {round(successful_fixes / total_fixes * 100, 1) if total_fixes > 0 else 0}%<br/>
        """
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        # Individual remediation details
        for issue_id, remediation in remediations.items():
            story.append(Paragraph(f"Issue: {issue_id}", self.styles['Heading4']))

            model = remediation.get('model', 'Unknown')
            timestamp = remediation.get('timestamp', 'Unknown')
            result = remediation.get('result', {})

            remediation_info = f"""
            <b>Model Used:</b> {model}<br/>
            <b>Fixed At:</b> {timestamp}<br/>
            <b>Changes Applied:</b> {len(result.get('changes', []))}<br/>
            """
            story.append(Paragraph(remediation_info, self.styles['Normal']))

            # Show changes
            changes = result.get('changes', [])
            if changes:
                story.append(Paragraph("<b>Applied Changes:</b>", self.styles['Normal']))

                for i, change in enumerate(changes[:3]):  # Show first 3 changes
                    change_text = f"""
                    <b>Change {i + 1}:</b><br/>
                    Line {change.get('line_number', 'N/A')}: {change.get('explanation', 'No explanation')}
                    """
                    story.append(Paragraph(change_text, self.styles['Normal']))

                    if change.get('original') and change.get('fixed'):
                        story.append(Paragraph("<b>Before:</b>", self.styles['Normal']))
                        story.append(Paragraph(change['original'][:100] + "...", self.styles['CodeBlock']))
                        story.append(Paragraph("<b>After:</b>", self.styles['Normal']))
                        story.append(Paragraph(change['fixed'][:100] + "...", self.styles['CodeBlock']))

                if len(changes) > 3:
                    story.append(Paragraph(f"... and {len(changes) - 3} more changes", self.styles['Normal']))

            story.append(Spacer(1, 0.2 * inch))

        return story

    def _create_recommendations_section(self, session_data: Dict[str, Any]) -> List:
        """Create recommendations section"""
        story = []

        story.append(Paragraph("Recommendations", self.styles['SectionHeader']))

        # Analyze findings to generate recommendations
        analysis_results = session_data.get('analysis_results', {})
        all_issues = []

        for model_results in analysis_results.values():
            if isinstance(model_results, list):
                for file_result in model_results:
                    all_issues.extend(file_result.get('issues', []))

        # Priority recommendations
        priority_recs = self._generate_priority_recommendations(all_issues)

        story.append(Paragraph("Priority Actions", self.styles['Heading3']))
        for i, rec in enumerate(priority_recs, 1):
            story.append(Paragraph(f"{i}. {rec}", self.styles['Normal']))

        story.append(Spacer(1, 0.2 * inch))

        # General recommendations
        general_recs = [
            "Implement automated accessibility testing in your CI/CD pipeline",
            "Train development team on WCAG 2.2 guidelines and best practices",
            "Establish accessibility code review processes",
            "Consider using accessibility testing tools like axe-core or WAVE",
            "Implement user testing with assistive technologies",
            "Create accessibility guidelines specific to infotainment systems",
            "Regular audit schedule for accessibility compliance"
        ]

        story.append(Paragraph("General Recommendations", self.styles['Heading3']))
        for i, rec in enumerate(general_recs, 1):
            story.append(Paragraph(f"{i}. {rec}", self.styles['Normal']))

        story.append(Spacer(1, 0.2 * inch))

        # Implementation timeline
        timeline_text = """
        <b>Suggested Implementation Timeline:</b><br/>
        • <b>Week 1-2:</b> Fix all Level A violations<br/>
        • <b>Week 3-4:</b> Address Level AA violations<br/>
        • <b>Month 2:</b> Implement automated testing<br/>
        • <b>Month 3:</b> Team training and process improvement<br/>
        • <b>Ongoing:</b> Regular audits and continuous improvement
        """
        story.append(Paragraph(timeline_text, self.styles['Normal']))

        return story

    def _create_appendices(self, session_data: Dict[str, Any]) -> List:
        """Create appendices section"""
        story = []

        story.append(Paragraph("Appendices", self.styles['SectionHeader']))

        # Appendix A: File List
        story.append(Paragraph("Appendix A: Analyzed Files", self.styles['Heading3']))

        files = session_data.get('files', [])
        file_data = [['Filename', 'Size (bytes)', 'Type']]

        for file_info in files:
            file_data.append([
                file_info.get('name', 'Unknown'),
                str(file_info.get('size', 0)),
                file_info.get('type', 'Unknown')
            ])

        file_table = Table(file_data, colWidths=[3 * inch, 1 * inch, 2 * inch])
        file_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(file_table)
        story.append(Spacer(1, 0.3 * inch))

        # Appendix B: WCAG 2.2 Guidelines Reference
        story.append(Paragraph("Appendix B: WCAG 2.2 Guidelines Reference", self.styles['Heading3']))

        wcag_summary = """
        This analysis is based on Web Content Accessibility Guidelines (WCAG) 2.2, 
        which provides recommendations for making web content more accessible. 
        The guidelines are organized under 4 principles:

        • <b>Perceivable:</b> Information must be presentable in ways users can perceive
        • <b>Operable:</b> Interface components must be operable
        • <b>Understandable:</b> Information and UI operation must be understandable
        • <b>Robust:</b> Content must be robust enough for interpretation by assistive technologies

        Each guideline has three levels of conformance: A (minimum), AA (standard), AAA (enhanced).
        """

        story.append(Paragraph(wcag_summary, self.styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        # Appendix C: Methodology
        story.append(Paragraph("Appendix C: Analysis Methodology", self.styles['Heading3']))

        methodology_text = """
        <b>Analysis Approach:</b><br/>
        1. File preprocessing and format detection<br/>
        2. Static code analysis for common accessibility patterns<br/>
        3. LLM-based semantic analysis using specialized prompts<br/>
        4. Cross-model result comparison and validation<br/>
        5. Issue prioritization and remediation suggestions<br/>

        <b>LLM Models Used:</b><br/>
        • GPT-4o: Advanced reasoning and code understanding<br/>
        • Claude Opus 4: Strong analytical capabilities<br/>
        • DeepSeek-V3: Code-focused analysis<br/>
        • LLaMA Maverick: Alternative perspective validation<br/>

        <b>Limitations:</b><br/>
        • Automated analysis may miss context-dependent issues<br/>
        • Some accessibility aspects require manual testing<br/>
        • LLM outputs should be validated by accessibility experts
        """

        story.append(Paragraph(methodology_text, self.styles['Normal']))

        return story

    def _create_severity_chart(self, severity_counts: Dict[str, int]) -> Drawing:
        """Create severity distribution chart"""
        drawing = Drawing(400, 200)

        # Create pie chart
        pie = Pie()
        pie.x = 150
        pie.y = 50
        pie.width = 100
        pie.height = 100

        pie.data = list(severity_counts.values())
        pie.labels = [f"Level {k}" for k in severity_counts.keys()]
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = colors.red
        pie.slices[1].fillColor = colors.orange
        pie.slices[2].fillColor = colors.yellow

        drawing.add(pie)

        # Add title
        from reportlab.graphics.shapes import String
        title = String(200, 180, "Issues by Severity Level", textAnchor='middle')
        title.fontSize = 12
        title.fontName = 'Helvetica-Bold'
        drawing.add(title)

        return drawing

    def _create_category_chart(self, category_counts: Dict[str, int]) -> Drawing:
        """Create category distribution chart"""
        drawing = Drawing(400, 200)

        # Create bar chart
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 50
        bc.height = 100
        bc.width = 300
        bc.data = [list(category_counts.values())]
        bc.categoryAxis.categoryNames = list(category_counts.keys())
        bc.bars[0].fillColor = colors.lightblue

        drawing.add(bc)

        # Add title
        from reportlab.graphics.shapes import String
        title = String(200, 180, "Issues by WCAG Category", textAnchor='middle')
        title.fontSize = 12
        title.fontName = 'Helvetica-Bold'
        drawing.add(title)

        return drawing

    def _get_model_strengths(self, model: str, results: List[Dict[str, Any]]) -> str:
        """Analyze model strengths based on results"""
        if not results:
            return "Insufficient data"

        # Simple heuristic based on model name and results
        if 'gpt' in model.lower():
            return "Comprehensive issue detection, clear explanations"
        elif 'claude' in model.lower():
            return "Detailed context analysis, nuanced understanding"
        elif 'deepseek' in model.lower():
            return "Code-focused analysis, technical precision"
        elif 'llama' in model.lower():
            return "Alternative perspective, diverse issue identification"
        else:
            return "Consistent analysis approach"

    def _get_model_weaknesses(self, model: str, results: List[Dict[str, Any]]) -> str:
        """Analyze model weaknesses based on results"""
        if not results:
            return "Insufficient data"

        # Calculate average issues per file
        total_issues = sum(len(result.get('issues', [])) for result in results)
        avg_issues = total_issues / len(results) if results else 0

        if avg_issues > 10:
            return "May be overly sensitive, potential false positives"
        elif avg_issues < 2:
            return "May miss subtle accessibility issues"
        else:
            return "Balanced detection approach"

    def _generate_priority_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate priority recommendations based on issues"""
        recommendations = []

        # Count severity and categories
        severity_counts = {'A': 0, 'AA': 0, 'AAA': 0}
        category_counts = {'perceivable': 0, 'operable': 0, 'understandable': 0, 'robust': 0}

        for issue in issues:
            severity = issue.get('severity', 'A')
            category = issue.get('category', 'unknown')

            if severity in severity_counts:
                severity_counts[severity] += 1
            if category in category_counts:
                category_counts[category] += 1

        # Generate recommendations based on most common issues
        if severity_counts['A'] > 0:
            recommendations.append(
                f"Immediately address {severity_counts['A']} Level A violations - these are critical accessibility barriers")

        if severity_counts['AA'] > 0:
            recommendations.append(
                f"Plan remediation for {severity_counts['AA']} Level AA violations to meet standard compliance")

        # Category-specific recommendations
        max_category = max(category_counts, key=category_counts.get) if any(category_counts.values()) else None

        if max_category == 'perceivable':
            recommendations.append("Focus on improving visual and sensory accessibility (alt text, contrast, etc.)")
        elif max_category == 'operable':
            recommendations.append("Enhance keyboard navigation and interactive element accessibility")
        elif max_category == 'understandable':
            recommendations.append("Improve content clarity and user interface predictability")
        elif max_category == 'robust':
            recommendations.append("Strengthen code structure and assistive technology compatibility")

        # If no specific recommendations, add general ones
        if not recommendations:
            recommendations.extend([
                "Implement comprehensive accessibility testing",
                "Review and update development processes",
                "Consider accessibility training for development team"
            ])

        return recommendations[:5]  # Return top 5 recommendations

    def generate_json_summary(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate JSON summary for API consumption"""
        analysis_results = session_data.get('analysis_results', {})

        summary = {
            'session_id': session_data['id'],
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': len(session_data.get('files', [])),
            'models_used': list(analysis_results.keys()),
            'total_issues': 0,
            'issues_by_severity': {'A': 0, 'AA': 0, 'AAA': 0},
            'issues_by_category': {'perceivable': 0, 'operable': 0, 'understandable': 0, 'robust': 0},
            'model_comparison': {},
            'compliance_score': 100
        }

        all_issues = []

        # Aggregate data from all models
        for model, model_results in analysis_results.items():
            if isinstance(model_results, list):
                model_issues = []
                for file_result in model_results:
                    file_issues = file_result.get('issues', [])
                    model_issues.extend(file_issues)
                    all_issues.extend(file_issues)

                summary['model_comparison'][model] = {
                    'files_processed': len(model_results),
                    'total_issues': len(model_issues),
                    'avg_issues_per_file': round(len(model_issues) / len(model_results), 2) if model_results else 0
                }

        # Calculate aggregated metrics
        summary['total_issues'] = len(all_issues)

        for issue in all_issues:
            severity = issue.get('severity', 'A')
            category = issue.get('category', 'unknown')

            if severity in summary['issues_by_severity']:
                summary['issues_by_severity'][severity] += 1
            if category in summary['issues_by_category']:
                summary['issues_by_category'][category] += 1

        # Calculate compliance score
        critical_issues = summary['issues_by_severity']['A'] + summary['issues_by_severity']['AA']
        summary['compliance_score'] = max(0, 100 - (critical_issues * 3))

        return summary

    def export_csv_data(self, session_data: Dict[str, Any]) -> str:
        """Export detailed findings as CSV data"""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # CSV headers
        headers = [
            'Model', 'File', 'Issue_ID', 'WCAG_Guideline', 'Severity', 'Category',
            'Description', 'Line_Numbers', 'Code_Snippet', 'Recommendation'
        ]
        writer.writerow(headers)

        # Export all issues
        analysis_results = session_data.get('analysis_results', {})

        for model, model_results in analysis_results.items():
            if isinstance(model_results, list):
                for file_result in model_results:
                    file_name = file_result.get('file_info', {}).get('name', 'Unknown')

                    for issue in file_result.get('issues', []):
                        row = [
                            model,
                            file_name,
                            issue.get('issue_id', ''),
                            issue.get('wcag_guideline', ''),
                            issue.get('severity', ''),
                            issue.get('category', ''),
                            issue.get('description', ''),
                            ';'.join(map(str, issue.get('line_numbers', []))),
                            issue.get('code_snippet', '')[:100] + "..." if len(
                                issue.get('code_snippet', '')) > 100 else issue.get('code_snippet', ''),
                            issue.get('recommendation', '')
                        ]
                        writer.writerow(row)

        return output.getvalue()