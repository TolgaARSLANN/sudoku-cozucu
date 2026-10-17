"""El yazısı rakam ağını eğitir ve ONNX'e aktarır; basılı/el yazısı ayrımını öğrenir.

Sadece eğitim için PyTorch gerekir; uygulama modeli cv2.dnn ile çalıştırır.

    pip install -r requirements-egitim.txt
    python veri_indir.py               # ölçüm fotoğrafları (model seçimi geliştirme setiyle yapılır)
    python egit_el_yazisi.py           # ~15 dk (CPU)

Üretir: el_yazisi.onnx, el_yazisi_tur.json
"""
import gzip
import json
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from benchmark import read_truth
from digits import DigitClassifier
from kontrol import MODEL_FILE, SIZE, TYPE_FILE, center, extract
from vision import load_image

VERI = Path(__file__).parent / "veri"
MNIST_URL = "https://storage.googleapis.com/cvdf-datasets/mnist/"
EPOCHS = 6

torch.manual_seed(0)
rng = np.random.default_rng(0)


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1), nn.ReLU(), nn.Conv2d(32, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(64 * 7 * 7, 128), nn.ReLU(), nn.Dropout(0.3),
                                  nn.Linear(128, 9))

    def forward(self, x):
        return self.head(self.features(x))


def mnist():
    """MNIST eğitim seti, 0'lar hariç (sudokuda yok), uygulamadaki kesimle aynı biçimde."""
    folder = VERI / "mnist"
    folder.mkdir(parents=True, exist_ok=True)
    data = {}
    for name in ("train-images-idx3-ubyte.gz", "train-labels-idx1-ubyte.gz"):
        if not (folder / name).exists():
            urllib.request.urlretrieve(MNIST_URL + name, folder / name)
        with gzip.open(folder / name) as f:
            data[name] = f.read()
    imgs = np.frombuffer(data["train-images-idx3-ubyte.gz"], np.uint8, offset=16).reshape(-1, 28, 28)
    labels = np.frombuffer(data["train-labels-idx1-ubyte.gz"], np.uint8, offset=8)
    X = []
    for im in imgs[labels > 0]:
        ys, xs = np.nonzero(im > 90)
        X.append(center(im[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.float32) / 255))
    return np.array(X, np.float32), labels[labels > 0]


def styled(img, digit):
    """Türk/Avrupa el yazısı: ortası çizgili 7, tepesi bayraklı 1 (MNIST'te az)."""
    img = img.reshape(SIZE, SIZE).copy()
    ys, xs = np.nonzero(img > 0.5)
    if len(ys) == 0:
        return None
    width = int(rng.integers(1, 3))
    if digit == 7:
        y = int(ys.min() + (ys.max() - ys.min()) * rng.uniform(0.45, 0.6))
        cols = np.nonzero(img[y] > 0.5)[0]
        if len(cols) == 0:
            return None
        x, half = int(cols.mean()), int(rng.integers(4, 7))
        cv2.line(img, (x - half, y), (x + half, y), 1.0, width, cv2.LINE_AA)
    else:
        top = ys.argmin()
        x0, y0, length = int(xs[top]), int(ys[top]), int(rng.integers(5, 9))
        cv2.line(img, (x0, y0), (x0 - length, y0 + int(length * rng.uniform(0.6, 1.0))), 1.0, width, cv2.LINE_AA)
    ys, xs = np.nonzero(img > 0.1)
    return center(img[ys.min():ys.max() + 1, xs.min():xs.max() + 1])


def augment(x):
    """Fotoğraftan kesilmiş rakama benzet: döndür/eğ/ölçekle, kalınlık, bulanıklık, kontrast, gürültü."""
    n = x.shape[0]
    angle = (torch.rand(n) - 0.5) * 2 * np.radians(12)
    shear = (torch.rand(n) - 0.5) * 0.4
    scale = 0.9 + torch.rand(n) * 0.2
    tx, ty = (torch.rand(n) - 0.5) * 0.15, (torch.rand(n) - 0.5) * 0.15
    cos, sin = torch.cos(angle) / scale, torch.sin(angle) / scale
    theta = torch.stack([torch.stack([cos, -sin + shear, tx], 1), torch.stack([sin, cos, ty], 1)], 1)
    x = F.grid_sample(x, F.affine_grid(theta, x.shape, align_corners=False), align_corners=False)
    r = torch.rand(n)
    thick, thin = (r < 0.3).view(-1, 1, 1, 1), ((r >= 0.3) & (r < 0.5)).view(-1, 1, 1, 1)
    x = torch.where(thick, F.max_pool2d(x, 3, 1, 1), x)               # kalın kalem
    x = torch.where(thin, -F.max_pool2d(-x, 3, 1, 1), x)              # ince kalem
    blur = (torch.rand(n) < 0.5).view(-1, 1, 1, 1)
    k = torch.tensor([1., 2., 1.])
    k = (k[:, None] * k[None, :] / 16).view(1, 1, 3, 3)
    x = torch.where(blur, F.conv2d(x, k, padding=1), x)               # bulanık fotoğraf
    x = x * (0.6 + 0.4 * torch.rand(n, 1, 1, 1))                      # soluk mürekkep
    x = x + torch.rand(n, 1, 1, 1) * 0.08 * torch.rand_like(x)        # kağıt dokusu
    return x.clamp(0, 1)


