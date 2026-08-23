from pathlib import Path

import cv2


ROOT = Path(r"E:\Data\sub-056_")
OUT = Path(r"C:\Users\green\.codex\visualizations\2026\08\21\01a0223b-47e2-79f3-a86d-f82f9ddf41d6") / "crossmodal_preview.png"


def read_frame(path: Path, index: int):
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot read {path} frame {index}")
    return frame


def main():
    rgb = ROOT / "rgb" / "sub-056_rgb.avi"
    nir = ROOT / "nir" / "sub-056_nir.avi"
    frames = []
    for role, path in (("RGB", rgb), ("NIR", nir)):
        raw = read_frame(path, 15000)
        if role == "NIR":
            raw = raw[400:900, 0:1920]
        raw = cv2.resize(raw, (640, 360))
        cv2.putText(raw, role, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
        frames.append(raw)
    canvas = cv2.hconcat(frames)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), canvas)
    print(OUT)


if __name__ == "__main__":
    main()
