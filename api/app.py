from flask import Flask, request, jsonify
import mysql.connector
import pymongo
import pika
import json
import os
import datetime
import time
import oci

app = Flask(__name__)

VAULT_TOKEN_OCID = "ocid1.vaultsecret.oc1.sa-saopaulo-1.amaaaaaaskvkz5qadezpfegvjjks727ryr6semyn224n7rmgun7gmgoyl7nq"

def get_token_from_vault(secret_ocid):
    config = oci.config.from_file()  # Pega configuração padrão ~/.oci/config
    secrets_client = oci.secrets.SecretsClient(config)
    response = secrets_client.get_secret_bundle(secret_ocid)
    encoded_content = response.data.secret_bundle_content.content

    if isinstance(encoded_content, bytes):
        token = encoded_content.decode('utf-8').strip()
    else:
        token = encoded_content.strip()
        return token

API_TOKEN = get_token_from_vault(VAULT_TOKEN_OCID)

@app.before_request
def verificar_token():
    if request.endpoint in ['health']:
        return None
    
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f"Bearer {API_TOKEN}":
        return jsonify({"erro": "Não autorizado"}), 401

def wait_for_services():
    print("Aguardando conexão com os serviços")
    
    while True:
        try:
            conn = mysql.connector.connect(
                host=os.environ.get('DB_HOST', 'mysql'),
                user="root",
                password="securepassword"
            )
            conn.close()
            print("MySQL conectado")
            break
        except:
            print("Aguardando MySQL")
            time.sleep(3)
    
    while True:
        try:
            client = pymongo.MongoClient(f"mongodb://admin:securepassword@{os.environ.get('MONGO_HOST', 'mongodb')}:27017/")
            client.server_info()
            print("MongoDB conectado")
            break
        except:
            print("Aguardando MongoDB")
            time.sleep(3)
    
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=os.environ.get('RABBITMQ_HOST', 'rabbitmq'))
            )
            connection.close()
            print("RabbitMQ conectado")
            break
        except:
            print("Aguardando RabbitMQ")
            time.sleep(3)

def get_mysql_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'mysql'),
        user="root",
        password="securepassword",
        database="hospital_db"
    )

def get_mongodb():
    client = pymongo.MongoClient(f"mongodb://admin:securepassword@{os.environ.get('MONGO_HOST', 'mongodb')}:27017/")
    return client["hospital"]

def send_notification(message):
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.environ.get('RABBITMQ_HOST', 'rabbitmq'))
        )
        channel = connection.channel()
        channel.queue_declare(queue='notifications', durable=True)
        channel.basic_publish(
            exchange='',
            routing_key='notifications',
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f"Notificação enviada: {message['type']}")
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "OK",
        "timestamp": datetime.datetime.now().isoformat(),
        "services": ["MySQL", "MongoDB", "RabbitMQ"]
    })

@app.route('/doctors', methods=['GET'])
def get_doctors():
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, specialty, phone FROM doctors")
        doctors = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(doctors)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/patients', methods=['GET'])
def get_patients():
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                p.id, p.name, p.age, p.gender, p.phone, p.address,
                d.name as doctor_name, d.specialty as doctor_specialty
            FROM patients p
            LEFT JOIN doctors d ON p.doctor_id = d.id
        """)
        patients = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(patients)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/doctors/<doctor_id>/patients', methods=['GET'])
def get_doctor_patients(doctor_id):
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT name, specialty FROM doctors WHERE id = %s", (doctor_id,))
        doctor = cursor.fetchone()
        
        if not doctor:
            return jsonify({"error": "Médico não encontrado"}), 404
        
        cursor.execute("""
            SELECT id, name, age, gender, phone, address 
            FROM patients 
            WHERE doctor_id = %s
        """, (doctor_id,))
        patients = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "doctor": doctor,
            "patients": patients,
            "total_patients": len(patients)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/monitor', methods=['POST'])
def receive_monitor_data():
    try:
        data = request.json
        patient_id = data.get('patient_id')
        heart_rate = data.get('heart_rate', 0)
        blood_pressure = data.get('blood_pressure', '')
        
        if not patient_id:
            return jsonify({"error": "patient_id obrigatório"}), 400
        
        data['timestamp'] = datetime.datetime.now()
        
        mongodb = get_mongodb()
        mongodb.monitoring.insert_one(data)
        
        is_critical = heart_rate > 100 or heart_rate < 60
        
        if is_critical:
            send_notification({
                'type': 'ALERTA_CRITICO',
                'patient_id': patient_id,
                'heart_rate': heart_rate,
                'blood_pressure': blood_pressure,
                'timestamp': datetime.datetime.now().isoformat()
            })
        
        return jsonify({
            "status": "recebido",
            "patient_id": patient_id,
            "critico": is_critical
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/patients/<patient_id>', methods=['GET'])
def get_patient_data(patient_id):
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                p.*, 
                d.name as doctor_name, 
                d.specialty as doctor_specialty,
                d.phone as doctor_phone
            FROM patients p
            LEFT JOIN doctors d ON p.doctor_id = d.id
            WHERE p.id = %s
        """, (patient_id,))
        patient = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not patient:
            return jsonify({"error": "Paciente não encontrado"}), 404
        
        for key, value in patient.items():
            if isinstance(value, (datetime.date, datetime.datetime)):
                patient[key] = value.isoformat()
        
        mongodb = get_mongodb()
        monitoring = list(mongodb.monitoring.find(
            {"patient_id": str(patient_id)},
            {"_id": 0}
        ).sort("timestamp", -1).limit(5))
        
        for record in monitoring:
            if 'timestamp' in record:
                record['timestamp'] = record['timestamp'].isoformat()
        
        patient["ultimos_monitoramentos"] = monitoring
        
        return jsonify(patient)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Iniciando Sistema Hospitalar")
    wait_for_services()
    print("Todos os serviços conectados. API rodando na porta 5000")
    app.run(host='0.0.0.0', port=5000, debug=True)