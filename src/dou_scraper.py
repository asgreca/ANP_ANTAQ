"""
Módulo de Extração do DOU via Web Scraping (Playwright).

Objetivo:
Acessar a página de leitura diária do DOU em in.gov.br/leiturajornal,
listar as matérias da Seção 1 e baixar os atos normativos da ANP e da ANTAQ.

Quando utilizar:
- Em ambientes e servidores onde Playwright e Chromium sejam permitidos.
- Quando você não tiver uma conta cadastrada no portal INLABS e precisar
  coletar imediatamente pelo navegador automatizado.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date
import json
from pathlib import Path
import re
import sys
import unicodedata

from bs4 import BeautifulSoup
import requests

from src.config import DOU_DIR, DOU_SECTIONS, TERMOS_BUSCA

# Import defensivo do Playwright para não quebrar ambientes sem suporte
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None


def normalizar_texto(texto: str) -> str:
    """Remove acentuação e converte para caixa baixa para comparação segura."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return u"".join([c for c in nfkd if not unicodedata.combining(c)]).lower()


def extrair_texto_visivel(html: str) -> str:
    """Extrai texto legível de um HTML eliminando tags técnicas."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script', 'style', 'noscript', 'meta', 'link']):
            tag.extract()
        return soup.get_text(separator='\n', strip=True)
    except Exception:
        return html


def extrair_dados_ato(html: str, url: str, data_publicacao: str) -> dict:
    """
    Analisa a estrutura padrão de matérias do portal da Imprensa Nacional (in.gov.br).
    Identifica órgão, autoridade signatária, título, ementa e texto completo.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    titulo_elem = soup.find('p', class_='identifica') or soup.find('h1') or soup.find('p', class_='title')
    ementa_elem = soup.find('p', class_='ementa') or soup.find('p', class_='sub-title')
    orgao_elem = soup.find('span', class_='orgao-dou-data') or soup.find('p', class_='orgao')
    autor_elem = soup.find('p', class_='assina')
    cargo_elem = soup.find('p', class_='cargo')
    
    titulo = titulo_elem.get_text(strip=True) if titulo_elem else ""
    ementa = ementa_elem.get_text(strip=True) if ementa_elem else ""
    orgao_texto = orgao_elem.get_text(strip=True) if orgao_elem else ""
    autor = autor_elem.get_text(strip=True) if autor_elem else ""
    cargo = cargo_elem.get_text(strip=True) if cargo_elem else ""
    
    texto_corpo = soup.find('div', class_='texto-dou') or soup.find('div', id='materia') or soup.find('body')
    texto_integral = extrair_texto_visivel(str(texto_corpo)) if texto_corpo else ""
    
    # Classificação da agência por palavras-chave
    texto_busca = normalizar_texto(f"{titulo} {ementa} {orgao_texto} {texto_integral[:2000]}")
    agencia = None
    if any(normalizar_texto(t) in texto_busca for t in TERMOS_BUSCA["ANP"]):
        agencia = "ANP"
    elif any(normalizar_texto(t) in texto_busca for t in TERMOS_BUSCA["ANTAQ"]):
        agencia = "ANTAQ"
        
    # Extração de tipo e número do ato normativo
    tipo_ato = "OUTRO"
    numero_ato = ""
    ano_ato = ""
    
    match_ato = re.search(
        r'(RESOLUÇÃO(?: NORMATIVA)?|PORTARIA|DESPACHO|AUTORIZAÇÃO|DELIBERAÇÃO|ACÓRDÃO|INSTRUÇÃO NORMATIVA|CONSULTA PÚBLICA|AUDIÊNCIA PÚBLICA)(?:[\s\-A-Z]+)?\s+N[º°o]?\s*([\d\.]+)(?:[^\d]+(\d{4}))?',
        f"{titulo} {texto_integral[:500]}",
        re.IGNORECASE
    )
    if match_ato:
        tipo_ato = match_ato.group(1).upper()
        numero_ato = match_ato.group(2).replace('.', '')
        ano_ato = match_ato.group(3) if match_ato.group(3) else (data_publicacao[-4:] if len(data_publicacao) >= 4 else str(date.today().year))
            
    return {
        "url": url,
        "data_publicacao": data_publicacao,
        "agencia": agencia,
        "tipo_ato": tipo_ato,
        "numero": numero_ato,
        "ano": ano_ato,
        "titulo": titulo or f"{tipo_ato} Nº {numero_ato}/{ano_ato}",
        "ementa": ementa,
        "orgao": orgao_texto,
        "autor": autor,
        "cargo": cargo,
        "texto_integral": texto_integral,
        "coletado_em": datetime.now().isoformat(),
    }


