db = db.getSiblingDB('hospital');

db.monitoring.insertMany([
  {
    patient_id: "1",
    heart_rate: 75,
    blood_pressure: "120/80",
    timestamp: new Date()
  },
  {
    patient_id: "2", 
    heart_rate: 82,
    blood_pressure: "110/70",
    timestamp: new Date()
  },
  {
    patient_id: "3",
    heart_rate: 68,
    blood_pressure: "125/85",
    timestamp: new Date()
  },
  {
    patient_id: "4",
    heart_rate: 95,
    blood_pressure: "140/90",
    timestamp: new Date()
  },
  {
    patient_id: "5",
    heart_rate: 72,
    blood_pressure: "115/75",
    timestamp: new Date()
  }
]);