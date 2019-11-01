import os
import uuid


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


def test_fs(client, tmpdir):
    resp = client.post(
        "/objects/buckets",
        json=dict(name="tBcfs", provider="fs", settings=dict(root_dir=str(tmpdir))),
    )
    assert resp.status_code == 201, resp.json()
    href = resp.json()["href"]

    resp = client.get(href)
    bucket = resp.json()
    assert resp.status_code == 200, bucket
    assert bucket["name"] == "tBcfs"
    assert bucket["provider"] == "fs"
    assert bucket["enabled"] is True
    assert bucket["settings"] == {"root_dir": str(tmpdir)}

    resp = client.get("/objects/buckets")
    assert resp.status_code == 200, resp.json()
    bucket2 = resp.json()[0]
    for key in ("name", "provider", "enabled"):
        assert bucket[key] == bucket2[key]
    assert bucket2["installed"]

    assert client.get("/objects/buckets/tBcfs/").json() == []
    assert client.get("/objects/buckets/tBcfs/%2F").status_code == 400
    assert client.get("/objects/buckets/tBcfs/abc").status_code == 404

    os.mkdir(os.path.join(tmpdir, "abc"))
    assert client.get("/objects/buckets/tBcfs/").json() == ["abc"]

    data = str(uuid.uuid4())
    with open(os.path.join(tmpdir, "abc/test.txt"), "a") as f:
        f.write(data)
    assert client.get("/objects/buckets/tBcfs/").json() == ["abc", "abc/test.txt"]
    assert client.get(
        "/objects/buckets/tBcfs/", params=dict(recursive=False)
    ).json() == ["abc"]
    assert client.get("/objects/buckets/tBcfs/abc").json() == ["abc/test.txt"]
    assert client.get("/objects/buckets/tBcfs/abc/test.txt").text == data

    with open(os.path.join(tmpdir, "abc/test.txt")) as f:
        assert (
            client.put("/objects/buckets/tBcfs/abc/", files=dict(file=f)).status_code
            == 409
        )
    with open(os.path.join(tmpdir, "abc/test.txt")) as f:
        assert client.put(
            "/objects/buckets/tBcfs/abc/upload.txt", files=dict(file=f)
        ).json()["size"] == len(data)
    assert client.get("/objects/buckets/tBcfs/abc/upload.txt").text == data
    assert sorted(client.get("/objects/buckets/tBcfs/abc").json()) == sorted(
        ["abc/test.txt", "abc/upload.txt"]
    )

    assert client.delete("/objects/buckets/tBcfs/abc").status_code == 204
    assert client.get("/objects/buckets/tBcfs/abc").status_code == 404
    assert client.get("/objects/buckets/tBcfs/").json() == []

    resp = client.delete(href)
    assert resp.status_code == 200, resp.json()
    assert resp.json()["href"] == href

    assert client.get(href).status_code == 404
    assert client.get("/objects/buckets").json() == []
