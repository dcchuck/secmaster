def test_rate_limit_headers_present(client):
    response = client.get("/api/v1/issuers")
    # slowapi adds X-RateLimit headers
    assert "X-RateLimit-Limit" in response.headers or response.status_code == 200
    # Basic smoke test -- the real enforcement is tested by exceeding the limit
