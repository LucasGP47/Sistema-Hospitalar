print("Consumer iniciado", flush=True)

import json
import pika
import oci
import time
import os
import sys

TOPIC_OCID = "ocid1.onstopic.oc1.sa-saopaulo-1.amaaaaaaskvkz5qarpict34pvr7fpqxcttje4jequmscode63yaapiqgaunq"

def wait_for_rabbitmq():
    print("Aguardando RabbitMQ ficar disponível...", flush=True)
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.environ.get("RABBITMQ_HOST", "rabbitmq"),
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            connection.close()
            print("RabbitMQ está disponível!", flush=True)
            return True
        except Exception as e:
            retry_count += 1
            print(f"Tentativa {retry_count}/{max_retries} falhou: {e}", flush=True)
            time.sleep(5)
    
    print("Falha ao conectar ao RabbitMQ após várias tentativas", flush=True)
    return False

def send_oci_email(message):
    try:
        print("Enviando notificação OCI...", flush=True)
        config = oci.config.from_file()
        client = oci.ons.NotificationControlPlaneClient(config)
        client.publish_message(
            TOPIC_OCID,
            oci.ons.models.PublishMessageDetails(
                message=json.dumps(message),
                default=f"[{message.get('type')}] Notificação recebida"
            )
        )
        print("Notificação enviada via OCI", flush=True)
    except Exception as e:
        print(f"Erro ao enviar notificação OCI: {e}", flush=True)

def callback(ch, method, properties, body):
    print(f"Mensagem recebida do RabbitMQ: {body}", flush=True)
    try:
        message = json.loads(body)
        print(f"Mensagem decodificada: {message}", flush=True)
        send_oci_email(message)
        print("Mensagem processada com sucesso", flush=True)
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}", flush=True)

def main():
    print("=== CONSUMER INICIADO ===", flush=True)
    print(f"Python version: {sys.version}", flush=True)
    print(f"Working directory: {os.getcwd()}", flush=True)
    print(f"RABBITMQ_HOST: {os.environ.get('RABBITMQ_HOST', 'rabbitmq')}", flush=True)
    
    if not wait_for_rabbitmq():
        print("Saindo devido a falha na conexão com RabbitMQ", flush=True)
        sys.exit(1)
    
    print("Conectando ao RabbitMQ...", flush=True)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.environ.get("RABBITMQ_HOST", "rabbitmq"),
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            channel = connection.channel()
            
            channel.queue_declare(queue='notifications', durable=True)
            print("Queue 'notifications' declarada", flush=True)
            
            channel.basic_qos(prefetch_count=1)
            
            print("Conectado. Aguardando mensagens...", flush=True)
            channel.basic_consume(
                queue='notifications', 
                on_message_callback=callback, 
                auto_ack=True
            )
            
            print("Consumer pronto para receber mensagens", flush=True)
            channel.start_consuming()
            
        except KeyboardInterrupt:
            print("Consumer interrompido pelo usuário", flush=True)
            break
        except Exception as e:
            print(f"Erro ao conectar ao RabbitMQ: {e}", flush=True)
            print("Tentando novamente em 5 segundos...", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()