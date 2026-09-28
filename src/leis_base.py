"""
Módulo de Coleta das Leis-Base Federais (Planalto).

Objetivo:
Baixar as leis que criaram e regem a ANP e a ANTAQ diretamente do Portal da
Legislação do Planalto (planalto.gov.br/ccivil_03).

Por que este módulo é feito assim:
1. As leis federais têm texto consolidado de acesso público, sem antibot ou captcha.
2. O servidor do Planalto utiliza codificação antiga (ISO-8859-1 / Windows-1252);
   por isso forçamos o charset correto para não quebrar a acentuação jurídica.
3. Não há necessidade de navegador headless (Playwright); tudo roda com requests puro.
"""

from datetime import datetime
import json
from pathlib import Path
import re
import sys

from bs4 import BeautifulSoup
import requests

from src.config import LEIS_BASE, LEIS_BASE_DIR


def limpar_espacos(texto: str) -> str:
    """Normaliza quebras de linha e múltiplos espaços consecutivos."""
    return re.sub(r'\s+', ' ', texto).strip()


def extrair_lei_planalto(url: str) -> dict:
    """
    Baixa uma página de lei do Planalto e devolve o texto estruturado.
    
    Passo a passo:
    1. Faz a requisição HTTP com cabeçalhos padrão de navegador.
    2. Decodifica em Windows-1252 para preservar todos os acentos da língua portuguesa.
    3. Remove scripts, estilos e tags visuais desnecessárias.
    4. Identifica a ementa oficial e os artigos da norma.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    resposta = requests.get(url, headers=headers, timeout=30)
    resposta.raise_for_status()
    
    # Tratamento específico para páginas antigas do Planalto
    if resposta.encoding and resposta.encoding.lower() == 'iso-8859-1':
        resposta.encoding = 'windows-1252'
    
    soup = BeautifulSoup(resposta.content, 'html.parser', from_encoding='windows-1252')
    
    # Limpeza de elementos técnicos que poluem o texto
    for elem in soup(['script', 'style', 'noscript', 'meta', 'link']):
        elem.extract()
        
    corpo = soup.find('body') or soup
    
    linhas = []
    for tag in corpo.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'blockquote']):
        texto = limpar_espacos(tag.get_text())
        if texto:
            linhas.append(texto)
            
    texto_completo = "\n\n".join(linhas)
    
    # Localiza a ementa (resumo do objetivo da lei nos primeiros parágrafos)
    ementa = ""
    for linha in linhas[:10]:
        if any(verbo in linha.lower() for verbo in ["dispõe sobre", "institui", "estabelece", "altera"]):
            ementa = linha
            break

    return {
        "ementa": ementa,
        "texto_integral": texto_completo,
        "total_caracteres": len(texto_completo),
        "total_paragrafos": len(linhas),
    }


def executar_coleta_leis_base(forcar_atualizacao: bool = False) -> list:
    """
    Orquestra o download de todas as leis-base federais catalogadas.
    Salva uma versão em JSON (metadados estruturados) e uma em Markdown
    (texto limpo pronto para alimentar o assistente de IA).
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando download das Leis-Base do Planalto...")
    
    documentos = []
    for chave, info in LEIS_BASE.items():
        arquivo_json = LEIS_BASE_DIR / f"{chave}.json"
        arquivo_md = LEIS_BASE_DIR / f"{chave}.md"
        
        # Se o arquivo já existe e o usuário não pediu para forçar, aproveita o cache
        if arquivo_json.exists() and not forcar_atualizacao:
            print(f"   [cache] {info['titulo']} já disponível localmente.")
            with open(arquivo_json, 'r', encoding='utf-8') as f:
                documentos.append(json.load(f))
            continue
            
        print(f"   [download] Baixando {info['titulo']}...")
        try:
            dados = extrair_lei_planalto(info['url'])
            
            registro = {
                "id": chave,
                "numero": info["numero"],
                "ano": info["ano"],
                "titulo": info["titulo"],
                "agencia": info["agencia"],
                "url_fonte": info["url"],
                "coletado_em": datetime.now().isoformat(),
                "ementa": dados["ementa"],
                "texto_integral": dados["texto_integral"],
                "total_caracteres": dados["total_caracteres"],
                "total_paragrafos": dados["total_paragrafos"],
            }
            
            # Grava JSON estruturado
            with open(arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(registro, f, ensure_ascii=False, indent=2)
                
            # Grava Markdown para leitura humana e indexação vetorial no RAG
            with open(arquivo_md, 'w', encoding='utf-8') as f:
                f.write(f"# {info['titulo']}\n\n")
                f.write(f"- **Agência de Referência**: {info['agencia']}\n")
                f.write(f"- **Fonte Oficial**: [{info['url']}]({info['url']})\n")
                f.write(f"- **Data da Coleta**: {registro['coletado_em']}\n\n")
                if dados["ementa"]:
                    f.write(f"**Ementa**: {dados['ementa']}\n\n---\n\n")
                f.write(dados["texto_integral"])
                
            print(f"   [ok] Salvo: {arquivo_json.name} ({dados['total_caracteres']:,} caracteres)")
            documentos.append(registro)
        except Exception as e:
            print(f"   [erro] Falha ao baixar {info['titulo']}: {e}", file=sys.stderr)
            
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Leis-base concluídas: {len(documentos)} leis no acervo.")
    return documentos


if __name__ == "__main__":
    forcar = "--force" in sys.argv or "--atualizar" in sys.argv
    executar_coleta_leis_base(forcar_atualizacao=forcar)
