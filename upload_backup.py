import subprocess
import oci
import datetime
import os

container_name = "sistema-hospitalar_mysql_1"
mysql_user = "root"
mysql_password = "root"
database_name = "hospital_db"
dump_filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

print("[1/3] Gerando dump do banco MySQL...")

dump_command = [
    "docker", "exec", container_name,
    "mysqldump", f"-u{mysql_user}", f"-p{mysql_password}", database_name
]

try:
    with open(dump_filename, "w") as f:
        subprocess.run(dump_command, stdout=f, check=True)
    print(f"Dump gerado: {dump_filename}")
except subprocess.CalledProcessError:
    print("Erro ao gerar o dump. Verifique credenciais e container.")
    exit(1)

print("[2/3] Enviando para OCI Object Storage...")

bucket_name = "hospital-storage"
namespace = "grbnhngdfn79"

try:
    config = oci.config.from_file()
    object_storage = oci.object_storage.ObjectStorageClient(config)

    with open(dump_filename, "rb") as f:
        object_storage.put_object(
            namespace_name=namespace,
            bucket_name=bucket_name,
            object_name=dump_filename,
            put_object_body=f
        )

    print(f"Backup enviado com sucesso como '{dump_filename}' no bucket '{bucket_name}'")
except Exception as e:
    print(f"Erro ao enviar para OCI: {e}")
    exit(1)

print("[3/3] Limpando backup local...")
os.remove(dump_filename)
print("Concluído!")