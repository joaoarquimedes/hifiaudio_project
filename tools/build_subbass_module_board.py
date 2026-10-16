#!/usr/bin/env python3
"""Build the placed SubBass processor module PCB from the hierarchical schematic netlist.
Run with the KiCad-bundled Python so its pcbnew module matches the KiCad version.
"""
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
import pcbnew

ROOT = Path(__file__).resolve().parents[1]
BOARD_FILE = ROOT / "hifi_audio.kicad_pcb"
STOCK = Path(__import__('os').environ["KICAD_STOCK_DATA_HOME"])

# Compact 100 x 64 mm placement study for the signal-processing module.
# Coordinates are intentionally grouped by function; final routing/clearance review remains required.
PLACEMENT = {
    "J2": (16.0, 42.0, 180), "J3": (103.0, 42.0, 0), "J1": (52.0, 69.0, 0),
    "U1": (40.0, 40.0, 0),
    "R3": (23.0, 38.0, 0), "C4": (28.0, 37.0, 0), "R4": (32.0, 34.0, 0), "C3": (34.0, 46.0, 0),
    "C5": (48.0, 37.0, 0), "C6": (52.0, 40.0, 0), "R6": (54.5, 45.0, 0), "R7": (50.0, 50.0, 0),
    "C1": (36.0, 27.0, 0), "C2": (44.0, 27.0, 0), "R1": (34.0, 56.0, 0), "R2": (43.0, 56.0, 0),
    "U4": (64.0, 24.0, 0), "U5": (71.0, 41.0, 0), "U6": (82.0, 24.0, 0),
    "D1": (55.0, 33.0, 0),
    "C7": (58.0, 24.0, 0), "C8": (60.0, 31.0, 0), "C9": (60.0, 36.0, 0), "C10": (83.5, 43.0, 0), "C11": (88.0, 28.0, 0),
    "R8": (91.0, 48.0, 0), "R9": (57.0, 50.0, 0), "R10": (64.0, 54.0, 0), "R11": (68.0, 53.0, 0),
    "R12": (74.0, 54.0, 0), "R13": (78.0, 54.0, 0), "R14": (72.0, 30.0, 0), "R15": (78.0, 32.0, 0),
    "R16": (83.0, 51.0, 0), "R17": (88.0, 56.0, 0), "R18": (92.0, 56.0, 0),
    "TP1": (95.0, 36.0, 0), "TP2": (69.0, 30.0, 0),
}
BOARD_RECT = (10.0, 10.0, 110.0, 74.0)

with tempfile.TemporaryDirectory(prefix="subbass-module-") as tmp:
    netlist = Path(tmp) / "module.xml"
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", str(netlist), str(ROOT / "hifi_audio.kicad_sch")], check=True)
    xml = ET.parse(netlist).getroot()

component_info = {}
for comp in xml.findall(".//components/comp"):
    ref = comp.get("ref")
    value = comp.findtext("value", default="")
    footprint = comp.findtext("footprint", default="")
    if footprint:
        component_info[ref] = (value, footprint)

net_nodes = {}
net_names = set()
for net in xml.findall(".//nets/net"):
    name = net.get("name")
    net_names.add(name)
    for node in net.findall("node"):
        net_nodes.setdefault((node.get("ref"), node.get("pin")), name)

board = pcbnew.BOARD()
board.SetFileName(str(BOARD_FILE))
board.GetTitleBlock().SetTitle("SubBass Processor Module")
board.GetTitleBlock().SetRevision("A0 - placement study")
board.GetDesignSettings().m_MinClearance = pcbnew.FromMM(0.15)
board.GetDesignSettings().m_TrackMinWidth = pcbnew.FromMM(0.25)

net_objects = {}
for name in sorted(net_names):
    net = pcbnew.NETINFO_ITEM(board, name)
    board.Add(net)
    net_objects[name] = net

missing = []
for ref, (value, footprint_id) in component_info.items():
    if ref not in PLACEMENT:
        missing.append((ref, footprint_id))
        continue
    lib, name = footprint_id.split(":", 1)
    fp = pcbnew.FootprintLoad(str(STOCK / "footprints" / f"{lib}.pretty"), name)
    if fp is None:
        raise RuntimeError(f"Footprint not found: {footprint_id}")
    fp.SetReference(ref)
    fp.SetValue(value)
    x, y, angle = PLACEMENT[ref]
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    fp.SetOrientationDegrees(angle)
    fp.SetPath(pcbnew.KIID_PATH("/"))
    board.Add(fp)
    for pad in fp.Pads():
        net_name = net_nodes.get((ref, pad.GetNumber()))
        if net_name in net_objects:
            pad.SetNet(net_objects[net_name])

# Two pairs of mechanical mounting holes are included in the outline study.
for x, y, ref in [(16, 16, "MH1"), (104, 16, "MH2"), (16, 68, "MH3"), (104, 68, "MH4")]:
    fp = pcbnew.FootprintLoad(str(STOCK / "footprints" / "MountingHole.pretty"), "MountingHole_3.2mm_M3")
    if fp is None:
        raise RuntimeError("MountingHole_3.2mm footprint not found")
    fp.SetReference(ref); fp.Reference().SetVisible(False); fp.SetValue("MountingHole_3.2mm_M3")
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    fp.SetPath(pcbnew.KIID_PATH("/"))
    board.Add(fp)

x1, y1, x2, y2 = BOARD_RECT
corners = [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]
for i, (a,b) in enumerate(zip(corners, corners[1:] + corners[:1])):
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_SEGMENT)
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]),pcbnew.FromMM(a[1])))
    edge.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[0]),pcbnew.FromMM(b[1])))
    edge.SetWidth(pcbnew.FromMM(0.05))
    board.Add(edge)

# Board markings identify the inter-module ports for assembly and bench work.
def add_text(text, x, y, layer=pcbnew.F_SilkS, size=1.0, thickness=0.15):
    item=pcbnew.PCB_TEXT(board); item.SetText(text); item.SetLayer(layer)
    item.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y)))
    item.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size),pcbnew.FromMM(size)))
    item.SetTextThickness(pcbnew.FromMM(thickness)); board.Add(item)
add_text("SUBBASS PROCESSOR", 34, 13, size=1.2)
add_text("AUDIO IN", 15, 52); add_text("AUDIO OUT", 95, 52)
add_text("+15 / GND / -15", 43, 63)
add_text("FILTER + AUTO MUTE / REV A0", 30, 71, layer=pcbnew.F_Fab, size=1.0)

if missing:
    raise RuntimeError(f"Footprinted schematic items without placement: {missing}")

pcbnew.SaveBoard(str(BOARD_FILE), board)
print(f"Wrote {BOARD_FILE}; {len(component_info)} component footprints, {len(net_objects)} nets, outline {x2-x1:g} x {y2-y1:g} mm")
