from jobradar.fingerprint import generate_fingerprint, normalize_text


def test_normalize_text():
    raw = "  Senior   Python Developer!! @ "
    expected = "senior python developer"
    assert normalize_text(raw) == expected


def test_fingerprint_identical_for_normalized_differences():
    job1 = {"company": "Google LLC", "title": "Senior Python Engineer"}
    job2 = {"company": "google llc!", "title": "senior   python engineer  "}

    assert generate_fingerprint(job1) == generate_fingerprint(job2)


def test_fingerprint_different_for_different_jobs():
    job1 = {"company": "Google", "title": "Python Engineer"}
    job2 = {"company": "Google", "title": "DevOps Engineer"}

    assert generate_fingerprint(job1) != generate_fingerprint(job2)