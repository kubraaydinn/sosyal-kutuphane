import os
import requests

# --- TMDb Ayarları ---
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"

# 1) Buraya kendi TMDb API v3 key'ini YAPIŞTIR
#    (developer.themoviedb.org -> API key (v3 auth))
TMDB_API_KEY = os.environ.get("TMDB_API_KEY") or "9610f6e5e74d04a07abf3c0e4773cb01"


def search_tmdb_movies(query, language="tr-TR"):
    """
    TMDb'de film arar.
    Sonuç: {external_id, title, year, overview, poster_url} listesi döner.
    """
    print("[TMDB] API KEY VAR MI? ->", bool(TMDB_API_KEY))  # DEBUG

    if not TMDB_API_KEY:
        return []

    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": language,
        "include_adult": False,
    }

    try:
        resp = requests.get(f"{TMDB_BASE_URL}/search/movie", params=params, timeout=5)
        print("[TMDB] status:", resp.status_code)  # DEBUG
        resp.raise_for_status()
    except requests.RequestException as e:
        print("[TMDB] HATA:", e)  # DEBUG
        return []

    data = resp.json()
    results = []

    for m in data.get("results", []):
        title = m.get("title") or m.get("name") or "İsimsiz"
        release_date = m.get("release_date") or ""
        year = release_date[:4] if release_date else None
        poster_path = m.get("poster_path")

        results.append({
            "external_id": str(m.get("id")),
            "title": title,
            "year": year,
            "overview": m.get("overview") or "",
            "poster_url": f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None,
        })

    print("[TMDB] Dönen sonuç sayısı:", len(results))  # DEBUG
    return results


def get_tmdb_movie_details(tmdb_id, language="tr-TR"):
    """
    Tek bir film için detay + cast bilgilerini getirir.
    Dönen dict:
      {
        "overview": str,
        "director": str,
        "cast": [str, ...],
        "genres": [str, ...],
        "runtime": int | None
      }
    """
    if not TMDB_API_KEY:
        return None

    params = {
        "api_key": TMDB_API_KEY,
        "language": language,
        "append_to_response": "credits",  # cast/crew için
    }

    try:
        resp = requests.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}", params=params, timeout=5)
        print("[TMDB DETAIL] status:", resp.status_code)  # DEBUG
        resp.raise_for_status()
    except requests.RequestException as e:
        print("[TMDB DETAIL] HATA:", e)
        return None

    data = resp.json()

    # Yönetmen
    director = ""
    cast_list = []
    credits = data.get("credits", {})

    for person in credits.get("crew", []):
        if person.get("job") == "Director":
            director = person.get("name", "")
            break

    # İlk 5 oyuncu
    for c in credits.get("cast", [])[:5]:
        name = c.get("name")
        if name:
            cast_list.append(name)

    # Türler
    genres = [g.get("name") for g in data.get("genres", []) if g.get("name")]

    overview = data.get("overview") or ""
    runtime = data.get("runtime")

    return {
        "overview": overview,
        "director": director,
        "cast": cast_list,
        "genres": genres,
        "runtime": runtime,
    }


# --- OpenLibrary Ayarları ---
OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPENLIBRARY_COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"


def search_openlibrary_books(query):
    """
    OpenLibrary'de kitap arar.
    Sonuç: {external_id, title, year, authors, poster_url} listesi döner.
    external_id olarak varsa edition_key, yoksa works key kullanılır.
    """
    query = (query or "").strip()
    if not query:
        return []

    params = {
        "title": query,
        "limit": 20,
    }

    try:
        resp = requests.get(OPENLIBRARY_SEARCH_URL, params=params, timeout=5)
        print("[OL] url:", resp.url)
        print("[OL] status:", resp.status_code)
        resp.raise_for_status()
    except requests.RequestException as e:
        print("[OL] HATA:", e)
        return []

    data = resp.json()
    print("[OL] raw num_found:", data.get("num_found"))

    docs = data.get("docs", [])
    print("[OL] docs len:", len(docs))  # DEBUG

    results = []

    for doc in docs:
        title = doc.get("title") or "İsimsiz"
        year = doc.get("first_publish_year")
        authors = ", ".join(doc.get("author_name", [])) if doc.get("author_name") else ""
        cover_id = doc.get("cover_i")

        # --- external_id seçimi ---
        external_id = None
        edition_keys = doc.get("edition_key")
        if edition_keys:
            external_id = edition_keys[0]             # örn: "OL12345M"
        else:
            external_id = doc.get("key")             # örn: "/works/OL82563W"

        if not external_id:
            continue

        poster_url = OPENLIBRARY_COVER_URL.format(cover_id=cover_id) if cover_id else None

        results.append({
            "external_id": external_id,
            "title": title,
            "year": year,
            "authors": authors,
            "poster_url": poster_url,
        })

    print("[OL] Dönen sonuç sayısı:", len(results))
    return results
