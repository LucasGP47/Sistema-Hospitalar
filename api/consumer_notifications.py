print("Consumer iniciado")

import json
import pika
import oci
import time
import os

TOPIC_OCID = "ocid1.onstopic.oc1.sa-saopaulo-1.amaaaaaaskvkz5qarpict34pvr7fpqxcttje4jequmscode63yaapiqgaunq"

def send_oci_email(message):
    config = oci.config.from_file()
    client = oci.ons.NotificationControlPlaneClient(config)
    client.publish_message(
        TOPIC_OCID,
        oci.ons.models.PublishMessageDetails(
            message=json.dumps(message),
            default=f"[{message.get('type')}] Notificação recebida"
        )
    )
    print("Notificação enviada via OCI")

def callback(ch, method, properties, body):
    print("Mensagem recebida do RabbitMQ")
    try:
        message = json.loads(body)
        send_oci_email(message)
    except Exception as e:
        print("Erro ao processar mensagem:", e)

def main():
    print("Conectando ao RabbitMQ...")
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=os.environ.get("RABBITMQ_HOST", "rabbitmq"))
            )
            channel = connection.channel()
            channel.queue_declare(queue='notifications', durable=True)
            print("Conectado. Aguardando mensagens...")
            channel.basic_consume(queue='notifications', on_message_callback=callback, auto_ack=True)
            channel.start_consuming()
        except Exception as e:
            print("Erro ao conectar ao RabbitMQ, tentando novamente em 5s:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()