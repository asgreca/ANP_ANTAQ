import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.config import CONSOLIDATED_DIR

try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None


def criar_navegador_stealth(p, user_data_dir: Path = None):
    args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
    ]
    
    if user_data_dir:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=True,
            args=args,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1920, "height": 1080},
        )
    else:
        browser = p.chromium.launch(headless=True, args=args)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1920, "height": 1080},
        )
    return context


def aguardar_desafio_cloudflare(page, max_segundos: int = 15):
    print("   [i] Verificando presenca de desafio Cloudflare...")
    inicio = time.time()
    while time.time() - inicio < max_segundos:
        conteudo = page.content().lower()
        if "just a moment" in conteudo or "verificando se voce e humano" in conteudo or "checking your browser" in conteudo:
            print("   [⏳] Desafio Cloudflare detectado. Aguardando resolucao automatica...")
            page.wait_for_timeout(2000)
        else:
            print("   [✓] Pagina carregada com sucesso (sem bloqueio ativo).")
            return True
    return False


def testar_acesso_anp():
    url = "https://leis.org/anp"
    print(f"\n--- Testando acesso ao acervo consolidado ANP ({url}) ---")
    session_dir = CONSOLIDATED_DIR / ".session_anp"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        context = criar_navegador_stealth(p, user_data_dir=session_dir)
        page = context.new_page()
        if stealth_sync:
            stealth_sync(page)
            
        try:
            print(f"-> Navegando para {url}...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            status_code = response.status if response else "N/A"
            print(f"-> Resposta HTTP inicial: {status_code}")
            
            aguardar_desafio_cloudflare(page)
            
            titulo_pagina = page.title()
            print(f"-> Titulo da pagina carregada: '{titulo_pagina}'")
            
            html = page.content()
            print(f"-> Tamanho do HTML retornado: {len(html)} bytes")
            
            # Verificar se os campos de busca estao visiveis
            campos_busca = page.query_selector_all("input, form, a")
            print(f"-> Elementos interativos encontrados na pagina: {len(campos_busca)}")
            
            # Salvar amostra
            amostra_path = CONSOLIDATED_DIR / "amostra_anp_leis_org.html"
            with open(amostra_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"-> Amostra gravada em {amostra_path.name}")
            
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao acessar {url}: {e}", file=sys.stderr)
            return False
        finally:
            page.close()
            context.close()


def testar_acesso_antaq():
    url = "https://sophia.antaq.gov.br"
    print(f"\n--- Testando acesso ao acervo Sophia ANTAQ ({url}) ---")
    session_dir = CONSOLIDATED_DIR / ".session_antaq"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        context = criar_navegador_stealth(p, user_data_dir=session_dir)
        page = context.new_page()
        if stealth_sync:
            stealth_sync(page)
            
        try:
            print(f"-> Navegando para {url}...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            status_code = response.status if response else "N/A"
            print(f"-> Resposta HTTP inicial: {status_code}")
            
            aguardar_desafio_cloudflare(page)
            
            titulo_pagina = page.title()
            print(f"-> Titulo da pagina carregada: '{titulo_pagina}'")
            
            html = page.content()
            print(f"-> Tamanho do HTML retornado: {len(html)} bytes")
            
            amostra_path = CONSOLIDATED_DIR / "amostra_antaq_sophia.html"
            with open(amostra_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"-> Amostra gravada em {amostra_path.name}")
            
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao acessar {url}: {e}", file=sys.stderr)
            return False
        finally:
            page.close()
            context.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrator de Normas Consolidadas (ANP e ANTAQ)")
    parser.add_argument("--alvo", choices=["anp", "antaq", "ambos"], default="ambos", help="Agencia alvo para teste ou extracao")
    args = parser.parse_args()
    
    if args.alvo in ["anp", "ambos"]:
        testar_acesso_anp()
    if args.alvo in ["antaq", "ambos"]:
        testar_acesso_antaq()
