import subprocess
import oci
import datetime
import os

mongo_container = "sistema-hospitalar_mongodb_1"
database_name = "hospital"
collection_name = "monitoring"
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
backup_filename = f"mongodb_backup_{timestamp}.json"

print("[1/3] Exportando dados do MongoDB...")

dump_command = [
    "docker", "exec", mongo_container,
    "mongoexport",
    "--db", database_name,
    "--collection", collection_name,
    "--username", "admin",
    "--password", "securepassword",
    "--authenticationDatabase", "admin",
    "--out", f"/data/{backup_filename}"
]

try:
    subprocess.run(dump_command, check=True)
    subprocess.run(["docker", "cp", f"{mongo_container}:/data/{backup_filename}", backup_filename], check=True)
    print(f"Backup MongoDB salvo como {backup_filename}")
except subprocess.CalledProcessError:
    print("Erro ao gerar ou copiar o backup do MongoDB.")
    exit(1)

print("[2/3] Enviando para OCI Object Storage...")

bucket_name = "hospital-storage"
namespace = "grbnhngdfn79"

try:
    config = oci.config.from_file()
    object_storage = oci.object_storage.ObjectStorageClient(config)

    with open(backup_filename, "rb") as f:
        object_storage.put_object(
            namespace_name=namespace,
            bucket_name=bucket_name,
            object_name=backup_filename,
            put_object_body=f
        )

    print(f"Backup enviado com sucesso como '{backup_filename}' no bucket '{bucket_name}'")
except Exception as e:
    print(f"Erro ao enviar para OCI: {e}")
    exit(1)

print("[3/3] Limpando backup local...")
os.remove(backup_filename)
print("Concluído!")