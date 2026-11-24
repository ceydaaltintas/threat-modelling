"""Reading diagrams as boxes and arrows instead of pictures."""

from __future__ import annotations

import base64
import io
import urllib.parse
import zipfile
import zlib
from pathlib import Path

from app.pipeline.diagrams import (
    parse_docx,
    parse_drawio,
    parse_file,
    parse_vsdx,
)

UNCOMPRESSED = """
<mxfile host="app.diagrams.net">
  <diagram name="Transfer akışı">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="API Geçidi" vertex="1" parent="1"/>
        <mxCell id="3" value="Transfer Servisi" vertex="1" parent="1"/>
        <mxCell id="4" value="Çekirdek Bankacılık" vertex="1" parent="1"/>
        <mxCell id="5" value="HTTPS" edge="1" source="2" target="3" parent="1"/>
        <mxCell id="6" edge="1" source="3" target="4" parent="1"/>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""


def test_drawio_gives_boxes_and_arrows() -> None:
    diagram = parse_drawio(UNCOMPRESSED)

    assert diagram.kind == "drawio"
    assert diagram.title == "Transfer akışı"
    assert [node.label for node in diagram.nodes] == [
        "API Geçidi",
        "Transfer Servisi",
        "Çekirdek Bankacılık",
    ]
    assert len(diagram.edges) == 2
    text = diagram.as_text()
    assert "API Geçidi → Transfer Servisi (HTTPS)" in text
    assert "Transfer Servisi → Çekirdek Bankacılık" in text


def test_compressed_drawio_is_inflated() -> None:
    """draw.io's default .drawio file packs the model; it must still open."""
    inner = (
        '<mxGraphModel><root>'
        '<mxCell id="2" value="Mobil Uygulama" vertex="1"/>'
        '<mxCell id="3" value="WAF" vertex="1"/>'
        '<mxCell id="4" edge="1" source="2" target="3"/>'
        "</root></mxGraphModel>"
    )
    packed = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
    blob = packed.compress(urllib.parse.quote(inner).encode()) + packed.flush()
    payload = base64.b64encode(blob).decode()

    diagram = parse_drawio(
        f'<mxfile><diagram name="Akış">{payload}</diagram></mxfile>'
    )

    assert [n.label for n in diagram.nodes] == ["Mobil Uygulama", "WAF"]
    assert "Mobil Uygulama → WAF" in diagram.as_text()


def test_unreadable_drawio_says_so_instead_of_failing() -> None:
    diagram = parse_drawio("bu bir XML değil")

    assert diagram.unreadable
    assert "çözümlenemedi" in diagram.unreadable


def test_labels_lose_their_markup() -> None:
    diagram = parse_drawio(
        '<mxGraphModel><root>'
        '<mxCell id="2" value="&lt;b&gt;Ödeme&lt;/b&gt;&lt;br&gt;Servisi" vertex="1"/>'
        "</root></mxGraphModel>"
    )

    assert [n.label for n in diagram.nodes] == ["Ödeme Servisi"]


# --- Visio -------------------------------------------------------------

VSDX_PAGE = """<?xml version="1.0" encoding="utf-8"?>
<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
  <Shapes>
    <Shape ID="1"><Text>Kimlik Doğrulama</Text></Shape>
    <Shape ID="2"><Text>Transfer Servisi</Text></Shape>
    <Shape ID="9"><Text>JWT</Text></Shape>
  </Shapes>
  <Connects>
    <Connect FromSheet="9" FromCell="BeginX" ToSheet="1"/>
    <Connect FromSheet="9" FromCell="EndX" ToSheet="2"/>
  </Connects>
</PageContents>
"""


def _vsdx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("visio/pages/page1.xml", VSDX_PAGE)
    return buffer.getvalue()


def test_vsdx_connector_becomes_an_arrow() -> None:
    diagram = parse_vsdx(_vsdx_bytes(), title="mimari.vsdx")

    labels = {node.label for node in diagram.nodes}
    assert labels == {"Kimlik Doğrulama", "Transfer Servisi"}
    # The connector itself is an arrow, not a box.
    assert "JWT" not in labels
    assert "Kimlik Doğrulama → Transfer Servisi (JWT)" in diagram.as_text()


# --- Word --------------------------------------------------------------


def _docx(media: dict[str, bytes], document_xml: str = "<w:document/>") -> Path:
    import tempfile

    path = Path(tempfile.mkdtemp()) / "doc.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        for name, payload in media.items():
            archive.writestr(name, payload)
    return path


def _png(text_chunks: dict[str, str] | None = None) -> bytes:
    from PIL import Image, PngImagePlugin

    image = Image.new("RGB", (8, 8), "white")
    info = PngImagePlugin.PngInfo()
    for key, value in (text_chunks or {}).items():
        info.add_text(key, value)
    buffer = io.BytesIO()
    image.save(buffer, "PNG", pnginfo=info)
    return buffer.getvalue()


def test_drawio_pasted_into_word_is_read_from_the_picture() -> None:
    """An editable PNG carries its own XML; no vision model needed."""
    path = _docx({"word/media/image1.png": _png({"mxfile": UNCOMPRESSED})})

    diagrams = parse_docx(path)

    assert len(diagrams) == 1
    assert diagrams[0].kind == "drawio"
    assert "API Geçidi → Transfer Servisi" in diagrams[0].as_text()


def test_a_flat_picture_is_reported_not_dropped() -> None:
    path = _docx({"word/media/image1.png": _png()})

    diagrams = parse_docx(path)

    assert len(diagrams) == 1
    assert diagrams[0].kind == "raster"
    assert "model onayı" in (diagrams[0].unreadable or "")


def test_visio_object_inside_word_is_read() -> None:
    path = _docx({"word/embeddings/oleObject1.vsdx": _vsdx_bytes()})

    diagrams = parse_docx(path)

    assert any(d.kind == "vsdx" for d in diagrams)
    assert "Kimlik Doğrulama → Transfer Servisi" in diagrams[0].as_text()


WORD_SHAPES = """<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <w:body>
    <wps:wsp><a:t>Mobil Uygulama</a:t></wps:wsp>
    <wps:wsp><a:t>API Geçidi</a:t></wps:wsp>
  </w:body>
</w:document>
"""


def test_word_shapes_give_boxes_and_say_arrows_are_missing() -> None:
    path = _docx({}, document_xml=WORD_SHAPES)

    diagrams = parse_docx(path)

    assert len(diagrams) == 1
    assert [n.label for n in diagrams[0].nodes] == ["Mobil Uygulama", "API Geçidi"]
    # Word does not record which shapes an arrow joins; say so.
    assert "akış yönleri çıkarılamadı" in (diagrams[0].unreadable or "")


def test_an_uploaded_drawio_file_is_read() -> None:
    import tempfile

    path = Path(tempfile.mkdtemp()) / "mimari.drawio"
    path.write_text(UNCOMPRESSED, encoding="utf-8")

    diagrams = parse_file(path)

    assert len(diagrams) == 1
    assert "Transfer Servisi → Çekirdek Bankacılık" in diagrams[0].as_text()
