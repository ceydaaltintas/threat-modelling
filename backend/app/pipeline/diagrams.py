"""Reading architecture diagrams as structure, not as pictures.

A flow diagram usually carries the part of the architecture that prose
leaves out: which component talks to which. Until now the platform ignored
it completely - a page with a diagram and a paragraph around it produced no
image and no boxes, so the diagram was invisible.

The trick is that most diagrams in bank documents are *not* pictures:

  * drawn with Word's own shapes   -> geometry and text sit in document.xml
  * pasted as draw.io editable PNG -> the diagram XML rides in PNG metadata
  * embedded as a Visio object     -> word/embeddings holds a .vsdx (a zip
                                      of XML)
  * a .drawio / .vsdx file uploaded on its own

In all of those the boxes and arrows are data. We turn them back into text
("API Geçidi → Transfer Servisi"), which means no vision model is needed:
the extracted flow is read by the same step that reads the prose.

Only a flattened raster (a screenshot, something drawn in Paint) carries no
structure. Those are reported as unreadable rather than quietly dropped, so
the expert can add the missing components at the model approval step.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# draw.io stores the diagram in a PNG text chunk under this key.
DRAWIO_PNG_KEYS = ("mxfile", "mxGraphModel")
MAX_LABEL = 200
MAX_NODES = 400


@dataclass
class DiagramNode:
    id: str
    label: str


@dataclass
class DiagramEdge:
    source: str
    target: str
    label: str | None = None


@dataclass
class Diagram:
    """One diagram, as boxes and arrows."""

    # drawio | vsdx | word_shapes | pdf_vector
    kind: str
    title: str | None = None
    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)
    # Set when a picture was found but carries no structure.
    unreadable: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.nodes and not self.edges and not self.unreadable

    def as_text(self) -> str:
        """The diagram as lines the extraction step can read.

        Written in the document's own language so it reads as part of the
        text rather than as a machine dump; the LLM is told in the prompt
        that these lines come from a diagram.
        """
        if self.unreadable:
            return (
                f"[Şema: {self.title or 'adsız'} — okunamadı] "
                f"{self.unreadable}"
            )

        names = {node.id: node.label for node in self.nodes}
        lines = [f"[Şema: {self.title or 'adsız'}]"]
        if self.nodes:
            lines.append(
                "Şemadaki kutular: "
                + ", ".join(node.label for node in self.nodes if node.label)
            )
        for edge in self.edges:
            source = names.get(edge.source, edge.source)
            target = names.get(edge.target, edge.target)
            if not source or not target:
                continue
            suffix = f" ({edge.label})" if edge.label else ""
            lines.append(f"Şemadaki akış: {source} → {target}{suffix}")
        return "\n".join(lines)


def _clean(value: str | None) -> str:
    if not value:
        return ""
    # Diagram labels carry markup and line breaks far more often than prose.
    text = re.sub(r"<br\s*/?>", " ", value)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    return " ".join(text.split())[:MAX_LABEL]


# --- draw.io -----------------------------------------------------------


def parse_drawio(data: bytes | str, *, title: str | None = None) -> Diagram:
    """A .drawio / mxfile document.

    Compressed diagrams (draw.io's default for .drawio files) are inflated
    first; an uncompressed <mxGraphModel> is read as is.
    """
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    diagram = Diagram(kind="drawio")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        logger.info("draw.io XML okunamadı: %s", exc)
        diagram.unreadable = "draw.io dosyası çözümlenemedi."
        return diagram

    models: list[ET.Element] = []
    if root.tag == "mxGraphModel":
        models.append(root)
    for node in root.iter("diagram"):
        inner = node.find("mxGraphModel")
        if inner is not None:
            models.append(inner)
            if not diagram.title:
                diagram.title = node.get("name")
        elif (node.text or "").strip():
            inflated = _inflate_drawio(node.text.strip())
            if inflated is None:
                diagram.unreadable = (
                    "Şema sıkıştırılmış ve açılamadı; draw.io'da "
                    "'Sıkıştırılmamış XML' olarak kaydedip tekrar yükleyin."
                )
                continue
            try:
                models.append(ET.fromstring(inflated))
            except ET.ParseError:
                diagram.unreadable = "Şema içeriği çözümlenemedi."
            if not diagram.title:
                diagram.title = node.get("name")

    diagram.title = diagram.title or title
    for model in models:
        _read_mxgraph(model, diagram)
    if diagram.nodes or diagram.edges:
        diagram.unreadable = None
    return diagram


def _inflate_drawio(payload: str) -> str | None:
    """draw.io packs the model as deflate + base64 + URL encoding."""
    import base64
    import urllib.parse
    import zlib

    try:
        raw = base64.b64decode(payload)
        inflated = zlib.decompress(raw, -zlib.MAX_WBITS)
        return urllib.parse.unquote(inflated.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 - any failure means "not readable"
        return None


def _read_mxgraph(model: ET.Element, diagram: Diagram) -> None:
    for cell in model.iter("mxCell"):
        cid = cell.get("id") or ""
        label = _clean(cell.get("value"))
        if cell.get("edge") == "1":
            source, target = cell.get("source"), cell.get("target")
            if source and target:
                diagram.edges.append(DiagramEdge(source, target, label or None))
        elif cell.get("vertex") == "1" and label:
            if len(diagram.nodes) < MAX_NODES:
                diagram.nodes.append(DiagramNode(cid, label))


# --- Visio -------------------------------------------------------------

_VSDX_NS = "{http://schemas.microsoft.com/office/visio/2012/main}"


def parse_vsdx(path_or_bytes: Path | bytes, *, title: str | None = None) -> Diagram:
    """A .vsdx file: a zip whose pages are XML.

    Visio keeps shape text in <Text> and connections in <Connect>, which is
    enough to recover boxes and the arrows between them.
    """
    import io

    diagram = Diagram(kind="vsdx", title=title)
    source = (
        io.BytesIO(path_or_bytes)
        if isinstance(path_or_bytes, bytes)
        else str(path_or_bytes)
    )
    try:
        with zipfile.ZipFile(source) as archive:
            pages = [
                name
                for name in archive.namelist()
                if re.fullmatch(r"visio/pages/page\d+\.xml", name)
            ]
            for name in sorted(pages):
                _read_vsdx_page(archive.read(name), diagram)
    except (zipfile.BadZipFile, KeyError) as exc:
        logger.info("vsdx okunamadı: %s", exc)
        diagram.unreadable = "Visio dosyası çözümlenemedi."
    return diagram


def _read_vsdx_page(data: bytes, diagram: Diagram) -> None:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return

    labels: dict[str, str] = {}
    for shape in root.iter(f"{_VSDX_NS}Shape"):
        sid = shape.get("ID") or ""
        text = "".join(shape.find(f"{_VSDX_NS}Text").itertext()) if shape.find(f"{_VSDX_NS}Text") is not None else ""
        label = _clean(text)
        if sid and label:
            labels[sid] = label

    # <Connect> rows pair a connector shape with the shape it touches.
    touches: dict[str, list[tuple[str, str]]] = {}
    for connect in root.iter(f"{_VSDX_NS}Connect"):
        from_shape = connect.get("FromSheet") or ""
        to_shape = connect.get("ToSheet") or ""
        role = connect.get("FromCell") or ""
        if from_shape and to_shape:
            touches.setdefault(from_shape, []).append((role, to_shape))

    for sid, label in labels.items():
        if len(diagram.nodes) < MAX_NODES:
            diagram.nodes.append(DiagramNode(sid, label))

    for connector, ends in touches.items():
        begin = next((s for role, s in ends if "Begin" in role), None)
        end = next((s for role, s in ends if "End" in role), None)
        if begin and end:
            diagram.edges.append(
                DiagramEdge(begin, end, labels.get(connector) or None)
            )

    # A connector's own label is not a box.
    connector_ids = set(touches)
    diagram.nodes = [n for n in diagram.nodes if n.id not in connector_ids]


# --- Word --------------------------------------------------------------

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_WPS = "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def parse_docx(path: Path) -> list[Diagram]:
    """Every diagram a .docx carries, whatever form it took."""
    found: list[Diagram] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()

            # 1 - Visio objects embedded as OLE.
            for name in names:
                if name.startswith("word/embeddings/") and name.endswith(".vsdx"):
                    found.append(
                        parse_vsdx(archive.read(name), title=Path(name).name)
                    )

            # 2 - pictures that still carry their draw.io source.
            for name in names:
                if not name.startswith("word/media/"):
                    continue
                payload = archive.read(name)
                embedded = _drawio_from_png(payload)
                if embedded is not None:
                    found.append(parse_drawio(embedded, title=Path(name).name))
                elif Path(name).suffix.lower() in (".png", ".jpg", ".jpeg", ".gif"):
                    found.append(
                        Diagram(
                            kind="raster",
                            title=Path(name).name,
                            unreadable=(
                                "Dokümandaki görsel düz bir resim; kutu ve ok "
                                "bilgisi taşımıyor. Şemadaki bileşenleri "
                                "model onayı adımında ekleyebilirsiniz."
                            ),
                        )
                    )

            # 3 - shapes drawn with Word's own tools.
            if "word/document.xml" in names:
                shapes = _word_shapes(archive.read("word/document.xml"))
                if shapes is not None:
                    found.append(shapes)
    except zipfile.BadZipFile:
        logger.info("docx açılamadı: %s", path)
        return []

    return [d for d in found if not d.is_empty]


def _drawio_from_png(data: bytes) -> str | None:
    """draw.io's "editable PNG" keeps the model in a tEXt/zTXt chunk."""
    if not data.startswith(b"\x89PNG"):
        return None
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            meta = dict(getattr(image, "text", {}) or {})
    except Exception:  # noqa: BLE001 - a broken picture is just not a diagram
        return None

    for key in DRAWIO_PNG_KEYS:
        if meta.get(key):
            value = meta[key]
            if key == "mxGraphModel":
                return value
            return value
    return None


def _word_shapes(data: bytes) -> Diagram | None:
    """Boxes drawn with Word's own shapes.

    Word stores a shape's text inside the shape, so the labels are real
    text. It does not record "A connects to B" the way draw.io does, so
    only the boxes are recovered; the arrows between them are not.
    """
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None

    labels: list[str] = []
    for shape in root.iter(f"{_WPS}wsp"):
        text = " ".join(
            node.text or "" for node in shape.iter(f"{_A}t")
        ) or " ".join(node.text or "" for node in shape.iter(f"{_W}t"))
        label = _clean(text)
        if label:
            labels.append(label)

    if not labels:
        return None

    diagram = Diagram(kind="word_shapes", title="Word şekilleri")
    for index, label in enumerate(labels[:MAX_NODES]):
        diagram.nodes.append(DiagramNode(f"w{index}", label))
    diagram.unreadable = (
        "Word şekillerinde kutular okundu; Word okların hangi kutuları "
        "bağladığını kaydetmediği için akış yönleri çıkarılamadı."
    )
    return diagram


# --- Standalone uploads ------------------------------------------------


def parse_file(path: Path) -> list[Diagram]:
    """A diagram uploaded on its own."""
    suffix = path.suffix.lower()
    if suffix in (".drawio", ".xml"):
        return [d for d in [parse_drawio(path.read_bytes(), title=path.name)] if not d.is_empty]
    if suffix == ".vsdx":
        return [d for d in [parse_vsdx(path, title=path.name)] if not d.is_empty]
    if suffix == ".docx":
        return parse_docx(path)
    return []


# --- PDF ---------------------------------------------------------------

# A page drawn with this many curve objects is doing more than ruling a
# table: across the sample documents every page of prose and tables has
# exactly zero, while a page carrying a diagram has dozens.
MIN_DIAGRAM_CURVES = 20


def detect_pdf_diagrams(path: Path) -> list[Diagram]:
    """Pages that appear to carry a diagram, reported but not interpreted.

    Reading boxes and arrows out of a PDF was tried and dropped. The
    drawing primitives do not say what they are: a table's cells are
    rectangles and its rules are lines, so tables came out as architecture
    - and a real diagram exported by one tool is rectangles while another
    tool's is curves, so genuine diagrams were missed. Inventing flows from
    a table is worse than reading none, so this only reports the page and
    asks for the source file, which the Word and draw.io paths do read.
    """
    import pdfplumber

    found: list[Diagram] = []
    try:
        with pdfplumber.open(str(path)) as document:
            for number, page in enumerate(document.pages, start=1):
                curves = len(page.curves or [])
                if curves < MIN_DIAGRAM_CURVES:
                    continue
                found.append(
                    Diagram(
                        kind="pdf_vector",
                        title=f"Sayfa {number}",
                        unreadable=(
                            "Bu sayfada bir şema var gibi görünüyor ama "
                            "PDF'ten kutu ve ok bilgisi güvenilir biçimde "
                            "okunamıyor. Şemanın kaynağını (.drawio, .vsdx) "
                            "veya şemayı içeren Word dosyasını yüklerseniz "
                            "akışlar da okunur."
                        ),
                    )
                )
    except Exception as exc:  # noqa: BLE001 - a broken PDF is not a diagram
        logger.info("PDF şeması incelenemedi: %s", exc)
    return found
