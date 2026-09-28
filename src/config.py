"""
Configurações Globais do Pipeline de Normas da ANP e ANTAQ.

Este arquivo centraliza todos os caminhos de pastas, palavras-chave de busca
para o Diário Oficial da União (DOU) e as URLs oficiais das leis-base federais.
"""

from pathlib import Path

# Raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios de armazenamento de dados
DATA_DIR = BASE_DIR / "data"
DOU_DIR = DATA_DIR / "dou"
LEIS_BASE_DIR = DATA_DIR / "leis_base"
CONSOLIDATED_DIR = DATA_DIR / "resolucoes_consolidadas"
LOGS_DIR = BASE_DIR / "logs"

# Cria os diretórios necessários automaticamente se não existirem
for pasta in [DATA_DIR, DOU_DIR, LEIS_BASE_DIR, CONSOLIDATED_DIR, LOGS_DIR]:
    pasta.mkdir(parents=True, exist_ok=True)

# Seções monitoradas no Diário Oficial da União
# dou1: Seção 1 (onde são publicados atos normativos, resoluções e portarias)
DOU_SECTIONS = ["dou1"]

# Dicionário de termos para filtragem inteligente de atos da ANP e ANTAQ
# Inclui nomes formais, siglas e os principais tipos de atos emitidos
TERMOS_BUSCA = {
    "ANP": [
        "Agência Nacional do Petróleo, Gás Natural e Biocombustíveis",
        "Agência Nacional do Petróleo",
        "ANP",
        "Resolução ANP",
        "Portaria ANP",
        "Despacho ANP",
        "Autorização ANP",
    ],
    "ANTAQ": [
        "Agência Nacional de Transportes Aquaviários",
        "ANTAQ",
        "Resolução ANTAQ",
        "Resolução Normativa ANTAQ",
        "Portaria ANTAQ",
        "Acórdão ANTAQ",
        "Deliberação ANTAQ",
    ],
}

# Ministérios supervisores no cabeçalho do DOU
MINISTERIOS = [
    "MINISTÉRIO DE MINAS E ENERGIA",
    "MINISTÉRIO DOS PORTOS E AEROPORTOS",
    "MINISTÉRIO DA INFRAESTRUTURA",
]

# Catálogo oficial das 7 Leis-Base Federais estruturantes no Portal do Planalto
LEIS_BASE = {
    "lei_9478_1997_lei_do_petroleo": {
        "numero": "9478",
        "ano": 1997,
        "titulo": "Lei nº 9.478/1997 (Lei do Petróleo, cria a ANP)",
        "agencia": "ANP",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l9478.htm",
    },
    "lei_12351_2010_partilha_producao": {
        "numero": "12351",
        "ano": 2010,
        "titulo": "Lei nº 12.351/2010 (Regime de Partilha de Produção no Pré-Sal)",
        "agencia": "ANP",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12351.htm",
    },
    "lei_14134_2021_nova_lei_do_gas": {
        "numero": "14134",
        "ano": 2021,
        "titulo": "Lei nº 14.134/2021 (Nova Lei do Gás)",
        "agencia": "ANP",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14134.htm",
    },
    "lei_9847_1999_fiscalizacao_abastecimento": {
        "numero": "9847",
        "ano": 1999,
        "titulo": "Lei nº 9.847/1999 (Fiscalização do Abastecimento Nacional de Combustíveis)",
        "agencia": "ANP",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l9847.htm",
    },
    "lei_10233_2001_criacao_antaq_antt": {
        "numero": "10233",
        "ano": 2001,
        "titulo": "Lei nº 10.233/2001 (Cria a ANTAQ e a ANTT)",
        "agencia": "ANTAQ",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10233.htm",
    },
    "lei_12815_2013_lei_dos_portos": {
        "numero": "12815",
        "ano": 2013,
        "titulo": "Lei nº 12.815/2013 (Lei dos Portos)",
        "agencia": "ANTAQ",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12815.htm",
    },
    "lei_13848_2019_lei_geral_agencias": {
        "numero": "13848",
        "ano": 2019,
        "titulo": "Lei nº 13.848/2019 (Lei Geral das Agências Reguladoras)",
        "agencia": "GERAL",
        "url": "https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/lei/l13848.htm",
    },
}
