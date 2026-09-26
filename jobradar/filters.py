import logging

logger = logging.getLogger(__name__)

def get_flat_tags(tags):
    """Spłaszcza tagi (API potrafią zwracać zagnieżdżone listy np. [['php']])."""
    result = set()
    if not tags:
        return result
    if isinstance(tags, str):
        result.add(tags.lower().strip())
        return result
        
    for item in tags:
        if isinstance(item, list):
            for subitem in item:
                if isinstance(subitem, str):
                    result.add(subitem.lower().strip())
        elif isinstance(item, str):
            result.add(item.lower().strip())
    return result

def has_excluded_tags(job_tags, excluded):
    if not excluded:
        return False
    tags_lower = get_flat_tags(job_tags)
    excluded_lower = {e.lower().strip() for e in excluded}
    return bool(tags_lower.intersection(excluded_lower))

def apply_filters(job, prefs):
    """
    Krok 3 potoku: Twarde filtry.
    Odrzuca oferty m.in. na podstawie wykluczonych tagów (np. php).
    """
    job_tags = job.get("tags", [])
    
    if has_excluded_tags(job_tags, prefs.get("excluded_tags", [])):
        return False
        
    return True