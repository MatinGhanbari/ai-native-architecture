#!/usr/bin/env python3
"""Merge the three presenter decks into one PowerPoint file.

Preserves each slide's XML (animations, transitions, notes, media) by
copying Office Open XML parts and remapping layouts onto the destination
package. Visible PowerPoint slide numbers become sequential. Hard-coded
numbers drawn inside shapes are left unchanged.

Usage (from the repo root):

    python tools/merge_decks.py
    python tools/merge_decks.py --parts-only
    python tools/merge_decks.py -o dist/AI-native-Architecture.pptx
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

REL_SLIDE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
REL_LAYOUT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
REL_NOTES = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
REL_NOTESMASTER = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster"
REL_SLIDEMASTER = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster"
REL_HANDOUTMASTER = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/handoutMaster"
REL_PRESPROPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps"
REL_VIEWPROPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps"
REL_TABLESTYLES = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/tableStyles"
REL_THEME = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
REL_COMMENTAUTHORS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/commentAuthors"
REL_TAGS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/tags"

# Relationships that must be remapped to the destination package, not copied.
REMAP_TYPES = {REL_LAYOUT, REL_NOTESMASTER, REL_SLIDEMASTER, REL_HANDOUTMASTER}

CONTENT_TYPES = {
    "slides": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
    "notesSlides": "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
    "charts": "application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
    "chartColors": "application/vnd.ms-office.chartcolorstyle+xml",
    "chartStyles": "application/vnd.ms-office.chartstyle+xml",
    "diagrams": "application/vnd.openxmlformats-officedocument.drawingml.diagramData+xml",
    "tags": "application/vnd.openxmlformats-officedocument.presentationml.tags+xml",
    "embeddings": "application/vnd.openxmlformats-officedocument.oleObject",
}

NSMAP_CT = {"ct": CT_NS}
NSMAP_REL = {"pr": REL_NS}
NSMAP_P = {"p": P_NS, "r": R_NS}

XML_PARSER = etree.XMLParser(remove_blank_text=False)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def unpack(pptx: Path, dest: Path) -> None:
    with zipfile.ZipFile(pptx) as zf:
        zf.extractall(dest)


def pack(src_dir: Path, out_pptx: Path) -> None:
    out_pptx.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(src_dir.rglob("*"), key=lambda p: p.as_posix())
    # [Content_Types].xml first, then _rels, then the rest — a common convention.
    def order(path: Path) -> tuple:
        rel = path.relative_to(src_dir).as_posix()
        if rel == "[Content_Types].xml":
            return (0, rel)
        if rel.startswith("_rels"):
            return (1, rel)
        return (2, rel)

    files = [p for p in files if p.is_file()]
    files.sort(key=order)
    with zipfile.ZipFile(out_pptx, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(src_dir).as_posix())


def parse(path: Path) -> etree._ElementTree:
    return etree.parse(str(path), XML_PARSER)


def write_xml(tree: etree._ElementTree, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(path),
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )


def rels_path_for(part: Path) -> Path:
    return part.parent / "_rels" / (part.name + ".rels")


def load_rels(part: Path) -> etree._ElementTree | None:
    rp = rels_path_for(part)
    if not rp.exists():
        return None
    return parse(rp)


def next_rid(rels_tree: etree._ElementTree) -> int:
    nums = [0]
    for rel in rels_tree.getroot():
        rid = rel.get("Id") or ""
        m = re.match(r"rId(\d+)$", rid)
        if m:
            nums.append(int(m.group(1)))
    return max(nums) + 1


def max_existing_index(folder: Path, prefix: str, suffix: str = ".xml") -> int:
    if not folder.exists():
        return 0
    nums = [0]
    for p in folder.iterdir():
        m = re.match(rf"{re.escape(prefix)}(\d+){re.escape(suffix)}$", p.name)
        if m:
            nums.append(int(m.group(1)))
    return max(nums)


def layout_name(layout_file: Path) -> str | None:
    tree = parse(layout_file)
    csld = tree.getroot().find(f"{{{P_NS}}}cSld")
    if csld is not None:
        return csld.get("name")
    return None


def dest_layouts(dest_dir: Path) -> dict[str, str]:
    """Map layout name -> package path like /ppt/slideLayouts/slideLayout1.xml."""
    out: dict[str, str] = {}
    folder = dest_dir / "ppt" / "slideLayouts"
    if not folder.exists():
        return out
    for p in sorted(folder.glob("slideLayout*.xml")):
        name = layout_name(p) or p.stem
        out[name] = "/" + p.relative_to(dest_dir).as_posix()
    return out


def dest_notes_master(dest_dir: Path) -> str | None:
    folder = dest_dir / "ppt" / "notesMasters"
    if not folder or not folder.exists():
        return None
    masters = sorted(folder.glob("notesMaster*.xml"))
    if not masters:
        return None
    return "/" + masters[0].relative_to(dest_dir).as_posix()


def resolve_rel_target(part: Path, target: str, src_dir: Path) -> Path | None:
    if target.startswith("/"):
        return src_dir / target.lstrip("/")
    # Targets in rels are relative to the part's parent, not the _rels folder.
    cand = (part.parent / target).resolve()
    try:
        cand.relative_to(src_dir.resolve())
    except ValueError:
        return None
    return cand if cand.exists() else None


def package_path(dest_dir: Path, path: Path) -> str:
    return "/" + path.relative_to(dest_dir).as_posix()


def ensure_content_type(dest_dir: Path, part_name: str, content_type: str | None, ext: str | None) -> None:
    ct_path = dest_dir / "[Content_Types].xml"
    tree = parse(ct_path)
    root = tree.getroot()
    if ext:
        ext = ext.lstrip(".")
        for el in root.findall(f"{{{CT_NS}}}Default"):
            if el.get("Extension") == ext:
                return
        if content_type:
            el = etree.SubElement(root, f"{{{CT_NS}}}Default")
            el.set("Extension", ext)
            el.set("ContentType", content_type)
            write_xml(tree, ct_path)
        return
    for el in root.findall(f"{{{CT_NS}}}Override"):
        if el.get("PartName") == part_name:
            return
    if not content_type:
        return
    el = etree.SubElement(root, f"{{{CT_NS}}}Override")
    el.set("PartName", part_name)
    el.set("ContentType", content_type)
    write_xml(tree, ct_path)


def guess_content_type(package_posix: str, path: Path) -> tuple[str | None, str | None]:
    """Return (override_type, default_ext). One of them is set."""
    parts = Path(package_posix.lstrip("/")).parts
    if "slides" in parts and path.suffix == ".xml" and path.name.startswith("slide"):
        return CONTENT_TYPES["slides"], None
    if "notesSlides" in parts and path.suffix == ".xml":
        return CONTENT_TYPES["notesSlides"], None
    if "charts" in parts and path.suffix == ".xml":
        name = path.name.lower()
        if "color" in name:
            return CONTENT_TYPES["chartColors"], None
        if "style" in name:
            return CONTENT_TYPES["chartStyles"], None
        return CONTENT_TYPES["charts"], None
    if path.suffix == ".xml" and "tags" in parts:
        return CONTENT_TYPES["tags"], None
    # Defaults by extension — only add if missing.
    ext = path.suffix.lstrip(".").lower()
    defaults = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
        "wdp": "image/vnd.ms-photo",
        "svg": "image/svg+xml",
        "emf": "image/x-emf",
        "wmf": "image/x-wmf",
        "bin": "application/vnd.openxmlformats-officedocument.oleObject",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "mp4": "video/mp4",
        "vml": "application/vnd.openxmlformats-officedocument.vmlDrawing",
    }
    if ext in defaults:
        return None, ext  # ensure_content_type will add Default if needed, using typemap
    if ext:
        return None, ext
    return None, None


EXT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "bmp": "image/bmp",
    "wdp": "image/vnd.ms-photo",
    "svg": "image/svg+xml",
    "emf": "image/x-emf",
    "wmf": "image/x-wmf",
    "bin": "application/vnd.openxmlformats-officedocument.oleObject",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "mp4": "video/mp4",
    "vml": "application/vnd.openxmlformats-officedocument.vmlDrawing",
}


def unique_dest_file(dest_dir: Path, subfolder: str, name: str) -> Path:
    folder = dest_dir / subfolder
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / name
    if not dest.exists():
        return dest
    stem, suffix = Path(name).stem, Path(name).suffix
    # Split trailing number if present.
    m = re.match(r"^(.*?)(\d+)$", stem)
    base, n = (m.group(1), int(m.group(2))) if m else (stem, 1)
    while True:
        n += 1
        dest = folder / f"{base}{n}{suffix}"
        if not dest.exists():
            return dest


class PartCopier:
    def __init__(self, src_dir: Path, dest_dir: Path):
        self.src_dir = src_dir
        self.dest_dir = dest_dir
        self.layouts = dest_layouts(dest_dir)
        self.notes_master = dest_notes_master(dest_dir)
        self.src_to_dest: dict[Path, Path] = {}
        self.media_counter = max_existing_index(dest_dir / "ppt" / "media", "image", "") 
        # media files have various suffixes; handled in unique_dest_file

    def remap_special(self, rel_type: str, src_target_path: Path | None) -> str | None:
        if rel_type == REL_LAYOUT and src_target_path is not None:
            name = layout_name(src_target_path) or src_target_path.stem
            pkg = self.layouts.get(name)
            if pkg:
                return pkg
            # Fallback: first layout.
            if self.layouts:
                print(f"warning: no layout named {name!r}; using a fallback", file=sys.stderr)
                return next(iter(self.layouts.values()))
            return None
        if rel_type == REL_NOTESMASTER:
            return self.notes_master
        # Do not copy masters/themes from the source presentation.
        if rel_type in {REL_SLIDEMASTER, REL_HANDOUTMASTER, REL_THEME}:
            return None
        return None

    def copy_part(self, src_part: Path, dest_hint: Path) -> Path:
        src_part = src_part.resolve()
        if src_part in self.src_to_dest:
            return self.src_to_dest[src_part]
        dest_hint.parent.mkdir(parents=True, exist_ok=True)
        if dest_hint.exists():
            dest_hint = unique_dest_file(self.dest_dir, dest_hint.parent.relative_to(self.dest_dir).as_posix(), dest_hint.name)
        shutil.copy2(src_part, dest_hint)
        self.src_to_dest[src_part] = dest_hint

        pkg = package_path(self.dest_dir, dest_hint)
        override, ext = guess_content_type(pkg, dest_hint)
        if ext and not override:
            ensure_content_type(self.dest_dir, pkg, EXT_TYPES.get(ext.lower()), ext)
        elif override:
            ensure_content_type(self.dest_dir, pkg, override, None)

        rels = load_rels(src_part)
        if rels is None:
            return dest_hint
        new_root = etree.Element(f"{{{REL_NS}}}Relationships")
        for rel in list(rels.getroot()):
            rel_type = rel.get("Type")
            target = rel.get("Target")
            mode = rel.get("TargetMode")
            rid = rel.get("Id")
            if mode == "External" or not target or target.startswith("http"):
                new_root.append(_copy_rel(rel))
                continue
            src_target = resolve_rel_target(src_part, target, self.src_dir)
            if rel_type in REMAP_TYPES:
                mapped = self.remap_special(rel_type, src_target)
                if not mapped:
                    continue
                # Target is relative to the dest part parent.
                new_target = _relpath(dest_hint.parent, self.dest_dir / mapped.lstrip("/"))
                el = etree.SubElement(new_root, f"{{{REL_NS}}}Relationship")
                el.set("Id", rid)
                el.set("Type", rel_type)
                el.set("Target", new_target)
                continue
            if src_target is None or not src_target.exists():
                # Keep the original target; better than dropping a relationship silently.
                new_root.append(_copy_rel(rel))
                continue
            # Choose a destination path that keeps the same subfolder under ppt/.
            try:
                rel_under_src = src_target.relative_to(self.src_dir)
            except ValueError:
                rel_under_src = Path("ppt") / "media" / src_target.name
            dest_target = self.copy_part(src_target, self.dest_dir / rel_under_src)
            new_target = _relpath(dest_hint.parent, dest_target)
            el = etree.SubElement(new_root, f"{{{REL_NS}}}Relationship")
            el.set("Id", rid)
            el.set("Type", rel_type)
            el.set("Target", new_target)
        rels_out = rels_path_for(dest_hint)
        rels_out.parent.mkdir(parents=True, exist_ok=True)
        write_xml(etree.ElementTree(new_root), rels_out)
        return dest_hint


def _copy_rel(rel: etree._Element) -> etree._Element:
    el = etree.Element(f"{{{REL_NS}}}Relationship")
    for k, v in rel.attrib.items():
        el.set(k, v)
    return el


def _relpath(from_dir: Path, to_file: Path) -> str:
    return Path(os_relpath(to_file, from_dir)).as_posix()


def os_relpath(to_file: Path, from_dir: Path) -> str:
    import os

    return os.path.relpath(str(to_file), str(from_dir))


def drop_section_list(dest_dir: Path) -> None:
    """Remove p14:sectionLst so leftover section markers do not point at old slides."""
    pres = dest_dir / "ppt" / "presentation.xml"
    tree = parse(pres)
    changed = False
    for el in tree.getroot().xpath(
        "//*[local-name()='sectionLst']"
    ):
        parent = el.getparent()
        if parent is not None:
            parent.remove(el)
            changed = True
    if changed:
        write_xml(tree, pres)


def add_slide_to_presentation(dest_dir: Path, slide_part: Path) -> None:
    pres = dest_dir / "ppt" / "presentation.xml"
    pres_rels = dest_dir / "ppt" / "_rels" / "presentation.xml.rels"
    tree = parse(pres)
    rels = parse(pres_rels)
    rid_n = next_rid(rels)
    rid = f"rId{rid_n}"
    rel = etree.SubElement(rels.getroot(), f"{{{REL_NS}}}Relationship")
    rel.set("Id", rid)
    rel.set("Type", REL_SLIDE)
    rel.set("Target", _relpath(dest_dir / "ppt", slide_part))
    write_xml(rels, pres_rels)

    root = tree.getroot()
    sld_id_lst = root.find(f"{{{P_NS}}}sldIdLst")
    if sld_id_lst is None:
        sld_id_lst = etree.SubElement(root, f"{{{P_NS}}}sldIdLst")
    used = [256]
    for s in sld_id_lst.findall(f"{{{P_NS}}}sldId"):
        try:
            used.append(int(s.get("id")))
        except (TypeError, ValueError):
            pass
    sld = etree.SubElement(sld_id_lst, f"{{{P_NS}}}sldId")
    sld.set("id", str(max(used) + 1))
    sld.set(f"{{{R_NS}}}id", rid)
    write_xml(tree, pres)


def count_slides(dest_dir: Path) -> int:
    lst = parse(dest_dir / "ppt" / "presentation.xml").getroot().find(f"{{{P_NS}}}sldIdLst")
    if lst is None:
        return 0
    return len(lst.findall(f"{{{P_NS}}}sldId"))


def append_deck(dest_dir: Path, src_pptx: Path) -> int:
    added = 0
    with tempfile.TemporaryDirectory(prefix="merge-src-") as td:
        src_dir = Path(td)
        unpack(src_pptx, src_dir)
        src_pres = src_dir / "ppt" / "presentation.xml"
        src_rels = parse(src_dir / "ppt" / "_rels" / "presentation.xml.rels")
        rel_by_id = {rel.get("Id"): rel for rel in src_rels.getroot()}
        sld_lst = parse(src_pres).getroot().find(f"{{{P_NS}}}sldIdLst")
        if sld_lst is None:
            return 0
        copier = PartCopier(src_dir, dest_dir)
        next_n = max_existing_index(dest_dir / "ppt" / "slides", "slide") + 1
        for sld in sld_lst.findall(f"{{{P_NS}}}sldId"):
            rid = sld.get(f"{{{R_NS}}}id")
            rel = rel_by_id.get(rid)
            if rel is None:
                print(f"warning: missing relationship {rid} in {src_pptx}", file=sys.stderr)
                continue
            target = rel.get("Target")
            src_slide = resolve_rel_target(src_dir / "ppt" / "presentation.xml", target, src_dir)
            if src_slide is None:
                print(f"warning: cannot resolve {target} in {src_pptx}", file=sys.stderr)
                continue
            dest_slide = dest_dir / "ppt" / "slides" / f"slide{next_n}.xml"
            copier.copy_part(src_slide, dest_slide)
            add_slide_to_presentation(dest_dir, dest_slide)
            next_n += 1
            added += 1
    return added


def merge(paths: list[Path], output: Path) -> int:
    if not paths:
        raise SystemExit("no input decks")
    for p in paths:
        if not p.exists():
            raise SystemExit(f"missing input: {p}")
    with tempfile.TemporaryDirectory(prefix="merge-dst-") as td:
        dest_dir = Path(td)
        unpack(paths[0], dest_dir)
        drop_section_list(dest_dir)
        total = count_slides(dest_dir)
        for src in paths[1:]:
            added = append_deck(dest_dir, src)
            total += added
            print(f"  appended {added} slides from {src}")
        drop_section_list(dest_dir)
        pack(dest_dir, output)
    return total


def default_paths(root: Path, parts_only: bool) -> list[Path]:
    part1 = root / "part-01_foundations" / "slides" / "part-01_foundations.pptx"
    part2 = _first_existing(
        root / "part-02" / "slides" / "part-02_original.pptx",
        root / "part-02" / "slides" / "part-02.pptx",
    )
    part3 = _first_existing(
        root / "part-03_control-quality" / "slides" / "part-03_v2.pptx",
        root / "part-03_control-quality" / "slides" / "part-03_v1.pptx",
        root / "part-03_control-quality" / "slides" / "part-03.pptx",
    )
    front = root / "shared" / "slides" / "front.pptx"
    back = root / "shared" / "slides" / "back.pptx"
    paths: list[Path] = []
    if not parts_only and front.exists():
        paths.append(front)
    for required, label in ((part1, "part-01"), (part2, "part-02"), (part3, "part-03")):
        if required is None:
            raise SystemExit(f"cannot find slides for {label}")
        paths.append(required)
    if not parts_only and back.exists():
        paths.append(back)
    return paths


def _first_existing(*candidates: Path) -> Path | None:
    for c in candidates:
        if c.exists():
            return c
    return None


def main(argv: list[str] | None = None) -> int:
    root = repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parts-only", action="store_true", help="skip shared title/agenda and references/thanks slides")
    parser.add_argument("--part1", type=Path)
    parser.add_argument("--part2", type=Path)
    parser.add_argument("--part3", type=Path)
    parser.add_argument("--front", type=Path)
    parser.add_argument("--back", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=root / "dist" / "AI-native-Architecture.pptx")
    args = parser.parse_args(argv)

    if args.part1 or args.part2 or args.part3:
        paths: list[Path] = []
        front = args.front or (None if args.parts_only else root / "shared" / "slides" / "front.pptx")
        back = args.back or (None if args.parts_only else root / "shared" / "slides" / "back.pptx")
        if front and Path(front).exists() and not args.parts_only:
            paths.append(Path(front))
        for p in (args.part1, args.part2, args.part3):
            if p:
                paths.append(p)
        if back and Path(back).exists() and not args.parts_only:
            paths.append(Path(back))
    else:
        paths = default_paths(root, args.parts_only)

    output = args.output if args.output.is_absolute() else (Path.cwd() / args.output)
    print("merging:")
    for p in paths:
        print(f"  - {p}")
    total = merge(paths, output)
    print(f"wrote {output} ({total} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
