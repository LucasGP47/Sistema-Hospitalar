import pika
import json

def callback(ch, method, properties, body):
    message = json.loads(body)
    print(f"Notificação recebida: {message}")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

channel.queue_declare(queue='notifications', durable=True)

channel.basic_consume(
    queue='notifications', on_message_callback=callback, auto_ack=True
)

print('🔔 Aguardando notificações. Pressione CTRL+C para sair.')
channel.start_consuming()
