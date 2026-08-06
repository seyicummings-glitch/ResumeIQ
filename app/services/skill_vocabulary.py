"""Shared, curated vocabulary of real, named skills used by both sides of
matching: job_description_parser.py (extracting a JD's required skills) and
resume_structurer.py (finding skills anywhere in a resume, not just inside a
labeled "Skills" section). Keeping one shared list means both sides recognize
the same skill names consistently."""

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
    # Soft skills
    "Communication", "Leadership", "Problem Solving", "Teamwork", "Project Management",
    "Time Management", "Collaboration", "Critical Thinking", "Adaptability",
    "Analytical Skills", "Mentoring", "Stakeholder Management",
]
