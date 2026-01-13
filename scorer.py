import os
import sys
import cv2
import math
import json
import numpy as np
from inference import get_model

from overlay import overlay_ideal_on_real

from config import *

# ============================================================
# HELPERS
# ============================================================

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def center_of(pred):
    return np.array([pred.x, pred.y], dtype=float)

def radius_of(pred):
    return (pred.width + pred.height) / 4.0

# ============================================================
# SCORING (ISSF BEST EDGE)
# ============================================================

def score_shot(distance_mm, bullet_radius_mm):
    for pts in sorted(ISSF_RADII_MM.keys(), reverse=True):
        ring_r = ISSF_RADII_MM[pts]
        if distance_mm - bullet_radius_mm <= ring_r:
            return pts
    return 0

# ============================================================
# IDEAL TARGET DRAW
# ============================================================

def draw_ideal_target(shots, px_per_mm, out_path, size=1200):
    img = np.ones((size, size, 3), np.uint8) * 255
    c = size // 2

    # --- Black zone ---
    cv2.circle(img, (c, c), int(ISSF_RADII_MM[5]*px_per_mm), (0,0,0), -1)

    # --- Rings ---
    for pts, r_mm in ISSF_RADII_MM.items():
        r_px = int(r_mm * px_per_mm)
        col = (255,255,255) if pts >= 5 else (0,0,0)
        cv2.circle(img, (c,c), r_px, col, 2)

    # --- Numbers ---
    if SHOW_RING_NUMBERS:
        for pts in range(1,10):
            r_in = ISSF_RADII_MM.get(pts+1,0)
            r_out = ISSF_RADII_MM[pts]
            r = int((r_in+r_out)/2*px_per_mm)
            col = (255,255,255) if pts>=5 else (0,0,0)
            cv2.putText(img,str(pts),(c+r-10,c+5),
                        cv2.FONT_HERSHEY_SIMPLEX,0.7,col,2)

    # --- Center ---
    cv2.drawMarker(img,(c,c),(0,0,255),
                   cv2.MARKER_CROSS,40,2)

    # --- Shots ---
    for s in shots:
        x = int(c + s["dx_mm"]*px_per_mm)
        y = int(c + s["dy_mm"]*px_per_mm)

        if SHOW_DISTANCE_LINES:
            cv2.line(img,(c,c),(x,y),(150,150,150),1)

        if SHOW_BULLET_OUTLINE:
            cv2.circle(img,(x,y),
                       int(BULLET_RADIUS_MM*px_per_mm),
                       (0,180,0),2)

        cv2.circle(img,(x,y),2,(0,180,0),-1)

        col = (255,255,255) if s["score"]>=5 else (0,0,0)
        cv2.putText(img,str(s["score"]),
                    (x+10,y-6),
                    cv2.FONT_HERSHEY_SIMPLEX,0.7,col,2)

        if SHOW_DISTANCE_TEXT:
            cv2.putText(img,f'{s["dist_mm"]:.1f}mm',
                        (x+10,y+14),
                        cv2.FONT_HERSHEY_SIMPLEX,0.45,col,1)

    cv2.imwrite(out_path,img)
    
def draw_ideal_target_rgba(shots, px_per_mm, size=1200):
    """
    Ideal target with transparent background (RGBA)
    Used ONLY for overlay
    """
    img = np.zeros((size, size, 4), np.uint8)
    c = size // 2

    # --- Black zone ---
    cv2.circle(
        img, (c, c),
        int(ISSF_RADII_MM[5] * px_per_mm),
        (0, 0, 0, 255), -1
    )

    # --- Rings ---
    for pts, r_mm in ISSF_RADII_MM.items():
        r_px = int(r_mm * px_per_mm)
        col = (255,255,255,255) if pts >= 5 else (0,0,0,255)
        cv2.circle(img, (c,c), r_px, col, 2)

    # --- Center ---
    cv2.drawMarker(
        img, (c,c),
        (255,0,0,255),
        cv2.MARKER_CROSS, 40, 2
    )

    return img

# ============================================================
# REAL IMAGE DRAW
# ============================================================

def draw_real(image, center, shots, out_path):
    vis = image.copy()
    cv2.drawMarker(vis,tuple(center.astype(int)),
                   (0,0,255),
                   cv2.MARKER_CROSS,40,2)

    for s in shots:
        x,y = map(int,s["center_px"])
        r = int(s["bullet_radius_px"])
        cv2.circle(vis,(x,y),r,(0,255,0),2)

        col = (255,255,255) if s["score"]>=5 else (0,0,0)
        cv2.putText(vis,f'{s["id"]}: {s["score"]}',
                    (x+10,y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,col,2)

    cv2.imwrite(out_path,vis)

# ============================================================
# CORE
# ============================================================

def score_image(path):
    img = cv2.imread(path)
    model = get_model(MODEL_ID)
    inf = model.infer(img,confidence=CONF_THRESHOLD)[0]

    bullets=[]
    centers=[]

    for p in inf.predictions:
        if p.class_name=="bullet_hole":
            bullets.append(p)
        elif p.class_name in ("target_center","dark_circle","target_circle"):
            centers.append(center_of(p))

    if not centers:
        raise RuntimeError("No target center detected")

    center = np.mean(centers,axis=0)

    scale_ref = next(p for p in inf.predictions if p.class_name=="target_circle")
    px_per_mm = radius_of(scale_ref)/ISSF_RADII_MM[1]

    shots=[]
    total=0

    for i,b in enumerate(bullets):
        c = center_of(b)
        d_px = dist(center,c)
        d_mm = d_px/px_per_mm

        score = score_shot(d_mm,BULLET_RADIUS_MM)

        shots.append({
            "id":i+1,
            "center_px":[int(c[0]),int(c[1])],
            "dx_mm":(c[0]-center[0])/px_per_mm,
            "dy_mm":(c[1]-center[1])/px_per_mm,
            "dist_mm":d_mm,
            "bullet_radius_px":radius_of(b),
            "score":score
        })
        total+=score

    filename = os.path.basename(path)
    name, ext = os.path.splitext(filename)

    out_real = os.path.join(OUTPUT_DIR, name + "_scored" + ext)
    out_ideal = os.path.join(OUTPUT_DIR, name + "_ideal" + ext)
    out_overlay = os.path.join(OUTPUT_DIR, name + "_overlay" + ext)

    draw_real(img, center, shots, out_real)
    draw_ideal_target(shots, px_per_mm, out_ideal)
    ideal_rgba = draw_ideal_target_rgba(shots, px_per_mm)

    overlay_img = overlay_ideal_on_real(
        real_bgr=img,
        ideal_rgba=ideal_rgba,
        center_px=center,
        alpha=0.65
    )

    cv2.imwrite(out_overlay, overlay_img)

    # Normalize paths for web use (forward slashes, leading '/')
    def webpath(p):
        if not p:
            return None
        p = p.replace('\\', '/')
        return p if p.startswith('/') else '/' + p

    return {
        "center_px":center.astype(int).tolist(),
        "shots":shots,
        "shots_count":len(shots),
        "total_score":total,
        "images": {
            "overlay": webpath(out_overlay),
            "scored": webpath(out_real),
            "ideal": webpath(out_ideal),
        }
    }

