"""
Flask Web Application - DDoS Detection Dashboard
Real-time monitoring and detection interface
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import joblib
import json
import numpy as np
from datetime import datetime
from collections import deque
import threading
import time
import random

app = Flask(__name__)
CORS(app)

# Global variables for real-time monitoring
traffic_history = deque(maxlen=100)
detection_history = deque(maxlen=100)
attack_log = []
current_stats = {
    'packets_per_sec': 0,
    'bytes_per_sec': 0,
    'unique_src_ips': 0,
    'status': 'Normal',
    'confidence': 0,
    'alerts': 0
}

# Load ML models
try:
    rf_model = joblib.load('../models/saved_models/random_forest_model.pkl')
    iso_model = joblib.load('../models/saved_models/isolation_forest_model.pkl')
    scaler = joblib.load('../models/saved_models/scaler.pkl')
    
    with open('../models/saved_models/feature_names.json', 'r') as f:
        feature_names = json.load(f)
    
    with open('../models/saved_models/metadata.json', 'r') as f:
        metadata = json.load(f)
    
    print("[✓] Models loaded successfully!")
    print(f"    Accuracy: {metadata['ensemble_accuracy']*100:.2f}%")
    
except Exception as e:
    print(f"[!] Error loading models: {e}")
    print("[!] Please train models first: python models/train_model.py")
    rf_model = None
    iso_model = None
    scaler = None
    feature_names = None
    metadata = {'ensemble_accuracy': 0}

def extract_features(request_data):
    """
    Extract features from incoming traffic
    """
    traffic_type = request_data.get('type', 'normal')
    
    if traffic_type == 'normal':
        features = {
            'packets_per_sec': random.uniform(80, 120),
            'bytes_per_sec': random.uniform(40000, 60000),
            'unique_src_ips': random.randint(1, 10),
            'unique_dst_ports': random.randint(1, 5),
            'avg_packet_size': random.uniform(400, 600),
            'packet_size_variance': random.uniform(80, 120),
            'flow_duration': random.uniform(4, 6),
            'syn_count': random.randint(0, 10),
            'rst_count': random.randint(0, 5),
            'ack_count': random.randint(0, 100),
            'connection_rate': random.uniform(8, 12),
            'src_ip_entropy': random.uniform(2, 4)
        }
    elif traffic_type == 'attack':
        features = {
            'packets_per_sec': random.uniform(8000, 12000),
            'bytes_per_sec': random.uniform(4000000, 6000000),
            'unique_src_ips': random.randint(100, 1000),
            'unique_dst_ports': random.randint(1, 3),
            'avg_packet_size': random.uniform(250, 350),
            'packet_size_variance': random.uniform(40, 60),
            'flow_duration': random.uniform(0.5, 1.5),
            'syn_count': random.randint(1000, 10000),
            'rst_count': random.randint(0, 100),
            'ack_count': random.randint(1000, 10000),
            'connection_rate': random.uniform(900, 1100),
            'src_ip_entropy': random.uniform(5, 8)
        }
    else:  # syn_flood
        features = {
            'packets_per_sec': random.uniform(13000, 17000),
            'bytes_per_sec': random.uniform(900000, 1100000),
            'unique_src_ips': random.randint(500, 2000),
            'unique_dst_ports': random.randint(1, 5),
            'avg_packet_size': random.uniform(55, 65),
            'packet_size_variance': random.uniform(8, 12),
            'flow_duration': random.uniform(0.4, 0.6),
            'syn_count': random.randint(10000, 50000),
            'rst_count': random.randint(0, 50),
            'ack_count': random.randint(0, 100),
            'connection_rate': random.uniform(4500, 5500),
            'src_ip_entropy': random.uniform(6, 9)
        }
    
    return features

def detect_attack(features):
    """
    Use ML models to detect DDoS attacks
    Returns (is_attack, confidence, attack_type)
    """
    if rf_model is None or iso_model is None:
        return False, 0, "Unknown"
    
    # Prepare features
    feature_vector = np.array([features[name] for name in feature_names]).reshape(1, -1)
    feature_scaled = scaler.transform(feature_vector)
    
    # Random Forest prediction
    rf_pred = rf_model.predict(feature_scaled)[0]
    rf_proba = rf_model.predict_proba(feature_scaled)[0]
    
    # Isolation Forest prediction
    iso_pred = iso_model.predict(feature_scaled)[0]
    iso_pred = 1 if iso_pred == -1 else 0
    
    # Ensemble decision
    is_attack = (rf_pred + iso_pred) >= 1
    confidence = rf_proba[1] if is_attack else rf_proba[0]
    
    # Determine attack type based on features
    attack_type = "Normal"
    if is_attack:
        if features['syn_count'] > 5000:
            attack_type = "SYN Flood"
        elif features['packets_per_sec'] > 5000:
            attack_type = "HTTP Flood"
        elif features['bytes_per_sec'] > 5000000:
            attack_type = "UDP Flood"
        else:
            attack_type = "DDoS Attack"
    
    return is_attack, confidence, attack_type

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html', metadata=metadata)

@app.route('/api/traffic', methods=['GET', 'POST'])
def handle_traffic():
    """
    Handle incoming traffic and perform detection
    """
    # Extract features
    request_data = request.args if request.method == 'GET' else request.json or {}
    features = extract_features(request_data)
    
    # Detect attack
    is_attack, confidence, attack_type = detect_attack(features)
    
    # Update statistics
    current_stats['packets_per_sec'] = features['packets_per_sec']
    current_stats['bytes_per_sec'] = features['bytes_per_sec']
    current_stats['unique_src_ips'] = features['unique_src_ips']
    current_stats['status'] = attack_type
    current_stats['confidence'] = confidence * 100
    
    # Log detection
    detection = {
        'timestamp': datetime.now().isoformat(),
        'is_attack': is_attack,
        'attack_type': attack_type,
        'confidence': confidence * 100,
        'packets_per_sec': features['packets_per_sec']
    }
    
    detection_history.append(detection)
    traffic_history.append(features['packets_per_sec'])
    
    # Log attack
    if is_attack:
        current_stats['alerts'] += 1
        attack_log.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': attack_type,
            'confidence': f"{confidence*100:.1f}%",
            'packets_per_sec': f"{features['packets_per_sec']:.0f}"
        })
    
    return jsonify({
        'status': 'ok',
        'is_attack': bool(is_attack),
        'attack_type': attack_type,
        'confidence': float(confidence * 100)
    })

@app.route('/api/stats')
def get_stats():
    """
    Get current system statistics
    """
    return jsonify({
        'current': current_stats,
        'traffic_history': list(traffic_history),
        'detection_history': list(detection_history)[-20:],
        'attack_log': attack_log[-10:],
        'model_accuracy': metadata.get('ensemble_accuracy', 0) * 100
    })

@app.route('/api/reset')
def reset_stats():
    """
    Reset statistics
    """
    global attack_log, current_stats
    traffic_history.clear()
    detection_history.clear()
    attack_log = []
    current_stats['alerts'] = 0
    
    return jsonify({'status': 'reset complete'})

@app.route('/api/model-info')
def model_info():
    """
    Get model information
    """
    return jsonify(metadata)

def simulate_background_traffic():
    """
    Simulate background traffic for demo purposes
    """
    while True:
        # Generate random normal traffic
        features = extract_features({'type': 'normal'})
        is_attack, confidence, attack_type = detect_attack(features)
        
        # Update stats
        detection = {
            'timestamp': datetime.now().isoformat(),
            'is_attack': is_attack,
            'attack_type': attack_type,
            'confidence': confidence * 100,
            'packets_per_sec': features['packets_per_sec']
        }
        
        detection_history.append(detection)
        traffic_history.append(features['packets_per_sec'])
        
        time.sleep(2)  # Update every 2 seconds

if __name__ == '__main__':
    print("="*60)
    print("AI-POWERED DDoS DETECTION SYSTEM")
    print("="*60)
    print(f"Model Accuracy: {metadata.get('ensemble_accuracy', 0)*100:.2f}%")
    print("Starting web server...")
    print("\nAccess dashboard at: http://localhost:5000")
    print("="*60)
    
    # Start background traffic simulation
    # bg_thread = threading.Thread(target=simulate_background_traffic, daemon=True)
    # bg_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
