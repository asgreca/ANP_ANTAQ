#!/usr/bin/env python3
"""
Ponto de Entrada Único do Pipeline ANP e ANTAQ para o Assistente DLCM.

Este script orquestra todas as etapas de ingestão de normas em um único comando:
1. Leis-Base Federais: garante que as 7 leis federais do setor estejam baixadas e consolidadas.
2. Diário Oficial da União (DOU Seção 1): captura as publicações do dia para ANP e ANTAQ.
3. Sumário Executivo: apresenta a contagem de normas salvas em JSON e Markdown.

Como executar:
    python main.py                  # Executa o pipeline completo para a data de hoje
    python main.py --data 28-09-2026 # Executa para uma data específica
    python main.py --apenas-leis    # Atualiza apenas as leis-base federais
"""

import argparse
from datetime import date, datetime
import os
from pathlib import Path
import sys

# Carrega variáveis de ambiente de .env se existir
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(), valor.strip())

from src.config import DATA_DIR, DOU_DIR, LEIS_BASE_DIR
from src.leis_base import executar_coleta_leis_base


def exibir_cabecalho():
    print("=" * 65)
    print(" PIPELINE DE NORMAS ANP E ANTAQ | ASSISTENTE DLCM")
    print(" Extração autônoma, estruturação em JSON/Markdown e monitoramento")
    print("=" * 65)


def executar_pipeline(data_alvo: str = None, forcar_leis: bool = False, modo: str = "auto"):
    exibir_cabecalho()
    inicio = datetime.now()
    data_formatada = data_alvo or date.today().strftime("%d-%m-%Y")
    
    print(f"\n[Data de Referência]: {data_formatada}")
    print(f"[Diretório de Saída]: {DATA_DIR}\n")

    # -------------------------------------------------------------
    # ETAPA 1: Leis-Base Federais Estruturantes (Portal do Planalto)
    # -------------------------------------------------------------
    print("-" * 65)
    print("ETAPA 1: Verificação e Coleta das Leis-Base Federais")
    print("-" * 65)
    leis_coletadas = executar_coleta_leis_base(forcar_atualizacao=forcar_leis)
    print(f"Total de leis-base catalogadas: {len(leis_coletadas)}\n")

    if modo == "leis":
        print("Modo 'apenas leis' finalizado com sucesso.")
        return

    # -------------------------------------------------------------
    # ETAPA 2: Monitoramento Diário do DOU (Seção 1)
    # -------------------------------------------------------------
    print("-" * 65)
    print(f"ETAPA 2: Monitoramento do Diário Oficial da União ({data_formatada})")
    print("-" * 65)

    tem_credenciais_inlabs = bool(os.getenv("INLABS_EMAIL") and os.getenv("INLABS_PASSWORD"))
    atos_dou = {"ANP": [], "ANTAQ": []}

    # Decisão inteligente do motor de extração
    usar_inlabs = (modo == "inlabs") or (modo == "auto" and tem_credenciais_inlabs)

    if usar_inlabs:
        print("Motor Selecionado: INLABS Oficial da Imprensa Nacional (Sem Playwright/XML puro)")
        from src.dou_inlabs import InlabsDouExtractor
        data_obj = datetime.strptime(data_formatada, "%d-%m-%Y").date()
        extrator = InlabsDouExtractor()
        atos_dou = extrator.baixar_edicao_secao_1(data_obj)
    else:
        print("Motor Selecionado: Web Scraping do Portal DOU (in.gov.br)")
        try:
            from src.dou_scraper import executar_scraping_dou
            atos_dou = executar_scraping_dou(data_formatada)
        except RuntimeError as e:
            print(f"\n[ALERTA TÉCNICO]: {e}")
            print("Dica: Em servidores corporativos sem Playwright, configure as variáveis")
            print("INLABS_EMAIL e INLABS_PASSWORD no arquivo .env para download via XML oficial.\n")

    # -------------------------------------------------------------
    # ETAPA 3: Relatório de Conclusão e Estatísticas
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    print(" RESUMO DA EXECUÇÃO DO PIPELINE")
    print("=" * 65)
    total_anp = len(atos_dou.get("ANP", []))
    total_antaq = len(atos_dou.get("ANTAQ", []))
    tempo_total = (datetime.now() - inicio).total_seconds()

    print(f"-> Leis-Base no Acervo:  {len(leis_coletadas)} arquivos em {LEIS_BASE_DIR.relative_to(DATA_DIR.parent)}")
    print(f"-> Atos ANP no DOU:      {total_anp} novos atos capturados")
    print(f"-> Atos ANTAQ no DOU:    {total_antaq} novos atos capturados")
    print(f"-> Pasta dos Atos DOU:   {DOU_DIR.relative_to(DATA_DIR.parent)}/{data_formatada}/")
    print(f"-> Tempo de Execução:    {tempo_total:.1f} segundos")
    print("=" * 65)
    print("Pipeline concluído. A base de dados está pronta para o Assistente DLCM.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Unificado de Normas ANP e ANTAQ")
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="Data no formato DD-MM-AAAA (padrão: data de hoje)"
    )
    parser.add_argument(
        "--atualizar-leis",
        action="store_true",
        help="Força novo download das leis-base federais mesmo se já existirem em cache"
    )
    parser.add_argument(
        "--modo",
        choices=["auto", "inlabs", "web", "leis"],
        default="auto",
        help="Modo de extração do DOU: 'auto' (escolhe melhor método), 'inlabs' (XML sem navegador), 'web' (Playwright) ou 'leis' (somente leis-base)"
    )
    args = parser.parse_args()

    executar_pipeline(
        data_alvo=args.data,
        forcar_leis=args.atualizar_leis,
        modo=args.modo
    )
