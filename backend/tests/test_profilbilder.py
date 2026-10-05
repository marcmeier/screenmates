"""Profile pictures: upload, re-encoding, limits, rights, clean-up."""

import io

from PIL import Image

from app import bilder

from .conftest import login


def bild(fmt="JPEG", size=(1200, 800), color=(200, 30, 30), **save) -> bytes:
    out = io.BytesIO()
    Image.new("RGBA" if fmt == "PNG" else "RGB", size, color).save(out, fmt, **save)
    return out.getvalue()


def hoch(c, uid, data, ctype="image/jpeg"):
    return c.put(f"/api/users/{uid}/bild", content=data, headers={"content-type": ctype})


def dateien():
    return sorted(p.name for p in bilder.ordner().glob("*.webp"))


def test_upload_becomes_a_small_square_webp(client):
    me = login(client, "marc")
    r = hoch(client, me["id"], bild())
    assert r.status_code == 200, r.text
    url = r.json()["bild"]
    assert url.startswith(f"/api/users/{me['id']}/bild?v=")
    img = client.get(url)
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/webp"
    assert "immutable" in img.headers["cache-control"]
    pic = Image.open(io.BytesIO(img.content))
    assert (pic.format, pic.size) == ("WEBP", (256, 256))
    # Everyone sees it in the user list.
    assert client.get("/api/users").json()["ich"]["bild"] == url


def test_phone_photos_are_turned_upright_and_lose_their_metadata(client):
    me = login(client, "marc")
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90° clockwise to display
    exif[0x8825] = {2: (52.0, 31.0, 0.0)}  # GPS latitude
    exif[0x010F] = "Telefonhersteller"
    # Left half red, right half blue; after the 90° turn red is on top.
    raw = Image.new("RGB", (800, 400), (0, 0, 255))
    raw.paste((255, 0, 0), (0, 0, 400, 400))
    out = io.BytesIO()
    raw.save(out, "JPEG", exif=exif)
    url = hoch(client, me["id"], out.getvalue()).json()["bild"]
    pic = Image.open(io.BytesIO(client.get(url).content))
    assert not pic.getexif()
    assert b"Telefonhersteller" not in client.get(url).content
    top, bottom = pic.convert("RGB").getpixel((128, 20)), pic.convert("RGB").getpixel((128, 236))
    assert top[0] > 200 and top[2] < 60, top
    assert bottom[2] > 200 and bottom[0] < 60, bottom


def test_png_with_transparency_and_other_formats(client):
    me = login(client, "marc")
    assert hoch(client, me["id"], bild("PNG", color=(0, 0, 0, 0)), "image/png").status_code == 200
    assert hoch(client, me["id"], bild("WEBP"), "image/webp").status_code == 200
    assert hoch(client, me["id"], bild("GIF", size=(50, 50)), "image/gif").status_code == 200


def test_not_an_image_or_unknown_format_is_refused(client):
    me = login(client, "marc")
    r = hoch(client, me["id"], b"<?php echo 1; ?>")
    assert r.status_code == 422 and "nicht gelesen" in r.json()["detail"]
    r = hoch(client, me["id"], bild("TIFF", size=(10, 10)), "image/tiff")
    assert r.status_code == 422 and "JPG" in r.json()["detail"]
    assert hoch(client, me["id"], b"").status_code == 422


def test_size_limits(client, monkeypatch):
    me = login(client, "marc")
    assert hoch(client, me["id"], b"\0" * (bilder.MAX_BYTES + 1)).status_code == 413
    # Decompression bombs: refused by their claimed size, before decoding.
    monkeypatch.setattr(bilder, "MAX_PIXEL", 100)
    r = hoch(client, me["id"], bild(size=(20, 20)))
    assert r.status_code == 422 and "zu groß" in r.json()["detail"]


def test_only_owner_or_admin(client, browser):
    marc = login(client, "marc")
    lena = browser()
    login(lena, "lena")
    assert hoch(lena, marc["id"], bild()).status_code == 403
    assert lena.delete(f"/api/users/{marc['id']}/bild").status_code == 403
    assert hoch(browser(), marc["id"], bild()).status_code == 403  # nobody logged in


def test_admin_removes_someones_picture(client, browser):
    login(client, "marc", admin=True)
    lena_b = browser()
    lena = login(lena_b, "lena")
    hoch(lena_b, lena["id"], bild())
    assert len(dateien()) == 1
    r = client.delete(f"/api/users/{lena['id']}/bild")
    assert r.status_code == 200 and r.json()["bild"] is None
    assert dateien() == []
    assert client.get(f"/api/users/{lena['id']}/bild").status_code == 404


def test_new_picture_replaces_the_old_file(client):
    me = login(client, "marc")
    eins = hoch(client, me["id"], bild(color=(1, 2, 3))).json()["bild"]
    zwei = hoch(client, me["id"], bild(color=(3, 2, 1))).json()["bild"]
    assert eins != zwei
    assert len(dateien()) == 1


def test_deleting_a_user_deletes_the_picture(client, browser):
    login(client, "marc", admin=True)
    lena_b = browser()
    lena = login(lena_b, "lena")
    hoch(lena_b, lena["id"], bild())
    client.delete(f"/api/users/{lena['id']}")
    assert dateien() == []


def test_pictures_stay_behind_the_door(client, browser):
    from .conftest import set_door

    me = login(client, "marc", admin=True)
    url = hoch(client, me["id"], bild()).json()["bild"]
    set_door(client)
    assert browser().get(url).status_code == 423
    assert client.get(url).status_code == 200
