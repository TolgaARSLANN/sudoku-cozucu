# Render ve her Linux sunucu için: docker build -t sudoku . && docker run -p 7860:7860 sudoku
FROM python:3.12-slim

# Uygulama root olmayan bir kullanıcıyla çalışır
RUN useradd --create-home --uid 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /home/user/app

# Önce bağımlılıklar: kod değişince bu katman yeniden kurulmasın
COPY --chown=user requirements-sunucu.txt .
RUN pip install --no-cache-dir --user -r requirements-sunucu.txt

# Sadece çalışmak için gerekenler (veri, testler, arayüz kaynağı ve eğitim betiği imaja girmez)
COPY --chown=user app.py vision.py digits.py solver.py ipucu.py kalite.py adimlar.py kontrol.py gunicorn.conf.py ./
COPY --chown=user digits_data.npz el_yazisi.onnx el_yazisi_tur.json LICENSE ./
COPY --chown=user fonts ./fonts
COPY --chown=user static ./static

EXPOSE 7860
CMD ["gunicorn", "app:app"]
