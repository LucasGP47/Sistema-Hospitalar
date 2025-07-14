echo "Executando backup antes de desligar os containers..."

sudo python3 upload_backup.py

echo "Backup concluído. Parando containers..."
docker-compose down

echo "Containers finalizados."
echo "Sistema desligado com sucesso"
