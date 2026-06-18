# temu-api-client — Client Python pour l'API Temu Open Platform

**Auteur :** Allan ABATUCI  
**Dernière modification :** 2026-06-18

---

## Architecture interne

Ce document décrit les décisions d'implémentation et les conventions à respecter pour étendre ce package.

---

## Flux d'un appel API

```
TemuClient (facade.py)
  └── OrderRepository (orders.py)
        └── TemuHTTPClient.call(action, params)   ← client.py
              ├── build_signed_params()            ← auth.py
              │     └── SigningStrategy.sign()     ← MD5Signer / HMacSHA256Signer
              ├── requests.Session.post()
              ├── _parse_success() → dict brut
              └── Order.from_api(dict)             ← models.py
```

---

## Module par module

### `facade.py` — `TemuClient`

Point d'entrée unique. Câble le `TemuHTTPClient` avec les quatre repositories.
Ne contient aucune logique métier.

```python
client = TemuClient(save_responses=True, max_retries=3, timeout=10)
```

### `client.py` — `TemuHTTPClient`

Client HTTP bas niveau. Responsabilités strictes :
- Appel POST à `config.API_BASE_URL`
- Retry avec exponential backoff (2^n secondes, plafonné à `MAX_BACKOFF_SECONDS`)
- Parsing de la réponse JSON et levée des exceptions typées
- Sauvegarde optionnelle dans `./responses/`

**Ne pas appeler directement** — passer par `TemuClient`.

Algorithme de backoff :
```
délai = min(2.0 × 2^tentative, 32) secondes
si Retry-After header > délai calculé, utiliser Retry-After
```

### `config.py`

Charge `python-dotenv` depuis le `.env` situé deux niveaux au-dessus du package.
La fonction `validate()` est appelée implicitement par `build_signed_params()` — elle lève `EnvironmentError` si une variable est manquante.

**Ne pas appeler `validate()` à l'import** — cela empêcherait d'importer le package pour des tests sans credentials.

### `auth.py` — Signature (Strategy Pattern)

```
SigningStrategy (ABC)
├── MD5Signer         TEMU_SIGNING_ALGO=md5         (défaut)
└── HMacSHA256Signer  TEMU_SIGNING_ALGO=hmac_sha256
```

Pour ajouter un algorithme : créer une classe héritant de `SigningStrategy` et l'enregistrer dans `_SIGNERS`.

Paramètres toujours inclus dans la signature :
- `app_key`
- `access_token`
- `timestamp` (epoch ms)
- `data_type` (toujours `"JSON"`)

### `models.py` — Dataclasses (Adapter Pattern)

Chaque modèle expose un classmethod `from_api(data: dict)` qui mappe le JSON brut Temu vers des attributs Python nommés proprement.

**Règle :** toute modification de nommage côté Temu se corrige **uniquement** dans `from_api()`. Le reste du code ne dépend jamais des clés JSON Temu directement.

Hiérarchie :
```
Order
  ├── Address
  └── OrderItem[]

Product
  ├── ProductVariant[]
  └── ProductImage[]

StockEntry
ShipmentConfirmation
```

### `exceptions.py`

```
TemuAPIError (base)
├── AuthError          — 401/403, signature invalide, error_code 40001-40003
├── RateLimitError     — 429, contient retry_after (secondes)
├── NotFoundError      — 404
├── ServerError        — 5xx
└── NetworkError       — timeout, connexion perdue
```

Toujours capturer `TemuAPIError` en dernier recours dans les scripts appelants.

### Repositories

Chaque repository suit le même contrat :
- `list(page, page_size, ...)` → `(list[Model], has_more: bool)`
- `list_all(...)` → `list[Model]` (itère automatiquement)
- `get(id)` → `Model`
- Méthodes de mutation (`update_*`, `confirm_*`) → `bool`

---

## Conventions de code

- **Type hints** partout — Python 3.11+, utiliser `X | Y` au lieu de `Optional[X]`
- **Logging** via `logging.getLogger(__name__)`, jamais `print()`
- **Pas de logique métier dans `client.py`** — seulement HTTP
- **Pas d'état partagé entre repositories** — chacun est indépendant
- **`from_api()` ne lève jamais d'exception** — utiliser `.get()` avec des valeurs par défaut

---

## Ajouter un nouvel endpoint

1. Ajouter le classmethod `from_api()` dans le modèle correspondant (`models.py`) si la réponse est nouvelle
2. Ajouter la méthode dans le repository existant (ou créer un nouveau repository)
3. Si c'est une nouvelle ressource, exposer le repository dans `facade.py` et `__init__.py`

Exemple — ajouter `client.orders.cancel(order_id)` :

```python
# Dans orders.py
def cancel(self, order_id: str, reason: str = "") -> bool:
    data = self._http.call("bg.order.cancel", {
        "order_sn": order_id,
        "cancel_reason": reason,
    })
    return bool(data.get("success", False))
```

---

## Tests

Les tests sont à écrire avec `pytest` + `unittest.mock` pour mocker `TemuHTTPClient.call()`.

```python
from unittest.mock import MagicMock
from temu.orders import OrderRepository

def test_list_orders():
    mock_http = MagicMock()
    mock_http.call.return_value = {
        "order_list": [{"order_sn": "123", "order_status": "1", ...}],
        "has_more": False,
    }
    repo = OrderRepository(mock_http)
    orders, has_more = repo.list()
    assert len(orders) == 1
    assert orders[0].order_id == "123"
```

---

## Variables à valider lors de l'obtention des credentials

Les éléments suivants sont basés sur les conventions publiques de l'API Temu Open Platform et doivent être confirmés avec la documentation officielle :

| Élément | Fichier | À vérifier |
|---|---|---|
| URL de base | `config.py` | `https://openapi.temu.com/v1` |
| Algorithme de signature | `auth.py` | MD5 vs HMAC-SHA256, format exact |
| Noms des actions | `orders.py`, `catalog.py`... | `bg.order.list`, `bg.goods.detail`... |
| Noms des champs JSON | `models.py` | `order_sn`, `goods_id`, `sku_id`... |
| Codes d'erreur auth | `client.py` | `40001`, `40002`, `40003` |
| Format du timestamp | `auth.py` | epoch ms vs epoch s |
