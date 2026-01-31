# Examples

This page provides practical examples of using `aresilient` in real-world scenarios.

## Basic Examples

### Simple GET Request

The most basic usage - fetch data from an API:

```python
from aresilient import get_with_automatic_retry

response = get_with_automatic_retry("https://api.example.com/users")
users = response.json()

for user in users:
    print(f"User: {user['name']}")
```

### POST with JSON Data

Send data to an API:

```python
from aresilient import post_with_automatic_retry

new_user = {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
}

response = post_with_automatic_retry(
    "https://api.example.com/users",
    json=new_user
)

created_user = response.json()
print(f"Created user with ID: {created_user['id']}")
```

### Custom Retry Configuration

Configure retry behavior for a specific endpoint:

```python
from aresilient import get_with_automatic_retry

# Rate-limited API - be more patient
response = get_with_automatic_retry(
    "https://api.example.com/rate-limited-endpoint",
    max_retries=5,
    backoff_factor=2.0,
    jitter_factor=0.2,
    timeout=30.0
)
```

## Intermediate Examples

### Authenticated API Requests

Using a bearer token for authentication:

```python
import httpx
from aresilient import get_with_automatic_retry

API_TOKEN = "your-api-token-here"

# Method 1: Pass headers directly
response = get_with_automatic_retry(
    "https://api.example.com/protected/data",
    headers={"Authorization": f"Bearer {API_TOKEN}"}
)

# Method 2: Use a custom client
with httpx.Client(headers={"Authorization": f"Bearer {API_TOKEN}"}) as client:
    response1 = get_with_automatic_retry(
        "https://api.example.com/protected/users",
        client=client
    )
    response2 = get_with_automatic_retry(
        "https://api.example.com/protected/posts",
        client=client
    )
```

### File Upload

Upload files to an API:

```python
from aresilient import post_with_automatic_retry

# Upload single file
with open("document.pdf", "rb") as f:
    response = post_with_automatic_retry(
        "https://api.example.com/upload",
        files={"file": f}
    )

print(f"File uploaded: {response.json()['file_id']}")

# Upload multiple files
with open("image1.jpg", "rb") as img1, open("image2.jpg", "rb") as img2:
    response = post_with_automatic_retry(
        "https://api.example.com/gallery/upload",
        files={
            "image1": img1,
            "image2": img2
        }
    )
```

### Pagination

Fetch all pages from a paginated API:

```python
from aresilient import get_with_automatic_retry

def fetch_all_items(base_url: str, max_pages: int = 100) -> list:
    """Fetch all items from a paginated API."""
    all_items = []
    page = 1
    
    while page <= max_pages:
        response = get_with_automatic_retry(
            base_url,
            params={"page": page, "per_page": 100}
        )
        
        data = response.json()
        items = data.get("items", [])
        
        if not items:
            break
        
        all_items.extend(items)
        
        # Check if there are more pages
        if not data.get("has_next", False):
            break
        
        page += 1
    
    return all_items

# Usage
all_users = fetch_all_items("https://api.example.com/users")
print(f"Fetched {len(all_users)} users")
```

### Query Parameters

Working with query parameters:

```python
from aresilient import get_with_automatic_retry

# Search with filters
response = get_with_automatic_retry(
    "https://api.example.com/products/search",
    params={
        "query": "laptop",
        "category": "electronics",
        "min_price": 500,
        "max_price": 2000,
        "sort": "price_asc"
    }
)

products = response.json()
```

## Advanced Examples

### Async Concurrent Requests

Fetch multiple resources concurrently:

```python
import asyncio
import httpx
from aresilient import get_with_automatic_retry_async

async def fetch_user_details(user_ids: list[int]) -> list[dict]:
    """Fetch details for multiple users concurrently."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [
            get_with_automatic_retry_async(
                f"https://api.example.com/users/{user_id}",
                client=client
            )
            for user_id in user_ids
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        users = []
        for user_id, response in zip(user_ids, responses):
            if isinstance(response, Exception):
                print(f"Failed to fetch user {user_id}: {response}")
            else:
                users.append(response.json())
        
        return users

# Usage
user_ids = [1, 2, 3, 4, 5, 10, 15, 20]
users = asyncio.run(fetch_user_details(user_ids))
print(f"Successfully fetched {len(users)} users")
```

### Rate-Limited API Client

Create a client that handles rate limiting gracefully:

```python
import time
from typing import Any
from aresilient import get_with_automatic_retry

class RateLimitedAPIClient:
    """API client with built-in rate limiting."""
    
    def __init__(self, base_url: str, api_key: str, requests_per_second: float = 10):
        self.base_url = base_url
        self.api_key = api_key
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
    
    def _wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
    
    def get(self, endpoint: str, **kwargs: Any) -> dict:
        """Make a GET request with rate limiting."""
        self._wait_if_needed()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = get_with_automatic_retry(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            max_retries=5,
            backoff_factor=1.0,
            jitter_factor=0.1,
            **kwargs
        )
        return response.json()

# Usage
client = RateLimitedAPIClient(
    base_url="https://api.example.com",
    api_key="your-api-key",
    requests_per_second=10
)

# Make requests - they will be automatically rate limited
for i in range(20):
    user = client.get(f"users/{i}")
    print(f"Fetched user {user['name']}")
```

