"""Linux sunucuda (Hugging Face Spaces) gunicorn ayarları: gunicorn app:app

Windows'ta gunicorn çalışmaz; yerelde python app.py kullanılır.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '7860')}"
workers = 2              # ücretsiz Space'te 2 çekirdek; istekler işlemci yoğun, aynı anda 2 istek işlenir
timeout = 60             # normal istek 1 sn sürer; takılan işçi bu süreden sonra yeniden başlatılır
graceful_timeout = 10
max_requests = 500       # işçiler arada bir yenilenir: olası bellek sızıntısı birikmesin
max_requests_jitter = 50
# Erişim kaydı: sadece zaman, istek satırı, durum ve süre. IP adresi ve tarayıcı bilgisi yazılmaz;
# istek gövdesi (yüklenen görsel) hiçbir kayda girmez.
accesslog = "-"
access_log_format = '%(t)s "%(r)s" %(s)s %(M)sms'
errorlog = "-"
