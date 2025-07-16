print("Consumer iniciado", flush=True)

import json
import pika
import oci
import time
import os
import sys
import requests
from datetime import datetime

TOPIC_OCID = "ocid1.onstopic.oc1.sa-saopaulo-1.amaaaaaaskvkz5qarpict34pvr7fpqxcttje4jequmscode63yaapiqgaunq"

API_HOST = os.environ.get("API_HOST", "python_api")
API_PORT = "5000"
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

VAULT_TOKEN_OCID = "ocid1.vaultsecret.oc1.sa-saopaulo-1.amaaaaaaskvkz5qadezpfegvjjks727ryr6semyn224n7rmgun7gmgoyl7nq"

def get_token_from_vault(secret_ocid):
    try:
        config = oci.config.from_file()
        secrets_client = oci.secrets.SecretsClient(config)
        response = secrets_client.get_secret_bundle(secret_ocid)
        encoded_content = response.data.secret_bundle_content.content

        if isinstance(encoded_content, bytes):
            token = encoded_content.decode('utf-8').strip()
        else:
            token = encoded_content.strip()
        return token
    except Exception as e:
        print(f"Erro ao obter token do vault: {e}", flush=True)
        return None

API_TOKEN = get_token_from_vault(VAULT_TOKEN_OCID)

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

def get_patient_data(patient_id):
    """Busca dados do paciente via API interna"""
    try:
        print(f"Buscando dados do paciente {patient_id}...", flush=True)
        
        headers = {
            'Authorization': f'Bearer {API_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        url = f"{API_BASE_URL}/patients/{patient_id}"
        print(f"Fazendo requisição para: {url}", flush=True)
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            patient_data = response.json()
            print(f"Dados do paciente obtidos com sucesso: {patient_data.get('name', 'N/A')}", flush=True)
            return patient_data
        else:
            print(f"Erro ao buscar paciente: {response.status_code} - {response.text}", flush=True)
            return None
            
    except Exception as e:
        print(f"Erro ao buscar dados do paciente: {e}", flush=True)
        return None

def generate_html_email(message, patient_data):
    """Gera HTML para o email de alerta"""
    try:
        patient_id = message.get('patient_id', 'N/A')
        heart_rate = message.get('heart_rate', 'N/A')
        blood_pressure = message.get('blood_pressure', 'N/A')
        timestamp = message.get('timestamp', 'N/A')
        
        patient_name = "N/A"
        doctor_name = "N/A"
        doctor_specialty = "N/A"
        
        if patient_data:
            patient_name = patient_data.get('name', 'N/A')
            doctor_name = patient_data.get('doctor_name', 'N/A')
            doctor_specialty = patient_data.get('doctor_specialty', 'N/A')
        
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%d/%m/%Y às %H:%M:%S')
        except:
            formatted_time = timestamp
        
        html_content = f"""
            ALERTA AO DR. {doctor_name}
            Especialidade:</strong> {doctor_specialty}
            URGENTE: PACIENTE {patient_name}ESTÁ EM ESTADO CRÍTICO
            ID do Paciente:</strong> {patient_id}
            Hora do Log: {formatted_time}
            Sinais Vitais Críticos
            Frequência Cardíaca: {heart_rate} BPM
            Pressão Arterial: {blood_pressure}
            Log Completo do Sistema: {json.dumps(message, indent=2, ensure_ascii=False)}

            AÇÃO IMEDIATA REQUERIDA
            Este é um alerta automático do sistema de monitoramento
            Favor verificar o paciente imediatamente.

            Sistema Hospitalar - Monitoramento Automático
            Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
        """
        
        return html_content
        
    except Exception as e:
        print(f"Erro ao gerar HTML: {e}", flush=True)
        return f"<html><body><h1>Erro ao gerar email</h1><p>{str(e)}</p><p>Dados: {json.dumps(message)}</p></body></html>"

def send_oci_email(message):
    try:
        print("Enviando notificação OCI...", flush=True)
        
        patient_id = message.get('patient_id')
        patient_data = None
        if patient_id:
            patient_data = get_patient_data(patient_id)
        
        html_content = generate_html_email(message, patient_data)
        
        config = oci.config.from_file()
        client = oci.ons.NotificationDataPlaneClient(config)
        
        message_details = oci.ons.models.MessageDetails(
            body=html_content,
            title=f"[{message.get('type', 'ALERTA')}] Notificação Hospital - Paciente ID: {patient_id}"
        )
        
        response = client.publish_message(
            topic_id=TOPIC_OCID,
            message_details=message_details
        )
        
        print(f"Notificação enviada via OCI. Message ID: {response.data.message_id}", flush=True)
        
    except Exception as e:
        print(f"Erro ao enviar notificação OCI: {e}", flush=True)
        print(f"Tipo do erro: {type(e)}", flush=True)
        print(f"Dados da mensagem: {json.dumps(message, indent=2)}", flush=True)

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
    print("CONSUMER INICIADO", flush=True)
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