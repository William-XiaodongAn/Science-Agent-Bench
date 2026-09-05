import numpy as np
PATH = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
FPS = 529.09
DT_MS = 1000.0 / FPS
def load_raw():
    """Return (T,128,128) uint16 stack, transposed to analysis convention, frame 0 dropped."""
    mm = np.memmap(PATH, dtype="<u2", mode="r", offset=1024)
    nfr = mm.size // (128*128 + 4)
    fr = mm[: nfr * (128*128 + 4)].reshape(nfr, 128*128 + 4)[:, :128*128].reshape(nfr, 128, 128)
    fr = np.ascontiguousarray(np.transpose(fr, (0, 2, 1)))  # transpose each frame
    return fr[1:]
