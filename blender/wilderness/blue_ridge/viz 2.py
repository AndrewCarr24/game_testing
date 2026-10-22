import sys, math, numpy as np
SP = sys.argv[1]; RUN = sys.argv[2]
exec(open(SP + "/los.py").read().split("house = (0, 0, 7.0)")[0])
Hn = H; 
def vis_map(target, step=6.0, eye=1.7, ns=260):
    xs = np.arange(-600, 650, step); ys = np.arange(-1300, -150, step)
    CX, CY = np.meshgrid(xs, ys)
    jj = ((CY + OY + 768) / CELL).round().astype(int); ii = ((CX + 768) / CELL).round().astype(int)
    z0 = H[jj, ii] + eye
    t = (np.arange(1, ns) / ns)[None, None, :]
    px = CX[..., None] + t * (target[0] - CX[..., None]); py = CY[..., None] + t * (target[1] - CY[..., None])
    pz = z0[..., None] + t * (target[2] - z0[..., None])
    ins = py < -45
    pj = np.clip(((py + OY + 768) / CELL).round().astype(int), 0, N - 1); pi = np.clip(((px + 768) / CELL).round().astype(int), 0, N - 1)
    g = np.where(ins, H[pj, pi], 0.0); c = np.where(ins, can[pj, pi], 0.0)
    L = np.hypot(target[0] - CX, target[1] - CY)[..., None]
    c = np.where(t * L > 10, c, 0)
    clear = (pz - g - c).min(axis=2)
    return CX, CY, clear, z0 - eye
CX, CY, clr, Z = vis_map((0, 0, 7.0))
v = clr > 0
print("cells seeing the house:", int(v.sum()), "of", v.size)
idx = np.argsort(-clr.ravel())[:40]
for k in idx[:25]:
    print(round(float(CX.ravel()[k])), round(float(CY.ravel()[k])), "z", round(float(Z.ravel()[k])), "clear", round(float(clr.ravel()[k]), 1))
np.save(SP + "/vis_house.npy", np.dstack([CX, CY, clr, Z]))
