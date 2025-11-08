"""
Traffic Generator - Simulates Normal and DDoS Attack Traffic
Used for live demo during hackathon presentation
"""

import requests
import time
import random
import threading
from datetime import datetime
import argparse

class TrafficGenerator:
    def __init__(self, target_url="http://localhost:5000"):
        self.target_url = target_url
        self.running = False
        
    def generate_normal_traffic(self, duration=60, rate=10):
        """
        Generate normal traffic patterns
        rate: requests per second
        """
        print(f"[*] Generating NORMAL traffic ({rate} req/s for {duration}s)...")
        end_time = time.time() + duration
        count = 0
        
        while time.time() < end_time and self.running:
            try:
                response = requests.get(
                    f"{self.target_url}/api/traffic",
                    timeout=2,
                    params={'type': 'normal'}
                )
                count += 1
                if count % 100 == 0:
                    print(f"  [Normal] Sent {count} requests")
            except:
                pass
            
            time.sleep(1/rate)
        
        print(f"[✓] Normal traffic complete: {count} requests sent")
    
    def generate_http_flood(self, duration=30, rate=1000):
        """
        Simulate HTTP flood attack
        rate: requests per second
        """
        print(f"[!] Launching HTTP FLOOD attack ({rate} req/s for {duration}s)...")
        end_time = time.time() + duration
        count = 0
        
        def send_requests():
            nonlocal count
            while time.time() < end_time and self.running:
                try:
                    requests.get(
                        f"{self.target_url}/api/traffic",
                        timeout=1,
                        params={'type': 'attack'}
                    )
                    count += 1
                except:
                    pass
        
        # Use multiple threads to simulate high request rate
        threads = []
        for _ in range(10):
            t = threading.Thread(target=send_requests)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # Monitor progress
        while time.time() < end_time and self.running:
            time.sleep(5)
            print(f"  [ATTACK] Sent {count} requests so far...")
        
        self.running = False
        for t in threads:
            t.join(timeout=1)
        
        print(f"[✓] HTTP flood complete: {count} requests sent")
    
    def generate_syn_flood(self, duration=30):
        """
        Simulate SYN flood attack (simplified for demo)
        """
        print(f"[!] Launching SYN FLOOD attack ({duration}s)...")
        end_time = time.time() + duration
        count = 0
        
        while time.time() < end_time and self.running:
            try:
                requests.get(
                    f"{self.target_url}/api/traffic",
                    timeout=1,
                    params={'type': 'syn_flood'}
                )
                count += 1
                if count % 1000 == 0:
                    print(f"  [SYN FLOOD] Sent {count} packets")
            except:
                pass
            
            time.sleep(0.001)  # Very high frequency
        
        print(f"[✓] SYN flood complete: {count} packets sent")

def demo_scenario_1(generator):
    """Demo Scenario 1: Normal Traffic"""
    print("\n" + "="*60)
    print("DEMO SCENARIO 1: NORMAL TRAFFIC")
    print("="*60)
    generator.running = True
    generator.generate_normal_traffic(duration=30, rate=20)
    time.sleep(5)

def demo_scenario_2(generator):
    """Demo Scenario 2: HTTP Flood Attack"""
    print("\n" + "="*60)
    print("DEMO SCENARIO 2: HTTP FLOOD ATTACK")
    print("="*60)
    generator.running = True
    generator.generate_http_flood(duration=20, rate=500)
    time.sleep(5)

def demo_scenario_3(generator):
    """Demo Scenario 3: Mixed Traffic"""
    print("\n" + "="*60)
    print("DEMO SCENARIO 3: MIXED TRAFFIC (Normal then Attack)")
    print("="*60)
    
    # Start with normal traffic
    generator.running = True
    normal_thread = threading.Thread(
        target=generator.generate_normal_traffic,
        args=(20, 10)
    )
    normal_thread.start()
    normal_thread.join()
    
    time.sleep(5)
    
    # Suddenly switch to attack
    print("\n[!] ATTACK DETECTED - Switching to attack traffic!")
    generator.running = True
    generator.generate_http_flood(duration=15, rate=800)

def main():
    parser = argparse.ArgumentParser(description='DDoS Traffic Generator')
    parser.add_argument(
        '--url',
        default='http://localhost:5000',
        help='Target URL (default: http://localhost:5000)'
    )
    parser.add_argument(
        '--scenario',
        type=int,
        choices=[1, 2, 3],
        help='Demo scenario (1=Normal, 2=Attack, 3=Mixed)'
    )
    parser.add_argument(
        '--rate',
        type=int,
        default=100,
        help='Request rate per second (default: 100)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Duration in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    generator = TrafficGenerator(target_url=args.url)
    
    print("="*60)
    print("DDoS TRAFFIC GENERATOR")
    print("="*60)
    print(f"Target: {args.url}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if args.scenario:
        if args.scenario == 1:
            demo_scenario_1(generator)
        elif args.scenario == 2:
            demo_scenario_2(generator)
        elif args.scenario == 3:
            demo_scenario_3(generator)
    else:
        # Interactive mode
        print("\nSelect demo scenario:")
        print("  1. Normal Traffic")
        print("  2. HTTP Flood Attack")
        print("  3. Mixed Traffic (Normal -> Attack)")
        print("  4. Run All Scenarios")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            demo_scenario_1(generator)
        elif choice == '2':
            demo_scenario_2(generator)
        elif choice == '3':
            demo_scenario_3(generator)
        elif choice == '4':
            demo_scenario_1(generator)
            demo_scenario_2(generator)
            demo_scenario_3(generator)
        else:
            print("Invalid choice!")
    
    print("\n" + "="*60)
    print("TRAFFIC GENERATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
