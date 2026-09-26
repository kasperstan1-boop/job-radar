from jobradar.filters import apply_filters

# Preferencje uzytkownika: szukamy Remote / Worldwide / UK, unikamy PHP i WordPress
user_preferences = {
    "allowed_locations": ["United Kingdom", "UK", "Europe"],
    "excluded_tags": ["php", "wordpress"],
}


def test_job_accepted_worldwide():
    job = {
        "title": "Python Developer",
        "location": "Worldwide",
        "tags": ["python", "fastapi", "docker"],
    }
    assert apply_filters(job, user_preferences) is True


def test_job_accepted_uk_location():
    job = {
        "title": "Backend Engineer",
        "location": "London, UK",
        "tags": ["python", "django"],
    }
    assert apply_filters(job, user_preferences) is True


def test_job_rejected_excluded_tag():
    job = {
        "title": "Fullstack Web Developer",
        "location": "Remote",
        "tags": ["python", "wordpress"],
    }
    assert apply_filters(job, user_preferences) is False


def test_job_rejected_wrong_location():
    job = {
        "title": "Software Engineer",
        "location": "Only US Citizens (New York)",
        "tags": ["python"],
    }
    assert apply_filters(job, user_preferences) is False


def test_job_rejected_empty_title():
    job = {
        "title": "",
        "location": "Worldwide",
        "tags": ["python"],
    }
    assert apply_filters(job, user_preferences) is False