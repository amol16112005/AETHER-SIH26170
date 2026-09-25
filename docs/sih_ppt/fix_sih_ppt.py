"""Visual QA fixes on the filled SIH 2026 deck."""
from pathlib import Path
import defusedxml.minidom as minidom

SLIDES = Path(__file__).resolve().parent / "unpacked_aether" / "ppt" / "slides"


def fix_slide1() -> None:
    path = SLIDES / "slide1.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    for pPr in doc.getElementsByTagName("a:pPr"):
        if pPr.getAttribute("algn") == "just":
            pPr.setAttribute("algn", "l")
        for ln in pPr.getElementsByTagName("a:spcPct"):
            ln.setAttribute("val", "115000")
    for rPr in doc.getElementsByTagName("a:rPr"):
        if rPr.getAttribute("sz") == "2400":
            rPr.setAttribute("sz", "2000")
    path.write_text(doc.toxml(), encoding="utf-8")
    print("slide1: left-align + 20pt")


def fix_ovals() -> None:
    for n in range(2, 7):
        path = SLIDES / f"slide{n}.xml"
        doc = minidom.parseString(path.read_text(encoding="utf-8"))
        for sp in doc.getElementsByTagName("p:sp"):
            names = [c.getAttribute("name") for c in sp.getElementsByTagName("p:cNvPr")]
            if not any(name == "Oval 9" for name in names):
                continue
            for xfrm in sp.getElementsByTagName("a:xfrm"):
                ext = xfrm.getElementsByTagName("a:ext")
                if ext:
                    ext[0].setAttribute("cx", "1750000")
                    ext[0].setAttribute("cy", "900000")
            for rPr in sp.getElementsByTagName("a:rPr"):
                rPr.setAttribute("sz", "1200")
                rPr.setAttribute("b", "1")
            for bodyPr in sp.getElementsByTagName("a:bodyPr"):
                bodyPr.setAttribute("wrap", "none")
        path.write_text(doc.toxml(), encoding="utf-8")
    print("ovals: wider + 12pt no-wrap")


def fix_slide2_underline() -> None:
    path = SLIDES / "slide2.xml"
    doc = minidom.parseString(path.read_text(encoding="utf-8"))
    headers = {
        "Proposed Solution (Describe your Idea/Solution/Prototype)",
        "Detailed explanation of the proposed solution",
        "How it addresses the problem",
        "Innovation and uniqueness of the solution",
    }
    for r in doc.getElementsByTagName("a:r"):
        ts = r.getElementsByTagName("a:t")
        if not ts or not ts[0].firstChild:
            continue
        text = ts[0].firstChild.data
        rPrs = r.getElementsByTagName("a:rPr")
        if not rPrs:
            continue
        if text in headers:
            rPrs[0].setAttribute("u", "sng")
            rPrs[0].setAttribute("b", "1")
        elif rPrs[0].getAttribute("u") == "sng":
            rPrs[0].removeAttribute("u")
    # also strip u from endParaRPr
    for epr in doc.getElementsByTagName("a:endParaRPr"):
        if epr.getAttribute("u") == "sng":
            epr.removeAttribute("u")
    path.write_text(doc.toxml(), encoding="utf-8")
    print("slide2: underline only on section headers")


def fix_degree_spacing() -> None:
    for n in range(1, 7):
        path = SLIDES / f"slide{n}.xml"
        raw = path.read_text(encoding="utf-8")
        raw = raw.replace("125 °C", "125°C").replace("125 ° C", "125°C")
        path.write_text(raw, encoding="utf-8")
    print("degree-C spacing")


if __name__ == "__main__":
    fix_slide1()
    fix_ovals()
    fix_slide2_underline()
    fix_degree_spacing()
