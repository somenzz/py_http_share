gunicorn -w 4 -b 0.0.0.0:10240 app:app \
  --keyfile certs/share.local.key \
  --certfile certs/share.local.crt
