"""
Módulo de Extração do DOU via INLABS (Imprensa Nacional).

Objetivo:
Baixar e processar os atos diários do Diário Oficial da União (Seção 1)
diretamente do serviço oficial de Dados Abertos da Imprensa Nacional (INLABS).

Por que este módulo é ideal para servidores corporativos:
1. NÃO utiliza Playwright, Chromium, Selenium ou qualquer navegador headless.
2. Utiliza apenas requisições HTTP seguras (requests) e parsing de XML nativo.
3. Não sofre bloqueios de Cloudflare ou proteção antibot porque é um serviço
   oficial criado pela Imprensa Nacional para download automatizado em lote.
4. O pacote diário chega em arquivo .zip contendo os XMLs individuais de cada ato.
"""

from datetime import datetime, date
import io
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import requests

from src.config import DOU_DIR, TERMOS_BUSCA


def normalizar_texto(texto: str) -> str:
    """Remove acentos e converte para minúsculas para comparações seguras."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize('NFKD', texto)
    return u"".join([c for c in nfkd if not unicodedata.combining(c)]).lower()


class InlabsDouExtractor:
    """
    Cliente para autenticação e download de pacotes XML no portal INLABS.
    URL oficial: https://inlabs.in.gov.br
    """
    URL_LOGIN = "https://inlabs.in.gov.br/logar.php"
    URL_DOWNLOAD = "https://inlabs.in.gov.br/index.php?p="

    def __init__(self, email: str = None, password: str = None):
        self.email = email or os.getenv("INLABS_EMAIL")
        self.password = password or os.getenv("INLABS_PASSWORD")
        self.session = requests.Session()
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def autenticar(self) -> bool:
        """Realiza login com a conta gratuita cadastrada no INLABS."""
        if not self.email or not self.password:
            print("   [aviso] Credenciais INLABS não informadas (defina INLABS_EMAIL e INLABS_PASSWORD no .env).")
            return False

        payload = {"email": self.email, "password": self.password}
        try:
            resp = self.session.post(self.URL_LOGIN, data=payload, headers=self.headers, timeout=25)
            cookie = self.session.cookies.get("inlabs_session_cookie")
            if cookie:
                print("   [ok] Autenticado com sucesso no portal INLABS.")
                return True
            else:
                print("   [alerta] Credenciais inválidas no INLABS.")
                return False
        except Exception as e:
            print(f"   [erro] Conexão com INLABS falhou: {e}", file=sys.stderr)
            return False

    def baixar_edicao_secao_1(self, data_alvo: date = None) -> dict:
        """
        Baixa o pacote ZIP da Seção 1 (DO1) do dia e filtra atos de ANP e ANTAQ.
        """
        if data_alvo is None:
            data_alvo = date.today()

        data_iso = data_alvo.strftime("%Y-%m-%d")
        data_formatada = data_alvo.strftime("%d-%m-%Y")
        
        cookie = self.session.cookies.get("inlabs_session_cookie")
        if not cookie:
            if not self.autenticar():
                return {"ANP": [], "ANTAQ": []}
            cookie = self.session.cookies.get("inlabs_session_cookie")

        nome_arquivo = f"{data_iso}-DO1.zip"
        url_arquivo = f"{self.URL_DOWNLOAD}{data_iso}&dl={nome_arquivo}"
        cabecalho = {
            "Cookie": f"inlabs_session_cookie={cookie}",
            "origem": "736372697074"
        }

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Baixando Seção 1 do DOU ({nome_arquivo}) via INLABS...")
        resp = self.session.get(url_arquivo, headers=cabecalho, timeout=60)
        
        if resp.status_code == 404:
            print(f"   [alerta] A edição {nome_arquivo} ainda não foi disponibilizada pelo INLABS.")
            return {"ANP": [], "ANTAQ": []}
        elif resp.status_code != 200:
            print(f"   [erro] Resposta inesperada do INLABS: código HTTP {resp.status_code}")
            return {"ANP": [], "ANTAQ": []}

        print(f"   [ok] Pacote XML recebido ({len(resp.content):,} bytes). Processando matérias...")
        return self._processar_zip(resp.content, data_formatada)

    def _processar_zip(self, zip_bytes: bytes, data_str: str) -> dict:
        """
        Descompacta o arquivo em memória e lê cada XML sem tocar o disco.
        Filtra os nós com termos da ANP e da ANTAQ e salva os atos correspondentes.
        """
        atos_encontrados = {"ANP": [], "ANTAQ": []}
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            arquivos_xml = [f for f in z.namelist() if f.endswith('.xml')]
            print(f"   [info] Total de publicações na Seção 1 hoje: {len(arquivos_xml)} atos.")
            
            for nome_xml in arquivos_xml:
                try:
                    conteudo = z.read(nome_xml)
                    root = ET.fromstring(conteudo)
                    
                    titulo = root.findtext('.//artigo/titulo') or root.findtext('.//titulo') or ""
                    identifica = root.findtext('.//identifica') or ""
                    ementa = root.findtext('.//ementa') or ""
                    orgao = root.findtext('.//orgao') or ""
                    texto = root.findtext('.//texto') or ""
                    autor = root.findtext('.//assina') or ""
                    cargo = root.findtext('.//cargo') or ""
                    
                    if not texto:
                        texto = " ".join([elem.text for elem in root.iter() if elem.text])
                        
                    texto_busca = normalizar_texto(f"{titulo} {identifica} {ementa} {orgao} {texto[:2000]}")
                    
                    agencia = None
                    if any(normalizar_texto(t) in texto_busca for t in TERMOS_BUSCA["ANP"]):
                        agencia = "ANP"
                    elif any(normalizar_texto(t) in texto_busca for t in TERMOS_BUSCA["ANTAQ"]):
                        agencia = "ANTAQ"
                        
                    if agencia:
                        match_ato = re.search(
                            r'(RESOLUÇÃO(?: NORMATIVA)?|PORTARIA|DESPACHO|AUTORIZAÇÃO|DELIBERAÇÃO|ACÓRDÃO|INSTRUÇÃO NORMATIVA)(?:[\s\-A-Z]+)?\s+N[º°o]?\s*([\d\.]+)',
                            f"{identifica} {titulo}",
                            re.IGNORECASE
                        )
                        tipo_ato = match_ato.group(1).upper() if match_ato else "OUTRO"
                        numero_ato = match_ato.group(2).replace('.', '') if match_ato else ""
                        
                        registro = {
                            "agencia": agencia,
                            "tipo_ato": tipo_ato,
                            "numero": numero_ato,
                            "ano": data_str[-4:],
                            "titulo": identifica or titulo or f"{tipo_ato} Nº {numero_ato}",
                            "ementa": ementa,
                            "orgao": orgao,
                            "autor": autor,
                            "cargo": cargo,
                            "data_publicacao": data_str,
                            "texto_integral": texto,
                            "arquivo_origem": nome_xml,
                            "coletado_em": datetime.now().isoformat(),
                        }
                        atos_encontrados[agencia].append(registro)
                        print(f"      [+] [{agencia}] {registro['tipo_ato']} Nº {registro['numero']} ({registro['titulo'][:50]})")
                except Exception:
                    continue

        # Salva os atos encontrados no diretório de data
        pasta_destino = DOU_DIR / data_str
        pasta_destino.mkdir(parents=True, exist_ok=True)
        
        for ag in ["ANP", "ANTAQ"]:
            with open(pasta_destino / f"{ag.lower()}_inlabs_atos.json", "w", encoding="utf-8") as f:
                json.dump(atos_encontrados[ag], f, ensure_ascii=False, indent=2)
                
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Concluído via INLABS: ANP={len(atos_encontrados['ANP'])}, ANTAQ={len(atos_encontrados['ANTAQ'])}")
        return atos_encontrados
