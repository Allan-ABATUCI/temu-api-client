"""
Utilitaires — Pagination automatique

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def paginate(
    fetcher: Callable[[int, int], tuple[list, bool]],
    page_size: int = 50,
    max_pages: int = 100,
) -> list:
    """
    Itère automatiquement sur toutes les pages d'un endpoint Temu paginé.

    fetcher(page, page_size) doit retourner (items: list, has_more: bool).
    """
    results: list = []
    for page in range(1, max_pages + 1):
        items, has_more = fetcher(page, page_size)
        results.extend(items)
        if not has_more:
            break
        if page == max_pages:
            logger.warning("pagination_tronquee", extra={"max_pages": max_pages})
    return results