def photo_set(part, clf):
    """karisik/<part> fotoğraflarından: el yazısı ağ girdileri + etiketleri, tür özellikleri + etiketleri."""
    hand_X, hand_y, type_X, type_y = [], [], [], []
    for p in sorted((VERI / "karisik" / part).glob("*.jpg")):
        full = read_truth(p.with_suffix(".dat"))
        printed = read_truth(VERI / part / p.with_suffix(".dat").name)  # sadece basılı rakamlar
        _, idxs, vecs, features, _ = extract(load_image(str(p)), clf)
        for k, i in enumerate(idxs):
            if not full[i]:
                continue  # boş hücrede bulunan leke
            type_X.append(features[k])
            type_y.append(printed[i] == 0)
            if printed[i] == 0:
                hand_X.append(vecs[k])
                hand_y.append(full[i])
    return np.array(hand_X, np.float32), np.array(hand_y), np.array(type_X, np.float32), np.array(type_y, np.float32)


def predict(model, X):
    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy(X).view(-1, 1, SIZE, SIZE)).argmax(1).numpy() + 1


def train(X, y, dev_X, dev_y):
    X = torch.from_numpy(X).view(-1, 1, SIZE, SIZE)
    Y = torch.from_numpy(y.astype(np.int64) - 1)
    model = Net()
    opt = torch.optim.Adam(model.parameters(), 1e-3)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=EPOCHS * (len(X) // 128 + 1))
    best = (0, None)
    for epoch in range(EPOCHS):
        model.train()
        t = time.time()
        perm = torch.randperm(len(X))
        for s in range(0, len(X), 128):
            idx = perm[s:s + 128]
            loss = F.cross_entropy(model(augment(X[idx])), Y[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
        acc = (predict(model, dev_X) == dev_y).mean()
        print(f"tur {epoch + 1}/{EPOCHS}: {time.time() - t:.0f} sn, geliştirme el yazısı %{acc * 100:.2f}", flush=True)
        if acc > best[0]:
            best = (acc, {k: v.clone() for k, v in model.state_dict().items()})
    model.load_state_dict(best[1])
    model.eval()
    return model


def fit_logistic(X, y, steps=3000, lr=0.5):
    mean, std = X.mean(0), X.std(0) + 1e-6
    Z = np.hstack([(X - mean) / std, np.ones((len(X), 1))])
    w = np.zeros(Z.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-Z @ w))
        w -= lr * Z.T @ (p - y) / len(y)
    return {"ortalama": mean.tolist(), "sapma": std.tolist(), "agirlik": w.tolist()}


def main():
    clf = DigitClassifier()
    X, y = mnist()
    extra = [(v, d) for v, d in ((styled(x, d), d) for x, d in zip(X, y) if d in (1, 7)) if v is not None]
    X = np.vstack([X, np.array([v for v, _ in extra], np.float32)])
    y = np.concatenate([y, [d for _, d in extra]])
    print(f"eğitim: {len(X)} rakam (MNIST + {len(extra)} çizgili 7 / bayraklı 1)")
    dev_X, dev_y, dev_tX, dev_ty = photo_set("gelistirme", clf)
    model = train(X, y, dev_X, dev_y)
    torch.onnx.export(model, (torch.zeros(1, 1, SIZE, SIZE),), str(MODEL_FILE), input_names=["girdi"],
                      output_names=["cikti"], dynamic_axes={"girdi": {0: "n"}, "cikti": {0: "n"}},
                      external_data=False)  # cv2.dnn ayrı ağırlık dosyası okuyamıyor
    net = cv2.dnn.readNetFromONNX(np.fromfile(MODEL_FILE, np.uint8))
    net.setInput(dev_X.reshape(-1, 1, SIZE, SIZE))
    with torch.no_grad():
        diff = np.abs(net.forward() - model(torch.from_numpy(dev_X).view(-1, 1, SIZE, SIZE)).numpy()).max()
    assert diff < 1e-3, f"ONNX çıktısı PyTorch'tan farklı: {diff}"
    type_model = fit_logistic(dev_tX, dev_ty)
    TYPE_FILE.write_text(json.dumps(type_model, indent=1))
    print(f"kaydedildi: {MODEL_FILE.name}, {TYPE_FILE.name}")

    if (VERI / "karisik" / "dogrulama").exists():  # seçimde hiç kullanılmayan set
        val_X, val_y, val_tX, val_ty = photo_set("dogrulama", clf)
        mean, std, w = (np.array(type_model[k]) for k in ("ortalama", "sapma", "agirlik"))
        type_acc = (((val_tX - mean) / std @ w[:-1] + w[-1] > 0) == val_ty).mean()
        print(f"DOĞRULAMA: el yazısı okuma %{(predict(model, val_X) == val_y).mean() * 100:.2f}, "
              f"basılı/el ayrımı %{type_acc * 100:.1f}")


if __name__ == "__main__":
    main()