def coletar_links_playwright(data_str: str, secao: str = 'dou1') -> list:
    """Navega pelo portal leiturajornal do in.gov.br e extrai os links da edição."""
    if sync_playwright is None:
        raise RuntimeError("Playwright não está instalado neste ambiente. Instale via requirements-dev.txt ou utilize o modo inlabs.")

    url_leitura = f"https://www.in.gov.br/leiturajornal?data={data_str}&secao={secao}"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Acessando portal DOU ({url_leitura}) via navegador...")
    links = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.set_default_timeout(90000)
        
        try:
            page.goto(url_leitura, timeout=120000, wait_until="domcontentloaded")
            page.wait_for_timeout(5000)
            
            # Abre a árvore completa de matérias se o botão estiver visível
            if page.is_visible('#viewMenuOptionTree'):
                page.click('#viewMenuOptionTree')
                page.wait_for_timeout(2000)
                
            elementos = page.query_selector_all('a[data-senna-off="true"]')
            for el in elementos:
                try:
                    href = el.get_attribute('href')
                    if href and href.startswith('/web/dou/'):
                        links.append({
                            "titulo": el.inner_text().strip(),
                            "url": f"https://www.in.gov.br{href}",
                            "data_publicacao": data_str,
                            "secao": secao,
                        })
                except Exception:
                    continue
        finally:
            page.close()
            browser.close()
            
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Links extraídos da Seção {secao}: {len(links)}")
    return links


def executar_scraping_dou(data_str: str, max_workers: int = 8) -> dict:
    """
    Coordena a extração via Playwright com download multithread das matérias.
    Salva JSONs consolidados e arquivos Markdown individuais.
    """
    todos_links = []
    for secao in DOU_SECTIONS:
        todos_links.extend(coletar_links_playwright(data_str, secao=secao))
        
    if not todos_links:
        print(f"Nenhum link encontrado para a data {data_str}.")
        return {"ANP": [], "ANTAQ": []}
        
    print(f"Baixando e analisando {len(todos_links)} links com {max_workers} threads...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    atos = {"ANP": [], "ANTAQ": []}
    
    def processar(item: dict):
        try:
            resp = requests.get(item["url"], headers=headers, timeout=25)
            if resp.status_code == 200:
                dados = extrair_dados_ato(resp.text, item["url"], item["data_publicacao"])
                if dados["agencia"] in ["ANP", "ANTAQ"]:
                    return dados
        except Exception:
            pass
        return None
        
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(processar, link): link for link in todos_links}
        for future in as_completed(futures):
            res = future.result()
            if res and res["agencia"]:
                ag = res["agencia"]
                atos[ag].append(res)
                print(f"   [+] [{ag}] {res['tipo_ato']} Nº {res['numero']} ({res['titulo'][:50]})")
                
    # Salvar resultados
    pasta_data = DOU_DIR / data_str
    pasta_data.mkdir(parents=True, exist_ok=True)
    
    for ag in ["ANP", "ANTAQ"]:
        lista = atos[ag]
        with open(pasta_data / f"{ag.lower()}_atos.json", "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)
            
        for ato in lista:
            slug = f"{ato['tipo_ato'].lower()}_{ato['numero']}_{ato['ano']}".replace(' ', '_')
            with open(pasta_data / f"{ag.lower()}_{slug}.md", "w", encoding="utf-8") as f:
                f.write(f"# {ato['titulo']}\n\n")
                f.write(f"- **Agência**: {ato['agencia']}\n")
                f.write(f"- **Data de Publicação**: {ato['data_publicacao']}\n")
                f.write(f"- **Órgão**: {ato['orgao']}\n")
                f.write(f"- **Autoridade**: {ato['autor']} ({ato['cargo']})\n")
                f.write(f"- **Link Oficial**: [{ato['url']}]({ato['url']})\n\n")
                if ato['ementa']:
                    f.write(f"**Ementa**: {ato['ementa']}\n\n---\n\n")
                f.write(ato['texto_integral'])
                
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scraping web concluído: ANP={len(atos['ANP'])}, ANTAQ={len(atos['ANTAQ'])}")
    return atos
