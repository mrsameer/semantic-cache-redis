import dateparser
import datetime
from datetime import date

def normalize_query_dates(query: str, relative_base: datetime.datetime = None) -> str:
    """
    Parses the input query for relative dates and replaces them with absolute ISO dates.
    
    Args:
        query: The user's query string.
        relative_base: The reference time for relative date calculation. 
                       Defaults to datetime.now() if None.
                       
    Returns:
        The query string with relative dates replaced by absolute dates (YYYY-MM-DD).
    """
    if relative_base is None:
        relative_base = datetime.datetime.now()
        
    # Settings for dateparser
    settings = {
        'RELATIVE_BASE': relative_base,
        'PREFER_DATES_FROM': 'past', # Assuming queries are often about past data or current state
        'STRICT_PARSING': False # Allow fuzzy parsing
    }
    
    # We use search_dates to find date substrings
    # dateparser.search.search_dates returns a list of tuples: (substring, datetime_obj)
    try:
        from dateparser.search import search_dates
        matches = search_dates(query, settings=settings)
    except ImportError:
        # Fallback if search module is not available (though it should be in standard dateparser)
        return query
    except Exception as e:
        print(f"Error parsing dates: {e}")
        return query

    if not matches:
        return query
        
    # We need to replace the substrings with the formatted date.
    # We should replace from longest to shortest to avoid partial replacements if they overlap,
    # or better, replace based on position. 
    # However, search_dates doesn't return position.
    # A simple string replacement might be risky if the date string appears in a non-date context,
    # but for this MVP it's acceptable.
    
    normalized_query = query
    
    # Sort matches by length of substring descending to avoid partial matches being replaced first
    # e.g. "last Friday" vs "Friday"
    matches.sort(key=lambda x: len(x[0]), reverse=True)
    
    for date_string, date_obj in matches:
        # Format as YYYY-MM-DD
        formatted_date = date_obj.strftime("%Y-%m-%d")
        
        # Replace only if the formatted date is different from the original string
        # (to avoid replacing "2023-10-27" with "2023-10-27")
        if date_string != formatted_date:
            normalized_query = normalized_query.replace(date_string, formatted_date)
            
    return normalized_query

def extract_date_from_query(query: str, relative_base: datetime.datetime = None) -> list[str]:
    """
    Extracts all found dates from the query and returns them as a list of ISO strings (YYYY-MM-DD).
    Returns empty list if no date is found.
    """
    if relative_base is None:
        relative_base = datetime.datetime.now()
        
    settings = {
        'RELATIVE_BASE': relative_base,
        'PREFER_DATES_FROM': 'past',
        'STRICT_PARSING': False
    }
    
    # Pre-process query to help dateparser split "today and yesterday"
    # Replacing " and " with " & " often helps dateparser treat them as separate entities
    # rather than a single range or group.
    processed_query = query.replace(" and ", " & ")
    
    try:
        from dateparser.search import search_dates
        matches = search_dates(processed_query, settings=settings)
    except Exception:
        return []

    if matches:
        # Return all found dates formatted
        # matches is a list of (substring, datetime_obj)
        # Use set to dedup if needed, but list is fine.
        dates = []
        for _, date_obj in matches:
            dates.append(date_obj.strftime("%Y-%m-%d"))
        return list(set(dates)) # Dedup just in case
    
    return []
