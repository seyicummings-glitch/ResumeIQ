from app.services.resume_structurer import structure_resume


def test_structures_french_resume_sections():
    text = (
        "Jean Dupont\n"
        "Expérience Professionnelle\n"
        "Développeur Python chez Acme, 3 ans\n"
        "\n"
        "Compétences\n"
        "Python, FastAPI, PostgreSQL\n"
        "\n"
        "Formation\n"
        "Master Informatique, Université de Paris\n"
    )
    result = structure_resume(text)
    assert "python" in [s.lower() for s in result["skills"]]
    assert "Développeur Python" in result["experience"]
    assert "Master Informatique" in result["education"]


def test_structures_spanish_resume_sections():
    text = (
        "Ana García\n"
        "Experiencia Laboral\n"
        "Desarrolladora Python en Acme, 3 años\n"
        "\n"
        "Habilidades\n"
        "Python, FastAPI, PostgreSQL\n"
        "\n"
        "Educación\n"
        "Máster en Informática\n"
    )
    result = structure_resume(text)
    assert "python" in [s.lower() for s in result["skills"]]
    assert "Desarrolladora Python" in result["experience"]


def test_english_still_works():
    text = "Summary\nExperienced engineer.\n\nSkills\nPython, SQL\n"
    result = structure_resume(text)
    assert "python" in [s.lower() for s in result["skills"]]
