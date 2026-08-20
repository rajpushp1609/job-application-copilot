from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer


OUTPUT = "output/pdf/Pushp_Raj_Resume_Revised.pdf"


def p(text, style):
    return Paragraph(text, style)


def build():
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=11 * mm,
        title="Pushp Raj - Resume",
        author="Pushp Raj",
    )
    base = getSampleStyleSheet()
    normal = ParagraphStyle(
        "NormalResume", parent=base["BodyText"], fontName="Helvetica", fontSize=9,
        leading=11.1, textColor=colors.HexColor("#1F2937"), spaceAfter=0,
    )
    name = ParagraphStyle(
        "Name", parent=normal, fontName="Helvetica-Bold", fontSize=19, leading=21,
        textColor=colors.HexColor("#111827"), alignment=TA_LEFT,
    )
    contact = ParagraphStyle(
        "Contact", parent=normal, fontSize=9, leading=11, textColor=colors.HexColor("#374151"),
    )
    summary = ParagraphStyle(
        "Summary", parent=normal, fontSize=9, leading=11.25, spaceAfter=1.5 * mm,
    )
    section = ParagraphStyle(
        "Section", parent=normal, fontName="Helvetica-Bold", fontSize=10, leading=12.4,
        textColor=colors.HexColor("#0F4C5C"), spaceBefore=1.5 * mm, spaceAfter=0.9 * mm,
    )
    role = ParagraphStyle(
        "Role", parent=normal, fontName="Helvetica-Bold", fontSize=9.25, leading=11.3,
    )
    date = ParagraphStyle(
        "Date", parent=normal, fontSize=9, leading=10.9, textColor=colors.HexColor("#4B5563"),
    )
    bullet = ParagraphStyle(
        "Bullet", parent=normal, leftIndent=3.4 * mm, firstLineIndent=-2.5 * mm,
        spaceBefore=0, spaceAfter=0,
    )
    compact = ParagraphStyle(
        "Compact", parent=normal, fontSize=8.9, leading=10.9,
    )

    story = []
    story += [
        p("PUSHP RAJ", name),
        p("rajpushp1609@gmail.com  |  +91 7368089031  |  LinkedIn", contact),
        Spacer(1, 1.4 * mm),
        p(
            "Product Manager with 3+ years of experience building and optimizing consumer and B2B SaaS products across fintech and edtech. "
            "Experienced in product analytics, experimentation, AI-enabled workflows, and funnel optimization, with measurable gains in adoption, conversion, payment success, and platform cost efficiency.",
            summary,
        ),
        p("EXPERIENCE", section), HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9CA3AF")), Spacer(1, 0.7 * mm),
    ]

    experience = [
        ("WAYGROUND (formerly Quizizz) | Content AI - Bengaluru, India", "Product Manager | Jul 2025 - Present", [
            "Scaled Voyage Math, a 0-to-1 US math-practice product, to 5K monthly active teachers within four months of beta launch, achieving 60% Month-3 retention.",
            "Led development of the High-Quality Resource Library (HQRL), introducing a standardized discovery framework and curated resources that drove 7% adoption among high-frequency users.",
            "Defined curriculum-alignment standards and supporting infrastructure, improving content consistency while reducing infrastructure cost by 15% (approximately $10K per month).",
        ]),
        ("WAYGROUND (formerly Quizizz) | Content AI - Bengaluru, India", "Product Analyst | Oct 2024 - Jun 2025", [
            "Improved assessment creation by enabling AI-powered quiz generation from user-provided content; used A/B experimentation to increase publish rate from 65% to 75%.",
            "Scaled Interactive Video, a new content format, increasing weekly active teacher adoption from 3% to 15% over two quarters.",
        ]),
        ("NAVI | Personal Loans & Cross-Sell - Bengaluru, India", "Product Analyst | Lending, Payments & Cross-Sell | Jan 2023 - Oct 2024", [
            "Owned analytics-led product improvements across offer generation, verification, KYC, payments, collections, and cross-sell journeys, identifying bottlenecks and prioritizing data-backed interventions.",
            "Diagnosed drop-offs across the pre-purchase loan funnel using step-level funnel analysis, then ran A/B experiments to optimize critical user journeys, improving pre-purchase conversion by 20-25%.",
            "Built a large-scale Account Aggregator experience supporting 50K+ daily users in securely sharing financial data for faster loan processing.",
            "Improved NACH, penny-drop, and disbursement success rates by 18% through payment-funnel optimization in the product management system.",
            "Improved collection efficiency through analytics-led insights across contactability, recovery rates, and NACH-cycle optimization, improving repayment timelines by 15% month over month.",
            "Delivered product insights for cross-selling loans to mutual-fund customers through targeted placements and nudges.",
        ]),
        ("SQUADSTACK | Revenue & Customer Success - Gurugram, India", "Decision Science Intern | Sep 2021 - Mar 2022", [
            "Generated customer-acquisition and retention insights for fintech clients, contributing to $3M in annual revenue and 7% month-over-month growth.",
            "Applied root-cause analysis to streamline internal operations and client workflows, reducing customer turnaround time by 32%.",
            "Integrated cross-platform data to improve visibility into acquisition funnels and operational performance, enabling more informed client decision-making.",
        ]),
    ]
    for company, title, bullets in experience:
        block = [p(company, role), p(title, date)]
        block += [p("• " + item, bullet) for item in bullets]
        story.append(KeepTogether(block))
        story.append(Spacer(1, 0.5 * mm))

    story += [
        p("EDUCATION", section), HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9CA3AF")), Spacer(1, 0.7 * mm),
        p("<b>Birla Institute of Technology, Mesra</b> | Ranchi, India", compact),
        p("B.Tech, Electrical and Electronics Engineering | Jul 2019 - May 2023", compact),
        p("ADDITIONAL EXPERIENCE", section), HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9CA3AF")), Spacer(1, 0.7 * mm),
        p("<b>Research Scholar, Northeastern University</b> | Boston, USA | Jun 2022 - Aug 2022", compact),
        p("• Designed a human-limb temperature sensor with 0.001°C resolution, 10x more precise than prior sensors.", bullet),
        p("• <b>Student Coordinator, Training & Placement Cell</b> - Coordinated hiring processes for 15+ companies and a 200-student batch.", bullet),
        p("• <b>Founding Vice-President, 180 Degrees Consulting</b> - Acquired clients and delivered four projects.", bullet),
        p("SKILLS", section), HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9CA3AF")), Spacer(1, 0.7 * mm),
        p("<b>Product:</b> Product Analytics, Funnel Analysis, A/B Testing, Root-Cause Analysis, AI-enabled Product Workflows, Data Storytelling", compact),
        p("<b>Technical:</b> SQL, Python, BigQuery, Excel, Tableau, Looker Studio, Metabase, Statistical Modeling, R (basic)", compact),
    ]
    doc.build(story)


if __name__ == "__main__":
    build()
