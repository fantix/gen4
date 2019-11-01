def test_schema(client):
    assert client.post("/objects/buckets").status_code == 422
    assert client.post("/objects/buckets", json=dict(name="tBc_1")).status_code == 422
    assert (
        client.post(
            "/objects/buckets", json=dict(name="1_tbc", provider="s3")
        ).status_code
        == 422
    )
    assert client.put("/objects/buckets/na", json=dict(name="xx")).status_code == 422
    assert client.put("/objects/buckets/na", json=dict(enabled=True)).status_code == 404
    assert client.delete("/objects/buckets/na").status_code == 404


def test_crud(client):
    assert client.get("/objects/buckets").json() == []

    resp = client.post("/objects/buckets", json=dict(name="tBc_1", provider="n/a"))
    assert resp.status_code == 201, resp.json()
    href = resp.json()["href"]

    resp = client.get(href)
    bucket = resp.json()
    assert resp.status_code == 200, bucket
    assert bucket["name"] == "tBc_1"
    assert bucket["provider"] == "n/a"
    assert bucket["enabled"] is True
    assert bucket["settings"] == {}

    resp = client.get("/objects/buckets")
    assert resp.status_code == 200, resp.json()
    bucket2 = resp.json()[0]
    for key in ("name", "provider", "enabled"):
        assert bucket[key] == bucket2[key]
    assert not bucket2["installed"]

    resp = client.put(href, json=dict(enabled=False))
    assert resp.status_code == 200, resp.json()
    assert resp.json()["href"] == href
    assert not client.get(href).json()["enabled"]

    resp = client.put(href, json=dict(settings={"abc": 123}))
    assert resp.status_code == 200, resp.json()
    assert resp.json()["href"] == href
    assert client.get(href).json()["settings"] == {"abc": 123}

    resp = client.delete(href)
    assert resp.status_code == 200, resp.json()
    assert resp.json()["href"] == href

    assert client.get(href).status_code == 404
    assert client.get("/objects/buckets").json() == []