### Caching with Retry

Implement caching with automatic retry:

```python
import hashlib
import json
from functools import lru_cache
from typing import Any
from aresilient import get_with_automatic_retry

def cache_key(url: str, params: dict | None = None) -> str:
    """Generate cache key from URL and params."""
    key_data = {"url": url, "params": params or {}}
    key_json = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_json.encode()).hexdigest()

@lru_cache(maxsize=1000)
def cached_get(url: str, params_json: str = "{}") -> dict:
    """Cached GET request with automatic retry."""
    params = json.loads(params_json)
    response = get_with_automatic_retry(
        url,
        params=params,
        max_retries=3,
        timeout=15.0
    )
    return response.json()

# Usage
def fetch_user(user_id: int) -> dict:
    """Fetch user with caching."""
    return cached_get(f"https://api.example.com/users/{user_id}")

# First call - fetches from API
user = fetch_user(123)

# Second call - returns cached result
user = fetch_user(123)  # No API call made
```

### Batch Processing

Process items in batches with retry logic:

```python
from typing import Any
from aresilient import post_with_automatic_retry

def process_in_batches(
    items: list[Any],
    batch_size: int = 100,
    api_url: str = "https://api.example.com/batch"
) -> list[dict]:
    """Process items in batches."""
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        print(f"Processing batch {i//batch_size + 1} ({len(batch)} items)")
        
        try:
            response = post_with_automatic_retry(
                api_url,
                json={"items": batch},
                max_retries=5,
                backoff_factor=1.0,
                timeout=60.0
            )
            
            batch_results = response.json()
            results.extend(batch_results)
            
        except Exception as e:
            print(f"Failed to process batch: {e}")
            # Optionally retry individual items
            for item in batch:
                try:
                    response = post_with_automatic_retry(
                        api_url,
                        json={"items": [item]},
                        max_retries=3
                    )
                    results.extend(response.json())
                except Exception as item_error:
                    print(f"Failed to process item: {item_error}")
    
    return results

# Usage
items = [{"id": i, "data": f"item_{i}"} for i in range(1000)]
results = process_in_batches(items, batch_size=100)
print(f"Processed {len(results)} items")
```

### Error Recovery with Fallback

Implement fallback strategies for resilience:

```python
from aresilient import get_with_automatic_retry, HttpRequestError

def fetch_with_fallback(resource_id: str) -> dict:
    """Fetch data with multiple fallback strategies."""
    
    # Strategy 1: Try primary API
    try:
        response = get_with_automatic_retry(
            f"https://primary-api.example.com/resource/{resource_id}",
            max_retries=2,
            timeout=10.0
        )
        return {"source": "primary", "data": response.json()}
    except HttpRequestError as e:
        print(f"Primary API failed: {e}")
    
    # Strategy 2: Try secondary API
    try:
        response = get_with_automatic_retry(
            f"https://secondary-api.example.com/resource/{resource_id}",
            max_retries=2,
            timeout=15.0
        )
        return {"source": "secondary", "data": response.json()}
    except HttpRequestError as e:
        print(f"Secondary API failed: {e}")
    
    # Strategy 3: Try cache
    cached_data = get_from_cache(resource_id)
    if cached_data:
        return {"source": "cache", "data": cached_data}
    
    # Strategy 4: Return default/placeholder
    return {
        "source": "default",
        "data": {
            "id": resource_id,
            "available": False,
            "message": "Resource temporarily unavailable"
        }
    }

def get_from_cache(resource_id: str) -> dict | None:
    """Get data from cache (implementation depends on your cache)."""
    # Placeholder for cache implementation
    return None

# Usage
data = fetch_with_fallback("abc123")
print(f"Data source: {data['source']}")
```

## Real-World Scenarios

### GitHub API Client

Example of a GitHub API client:

```python
import httpx
from aresilient import get_with_automatic_retry

class GitHubClient:
    """Simple GitHub API client."""
    
    def __init__(self, token: str):
        self.base_url = "https://api.github.com"
        self.client = httpx.Client(
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            },
            timeout=30.0
        )
    
    def get_user(self, username: str) -> dict:
        """Get user information."""
        response = get_with_automatic_retry(
            f"{self.base_url}/users/{username}",
            client=self.client,
            max_retries=3
        )
        return response.json()
    
    def get_repos(self, username: str) -> list[dict]:
        """Get user's repositories."""
        response = get_with_automatic_retry(
            f"{self.base_url}/users/{username}/repos",
            client=self.client,
            params={"per_page": 100},
            max_retries=3
        )
        return response.json()
    
    def __del__(self):
        """Close client on cleanup."""
        self.client.close()

# Usage
gh = GitHubClient(token="your-github-token")
user = gh.get_user("octocat")
repos = gh.get_repos("octocat")
print(f"{user['name']} has {len(repos)} repositories")
```

