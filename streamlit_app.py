import streamlit as st
import os
import tempfile
import docx
import json
import re
import difflib
import matplotlib.pyplot as plt
import numpy as np
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from tabulate import tabulate
import nltk
import base64
from io import BytesIO

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Set page configuration
st.set_page_config(
    page_title="QAJ DOCX Format Checker by Ridwan Marqas",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6f0ff;
    }
    .compliance-compliant {
        color: green;
        font-weight: bold;
    }
    .compliance-non-compliant {
        color: red;
        font-weight: bold;
    }
    .compliance-partially-compliant {
        color: orange;
        font-weight: bold;
    }
    h1 {
        margin-bottom: 1.5rem;
    }
    h2 {
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    h3 {
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

class DocumentAnalyzer:
    """Class to analyze and compare DOCX documents for format compliance."""
    
    def __init__(self, template_file, article_file):
        """Initialize with template and article file objects."""
        self.template_file = template_file
        self.article_file = article_file
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize data structures
        self.template_info = None
        self.article_info = None
        self.comparison_results = {
            "structure": [],
            "formatting": [],
            "content": [],
            "major_issues": []
        }
    
    def extract_document_info(self, file_obj, output_prefix):
        """Extract document information including styles, formatting, and structure."""
        # Save file to temporary location
        temp_path = os.path.join(self.temp_dir, f"{output_prefix}.docx")
        with open(temp_path, 'wb') as f:
            f.write(file_obj.getvalue())
        
        # Open document
        doc = docx.Document(temp_path)
        
        # Document information
        doc_info = {
            "filename": file_obj.name,
            "paragraphs_count": len(doc.paragraphs),
            "sections_count": len(doc.sections),
            "tables_count": len(doc.tables),
            "styles": {},
            "paragraphs": [],
            "sections": [],
            "tables": []
        }
        
        # Extract styles information
        for style in doc.styles:
            if style.type == WD_STYLE_TYPE.PARAGRAPH:
                style_info = {
                    "name": style.name,
                    "type": "paragraph",
                    "font": None,
                    "font_size": None,
                    "bold": None,
                    "italic": None,
                    "alignment": None,
                    "spacing_before": None,
                    "spacing_after": None,
                    "line_spacing": None
                }
                
                if style.font:
                    style_info["font"] = style.font.name if style.font.name else None
                    style_info["font_size"] = style.font.size.pt if style.font.size else None
                    style_info["bold"] = style.font.bold if hasattr(style.font, 'bold') else None
                    style_info["italic"] = style.font.italic if hasattr(style.font, 'italic') else None
                
                if style.paragraph_format:
                    pf = style.paragraph_format
                    style_info["alignment"] = str(pf.alignment) if pf.alignment else None
                    style_info["spacing_before"] = pf.space_before.pt if pf.space_before else None
                    style_info["spacing_after"] = pf.space_after.pt if pf.space_after else None
                    style_info["line_spacing"] = pf.line_spacing if pf.line_spacing else None
                
                doc_info["styles"][style.name] = style_info
        
        # Extract paragraph information
        for i, para in enumerate(doc.paragraphs):
            para_info = {
                "index": i,
                "text": para.text,
                "style": para.style.name if para.style else "Default",
                "alignment": str(para.alignment) if para.alignment else None,
                "runs": []
            }
            
            # Extract run information (formatting within paragraph)
            for j, run in enumerate(para.runs):
                run_info = {
                    "index": j,
                    "text": run.text,
                    "bold": run.bold,
                    "italic": run.italic,
                    "underline": run.underline,
                    "font": run.font.name if run.font.name else None,
                    "font_size": run.font.size.pt if run.font.size else None
                }
                para_info["runs"].append(run_info)
            
            doc_info["paragraphs"].append(para_info)
        
        # Extract section information
        for i, section in enumerate(doc.sections):
            section_info = {
                "index": i,
                "page_width": section.page_width.inches,
                "page_height": section.page_height.inches,
                "left_margin": section.left_margin.inches,
                "right_margin": section.right_margin.inches,
                "top_margin": section.top_margin.inches,
                "bottom_margin": section.bottom_margin.inches,
                "header_distance": section.header_distance.inches,
                "footer_distance": section.footer_distance.inches,
                "orientation": "portrait" if section.orientation == 0 else "landscape"
            }
            doc_info["sections"].append(section_info)
        
        # Extract table information
        for i, table in enumerate(doc.tables):
            table_info = {
                "index": i,
                "rows": len(table.rows),
                "columns": len(table.columns),
                "cells": []
            }
            
            for r, row in enumerate(table.rows):
                for c, cell in enumerate(row.cells):
                    cell_info = {
                        "row": r,
                        "column": c,
                        "text": cell.text,
                        "paragraphs": []
                    }
                    
                    for p, para in enumerate(cell.paragraphs):
                        para_info = {
                            "index": p,
                            "text": para.text,
                            "style": para.style.name if para.style else "Default"
                        }
                        cell_info["paragraphs"].append(para_info)
                    
                    table_info["cells"].append(cell_info)
            
            doc_info["tables"].append(table_info)
        
        return doc_info
    
    def analyze_documents(self):
        """Extract information from both template and article documents."""
        self.template_info = self.extract_document_info(self.template_file, "template")
        self.article_info = self.extract_document_info(self.article_file, "article")
    
    def extract_sections(self, doc_info):
        """Extract main sections from document."""
        sections = []
        
        # Find title
        if doc_info["paragraphs"]:
            title = doc_info["paragraphs"][0]["text"]
            sections.append(f"Title: \"{title}\"")
        
        # Look for common sections in academic papers
        section_keywords = ["ABSTRACT", "Introduction", "Related Work", "Method", "Results", 
                           "Discussion", "Conclusion", "References"]
        
        for keyword in section_keywords:
            for para in doc_info["paragraphs"]:
                if keyword.lower() in para["text"].lower() and len(para["text"]) < 50:
                    sections.append(f"{keyword}: Present")
                    break
        
        return sections
    
    def extract_formatting_requirements(self, doc_info):
        """Extract formatting requirements from template."""
        formatting = []
        
        # Font information
        fonts = set()
        for style_name, style_info in doc_info["styles"].items():
            if style_info["font"]:
                fonts.add(style_info["font"])
        
        if fonts:
            formatting.append(f"Font: Primary fonts are {', '.join(fonts)}")
        
        # Paragraph alignment
        alignments = {}
        for para in doc_info["paragraphs"]:
            if para["alignment"]:
                alignments[para["alignment"]] = alignments.get(para["alignment"], 0) + 1
        
        if alignments:
            main_alignment = max(alignments.items(), key=lambda x: x[1])[0]
            formatting.append(f"Paragraph Alignment: {main_alignment}")
        
        # Heading styles
        heading_styles = {}
        for style_name, style_info in doc_info["styles"].items():
            if "heading" in style_name.lower():
                heading_styles[style_name] = style_info
        
        if heading_styles:
            formatting.append("Headings: Various levels with specific formatting")
        
        # Tables
        if doc_info["tables_count"] > 0:
            formatting.append(f"Tables: {doc_info['tables_count']} tables with specific formatting")
        
        # Citations
        citation_pattern = r'\[\d+\]'
        has_numbered_citations = False
        for para in doc_info["paragraphs"]:
            if re.search(citation_pattern, para["text"]):
                has_numbered_citations = True
                break
        
        if has_numbered_citations:
            formatting.append("Citations: Numbered format [1], [2, 3], [4-6]")
        
        return formatting
    
    def identify_potential_issues(self):
        """Identify potential issues in the article format."""
        issues = []
        
        # Check for grammatical and typographical errors
        error_count = 0
        for para in self.article_info["paragraphs"]:
            # Simple check for common errors
            text = para["text"]
            if "  " in text:  # Double spaces
                error_count += 1
            if re.search(r'[a-z][A-Z]', text):  # Missing space between sentences
                error_count += 1
            if re.search(r'[.,;:]\w', text):  # Missing space after punctuation
                error_count += 1
        
        if error_count > 10:
            issues.append(f"Potential grammatical and typographical errors ({error_count} instances detected)")
        
        # Check for inconsistent formatting
        style_counts = {}
        for para in self.article_info["paragraphs"]:
            style_counts[para["style"]] = style_counts.get(para["style"], 0) + 1
        
        if len(style_counts) > 10:
            issues.append(f"Inconsistent paragraph styles ({len(style_counts)} different styles detected)")
        
        # Check for citation format
        citation_pattern_numbered = r'\[\d+\]'
        citation_pattern_author_date = r'\([A-Za-z]+ et al\., \d{4}\)'
        
        numbered_citations = 0
        author_date_citations = 0
        
        for para in self.article_info["paragraphs"]:
            numbered_citations += len(re.findall(citation_pattern_numbered, para["text"]))
            author_date_citations += len(re.findall(citation_pattern_author_date, para["text"]))
        
        if numbered_citations > 0 and author_date_citations > 0:
            issues.append(f"Inconsistent citation format (both numbered [{numbered_citations}] and author-date [{author_date_citations}] detected)")
        elif author_date_citations > 0 and numbered_citations == 0:
            issues.append(f"Author-date citation format detected instead of numbered format")
        
        return issues
    
    def compare_documents(self):
        """Compare template and article to identify differences."""
        # Compare document structure
        self.compare_structure()
        
        # Compare formatting
        self.compare_formatting()
        
        # Compare content organization
        self.compare_content_organization()
        
        # Identify major issues
        self.identify_major_issues()
    
    def compare_structure(self):
        """Compare document structure between template and article."""
        # Extract sections from both documents
        template_sections = [para["text"] for para in self.template_info["paragraphs"] 
                            if para["style"].lower().startswith("heading") or para["text"].isupper()]
        
        article_sections = [para["text"] for para in self.article_info["paragraphs"] 
                           if para["style"].lower().startswith("heading") or para["text"].isupper()]
        
        # Find common and different sections
        matcher = difflib.SequenceMatcher(None, template_sections, article_sections)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for section in template_sections[i1:i2]:
                    self.comparison_results["structure"].append({
                        "element": section,
                        "status": "compliant",
                        "details": "Section present in both documents"
                    })
            elif tag == 'delete':
                for section in template_sections[i1:i2]:
                    self.comparison_results["structure"].append({
                        "element": section,
                        "status": "missing",
                        "details": "Required section missing in article"
                    })
            elif tag == 'insert':
                for section in article_sections[j1:j2]:
                    self.comparison_results["structure"].append({
                        "element": section,
                        "status": "extra",
                        "details": "Extra section in article not in template"
                    })
            elif tag == 'replace':
                for section in template_sections[i1:i2]:
                    self.comparison_results["structure"].append({
                        "element": section,
                        "status": "missing",
                        "details": "Required section missing in article"
                    })
                for section in article_sections[j1:j2]:
                    self.comparison_results["structure"].append({
                        "element": section,
                        "status": "extra",
                        "details": "Extra section in article not in template"
                    })
    
    def compare_formatting(self):
        """Compare formatting between template and article."""
        # Compare fonts
        template_fonts = set()
        article_fonts = set()
        
        for style_name, style_info in self.template_info["styles"].items():
            if style_info["font"]:
                template_fonts.add(style_info["font"])
        
        for style_name, style_info in self.article_info["styles"].items():
            if style_info["font"]:
                article_fonts.add(style_info["font"])
        
        if template_fonts == article_fonts:
            self.comparison_results["formatting"].append({
                "element": "Fonts",
                "status": "compliant",
                "details": f"Both documents use the same fonts: {', '.join(template_fonts)}"
            })
        else:
            self.comparison_results["formatting"].append({
                "element": "Fonts",
                "status": "non-compliant",
                "details": f"Template fonts: {', '.join(template_fonts)}; Article fonts: {', '.join(article_fonts)}"
            })
        
        # Compare paragraph alignment
        template_alignments = {}
        article_alignments = {}
        
        for para in self.template_info["paragraphs"]:
            if para["alignment"]:
                template_alignments[para["alignment"]] = template_alignments.get(para["alignment"], 0) + 1
        
        for para in self.article_info["paragraphs"]:
            if para["alignment"]:
                article_alignments[para["alignment"]] = article_alignments.get(para["alignment"], 0) + 1
        
        if template_alignments and article_alignments:
            template_main = max(template_alignments.items(), key=lambda x: x[1])[0]
            article_main = max(article_alignments.items(), key=lambda x: x[1])[0]
            
            if template_main == article_main:
                self.comparison_results["formatting"].append({
                    "element": "Paragraph Alignment",
                    "status": "compliant",
                    "details": f"Both documents primarily use {template_main} alignment"
                })
            else:
                self.comparison_results["formatting"].append({
                    "element": "Paragraph Alignment",
                    "status": "non-compliant",
                    "details": f"Template primarily uses {template_main}; Article primarily uses {article_main}"
                })
        
        # Compare citation style
        citation_pattern_numbered = r'\[\d+\]'
        citation_pattern_author_date = r'\([A-Za-z]+ et al\., \d{4}\)'
        
        template_numbered = 0
        template_author_date = 0
        article_numbered = 0
        article_author_date = 0
        
        for para in self.template_info["paragraphs"]:
            template_numbered += len(re.findall(citation_pattern_numbered, para["text"]))
            template_author_date += len(re.findall(citation_pattern_author_date, para["text"]))
        
        for para in self.article_info["paragraphs"]:
            article_numbered += len(re.findall(citation_pattern_numbered, para["text"]))
            article_author_date += len(re.findall(citation_pattern_author_date, para["text"]))
        
        template_style = "numbered" if template_numbered > template_author_date else "author-date"
        article_style = "numbered" if article_numbered > article_author_date else "author-date"
        
        if template_style == article_style:
            self.comparison_results["formatting"].append({
                "element": "Citation Style",
                "status": "compliant",
                "details": f"Both documents use {template_style} citation style"
            })
        else:
            self.comparison_results["formatting"].append({
                "element": "Citation Style",
                "status": "non-compliant",
                "details": f"Template uses {template_style} citation style; Article uses {article_style} citation style"
            })
        
        # Compare tables
        if self.template_info["tables_count"] == self.article_info["tables_count"]:
            self.comparison_results["formatting"].append({
                "element": "Tables",
                "status": "compliant",
                "details": f"Both documents have {self.template_info['tables_count']} tables"
            })
        else:
            self.comparison_results["formatting"].append({
                "element": "Tables",
                "status": "non-compliant",
                "details": f"Template has {self.template_info['tables_count']} tables; Article has {self.article_info['tables_count']} tables"
            })
    
    def compare_content_organization(self):
        """Compare content organization between template and article."""
        # Check for abstract
        template_abstract = None
        article_abstract = None
        
        for para in self.template_info["paragraphs"]:
            if para["text"].startswith("ABSTRACT:") or para["text"].startswith("Abstract:"):
                template_abstract = para["text"]
                break
        
        for para in self.article_info["paragraphs"]:
            if para["text"].startswith("ABSTRACT") or para["text"].startswith("Abstract"):
                article_abstract = para["text"]
                break
        
        if template_abstract and article_abstract:
            template_words = len(template_abstract.split())
            article_words = len(article_abstract.split())
            
            if 150 <= article_words <= 300:
                self.comparison_results["content"].append({
                    "element": "Abstract Length",
                    "status": "compliant",
                    "details": f"Article abstract has {article_words} words (within 150-300 word limit)"
                })
            else:
                self.comparison_results["content"].append({
                    "element": "Abstract Length",
                    "status": "non-compliant",
                    "details": f"Article abstract has {article_words} words (outside 150-300 word limit)"
                })
        
        # Check for keywords
        template_keywords = None
        article_keywords = None
        
        for para in self.template_info["paragraphs"]:
            if para["text"].startswith("Keywords:"):
                template_keywords = para["text"]
                break
        
        for para in self.article_info["paragraphs"]:
            if para["text"].startswith("Keywords:"):
                article_keywords = para["text"]
                break
        
        if template_keywords and article_keywords:
            template_count = len(template_keywords.split(","))
            article_count = len(article_keywords.split(","))
            
            if template_count == article_count:
                self.comparison_results["content"].append({
                    "element": "Keywords Count",
                    "status": "compliant",
                    "details": f"Both documents have {template_count} keywords"
                })
            else:
                self.comparison_results["content"].append({
                    "element": "Keywords Count",
                    "status": "non-compliant",
                    "details": f"Template has {template_count} keywords; Article has {article_count} keywords"
                })
    
    def identify_major_issues(self):
        """Identify major issues based on comparison results."""
        # Structure issues
        missing_sections = [item["element"] for item in self.comparison_results["structure"] 
                           if item["status"] == "missing"]
        
        if missing_sections:
            self.comparison_results["major_issues"].append({
                "category": "Structure",
                "issue": f"Missing required sections: {', '.join(missing_sections[:3])}{'...' if len(missing_sections) > 3 else ''}"
            })
        
        # Formatting issues
        non_compliant_formatting = [item["element"] for item in self.comparison_results["formatting"] 
                                   if item["status"] == "non-compliant"]
        
        if non_compliant_formatting:
            self.comparison_results["major_issues"].append({
                "category": "Formatting",
                "issue": f"Non-compliant formatting: {', '.join(non_compliant_formatting)}"
            })
        
        # Content issues
        non_compliant_content = [item["element"] for item in self.comparison_results["content"] 
                                if item["status"] == "non-compliant"]
        
        if non_compliant_content:
            self.comparison_results["major_issues"].append({
                "category": "Content",
                "issue": f"Non-compliant content: {', '.join(non_compliant_content)}"
            })
        
        # Check for grammatical issues
        error_count = 0
        for para in self.article_info["paragraphs"]:
            text = para["text"]
            if "  " in text:  # Double spaces
                error_count += 1
            if re.search(r'[a-z][A-Z]', text):  # Missing space between sentences
                error_count += 1
            if re.search(r'[.,;:]\w', text):  # Missing space after punctuation
                error_count += 1
        
        if error_count > 10:
            self.comparison_results["major_issues"].append({
                "category": "Writing Quality",
                "issue": f"Potential grammatical and typographical errors ({error_count} instances detected)"
            })
    
    def generate_compliance_chart(self):
        """Generate a chart visualizing compliance status."""
        # Count compliance status
        categories = ["Structure", "Formatting", "Content"]
        compliant = []
        non_compliant = []
        
        for category in ["structure", "formatting", "content"]:
            category_items = self.comparison_results[category]
            category_compliant = sum(1 for item in category_items if item.get("status") == "compliant")
            category_total = len(category_items)
            
            if category_total > 0:
                compliant.append(category_compliant / category_total * 100)
                non_compliant.append(100 - (category_compliant / category_total * 100))
            else:
                compliant.append(0)
                non_compliant.append(0)
        
        # Create chart
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = np.arange(len(categories))
        width = 0.35
        
        ax.bar(x, compliant, width, label='Compliant', color='#4CAF50')
        ax.bar(x, non_compliant, width, bottom=compliant, label='Non-Compliant', color='#F44336')
        
        ax.set_title('Compliance by Category')
        ax.set_ylabel('Percentage')
        ax.set_yticks(np.arange(0, 101, 20))
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.legend()
        
        # Add percentage labels
        for i, v in enumerate(compliant):
            ax.text(i, v/2, f"{v:.1f}%", ha='center', va='center', color='white', fontweight='bold')
            ax.text(i, v + non_compliant[i]/2, f"{non_compliant[i]:.1f}%", ha='center', va='center', color='white', fontweight='bold')
        
        plt.tight_layout()
        
        # Convert plot to image
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        
        return buf
    
    def run_analysis(self):
        """Run the complete document analysis and comparison."""
        self.analyze_documents()
        self.compare_documents()
        return self.comparison_results

def get_table_download_link(df, filename, text):
    """Generate a link to download the dataframe as a CSV file."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">{text}</a>'
    return href

def main():
    st.title("DOCX Format Checker")
    
    st.markdown("""
    This tool compares a document against a template to check for format compliance. 
    Upload a template document and an article document to analyze their structure, formatting, and content.
    """)
    
    # File upload
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Template Document")
        template_file = st.file_uploader("Upload template document", type=["docx"], key="template")
    
    with col2:
        st.subheader("Article Document")
        article_file = st.file_uploader("Upload article document", type=["docx"], key="article")
    
    if template_file and article_file:
        # Run analysis
        with st.spinner("Analyzing documents..."):
            analyzer = DocumentAnalyzer(template_file, article_file)
            comparison_results = analyzer.run_analysis()
            
            # Generate compliance chart
            chart_image = analyzer.generate_compliance_chart()
        
        # Display results
        st.success("Analysis complete!")
        
        # Calculate overall compliance
        total_items = 0
        compliant_items = 0
        
        for category in ["structure", "formatting", "content"]:
            category_items = comparison_results[category]
            total_items += len(category_items)
            compliant_items += sum(1 for item in category_items if item.get("status") == "compliant")
        
        compliance_percentage = (compliant_items / total_items * 100) if total_items > 0 else 0
        
        # Display compliance score
        st.subheader("Overall Compliance")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.metric("Compliance Score", f"{compliance_percentage:.1f}%")
        
        with col2:
            if compliance_percentage >= 80:
                st.success("The document is **largely compliant** with the template requirements.")
            elif compliance_percentage >= 50:
                st.warning("The document is **partially compliant** with the template requirements.")
            else:
                st.error("The document is **mostly non-compliant** with the template requirements.")
        
        # Display compliance chart
        st.image(chart_image, caption="Compliance by Category", use_column_width=True)
        
        # Create tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(["Major Issues", "Structure", "Formatting", "Content"])
        
        with tab1:
            st.subheader("Major Issues")
            
            if comparison_results["major_issues"]:
                for issue in comparison_results["major_issues"]:
                    st.markdown(f"### {issue['category']}")
                    st.markdown(f"{issue['issue']}")
            else:
                st.success("No major issues detected.")
        
        with tab2:
            st.subheader("Structure Comparison")
            
            # Group by status
            structure_by_status = {"compliant": [], "missing": [], "extra": []}
            for item in comparison_results["structure"]:
                if item["status"] in structure_by_status:
                    structure_by_status[item["status"]].append(item)
            
            # Compliant sections
            if structure_by_status["compliant"]:
                st.markdown("### Compliant Sections")
                for item in structure_by_status["compliant"]:
                    st.markdown(f"- **{item['element']}**: {item['details']}")
            
            # Missing sections
            if structure_by_status["missing"]:
                st.markdown("### Missing Sections")
                st.markdown("The following required sections are missing in the article:")
                for item in structure_by_status["missing"]:
                    st.markdown(f"- **{item['element']}**: {item['details']}")
            
            # Extra sections
            if structure_by_status["extra"]:
                st.markdown("### Extra Sections")
                st.markdown("The following sections in the article are not present in the template:")
                for item in structure_by_status["extra"]:
                    st.markdown(f"- **{item['element']}**: {item['details']}")
        
        with tab3:
            st.subheader("Formatting Comparison")
            
            # Create table
            table_data = []
            for item in comparison_results["formatting"]:
                status_symbol = "✅" if item["status"] == "compliant" else "❌"
                status_class = "compliance-compliant" if item["status"] == "compliant" else "compliance-non-compliant"
                table_data.append([
                    item["element"], 
                    f'<span class="{status_class}">{status_symbol}</span>', 
                    item["details"]
                ])
            
            # Display table
            st.markdown(
                tabulate(table_data, headers=["Element", "Status", "Details"], tablefmt="html"),
                unsafe_allow_html=True
            )
        
        with tab4:
            st.subheader("Content Comparison")
            
            # Create table
            table_data = []
            for item in comparison_results["content"]:
                status_symbol = "✅" if item["status"] == "compliant" else "❌"
                status_class = "compliance-compliant" if item["status"] == "compliant" else "compliance-non-compliant"
                table_data.append([
                    item["element"], 
                    f'<span class="{status_class}">{status_symbol}</span>', 
                    item["details"]
                ])
            
            # Display table
            st.markdown(
                tabulate(table_data, headers=["Element", "Status", "Details"], tablefmt="html"),
                unsafe_allow_html=True
            )
        
        # Recommendations
        st.subheader("Recommendations")
        
        if comparison_results["major_issues"]:
            st.markdown("Based on the comparison, the following changes are recommended:")
            
            for issue in comparison_results["major_issues"]:
                st.markdown(f"1. **{issue['category']}**: Address {issue['issue'].lower()}")
            
            st.markdown("Refer to the template document for specific formatting and structure requirements.")
        else:
            st.success("The document appears to be compliant with the template requirements.")

if __name__ == "__main__":
    main()
