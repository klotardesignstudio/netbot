import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import setup_logger, NetBotLoggerAdapter
import time

# Setup logger
logger = setup_logger()

def test_system_logs():
    print("\n--- Testing System Logs ---")
    sys_logger = NetBotLoggerAdapter(logger, {'status_code': 'SYSTEM'})
    sys_logger.info("INICIANDO CICLO #128")
    
    stats_logger = NetBotLoggerAdapter(logger, {'status_code': 'FINANCE'})
    stats_logger.info("Limites Diários: Twitter (5/15) | Dev.to (2/10)")

def test_twitter_flow():
    print("\n--- Testing Twitter Flow ---")
    # Simulate a Twitter Client
    t_logger = NetBotLoggerAdapter(logger, {'network': 'Twitter'})
    
    # Stage A: Collector
    t_logger.info("FOUND: Post 189123 via #rustlang", stage='A')
    time.sleep(0.1)
    
    # Stage B: Filter (Warning)
    t_logger.warning("SKIP: Engajamento baixo (Likes: 2, Replies: 0)", stage='B')
    time.sleep(0.1)
    
    # Stage C: Brain (Complex multiline)
    reasoning = """Analisando post...
Reasoning: "Post técnico sobre Rust com alto engajamento. Oportunidade de reforçar autoridade em memória segura."
Confidence: 89%"""
    t_logger.info(reasoning, stage='C')
    time.sleep(0.1)
    
    # Stage D: Action
    t_logger.info("SUCCESS: Comentário publicado com sucesso.", stage='D')

def test_error_handling():
    print("\n--- Testing Error Handling ---")
    err_logger = NetBotLoggerAdapter(logger, {'status_code': 'ERROR'})
    try:
        raise ValueError("Simulated Connection Error")
    except Exception as e:
        err_logger.error(f"Falha crítica no login: {e}")

if __name__ == "__main__":
    test_system_logs()
    test_twitter_flow()
    test_error_handling()