### Weather API Client

Fetch weather data with retry logic:

```python
from aresilient import get_with_automatic_retry

class WeatherClient:
    """Weather API client."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.weatherapi.com/v1"
    
    def get_current_weather(self, location: str) -> dict:
        """Get current weather for a location."""
        response = get_with_automatic_retry(
            f"{self.base_url}/current.json",
            params={
                "key": self.api_key,
                "q": location,
                "aqi": "no"
            },
            max_retries=3,
            backoff_factor=0.5,
            timeout=15.0
        )
        return response.json()
    
    def get_forecast(self, location: str, days: int = 3) -> dict:
        """Get weather forecast."""
        response = get_with_automatic_retry(
            f"{self.base_url}/forecast.json",
            params={
                "key": self.api_key,
                "q": location,
                "days": days,
                "aqi": "no"
            },
            max_retries=3,
            backoff_factor=0.5,
            timeout=20.0
        )
        return response.json()

# Usage
weather = WeatherClient(api_key="your-api-key")
current = weather.get_current_weather("London")
print(f"Temperature: {current['current']['temp_c']}°C")

forecast = weather.get_forecast("London", days=5)
for day in forecast['forecast']['forecastday']:
    print(f"{day['date']}: {day['day']['condition']['text']}")
```

### Database-backed API Cache

Implement a persistent cache for API responses:

```python
import sqlite3
import json
import time
from typing import Any
from aresilient import get_with_automatic_retry

class CachedAPIClient:
    """API client with SQLite-based caching."""
    
    def __init__(self, db_path: str = "api_cache.db", ttl: int = 3600):
        self.db_path = db_path
        self.ttl = ttl  # Cache time-to-live in seconds
        self._init_db()
    
    def _init_db(self):
        """Initialize cache database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    timestamp REAL
                )
            """)
    
    def _get_cache_key(self, url: str, params: dict | None = None) -> str:
        """Generate cache key."""
        key_data = {"url": url, "params": params or {}}
        return json.dumps(key_data, sort_keys=True)
    
    def _get_cached(self, key: str) -> Any | None:
        """Get value from cache if not expired."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value, timestamp FROM cache WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if row:
                value, timestamp = row
                if time.time() - timestamp < self.ttl:
                    return json.loads(value)
                else:
                    # Expired, delete it
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        
        return None
    
    def _set_cached(self, key: str, value: Any):
        """Store value in cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, timestamp) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time())
            )
    
    def get(self, url: str, params: dict | None = None, **kwargs: Any) -> dict:
        """Get data with caching."""
        cache_key = self._get_cache_key(url, params)
        
        # Try cache first
        cached = self._get_cached(cache_key)
        if cached is not None:
            print(f"Cache hit for {url}")
            return cached
        
        # Cache miss, fetch from API
        print(f"Cache miss for {url}")
        response = get_with_automatic_retry(
            url,
            params=params,
            **kwargs
        )
        
        data = response.json()
        self._set_cached(cache_key, data)
        
        return data

# Usage
client = CachedAPIClient(ttl=3600)  # 1 hour cache

# First call - fetches from API
data1 = client.get("https://api.example.com/users/123")

# Second call - returns cached result
data2 = client.get("https://api.example.com/users/123")
```

## Testing Examples

### Unit Testing with Mocks

Example of testing code that uses aresilient:

```python
import pytest
import httpx
import respx
from aresilient import get_with_automatic_retry, HttpRequestError

@respx.mock
def test_successful_api_call():
    """Test successful API call."""
    # Mock the API endpoint
    respx.get("https://api.example.com/users/123").mock(
        return_value=httpx.Response(
            200,
            json={"id": 123, "name": "John Doe"}
        )
    )
    
    # Call the function
    response = get_with_automatic_retry("https://api.example.com/users/123")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 123
    assert data["name"] == "John Doe"

@respx.mock
def test_retry_on_server_error():
    """Test that retry works on server errors."""
    # Mock: first two calls fail, third succeeds
    route = respx.get("https://api.example.com/data")
    route.side_effect = [
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(503, text="Service Unavailable"),
        httpx.Response(200, json={"status": "ok"}),
    ]
    
    # Should succeed on third attempt
    response = get_with_automatic_retry(
        "https://api.example.com/data",
        max_retries=3,
        backoff_factor=0.01  # Fast retry for tests
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@respx.mock
def test_failure_after_max_retries():
    """Test that error is raised after max retries."""
    # Mock: all calls fail
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    
    # Should raise after exhausting retries
    with pytest.raises(HttpRequestError) as exc_info:
        get_with_automatic_retry(
            "https://api.example.com/data",
            max_retries=2,
            backoff_factor=0.01
        )
    
    assert exc_info.value.status_code == 500
```

## See Also

- [User Guide](user_guide.md) - Comprehensive usage documentation
- [Best Practices](best_practices.md) - Recommended patterns and practices
- [API Reference](refs/index.md) - Complete API documentation
- [FAQ](faq.md) - Frequently asked questions
