"""Shared, curated vocabulary of real, named skills used by both sides of
matching: job_description_parser.py (extracting a JD's required skills) and
resume_structurer.py (finding skills anywhere in a resume, not just inside a
labeled "Skills" section). Keeping one shared list means both sides recognize
the same skill names consistently.

Historically this list skewed almost entirely technical (programming
languages, frameworks, cloud/DevOps tooling), which meant a non-technical JD
or resume (marketing, accounting, business, healthcare, ...) would rarely
match 3+ vocabulary terms and would fall through to extract_required_skills()'s
noisy word-frequency fallback — producing junk "required skills" and, further
downstream, tech-flavored missing-skill/roadmap content for candidates who
were never software engineers in the first place. Every non-technical section
below exists to close that gap so skill matching (and anything built on top
of it, like the Learning Roadmap) is accurate regardless of the candidate's
actual field."""

SKILL_VOCABULARY = [
    # Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Golang", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "SQL", "HTML", "CSS", "Bash",
    # Frontend
    "React", "Angular", "Vue", "Vue.js", "Next.js", "Redux", "jQuery", "Svelte",
    "Tailwind CSS", "Bootstrap", "Webpack",
    # Backend
    "Node.js", "Express", "Django", "Flask", "FastAPI", "Spring", "Spring Boot",
    "ASP.NET", ".NET", "Ruby on Rails", "Laravel", "GraphQL", "REST API", "Microservices",
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite", "Oracle", "DynamoDB",
    "Elasticsearch", "Cassandra", "Firebase",
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "Terraform",
    "Jenkins", "CI/CD", "Ansible", "Linux", "Git", "GitHub Actions", "Nginx", "DevOps",
    # Data & ML
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Pandas", "NumPy",
    "Data Analysis", "Data Science", "NLP", "Computer Vision", "Data Engineering",
    "ETL", "Big Data", "Spark", "Hadoop",
    # Mobile
    "iOS", "Android", "React Native", "Flutter", "SwiftUI",
    # Testing
    "Unit Testing", "Jest", "Selenium", "Cypress", "QA", "Test Automation", "Pytest",
    # Methodology
    "Agile", "Scrum", "Kanban", "TDD",

    # --- Marketing -----------------------------------------------------
    "SEO", "SEM", "Google Analytics", "Google Ads", "Meta Ads", "Facebook Ads",
    "Social Media Marketing", "Content Marketing", "Content Strategy", "Email Marketing",
    "Marketing Automation", "HubSpot", "Mailchimp", "Copywriting", "Brand Management",
    "Branding", "Campaign Management", "Digital Marketing", "Growth Marketing",
    "Marketing Analytics", "A/B Testing", "Conversion Rate Optimization", "CRO",
    "Influencer Marketing", "Public Relations", "Media Planning", "Affiliate Marketing",
    "Market Research", "Marketing Strategy", "CRM", "Salesforce Marketing Cloud",
    "Adobe Creative Suite", "Canva", "Google Tag Manager", "GA4",

    # --- Sales -----------------------------------------------------------
    "Sales", "Business Development", "Lead Generation", "Cold Calling", "Negotiation",
    "Account Management", "Client Relationship Management", "Salesforce",
    "Sales Forecasting", "Pipeline Management", "B2B Sales", "B2C Sales",
    "Customer Acquisition", "Upselling", "Cross-selling",

    # --- Accounting & Finance --------------------------------------------
    "Accounting", "Bookkeeping", "GAAP", "IFRS", "Financial Reporting",
    "Financial Analysis", "Financial Modeling", "Budgeting", "Forecasting",
    "Accounts Payable", "Accounts Receivable", "Payroll", "Tax Preparation",
    "Taxation", "Auditing", "Internal Controls", "Reconciliation", "General Ledger",
    "QuickBooks", "SAP", "Oracle Financials", "NetSuite", "Xero", "Excel",
    "Financial Statements", "Cost Accounting", "Cash Flow Management",
    "Accounts Reconciliation", "Variance Analysis", "CPA", "CFA",

    # --- Business Administration & Management ----------------------------
    "Program Management", "Operations Management",
    "Strategic Planning", "Business Strategy", "Business Analysis",
    "Change Management", "Process Improvement",
    "Six Sigma", "Lean Management", "Risk Management", "Vendor Management",
    "Contract Negotiation", "PMP", "Business Intelligence",
    "Power BI", "Tableau", "KPI Reporting", "Supply Chain Management",
    "Procurement", "Logistics", "Inventory Management", "Quality Assurance",
    "Team Leadership", "Cross-functional Collaboration", "Budget Management",
    "SWOT Analysis", "Market Analysis",

    # --- Healthcare & Clinical --------------------------------------------
    "Patient Care", "Clinical Documentation", "EHR", "EMR", "Epic Systems",
    "Cerner", "HIPAA Compliance", "Medical Coding", "ICD-10", "CPT Coding",
    "Medical Billing", "Nursing", "Phlebotomy", "Vital Signs Monitoring",
    "Patient Assessment", "Care Coordination", "Clinical Research",
    "Pharmacology", "CPR Certification", "BLS Certification", "ACLS Certification",
    "Infection Control", "Medical Terminology", "Triage", "Case Management",
    "Telehealth", "Healthcare Administration",

    # --- Human Resources ---------------------------------------------------
    "Recruiting", "Talent Acquisition", "Onboarding", "Employee Relations",
    "Performance Management", "Compensation & Benefits", "HRIS", "Workday",
    "ADP", "Payroll Administration", "Labor Relations", "Employment Law",
    "Diversity & Inclusion", "Succession Planning", "Training & Development",
    "Organizational Development", "Applicant Tracking Systems",

    # --- Legal ---------------------------------------------------------------
    "Litigation", "Legal Research", "Contract Drafting", "Contract Review",
    "Legal Writing", "Compliance", "Regulatory Compliance", "Due Diligence",
    "Intellectual Property", "Corporate Law", "Paralegal",
    "Legal Documentation", "Westlaw", "LexisNexis",

    # --- Design & Creative -----------------------------------------------
    "Graphic Design", "UI Design", "UX Design", "UI/UX Design", "Figma",
    "Adobe Photoshop", "Adobe Illustrator", "Adobe InDesign", "Adobe XD",
    "Sketch", "Wireframing", "Prototyping", "Typography", "Visual Design",
    "Video Editing", "Adobe Premiere Pro", "After Effects", "Motion Graphics",
    "Photography", "Illustration", "Design Systems", "User Research",

    # --- Education ------------------------------------------------------
    "Curriculum Development", "Lesson Planning", "Classroom Management",
    "Instructional Design", "Student Assessment", "Differentiated Instruction",
    "E-Learning", "Learning Management Systems", "LMS", "Tutoring",
    "Special Education", "Academic Advising",

    # --- Customer Service / Hospitality / Retail --------------------------
    "Customer Service", "Customer Support", "Help Desk Support", "Zendesk",
    "Client Onboarding", "Conflict Resolution", "Order Processing",
    "Point of Sale Systems", "POS Systems", "Retail Operations",
    "Inventory Control", "Merchandising", "Food Safety", "ServSafe",
    "Front Desk Operations", "Reservations Management", "Guest Relations",

    # --- Soft skills -------------------------------------------------------
    "Communication", "Leadership", "Problem Solving", "Teamwork", "Project Management",
    "Time Management", "Collaboration", "Critical Thinking", "Adaptability",
    "Analytical Skills", "Mentoring", "Stakeholder Management", "Public Speaking",
    "Presentation Skills", "Decision Making", "Attention to Detail",
    "Interpersonal Skills", "Emotional Intelligence", "Creativity", "Multitasking",
]
